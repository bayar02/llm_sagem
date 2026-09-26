import sys, os

sys.path.insert(0, os.path.join(os.getcwd(), "rag_env", "modules_rag"))

from rag_extractor_rf import BAND_QUERIES
from rag_retriever import hybrid_search

query = BAND_QUERIES["Bluetooth"]
print("QUERY:", query)
print()

results = hybrid_search(query, product="DIW252_LOWI", top_k=8)
print("(recherche AVEC filtre produit DIW252_LOWI)")
print("NB PASSAGES:", len(results))
print()

for i, p in enumerate(results):
    page = p.get("page", p.get("metadata", {}).get("page", "?"))
    text = p["text"]
    print(f"--- Passage {i+1} (page {page}) ---")
    print(text[:400])
    print()