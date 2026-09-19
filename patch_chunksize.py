from pathlib import Path

path = Path("rag_env/modules_rag/ingest.py")
content = path.read_text(encoding="utf-8")

replacements = [
    ("CHUNK_SIZE = 800", "CHUNK_SIZE = 3000"),
    ("CHUNK_OVERLAP = 150", "CHUNK_OVERLAP = 300"),
]

for old, new in replacements:
    if old not in content:
        raise SystemExit(f"Bloc non trouve: {old!r}")
    content = content.replace(old, new)

path.write_text(content, encoding="utf-8")
print("OK: CHUNK_SIZE=3000 / CHUNK_OVERLAP=300 appliques.")