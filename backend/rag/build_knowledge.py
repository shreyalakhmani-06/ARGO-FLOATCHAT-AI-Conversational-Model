import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_DIR = str(Path(__file__).parent / "chroma_db")

KEYS = ["intent", "parameters", "platform_numbers", "lat_min", "lat_max",
        "lon_min", "lon_max", "date_start", "date_end",
        "depth_min", "depth_max", "depth_target", "chart"]


def F(**kw):
    """Build a filter dict with every key present (unused ones are None / [])."""
    assert set(kw) <= set(KEYS), f"unknown key in {kw}"
    base = {k: None for k in KEYS}
    base["parameters"] = []
    base["platform_numbers"] = []
    base.update(kw)
    return base


# ---------- regions (approximate boundaries; a heuristic, say so in the README) ----------
REGIONS = {
    "Arabian Sea": (5, 25, 50, 77, "The sea west of India, between India and Arabia."),
    "Bay of Bengal": (5, 23, 78, 100, "The bay east of India, between India and Southeast Asia."),
    "Equatorial Indian Ocean": (-10, 5, 40, 100, "Tropical band around the equator."),
    "Southern Indian Ocean": (-45, -10, 20, 120, "The Indian Ocean south of 10 degrees south."),
    "Indian Ocean": (-45, 25, 40, 100, "The whole area covered by this dataset."),
}

NOTES = []  # (kind, text)

for name, (a, b, c, d, extra) in REGIONS.items():
    NOTES.append(("region",
        f"Region {name}: latitude {a} to {b}, longitude {c} to {d} "
        f"(approximate box, degrees). {extra}"))

NOTES += [
    ("dataset", "The dataset has 60 Argo floats from the Indian national Argo programme "
                "(INCOIS) with 6768 profiles from 2002-10-24 to 2025-08-29, in the Indian Ocean "
                "(latitude -44 to 21, longitude 40 to 98)."),
    ("glossary", "Argo float: an autonomous instrument that drifts with ocean currents and "
                 "periodically dives and rises, measuring temperature and salinity."),
    ("glossary", "PRES is sea pressure in decibars (dbar), used as the depth axis. "
                 "1 dbar is roughly 1 metre of depth, so 100 m is about 100 dbar. "
                 "Argo floats usually profile from near the surface to about 2000 dbar."),
    ("glossary", "TEMP is sea temperature in degrees Celsius. Tropical surface water is often "
                 "25 to 30 C and gets colder with depth."),
    ("glossary", "PSAL is practical salinity (unitless, similar to PSU). Open-ocean values are "
                 "typically about 34 to 36."),
    ("glossary", "JULD is the date and time of a profile. CYCLE_NUMBER counts the float's dive "
                 "cycles; cycles are typically about 10 days apart. A profile is one vertical "
                 "set of measurements from one cycle."),
    ("glossary", "A thermocline is the layer where temperature drops quickly with depth, "
                 "typically within the upper few hundred metres in the tropics."),
    ("glossary", "A temperature-salinity (T-S) diagram plots temperature against salinity "
                 "and is used to identify water masses."),
    ("qc", "Argo quality-control flags: 1 good, 2 probably good, 3 probably bad, 4 bad, "
           "5 changed, 8 estimated, 9 missing. Flag 4 means the reading failed quality checks "
           "and should not be used."),
    ("qc", "By default only use readings with QC flag 1 or 2. In the database the flags are "
           "in columns pres_qc, temp_qc and psal_qc."),
    ("schema", "Table argo_floats has one row per float: platform_number, project_name, pi_name, "
               "platform_type, launch_date, launch_latitude, launch_longitude, n_profiles, "
               "first_profile, last_profile, lat_min, lat_max, lon_min, lon_max."),
    ("schema", "Table argo_measurements has one row per depth reading: platform_number, "
               "cycle_number, juld, latitude, longitude, pres, temp, psal, pres_qc, temp_qc, psal_qc."),
    ("rule", "Rule for 'near' a point: use a box of plus or minus 2 degrees around the "
             "latitude and longitude. 'Surface' means depth_max 10 (dbar). Depth in metres is "
             "about the same number in dbar."),
    ("rule", "Rule for dates: a month like March 2023 means date_start 2023-03-01 and "
             "date_end 2023-03-31. A year means January 1 to December 31. 'Recent' means "
             "date_start 2024-01-01, because the data ends on 2025-08-29."),
    ("rule", "Rule for coordinates: south latitudes and west longitudes are negative. "
             "Dates are written YYYY-MM-DD. Parameters are written TEMP, PSAL or PRES. "
             "Chart is depth_profile (parameter against depth) or ts_scatter (temperature "
             "against salinity)."),
]

# ---------- worked examples: embed the QUESTION, return question + JSON ----------
EXAMPLES = [
    ("Show temperature profiles in the Arabian Sea",
     F(intent="plot", parameters=["TEMP"], lat_min=5, lat_max=25, lon_min=50, lon_max=77,
       chart="depth_profile")),
    ("Show salinity vs depth for float 1902669",
     F(intent="plot", parameters=["PSAL"], platform_numbers=["1902669"], chart="depth_profile")),
    ("What is the salinity near 15N 65E in March 2023?",
     F(intent="value", parameters=["PSAL"], lat_min=13, lat_max=17, lon_min=63, lon_max=67,
       date_start="2023-03-01", date_end="2023-03-31")),
    ("Find floats active in the Bay of Bengal in 2024",
     F(intent="list_floats", lat_min=5, lat_max=23, lon_min=78, lon_max=100,
       date_start="2024-01-01", date_end="2024-12-31")),
    ("Temperature at 100 m for float 2900275",
     F(intent="value", parameters=["TEMP"], platform_numbers=["2900275"], depth_target=100)),
    ("Compare temperature and salinity for float 1902670",
     F(intent="plot", parameters=["TEMP", "PSAL"], platform_numbers=["1902670"], chart="ts_scatter")),
    ("Temperature below 200 m in the southern Indian Ocean",
     F(intent="plot", parameters=["TEMP"], lat_min=-45, lat_max=-10, lon_min=20, lon_max=120,
       depth_min=200, chart="depth_profile")),
    ("Which floats were active recently in the Arabian Sea?",
     F(intent="list_floats", lat_min=5, lat_max=25, lon_min=50, lon_max=77,
       date_start="2024-01-01", date_end="2025-08-29")),
    ("What does QC flag 4 mean?", F(intent="explain")),
]


def main():
    ids, docs, embed_texts, metas = [], [], [], []
    for i, (kind, text) in enumerate(NOTES):
        ids.append(f"note{i:02d}")
        docs.append(text)
        embed_texts.append(text)
        metas.append({"kind": kind})
    for j, (q, f) in enumerate(EXAMPLES):
        ids.append(f"example{j:02d}")
        docs.append(f"Example question: {q}\nFilters: {json.dumps(f)}")
        embed_texts.append(q)
        metas.append({"kind": "example"})

    print(f"{len(ids)} chunks "
          f"({len(NOTES)} notes + {len(EXAMPLES)} examples)")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        client.delete_collection("knowledge")
    except Exception:
        pass
    col = client.create_collection("knowledge", metadata={"hnsw:space": "cosine"})
    col.add(ids=ids, documents=docs, metadatas=metas,
            embeddings=model.encode(embed_texts).tolist())
    print("Stored in ChromaDB collection 'knowledge'\n")

    tests = [
        "what does QC flag 4 mean",
        "show me salinity near 18N 68E in 2024",
        "temperature in the southern Indian Ocean",
        "what is PSAL",
        "floats that are active recently",
        "plot temperature vs salinity for float 1902671",
    ]
    for q in tests:
        res = col.query(query_embeddings=model.encode([q]).tolist(), n_results=4)
        print(f"Q: {q}")
        for d, m, doc in zip(res["distances"][0], res["metadatas"][0], res["documents"][0]):
            print(f"   {d:.3f}  [{m['kind']:<8}] {doc[:85].replace(chr(10), ' ')}")
        print()


if __name__ == "__main__":
    main()