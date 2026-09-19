from pathlib import Path

path = Path("rag_env/modules_rag/llm_router.py")
content = path.read_text(encoding="utf-8")

old = '"options": {"num_ctx": 4096},'
new = '"options": {"num_ctx": 4096, "temperature": 0},'

if old not in content:
    raise SystemExit("Bloc non trouve - le fichier a peut-etre deja ete modifie.")

content = content.replace(old, new)
path.write_text(content, encoding="utf-8")
print("OK: temperature=0 ajoute au bloc Ollama.")