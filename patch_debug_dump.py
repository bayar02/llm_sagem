from pathlib import Path

path = Path("rag_env/modules_rag/rag_extractor.py")
content = path.read_text(encoding="utf-8")

old = "except json.JSONDecodeError as e:\n        raise ValueError("
new = (
    "except json.JSONDecodeError as e:\n"
    "        with open(\"last_raw_response.txt\", \"w\", encoding=\"utf-8\") as f:\n"
    "            f.write(raw_response)\n"
    "        raise ValueError("
)

if old not in content:
    raise SystemExit("Bloc non trouve.")

content = content.replace(old, new)
path.write_text(content, encoding="utf-8")
print("OK: dump raw_response ajoute en cas d'echec JSON.")