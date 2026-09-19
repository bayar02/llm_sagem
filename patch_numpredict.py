from pathlib import Path

path = Path("rag_env/modules_rag/llm_router.py")
content = path.read_text(encoding="utf-8")

old = '"options": {"num_ctx": 8192, "temperature": 0},'
new = '"options": {"num_ctx": 8192, "temperature": 0, "num_predict": 2048},'

if old not in content:
    raise SystemExit("Bloc non trouve.")

content = content.replace(old, new)
path.write_text(content, encoding="utf-8")
print("OK: num_predict=2048 ajoute.")