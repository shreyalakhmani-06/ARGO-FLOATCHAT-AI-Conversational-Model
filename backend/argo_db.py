import os
from datetime import timedelta
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)

COL = {"TEMP": "temp", "PSAL": "psal", "PRES": "pres"}


@lru_cache(maxsize=1)
def known_floats():
    with engine.connect() as c:
        return {r[0] for r in c.execute(text("SELECT platform_number FROM argo_floats"))}


def _where(f, need=()):
    """Build WHERE from VALIDATED filters. Values are bound parameters; no text from the
    user or the LLM is ever pasted into the SQL string."""
    sql, p = ["pres IS NOT NULL", "pres_qc IN ('1','2')"], {}
    if f["platform_numbers"]:
        sql.append("platform_number = ANY(:ids)")
        p["ids"] = f["platform_numbers"]
    for key, col, op in (("lat_min", "latitude", ">="), ("lat_max", "latitude", "<="),
                         ("lon_min", "longitude", ">="), ("lon_max", "longitude", "<="),
                         ("depth_min", "pres", ">="), ("depth_max", "pres", "<=")):
        if f[key] is not None:
            sql.append(f"{col} {op} :{key}")
            p[key] = f[key]
    if f["date_start"] is not None:
        sql.append("juld >= :date_start")
        p["date_start"] = f["date_start"]
    if f["date_end"] is not None:
        sql.append("juld < :date_end_excl")          # include the whole last day
        p["date_end_excl"] = f["date_end"] + timedelta(days=1)
    for prm in need:                                  # only good-quality readings (QC 1 or 2)
        c = COL[prm]
        sql.append(f"{c} IS NOT NULL AND {c}_qc IN ('1','2')")
    return " AND ".join(sql), p


def fetch_rows(f, need, limit=30000):
    where, p = _where(f, need)
    q = (f"SELECT platform_number, cycle_number, juld, latitude, longitude, pres, temp, psal "
         f"FROM argo_measurements WHERE {where} ORDER BY platform_number, juld, pres LIMIT :limit")
    with engine.connect() as c:
        return [dict(r._mapping) for r in c.execute(text(q), {**p, "limit": limit})]


def closest_depth(f, need, target, k=3):
    where, p = _where(f, need)
    q = (f"SELECT platform_number, cycle_number, juld, latitude, longitude, pres, temp, psal "
         f"FROM argo_measurements WHERE {where} ORDER BY ABS(pres - :target) LIMIT :k")
    with engine.connect() as c:
        return [dict(r._mapping) for r in c.execute(text(q), {**p, "target": target, "k": k})]


def fetch_floats(f, limit=25):
    where, p = _where(f)
    q = (f"SELECT platform_number, COUNT(DISTINCT cycle_number) AS profiles, "
         f"MIN(juld) AS first, MAX(juld) AS last, "
         f"ROUND(CAST(AVG(latitude) AS numeric), 1) AS lat, "
         f"ROUND(CAST(AVG(longitude) AS numeric), 1) AS lon "
         f"FROM argo_measurements WHERE {where} GROUP BY platform_number "
         f"ORDER BY platform_number LIMIT :limit")
    with engine.connect() as c:
        return [dict(r._mapping) for r in c.execute(text(q), {**p, "limit": limit})]
    
def aggregate(f, need):
    """Compute stats over ALL matching rows inside Postgres (no row cap)."""
    where, p = _where(f, need)
    sels = ["COUNT(*) AS n", "COUNT(DISTINCT platform_number) AS floats",
            "MIN(juld) AS t0", "MAX(juld) AS t1"]
    for prm in need:
        c = COL[prm]
        sels += [f"AVG({c}) AS {c}_mean", f"MIN({c}) AS {c}_min", f"MAX({c}) AS {c}_max"]
    q = f"SELECT {', '.join(sels)} FROM argo_measurements WHERE {where}"
    with engine.connect() as c:
        return dict(c.execute(text(q), p).one()._mapping)