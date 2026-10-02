import json

import pandas as pd
import plotly.express as px

from argo_db import aggregate, closest_depth, fetch_floats, fetch_rows
from rag.planner import explain, plan_query

COL = {"TEMP": "temp", "PSAL": "psal", "PRES": "pres"}
LABEL = {"TEMP": "Temperature (°C)", "PSAL": "Salinity (PSU)"}
UNIT = {"TEMP": "°C", "PSAL": "PSU"}


def _fig(fig):
    # to_json handles numpy arrays; to_dict() can break FastAPI's JSON encoding
    return {"type": "plotly", "figure": json.loads(fig.to_json())}


def _plots(df, f, need):
    d = df if len(df) <= 8000 else df.sample(8000, random_state=0)
    out = {}
    if f["chart"] == "ts_scatter":
        fig = px.scatter(d, x="psal", y="temp", color="pres",
                         color_continuous_scale="viridis", render_mode="svg",
                         labels={"psal": LABEL["PSAL"], "temp": LABEL["TEMP"],
                                 "pres": "Pressure (dbar)"},
                         title="Temperature vs Salinity")
        out["temp_vs_salinity"] = _fig(fig)
        return out
    for p in need:
        c = COL[p]
        many = d["platform_number"].nunique() > 10
        fig = px.scatter(d, x=c, y="pres", color=None if many else "platform_number",
                         opacity=0.6, render_mode="svg",
                         labels={c: LABEL[p], "pres": "Pressure (dbar)"},
                         title=f"{LABEL[p]} vs depth")
        fig.update_yaxes(autorange="reversed")
        out[f"{c}_vs_depth"] = _fig(fig)
    return out


def _day(x):
    return str(x)[:10]


def answer(question):
    plan = plan_query(question)
    f, ctx = plan["filters"], plan["context"]
    base = {"filters": f,
            "platform_number": f["platform_numbers"][0] if f["platform_numbers"] else None}

    if plan["unknown_floats"]:
        return {**base, "response": "I don't have data for float(s) "
                + ", ".join(plan["unknown_floats"])
                + ". This dataset covers 60 Indian Ocean floats."}

    intent = f["intent"]

    if intent == "explain":
        return {**base, "response": explain(question, ctx)}

    if intent == "list_floats":
        rows = fetch_floats(f)
        if not rows:
            return {**base, "response": "No floats with good-quality data match that area and period."}
        lines = [f"- {r['platform_number']}: {r['profiles']} profiles, {_day(r['first'])} to "
                 f"{_day(r['last'])}, around {abs(r['lat'])}°{'N' if r['lat'] >= 0 else 'S'} "
                 f"{abs(r['lon'])}°{'E' if r['lon'] >= 0 else 'W'}" for r in rows]
        return {**base, "response": f"Found {len(rows)} float(s):\n" + "\n".join(lines),
                "floats": [r["platform_number"] for r in rows]}

    if f["chart"] == "ts_scatter":
        need = ["TEMP", "PSAL"]
    else:
        need = [p for p in f["parameters"] if p in ("TEMP", "PSAL")] or ["TEMP", "PSAL"]

    if intent == "value" and f["depth_target"] is not None:
        rows = closest_depth(f, need, f["depth_target"])
        if not rows:
            return {**base, "response": "No good-quality readings match those filters."}
        lines = []
        for r in rows:
            vals = ", ".join(f"{p} {r[COL[p]]:.3f} {UNIT[p]}" for p in need)
            lines.append(f"- float {r['platform_number']}, {_day(r['juld'])}, "
                         f"at {r['pres']:.1f} dbar: {vals}")
        return {**base, "response": f"Closest readings to {f['depth_target']:g} dbar:\n"
                + "\n".join(lines)}

    if intent == "value":
        a = aggregate(f, need)
        if not a["n"]:
            return {**base, "response": "No good-quality measurements match those filters."}
        lines = [f"- {p}: mean {a[COL[p] + '_mean']:.2f} {UNIT[p]} "
                 f"(min {a[COL[p] + '_min']:.2f}, max {a[COL[p] + '_max']:.2f})" for p in need]
        return {**base, "response": f"Based on {a['n']:,} readings from {a['floats']} float(s), "
                f"{_day(a['t0'])} to {_day(a['t1'])}:\n" + "\n".join(lines)
                + "\nOnly quality-controlled readings (QC 1-2) are used."}

    rows = fetch_rows(f, need)
    if not rows:
        return {**base, "response": "No good-quality measurements match those filters. "
                                    "Try a wider area or a different period."}
    df = pd.DataFrame(rows)
    span = f"{_day(df['juld'].min())} to {_day(df['juld'].max())}"
    note = " Only quality-controlled readings (QC 1-2) are used."
    if len(df) >= 30000:
        note += " Showing the first 30,000 readings."

    plots = _plots(df, f, need)
    res = {**base, "response": f"Plotted {len(df):,} readings from "
                               f"{df['platform_number'].nunique()} float(s), {span}.{note}"}
    if len(plots) == 1:
        res["visualization"] = next(iter(plots.values()))
    else:
        res["visualizations"] = plots
    return res