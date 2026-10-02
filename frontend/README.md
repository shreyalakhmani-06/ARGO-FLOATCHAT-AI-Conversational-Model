# FloatChat

Ask questions about Argo ocean float data in plain English and get answers or charts back.

FloatChat covers 60 Argo profiling floats in the Indian Ocean (2002-2025). A language model reads the question and plans what to look up. PostgreSQL does the actual number crunching, and a React chat UI shows the answer with Plotly charts.

Example questions:

- `Plot temperature for float 1902669`
- `Show temperature vs salinity for float 1902670`
- `Which floats were active in the Bay of Bengal in 2024?`
- `What is the average salinity in the Arabian Sea in 2004?`
- `What is the temperature at 150 m for float 1902670?`
- `What is a thermocline?`

## How it works

```
question
   |
   v
retrieve context  (ChromaDB + sentence-transformers)
   |
   v
LLM planner       (Gemini API) -> JSON filters
   |
   v
validator         (types, ranges, known float IDs)
   |
   v
parameterized SQL (PostgreSQL) -> text answer or Plotly chart
```

1. **Retrieve.** A small knowledge base holds region boundaries, a glossary, QC flag meanings, interpretation rules and solved examples. Short rules ("near" means plus or minus 2 degrees, "recent" means 2024 onward) are always included. Regions, glossary notes and similar solved examples are looked up per question.
2. **Plan.** The LLM returns one JSON object with fixed keys: intent, parameters, float IDs, latitude/longitude box, dates, depth limits and chart type.
3. **Validate.** The JSON is treated as untrusted. Types are coerced, ranges are clamped, invalid dates are dropped, and float IDs that are not in the question or not in the database are rejected.
4. **Query.** Validated values are passed to PostgreSQL as bound parameters, never pasted into SQL text. Only readings with QC flag 1 or 2 are used. Averages are computed inside SQL.

The LLM only plans. Every number in an answer comes from the database.

## Tech stack

- Backend: Python, FastAPI, SQLAlchemy, pandas, Plotly
- Retrieval: ChromaDB, sentence-transformers (`all-MiniLM-L6-v2`)
- LLM: Gemini API (`google-genai`)
- Database: PostgreSQL
- Frontend: React, react-plotly.js, Tailwind CSS

## Data

- 60 floats from the INCOIS Argo data centre
- 6,768 profiles, 345,549 depth readings (pressure, temperature, salinity)
- Dates from 2002-10-24 to 2025-08-29; latitude -44 to 21, longitude 40 to 98
- Per-reading quality-control flags are kept

Stored in two tables: `argo_floats` (one row per float, with coverage summary) and `argo_measurements` (one row per reading, indexed by float, time and position).

The raw data files are not in this repository because of their size. `Database/download_data.py` fetches them.

## Project structure

```
FloatChat/
├── backend/
│   ├── main.py             FastAPI app (/chat, /health)
│   ├── chat_pipeline.py    question -> plan -> SQL -> answer or chart
│   ├── argo_db.py          parameterized SQL queries
│   ├── nlp_to_sql.py       original regex parser, kept as the evaluation baseline
│   ├── evaluate.py         compares the three systems on 24 questions
│   ├── eval_results.json   results of my evaluation run
│   ├── test_pipeline.py    end-to-end smoke test
│   ├── test_gemini.py      checks API key and model access
│   └── rag/
│       ├── build_catalog.py     one text description per float -> ChromaDB
│       ├── build_knowledge.py   regions, glossary, QC, rules, examples -> ChromaDB
│       ├── retriever.py         selects the context for a question
│       ├── planner.py           LLM call, caching, model fallback, validation
│       └── hybrid_demo.py       exact metadata filters combined with semantic search
├── Database/
│   ├── download_data.py    downloads NetCDF files
│   ├── load_argo.py        NetCDF -> PostgreSQL
│   └── ...                 older CSV-based scripts from the hackathon version
└── frontend/               React chat UI
```

## Setup

You need Python 3.12, PostgreSQL 17, Node.js with npm, and a Gemini API key. This project was developed and tested with those versions.

**1. Database**

Create an empty database named `argo_db` (in pgAdmin, or with `CREATE DATABASE argo_db;`), then:

```
cd Database
python download_data.py
python load_argo.py
```

`download_data.py` saves 60 profile and 60 metadata files under `data/`. `load_argo.py` asks for the PostgreSQL password, drops and recreates its two tables, loads everything, and adds indexes. It is safe to re-run.

**2. Backend**

```
cd backend
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill it in:

| Variable | Meaning |
|---|---|
| `GEMINI_API_KEY` | your Gemini API key |
| `GEMINI_MODELS` | model names, comma-separated; tried in order |
| `DATABASE_URL` | for example `postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/argo_db` |

Build the two retrieval collections once, then start the server:

```
python rag/build_catalog.py
python rag/build_knowledge.py
python -m uvicorn main:app --port 8000
```

The first start takes a few seconds longer because the embedding model loads (about 90 MB is downloaded on first use). Check `http://127.0.0.1:8000/health`.

**3. Frontend**

```
cd frontend
npm install
npm start
```

The app opens at `http://localhost:3000` and talks to the backend on port 8000.

## API

- `GET /health` returns `{"status": "ok"}`
- `POST /chat` with body `{"query": "..."}`

The `/chat` response contains:

- `response`: the text answer
- `visualization` (one chart) or `visualizations` (several): Plotly figures
- `filters`: the validated filters that were used
- `platform_number`: the float ID, if the question named one

## Evaluation

24 hand-labelled questions, strict scoring: every checked field must be correct (1 degree and 1 dbar tolerance).

| System | Fully correct |
|---|---|
| Regex parser (original hackathon version) | 1/24 (4%) |
| LLM only, no retrieval | 9/24 (38%) |
| LLM + retrieval (this project) | 22/24 (92%) |

The two misses were both "surface" questions where the model set a lower depth bound of 0 instead of leaving it empty.

Run it with `python evaluate.py` from `backend/`.

How to read these numbers:

- It is a small set written by one person, and the questions resemble the stored examples.
- The labels follow this project's own definitions (region boxes, "near" = plus or minus 2 degrees, "recent" = 2024 onward). Retrieval wins mostly because it makes the model follow those definitions consistently, not because it knows more geography.
- The regex baseline was adapted to the same output format and could not handle list or explain questions at all.
- One model (`gemini-3.1-flash-lite`) and one run.
- Float IDs in the questions refer to the 60 floats in my dataset.

## Notes and limitations

- Region boundaries are approximate boxes.
- Results are limited to quality-controlled readings (QC 1-2), and plots are capped at 30,000 readings.
- Responses from the LLM are cached in `backend/llm_cache.json`, so repeated questions are instant and free. Delete the file if you change model or prompt and want fresh answers.
- Free-tier API limits apply. If one model hits its quota, the planner falls back to the next in `GEMINI_MODELS`.
- Only the chat page uses the new backend. The other pages of the UI (map, anomaly alerts, sign-in) are unchanged from the hackathon version.
- The scripts in `Database/` other than `download_data.py` and `load_argo.py` belong to the older CSV-based pipeline and are kept for reference.

## Background

FloatChat started as a team project for Smart India Hackathon 2025, where it qualified for the next round. The original team built the data download and conversion scripts and the first chat interface. This repository is my continuation. After the hackathon I added:

- a rebuilt PostgreSQL schema and loader that keeps QC flags
- the retrieval layer, LLM planner and output validator
- the evaluation above
- multi-chart response handling in the React chat
