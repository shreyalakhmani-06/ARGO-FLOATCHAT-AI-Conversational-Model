import json
import time

from chat_pipeline import answer

QUESTIONS = [
    "What is the average salinity in the Arabian Sea in 2004?",
    "Which floats were active in the Bay of Bengal in 2024?",
    "Plot temperature for float 1902669",
    "temperature at 150 m for float 1902670",
    "what is a thermocline",
    "list floats near 17N 70E",
    "Plot salinity for float 9999999",
]

for q in QUESTIONS:
    r = answer(q)
    f = {k: v for k, v in r.get("filters", {}).items() if v not in (None, [])}
    n_charts = 1 if "visualization" in r else len(r.get("visualizations", {}))
    print("\nQ:", q)
    print("  filters :", json.dumps(f, default=str))
    print("  response:", r["response"][:300].replace("\n", " | "))
    print("  charts  :", n_charts)
    time.sleep(15)  # stay under the free-tier rate limit