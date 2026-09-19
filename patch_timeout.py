from pathlib import Path

path = Path("rag_env/modules_rag/llm_router.py")
content = path.read_text(encoding="utf-8")

old = "timeout=300,"
new = "timeout=600,"

if old not in content:
    raise SystemExit("Bloc non trouve.")

content = content.replace(old, new)
path.write_text(content, encoding="utf-8")
print("OK: timeout porte a 600s.")