from pathlib import Path

path = Path("rag_env/modules_rag/rag_extractor.py")
content = path.read_text(encoding="utf-8")

# 1. Revert the rule that caused DVB-mislabeling hallucinations
bad_addition = '''

Tres important - ne pas halluciner de tests FE : les tests FE authentiques utilisent
TOUJOURS une Modulation de type DVB-C, DVB-S, DVB-S2, DVB-T ou DVB-T2, et des parametres
parmi Viterbi BER, Uncorrected blocks, RSSI, Carrier-to-Noise Ratio, Frequency Offset,
Rate Offset. Si les extraits fournis ne contiennent AUCUNE donnee correspondant a ce
format (par exemple s'ils ne contiennent que des donnees RF Wi-Fi ou Bluetooth, avec des
parametres comme Power, EVM, MASK, PER, LO Leakage, Frequency drift, Frequency tolerance,
ou une Modulation de type PRBS/MCS/HT/vHT), alors ce document n'a PAS de section FE :
retourne "FE_Tests": [] (liste vide). Ne jamais reutiliser des donnees RF Wi-Fi/Bluetooth
comme si elles etaient des tests FE.'''

if bad_addition not in content:
    raise SystemExit("Ancienne regle non trouvee - deja revertie ?")
content = content.replace(bad_addition, "")

# 2. Add a deterministic pre-filter: skip the LLM entirely if no genuine DVB marker is retrieved
old2 = 'context = "\\n---\\n".join(p["text"] for p in passages)'
new2 = old2 + '''

    if "DVB" not in context.upper():
        print("[rag_extractor] Aucun marqueur DVB dans les passages recuperes - pas de section FE, retour direct d'une liste vide (LLM non appele).")
        return {"FE_Tests": []}'''

if old2 not in content:
    raise SystemExit("Bloc old2 non trouve.")
content = content.replace(old2, new2)

path.write_text(content, encoding="utf-8")
print("OK: regle hallucinante revertie + filtre DVB deterministe ajoute.")