import json
import time
from collections import defaultdict

from nlp_to_sql import parse_query_to_filters
from rag.planner import _cache_get, plan_filters

KEYS = ["intent", "parameters", "platform_numbers", "lat_min", "lat_max", "lon_min", "lon_max",
        "date_start", "date_end", "depth_min", "depth_max", "depth_target", "chart"]


def G(**kw):
    g = {k: None for k in KEYS}
    g["parameters"], g["platform_numbers"] = [], []
    g.update(kw)
    return g


AS = dict(lat_min=5, lat_max=25, lon_min=50, lon_max=77)
BOB = dict(lat_min=5, lat_max=23, lon_min=78, lon_max=100)
EQ = dict(lat_min=-10, lat_max=5, lon_min=40, lon_max=100)
SIO = dict(lat_min=-45, lat_max=-10, lon_min=20, lon_max=120)

# (question, correct filters, extra keys to ignore). REVIEW THESE LABELS YOURSELF.
CASES = [
    ("How warm is the water at the surface in the Arabian Sea?",
     G(intent="value", parameters=["TEMP"], **AS, depth_max=10), []),
    ("Show the salinity profile for float 2900229",
     G(intent="plot", parameters=["PSAL"], platform_numbers=["2900229"], chart="depth_profile"), []),
    ("List floats in the Equatorial Indian Ocean during 2003",
     G(intent="list_floats", **EQ, date_start="2003-01-01", date_end="2003-12-31"), []),
    ("What was the temperature near 10N 85E in June 2024?",
     G(intent="value", parameters=["TEMP"], lat_min=8, lat_max=12, lon_min=83, lon_max=87,
       date_start="2024-06-01", date_end="2024-06-30"), []),
    ("Plot temperature vs salinity for float 2900335",
     G(intent="plot", parameters=["TEMP", "PSAL"], platform_numbers=["2900335"], chart="ts_scatter"), []),
    ("What does QC flag 3 mean?", G(intent="explain"), []),
    ("Which floats are in the southern Indian Ocean?", G(intent="list_floats", **SIO), []),
    ("What is the salinity at 1000 m for float 2900229?",
     G(intent="value", parameters=["PSAL"], platform_numbers=["2900229"], depth_target=1000), []),
    ("Are there any floats around 8N 90E in 2025?",
     G(intent="list_floats", lat_min=6, lat_max=10, lon_min=88, lon_max=92,
       date_start="2025-01-01", date_end="2025-12-31"), []),
    ("Plot salinity in the Bay of Bengal below 300 m",
     G(intent="plot", parameters=["PSAL"], **BOB, depth_min=300, chart="depth_profile"), []),
    ("What is practical salinity?", G(intent="explain"), []),
    ("Average temperature at 200 m near 15N 88E",
     G(intent="value", parameters=["TEMP"], lat_min=13, lat_max=17, lon_min=86, lon_max=90,
       depth_target=200), []),
    ("Plot temperature profiles in the Arabian Sea in March 2004",
     G(intent="plot", parameters=["TEMP"], **AS, date_start="2004-03-01", date_end="2004-03-31",
       chart="depth_profile"), []),
    ("What is the surface salinity of float 1902671?",
     G(intent="value", parameters=["PSAL"], platform_numbers=["1902671"], depth_max=10), []),
    ("Which floats were active recently near 5N 80E?",
     G(intent="list_floats", lat_min=3, lat_max=7, lon_min=78, lon_max=82,
       date_start="2024-01-01"), ["date_end"]),
    ("Show temperature and salinity for float 2900340 in 2004",
     G(intent="plot", parameters=["TEMP", "PSAL"], platform_numbers=["2900340"],
       date_start="2004-01-01", date_end="2004-12-31"), ["chart"]),
    ("Which floats are near 12S 80E?",
     G(intent="list_floats", lat_min=-14, lat_max=-10, lon_min=78, lon_max=82), []),
    ("Plot temperature below 1000 m for float 1900121",
     G(intent="plot", parameters=["TEMP"], platform_numbers=["1900121"], depth_min=1000,
       chart="depth_profile"), []),
    ("What is the maximum salinity in the Arabian Sea in 2003?",
     G(intent="value", parameters=["PSAL"], **AS, date_start="2003-01-01", date_end="2003-12-31"), []),
    ("Explain what a T-S diagram is", G(intent="explain"), []),
    ("Show temperature vs salinity in the Bay of Bengal in 2024",
     G(intent="plot", parameters=["TEMP", "PSAL"], **BOB, date_start="2024-01-01",
       date_end="2024-12-31", chart="ts_scatter"), []),
    ("Plot salinity between 100 and 200 m for float 2900275",
     G(intent="plot", parameters=["PSAL"], platform_numbers=["2900275"], depth_min=100,
       depth_max=200, chart="depth_profile"), []),
    ("Which floats are at 20N 65E?",
     G(intent="list_floats", lat_min=18, lat_max=22, lon_min=63, lon_max=67), []),
    ("What was the temperature at 50 m near 8S 75E in January 2025?",
     G(intent="value", parameters=["TEMP"], lat_min=-10, lat_max=-6, lon_min=73, lon_max=77,
       date_start="2025-01-01", date_end="2025-01-31", depth_target=50), []),
]


def baseline(q):
    """The old regex parser, adapted to the same output format (a generous adaptation)."""
    r = parse_query_to_filters(None, q)
    viz = r.get("_visualization_type", [])
    out = {k: None for k in KEYS}
    out["intent"] = "plot" if viz else "value"
    out["parameters"] = [p for p in r.get("_detected_parameters", []) if p in ("TEMP", "PSAL")]
    out["platform_numbers"] = [r["platform_number"]] if r.get("platform_number") else []
    out["lat_min"], out["lat_max"] = r.get("min_lat"), r.get("max_lat")
    out["lon_min"], out["lon_max"] = r.get("min_lon"), r.get("max_lon")
    out["depth_target"] = r.get("pres")
    out["chart"] = "ts_scatter" if "temp_vs_salinity" in viz else ("depth_profile" if viz else None)
    return out


SYSTEMS = [
    ("Regex baseline", baseline),
    ("LLM only (no retrieval)", lambda q: plan_filters(q, use_rag=False)),
    ("LLM + RAG", lambda q: plan_filters(q, use_rag=True)),
]


def keys_to_check(gold, extra):
    skip = set(extra)
    if gold["intent"] == "explain":
        skip |= set(KEYS) - {"intent"}
    if gold["intent"] == "list_floats":
        skip |= {"parameters", "chart"}
    if gold["intent"] == "value":
        skip |= {"chart"}
    return [k for k in KEYS if k not in skip]


def same(k, p, g):
    if k in ("parameters", "platform_numbers"):
        return set(map(str, p or [])) == set(map(str, g or []))
    if k in ("intent", "chart"):
        return p == g
    if k in ("date_start", "date_end"):
        return (None if p is None else str(p)[:10]) == g
    if p is None or g is None:
        return p is None and g is None
    return abs(float(p) - float(g)) <= 1.0     # 1 degree / 1 dbar tolerance


def run(name, fn):
    rows = []
    for q, gold, extra in CASES:
        before = len(_cache_get())
        try:
            pred = fn(q)
        except Exception as e:
            raise SystemExit(f"\nSTOPPED at '{q}' for system '{name}': {str(e)[:300]}\n"
                             "Answers so far are cached. Wait a few minutes (or fix the model "
                             "list in .env) and run again; it will continue where it stopped.")
        checked = keys_to_check(gold, extra)
        wrong = {k: {"got": str(pred[k]), "expected": str(gold[k])}
                 for k in checked if not same(k, pred[k], gold[k])}
        rows.append({"question": q, "ok": not wrong, "checked": checked, "wrong": wrong})
        if len(_cache_get()) > before:
            time.sleep(5)                      # stay under the free-tier rate limit
    return rows


def main():
    report = {}
    for name, fn in SYSTEMS:
        print(f"Running: {name} ...")
        report[name] = run(name, fn)

    print("\n" + "=" * 60)
    print(f"Results on {len(CASES)} hand-labelled questions "
          "(strict: every checked field must be right)")
    print("=" * 60)
    for name, rows in report.items():
        ok = sum(r["ok"] for r in rows)
        per = defaultdict(lambda: [0, 0])
        for r in rows:
            for k in r["checked"]:
                per[k][1] += 1
                per[k][0] += k not in r["wrong"]
        print(f"\n{name}: {ok}/{len(rows)} fully correct ({100 * ok / len(rows):.0f}%)")
        print("   per field: " + ", ".join(f"{k} {a}/{b}" for k, (a, b) in per.items()))

    print("\n--- Mistakes made by LLM + RAG ---")
    for r in report["LLM + RAG"]:
        if not r["ok"]:
            print("\nQ:", r["question"])
            for k, v in r["wrong"].items():
                print(f"   {k}: got {v['got']}  | expected {v['expected']}")

    with open("eval_results.json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    print("\nSaved details to eval_results.json")


if __name__ == "__main__":
    main()