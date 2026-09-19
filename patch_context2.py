from pathlib import Path

p1 = Path("rag_env/modules_rag/rag_extractor.py")
c1 = p1.read_text(encoding="utf-8")
old1 = "top_k=12,"
new1 = "top_k=6,"
if old1 not in c1:
    raise SystemExit(f"Bloc non trouve dans rag_extractor.py: {old1!r}")
c1 = c1.replace(old1, new1)
p1.write_text(c1, encoding="utf-8")

p2 = Path("rag_env/modules_rag/llm_router.py")
c2 = p2.read_text(encoding="utf-8")
old2 = '"options": {"num_ctx": 4096, "temperature": 0},'
new2 = '"options": {"num_ctx": 8192, "temperature": 0},'
if old2 not in c2:
    raise SystemExit(f"Bloc non trouve dans llm_router.py: {old2!r}")
c2 = c2.replace(old2, new2)
p2.write_text(c2, encoding="utf-8")

print("OK: top_k=6 (rag_extractor.py) + num_ctx=8192 (llm_router.py) appliques.")