import os
from getpass import getpass
from pathlib import Path

import chromadb
import psycopg2
from sentence_transformers import SentenceTransformer

CHROMA_DIR = str(Path(__file__).parent / "chroma_db")


def region_name(lat, lon):
    """Rough Indian Ocean regions (heuristic, based on the float's mid-position)."""
    if lat >= 5:
        return "Arabian Sea" if lon < 77 else "Bay of Bengal"
    if lat >= -10:
        return "Equatorial Indian Ocean"
    return "Southern Indian Ocean"


def lat_str(x):
    return f"{abs(x):.1f}°{'N' if x >= 0 else 'S'}"


def lon_str(x):
    return f"{abs(x):.1f}°{'E' if x >= 0 else 'W'}"


def describe(r):
    pid, project, pi, ptype, dc, ldate, llat, llon, n, t0, t1, a0, a1, o0, o1 = r
    mlat, mlon = (a0 + a1) / 2, (o0 + o1) / 2
    region = region_name(mlat, mlon)

    if t0.year >= 2020:
        era = "recent float"
    elif t1.year <= 2010:
        era = "historical float from the early 2000s"
    else:
        era = "float from the 2010s"

    parts = [
        f"Argo float {pid}, a {ptype} profiling float of the {project} programme "
        f"(PI {pi}, data centre {dc}).",
        f"Located in the {region}, around {lat_str(mlat)}, {lon_str(mlon)}; "
        f"it drifted between latitudes {lat_str(a0)} and {lat_str(a1)} "
        f"and longitudes {lon_str(o0)} and {lon_str(o1)}.",
    ]
    if ldate is not None and llat is not None and llon is not None:
        parts.append(f"Launched on {ldate:%Y-%m-%d} at {lat_str(llat)}, {lon_str(llon)}.")
    parts.append(
        f"Reported {n} profiles from {t0:%Y-%m-%d} to {t1:%Y-%m-%d} ({era}), "
        f"active during {t0.year} to {t1.year}."
    )
    meta = {
        "platform_number": pid,
        "region": region,
        "lat_mean": round(mlat, 2),
        "lon_mean": round(mlon, 2),
        "first_year": t0.year,
        "last_year": t1.year,
    }
    return " ".join(parts), meta


def main():
    pw = os.environ.get("PGPASSWORD") or getpass("Postgres password (typing is hidden): ")
    conn = psycopg2.connect(host="localhost", port=5432, dbname="argo_db",
                            user="postgres", password=pw)
    cur = conn.cursor()
    cur.execute("""
        SELECT platform_number, project_name, pi_name, platform_type, data_centre,
               launch_date, launch_latitude, launch_longitude,
               n_profiles, first_profile, last_profile,
               lat_min, lat_max, lon_min, lon_max
        FROM argo_floats
        WHERE n_profiles IS NOT NULL
        ORDER BY platform_number
    """)
    rows = cur.fetchall()
    conn.close()
    print(f"Read {len(rows)} floats from Postgres")

    docs, metas, ids = [], [], []
    for r in rows:
        text, meta = describe(r)
        docs.append(text)
        metas.append(meta)
        ids.append(meta["platform_number"])

    print("\nExample chunk:\n", docs[2], "\n")

    print("Loading embedding model (first run downloads ~90 MB)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        client.delete_collection("floats")
    except Exception:
        pass
    col = client.create_collection("floats", metadata={"hnsw:space": "cosine"})
    col.add(ids=ids, documents=docs, metadatas=metas,
            embeddings=model.encode(docs).tolist())
    print(f"Stored {col.count()} float descriptions in ChromaDB\n")

    tests = [
        "floats in the Arabian Sea",
        "floats in the Bay of Bengal",
        "old floats from the early 2000s",
        "recent floats active in 2025",
        "southern Indian Ocean",
        "floats near 17N 70E",
    ]
    for q in tests:
        res = col.query(query_embeddings=model.encode([q]).tolist(), n_results=3)
        print(f"Q: {q}")
        for i, d, m in zip(res["ids"][0], res["distances"][0], res["metadatas"][0]):
            print(f"   {i}  dist={d:.3f}  {m['region']:<24} {m['first_year']}-{m['last_year']}"
                  f"  ({m['lat_mean']}, {m['lon_mean']})")
        print()


if __name__ == "__main__":
    main()