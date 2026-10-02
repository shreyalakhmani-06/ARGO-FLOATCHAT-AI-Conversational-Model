
import hashlib
from pathlib import Path
import json
import os
import re
import time
from datetime import date

from dotenv import load_dotenv
from google import genai
from google.genai import types

from argo_db import known_floats
from rag.retriever import format_context, get_context

load_dotenv()
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
_client = None

INTENTS = {"plot", "value", "list_floats", "explain"}
PARAMS = {"TEMP", "PSAL", "PRES"}
SYNONYMS = {"TEMPERATURE": "TEMP", "SALINITY": "PSAL", "SAL": "PSAL",
            "PRESSURE": "PRES", "DEPTH": "PRES"}
CHARTS = {"depth_profile", "ts_scatter"}

PROMPT = """You convert questions about Argo ocean float data into ONE JSON object.

Keys (all required): intent, parameters, platform_numbers, lat_min, lat_max, lon_min,
lon_max, date_start, date_end, depth_min, depth_max, depth_target, chart.
- intent: "plot", "value", "list_floats" or "explain"
- parameters: list drawn from TEMP, PSAL, PRES
- platform_numbers: list of float IDs as strings
- lat/lon/depth: numbers or null; dates: "YYYY-MM-DD" strings or null
- chart: "depth_profile", "ts_scatter" or null
Use null or [] for anything the question does not mention. Never invent float IDs,
dates or coordinates that the question does not imply. Follow the instructions below.

{context}

Question: {question}
JSON:"""


def _client_get():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


CACHE_PATH = Path(__file__).parent.parent / "llm_cache.json"
_cache = None


def _cache_get():
    global _cache
    if _cache is None:
        try:
            _cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            _cache = {}
    return _cache


def _retry_seconds(err):
    m = re.search(r"retry in ([\d.]+)s", str(err), re.I) or \
        re.search(r"retryDelay'?\"?:\s*'?\"?(\d+)", str(err))
    return float(m.group(1)) if m else None


def _generate(prompt, json_mode=True):
    """Cached; tries several models; reports every model's failure."""
    key = hashlib.sha256(f"{json_mode}|{prompt}".encode()).hexdigest()
    cache = _cache_get()
    if key in cache:
        return cache[key]

    cfg = types.GenerateContentConfig(response_mime_type="application/json") if json_mode else None
    env_models = [m.strip() for m in os.getenv("GEMINI_MODELS", "").split(",") if m.strip()]
    models = env_models or list(dict.fromkeys([MODEL, "gemini-3.5-flash-lite", "gemini-2.5-flash"]))

    errors, dead = {}, set()
    for attempt in range(3):
        waits = []
        for m in models:
            if m in dead:
                continue
            try:
                out = _client_get().models.generate_content(
                    model=m, contents=prompt, config=cfg).text
                cache[key] = out
                try:
                    CACHE_PATH.write_text(json.dumps(cache), encoding="utf-8")
                except Exception:
                    pass
                return out
            except Exception as e:
                msg = str(e)
                errors[m] = msg[:140].replace("\n", " ")
                low = msg.lower()
                if "404" in msg or "not_found" in low or "per day" in low or "perday" in low:
                    dead.add(m)                      # retrying cannot help in this run
                elif "429" in msg or "503" in msg or "unavailable" in low or "exhausted" in low:
                    waits.append(_retry_seconds(msg) or 20)
                else:
                    raise RuntimeError(f"LLM call failed ({m}): {msg[:300]}")
        if not waits:
            break
        time.sleep(min(max(waits), 60) + 1)

    detail = " | ".join(f"{m}: {e}" for m, e in errors.items())
    raise RuntimeError(f"No Gemini model could answer. {detail}")

def _parse(text_):
    t = re.sub(r"^```(?:json)?|```$", "", text_.strip(), flags=re.M).strip()
    data = json.loads(t)
    if isinstance(data, list):
        data = data[0] if data else {}
    if not isinstance(data, dict):
        raise ValueError("LLM did not return a JSON object")
    return data


def _num(x, lo, hi):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if lo <= v <= hi else None


def _pair(a, b, lo, hi):
    a, b = _num(a, lo, hi), _num(b, lo, hi)
    if a is not None and b is not None and a > b:
        a, b = b, a
    return a, b


def _date(x):
    try:
        return date.fromisoformat(str(x)[:10])
    except (TypeError, ValueError):
        return None


def validate(raw, question):
    """The LLM output is untrusted: coerce types, clamp ranges, drop anything invalid."""
    f = {"intent": raw.get("intent") if raw.get("intent") in INTENTS else "plot"}

    params = []
    for p in raw.get("parameters") or []:
        p = str(p).upper().strip()
        p = SYNONYMS.get(p, p)
        if p in PARAMS and p not in params:
            params.append(p)
    f["parameters"] = params

    wanted = [str(i).strip() for i in (raw.get("platform_numbers") or [])]
    wanted = [i for i in wanted if i and i in question]    # never trust invented IDs
    known = known_floats()
    f["platform_numbers"] = [i for i in wanted if i in known]
    unknown = [i for i in wanted if i not in known]

    f["lat_min"], f["lat_max"] = _pair(raw.get("lat_min"), raw.get("lat_max"), -90, 90)
    f["lon_min"], f["lon_max"] = _pair(raw.get("lon_min"), raw.get("lon_max"), -180, 180)
    f["depth_min"], f["depth_max"] = _pair(raw.get("depth_min"), raw.get("depth_max"), 0, 12000)
    f["depth_target"] = _num(raw.get("depth_target"), 0, 12000)

    d0, d1 = _date(raw.get("date_start")), _date(raw.get("date_end"))
    if d0 and d1 and d0 > d1:
        d0, d1 = d1, d0
    f["date_start"], f["date_end"] = d0, d1
    f["chart"] = raw.get("chart") if raw.get("chart") in CHARTS else None
    return f, unknown


def plan_query(question):
    ctx = get_context(question)
    prompt = PROMPT.format(context=format_context(ctx), question=question)
    f, unknown = validate(_parse(_generate(prompt)), question)
    return {"filters": f, "context": ctx, "unknown_floats": unknown}


def explain(question, ctx):
    notes = ctx["notes"] + ctx["regions"] + ctx["rules"]
    prompt = ("Answer the question about Argo ocean float data in 2-4 sentences, using ONLY "
              "the notes below. If the notes do not cover it, say you are not sure.\n\nNOTES:\n"
              + "\n".join(f"- {n}" for n in notes) + f"\n\nQuestion: {question}")
    return _generate(prompt, json_mode=False).strip()

def plan_filters(question, use_rag=True):
    """Filters only (used by the evaluation). use_rag=False gives the no-retrieval baseline."""
    ctx_text = format_context(get_context(question)) if use_rag else "(no additional context)"
    prompt = PROMPT.format(context=ctx_text, question=question)
    f, _ = validate(_parse(_generate(prompt)), question)
    return f