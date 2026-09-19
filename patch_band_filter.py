from pathlib import Path

path = Path("rag_env/modules_rag/rag_extractor_rf.py")
content = path.read_text(encoding="utf-8")

anchor_def = "def _extract_band_rag(pdf_path: str, product: str, band: str) -> List[dict]:"
assert content.count(anchor_def) == 1, "ancre _extract_band_rag non trouvee ou ambigue"

classify_fn = '''def _classify_passage_band(text: str) -> str:
    import re
    t = text.upper()
    freqs = [int(x) for x in re.findall(r"(\\d{4})\\s*MHZ", t)]
    has_5g_freq = any(f >= 4900 for f in freqs)
    has_24_freq = any(2400 <= f <= 2500 for f in freqs)
    has_vht = "VHT" in t
    has_bt_kw = any(kw in t for kw in ["BLUETOOTH", "DH5", "LE 1M", "PRBS", "TX_BR", "TX_BLE", "RX_BR", "RX_BLE"])
    has_wifi24_kw = ("MCS" in t) and not has_vht
    has_5g_kw = has_vht or "5GHZ" in t or "802.11AC" in t or "802.11AX" in t

    if has_5g_freq or has_5g_kw:
        return "5GHz"
    if has_bt_kw and not has_wifi24_kw:
        return "Bluetooth"
    if has_wifi24_kw and not has_bt_kw:
        return "2.4GHz"
    if has_bt_kw and has_wifi24_kw:
        return "ambiguous"
    if has_24_freq:
        return "ambiguous"
    return "unknown"


'''

content = content.replace(anchor_def, classify_fn + anchor_def)

old_retrieval = '''    passages = hybrid_search(query=BAND_QUERIES[band], product=product, top_k=5)
    context = "\\n---\\n".join(p["text"] for p in passages)'''

new_retrieval = '''    passages = hybrid_search(query=BAND_QUERIES[band], product=product, top_k=10)

    filtered = [p for p in passages if _classify_passage_band(p["text"]) in (band, "unknown")]
    dropped = len(passages) - len(filtered)
    print(f"[rag_extractor_rf] bande {band} - passages gardes : {len(filtered)}/{len(passages)} ({dropped} ecartes par classification de bande)")

    if not filtered:
        print(f"[rag_extractor_rf] bande {band} - AUCUN passage correctement classe, fallback sur les passages bruts.")
        filtered = passages

    context = "\\n---\\n".join(p["text"] for p in filtered)'''

assert old_retrieval in content, "ancre 'old_retrieval' non trouvee"
content = content.replace(old_retrieval, new_retrieval)

path.write_text(content, encoding="utf-8")
print("OK: filtre deterministe par bande ajoute a rag_extractor_rf.py")