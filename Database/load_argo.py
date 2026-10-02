import glob, io, os
from getpass import getpass

import numpy as np
import pandas as pd
import psycopg2
import xarray as xr

PROFILE_DIR = os.path.join("data", "profiles")
META_DIR = os.path.join("data", "metadata")

SCHEMA = """
DROP TABLE IF EXISTS argo_measurements;
DROP TABLE IF EXISTS argo_floats;

CREATE TABLE argo_floats (
    platform_number  TEXT PRIMARY KEY,
    project_name     TEXT,
    pi_name          TEXT,
    platform_type    TEXT,
    data_centre      TEXT,
    launch_date      TIMESTAMP,
    launch_latitude  DOUBLE PRECISION,
    launch_longitude DOUBLE PRECISION,
    n_profiles       INTEGER,
    first_profile    TIMESTAMP,
    last_profile     TIMESTAMP,
    lat_min DOUBLE PRECISION, lat_max DOUBLE PRECISION,
    lon_min DOUBLE PRECISION, lon_max DOUBLE PRECISION
);

CREATE TABLE argo_measurements (
    id              BIGSERIAL PRIMARY KEY,
    platform_number TEXT REFERENCES argo_floats(platform_number),
    cycle_number    INTEGER,
    juld            TIMESTAMP,
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION,
    pres            DOUBLE PRECISION,
    temp            DOUBLE PRECISION,
    psal            DOUBLE PRECISION,
    pres_qc         CHAR(1),
    temp_qc         CHAR(1),
    psal_qc         CHAR(1)
);
"""

COLS = ["platform_number", "cycle_number", "juld", "latitude", "longitude",
        "pres", "temp", "psal", "pres_qc", "temp_qc", "psal_qc"]


def text(var):
    x = var.values
    x = x.item() if x.ndim == 0 else x.ravel()[0]
    return (x.decode("ascii", "ignore") if isinstance(x, bytes) else str(x)).strip()


def get(ds, name):
    return text(ds[name]) if name in ds else None


def num(x):
    v = float(x)
    return None if np.isnan(v) else v


def flags(ds, name, shape):
    """QC flags as 1-char strings; anything that isn't a digit becomes empty (NULL)."""
    if name not in ds:
        return np.full(shape, "", dtype=object).ravel()
    out = []
    for x in ds[name].values.ravel():
        s = (x.decode("ascii", "ignore") if isinstance(x, bytes) else str(x)).strip()
        out.append(s if s.isdigit() else "")
    return np.array(out, dtype=object)


def load_profiles(path, platform):
    d = xr.open_dataset(path)
    n_prof, n_lev = d.sizes["N_PROF"], d.sizes["N_LEVELS"]
    shape = (n_prof, n_lev)

    def level(name):
        if name in d:
            return np.round(d[name].values.astype("float64"), 3).ravel()
        return np.full(n_prof * n_lev, np.nan)

    juld = pd.Series(pd.to_datetime(d["JULD"].values)).dt.floor("s").values
    df = pd.DataFrame({
        "platform_number": platform,
        "cycle_number": np.repeat(d["CYCLE_NUMBER"].values.astype("float64"), n_lev),
        "juld": np.repeat(juld, n_lev),
        "latitude": np.repeat(np.round(d["LATITUDE"].values.astype("float64"), 3), n_lev),
        "longitude": np.repeat(np.round(d["LONGITUDE"].values.astype("float64"), 3), n_lev),
        "pres": level("PRES"), "temp": level("TEMP"), "psal": level("PSAL"),
        "pres_qc": flags(d, "PRES_QC", shape),
        "temp_qc": flags(d, "TEMP_QC", shape),
        "psal_qc": flags(d, "PSAL_QC", shape),
    })
    d.close()
    df["cycle_number"] = df["cycle_number"].astype("Int64")
    return df.dropna(subset=["pres", "temp", "psal"], how="all")


def copy_df(cur, df):
    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False, na_rep="")
    buf.seek(0)
    cur.copy_expert(
        f"COPY argo_measurements ({','.join(COLS)}) FROM STDIN WITH (FORMAT csv)", buf)


def main():
    pw = getpass("Postgres password (typing is hidden): ")
    conn = psycopg2.connect(host="localhost", port=5432, dbname="argo_db",
                            user="postgres", password=pw)
    cur = conn.cursor()
    cur.execute(SCHEMA)
    conn.commit()

    # ---- 1) float metadata ----
    ids = set()
    for f in sorted(glob.glob(os.path.join(META_DIR, "*.nc"))):
        fid = os.path.basename(f).split("_")[1]
        dm = xr.open_dataset(f)
        launch = pd.to_datetime(get(dm, "LAUNCH_DATE"), format="%Y%m%d%H%M%S", errors="coerce")
        cur.execute(
            """INSERT INTO argo_floats (platform_number, project_name, pi_name, platform_type,
               data_centre, launch_date, launch_latitude, launch_longitude)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
            (fid, get(dm, "PROJECT_NAME"), get(dm, "PI_NAME"), get(dm, "PLATFORM_TYPE"),
             get(dm, "DATA_CENTRE"), None if pd.isna(launch) else launch.to_pydatetime(),
             num(dm["LAUNCH_LATITUDE"].values), num(dm["LAUNCH_LONGITUDE"].values)))
        ids.add(fid)
        dm.close()
    conn.commit()
    print(f"Loaded metadata for {len(ids)} floats")

    # ---- 2) measurements ----
    total = 0
    for f in sorted(glob.glob(os.path.join(PROFILE_DIR, "*.nc"))):
        fid = os.path.basename(f).split("_")[1]
        if fid not in ids:
            print("  skipping (no metadata):", fid)
            continue
        try:
            df = load_profiles(f, fid)
            copy_df(cur, df)
            conn.commit()
            total += len(df)
            print(f"  {fid}: {len(df):>7} rows")
        except Exception as e:
            conn.rollback()
            print(f"  {fid}: FAILED -> {str(e)[:150]}")
    print(f"Total rows loaded: {total}")

    # ---- 3) indexes + per-float coverage stats ----
    cur.execute("CREATE INDEX ON argo_measurements (platform_number, juld)")
    cur.execute("CREATE INDEX ON argo_measurements (juld)")
    cur.execute("CREATE INDEX ON argo_measurements (latitude, longitude)")
    cur.execute("""
        UPDATE argo_floats f SET n_profiles = s.n, first_profile = s.t0, last_profile = s.t1,
               lat_min = s.a0, lat_max = s.a1, lon_min = s.o0, lon_max = s.o1
        FROM (SELECT platform_number, COUNT(DISTINCT cycle_number) n, MIN(juld) t0, MAX(juld) t1,
                     MIN(latitude) a0, MAX(latitude) a1, MIN(longitude) o0, MAX(longitude) o1
              FROM argo_measurements GROUP BY platform_number) s
        WHERE f.platform_number = s.platform_number""")
    cur.execute("ANALYZE")
    conn.commit()

    # ---- 4) quick check ----
    cur.execute("SELECT COUNT(*) FROM argo_measurements")
    print("\nargo_measurements rows:", cur.fetchone()[0])
    cur.execute("""SELECT platform_number, platform_type, n_profiles, first_profile::date,
                          last_profile::date, round(lat_min::numeric,1), round(lat_max::numeric,1),
                          round(lon_min::numeric,1), round(lon_max::numeric,1)
                   FROM argo_floats ORDER BY platform_number LIMIT 5""")
    print("argo_floats sample:")
    for r in cur.fetchall():
        print("  ", r)
    cur.execute("SELECT temp_qc, COUNT(*) FROM argo_measurements GROUP BY temp_qc ORDER BY 2 DESC")
    print("temperature QC flags:", cur.fetchall())
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()