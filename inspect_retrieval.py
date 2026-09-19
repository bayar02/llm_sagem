import sys
sys.path.insert(0, "rag_env/modules_rag")
from retriever import hybrid_search

passages = hybrid_search(
    query="limites de test FE Viterbi BER RSSI Carrier-to-Noise Frequency Offset Rate Offset",
    product="DCIW377_DISH",
    top_k=12,
)
with open("retrieval_dump.txt", "w", encoding="utf-8") as f:
    for i, p in enumerate(passages):
        f.write(f"--- passage {i+1} | page {p.get('page')} | score={p.get('score'):.3f} ---\n")
        f.write(p["text"])
        f.write("\n\n")
print("OK: dump ecrit dans retrieval_dump.txt")