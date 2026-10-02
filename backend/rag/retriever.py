from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_DIR = str(Path(__file__).parent / "chroma_db")

_model = None
_col = None


def _load():
    """Load the embedding model and collection once, then reuse them."""
    global _model, _col
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        _col = chromadb.PersistentClient(path=CHROMA_DIR).get_collection("knowledge")
    return _model, _col


def _top(emb, kinds, n, max_dist):
    _, col = _load()
    res = col.query(query_embeddings=emb, n_results=n,
                    where={"kind": {"$in": kinds}})
    return [doc for dist, doc in zip(res["distances"][0], res["documents"][0])
            if dist < max_dist]


def get_context(question, max_dist=0.65):
    model, col = _load()
    emb = model.encode([question]).tolist()
    return {
        # always included: short instructions that apply to every question
        "rules": col.get(where={"kind": {"$in": ["rule", "dataset"]}})["documents"],
        # looked up per question
        "examples": _top(emb, ["example"], 3, max_dist),
        "regions": _top(emb, ["region"], 2, max_dist),
        "notes": _top(emb, ["glossary", "qc", "schema"], 2, max_dist),
    }


def format_context(ctx):
    """Turn the retrieved pieces into text for the LLM prompt."""
    parts = []
    for title, key in [("INSTRUCTIONS", "rules"), ("RELEVANT REGIONS", "regions"),
                       ("RELEVANT NOTES", "notes"), ("SIMILAR SOLVED EXAMPLES", "examples")]:
        if ctx[key]:
            parts.append(f"## {title}\n" + "\n".join(f"- {d}" for d in ctx[key]))
    return "\n\n".join(parts)


if __name__ == "__main__":
    tests = [
        "salinity near 18N 68E in 2024",
        "show floats in the Arabian Sea that are still active",
        "what does PSAL mean",
        "thermocline for float 1902669 in the Bay of Bengal",
        "what is the capital of France",
    ]
    for q in tests:
        ctx = get_context(q)
        text = format_context(ctx)
        print(f"\nQ: {q}   (prompt context: {len(text)} characters)")
        for key in ["rules", "regions", "notes", "examples"]:
            print(f"  {key}: {len(ctx[key])} items")
            if key != "rules":
                for d in ctx[key]:
                    print("     -", d[:90].replace("\n", " "))