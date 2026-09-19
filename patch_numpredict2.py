from pathlib import Path

path = Path("rag_env/modules_rag/llm_router.py")
content = path.read_text(encoding="utf-8")

old = '"options": {"num_ctx": 8192, "temperature": 0, "num_predict": 2048},'
new = '"options": {"num_ctx": 8192, "temperature": 0, "num_predict": 4096},'

assert old in content, "texte non trouve, verifier le fichier"
content = content.replace(old, new)
path.write_text(content, encoding="utf-8")
print("OK: num_predict passe de 2048 a 4096 dans llm_router.py")