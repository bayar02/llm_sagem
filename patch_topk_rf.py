from pathlib import Path

path = Path("rag_env/modules_rag/rag_extractor_rf.py")
content = path.read_text(encoding="utf-8")

old = "passages = hybrid_search(query=BAND_QUERIES[band], product=product, top_k=8)"
new = "passages = hybrid_search(query=BAND_QUERIES[band], product=product, top_k=5)"

assert old in content, "texte non trouve, verifier le fichier"
content = content.replace(old, new)
path.write_text(content, encoding="utf-8")
print("OK: top_k passe de 8 a 5 dans rag_extractor_rf.py")