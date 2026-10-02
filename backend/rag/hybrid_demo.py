from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

client = chromadb.PersistentClient(path=str(Path(__file__).parent / "chroma_db"))
col = client.get_collection("floats")
model = SentenceTransformer("all-MiniLM-L6-v2")


def search(query, where=None, n=3):
    res = col.query(query_embeddings=model.encode([query]).tolist(),
                    n_results=n, where=where)
    print(f"Q: {query}\n   filter: {where}")
    if not res["ids"][0]:
        print("   (no floats match the filter)\n")
        return
    for i, d, m in zip(res["ids"][0], res["distances"][0], res["metadatas"][0]):
        print(f"   {i}  dist={d:.3f}  {m['region']:<24} {m['first_year']}-{m['last_year']}"
              f"  ({m['lat_mean']}, {m['lon_mean']})")
    print()


search("recent floats active in 2025", where={"last_year": {"$gte": 2025}})

search("floats in the Arabian Sea", where={"last_year": {"$gte": 2024}})

search("floats near 17N 70E", where={"$and": [
    {"lat_mean": {"$gte": 14}}, {"lat_mean": {"$lte": 20}},
    {"lon_mean": {"$gte": 67}}, {"lon_mean": {"$lte": 73}}]})

search("southern Indian Ocean", where={"lat_mean": {"$lt": -10}})