from pathlib import Path

path = Path("rag_env/modules_rag/rag_extractor.py")
content = path.read_text(encoding="utf-8")

old1 = "def extract_fe_tests_rag(pdf_path: str, product: str) -> Dict[str, Any]:"
new1 = (
    "def _try_repair_json(raw: str):\n"
    "    \"\"\"Tente de reparer un JSON tronque en ajoutant les caracteres de fermeture manquants.\"\"\"\n"
    "    suffixes = [\"\", \"}\", \"]}\", \"}]}\", \"]}}\", \"}}\", \"]}]}\", \"}]}}\"]\n"
    "    for suf in suffixes:\n"
    "        try:\n"
    "            return json.loads(raw + suf)\n"
    "        except json.JSONDecodeError:\n"
    "            continue\n"
    "    return None\n\n\n"
    "def extract_fe_tests_rag(pdf_path: str, product: str) -> Dict[str, Any]:"
)

old2 = (
    "except json.JSONDecodeError as e:\n"
    "        with open(\"last_raw_response.txt\", \"w\", encoding=\"utf-8\") as f:\n"
    "            f.write(raw_response)\n"
    "        raise ValueError("
)
new2 = (
    "except json.JSONDecodeError as e:\n"
    "        with open(\"last_raw_response.txt\", \"w\", encoding=\"utf-8\") as f:\n"
    "            f.write(raw_response)\n"
    "        repaired = _try_repair_json(raw_response)\n"
    "        if repaired is not None:\n"
    "            print(\"[rag_extractor] JSON tronque detecte, reparation automatique appliquee.\")\n"
    "            return repaired\n"
    "        raise ValueError("
)

for old, new, label in [(old1, new1, "insertion fonction"), (old2, new2, "bloc except")]:
    if old not in content:
        raise SystemExit(f"Bloc non trouve ({label}).")
    content = content.replace(old, new)

path.write_text(content, encoding="utf-8")
print("OK: reparation JSON automatique ajoutee.")