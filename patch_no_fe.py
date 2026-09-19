from pathlib import Path

path = Path("rag_env/modules_rag/rag_extractor.py")
content = path.read_text(encoding="utf-8")

old = '''Si une limite est indiquée "N/A" dans le document, retourne "Min": "N/A", "Max": "N/A"
(ne jamais inventer de valeur numérique).'''

new = old + '''

Tres important - ne pas halluciner de tests FE : les tests FE authentiques utilisent
TOUJOURS une Modulation de type DVB-C, DVB-S, DVB-S2, DVB-T ou DVB-T2, et des parametres
parmi Viterbi BER, Uncorrected blocks, RSSI, Carrier-to-Noise Ratio, Frequency Offset,
Rate Offset. Si les extraits fournis ne contiennent AUCUNE donnee correspondant a ce
format (par exemple s'ils ne contiennent que des donnees RF Wi-Fi ou Bluetooth, avec des
parametres comme Power, EVM, MASK, PER, LO Leakage, Frequency drift, Frequency tolerance,
ou une Modulation de type PRBS/MCS/HT/vHT), alors ce document n'a PAS de section FE :
retourne "FE_Tests": [] (liste vide). Ne jamais reutiliser des donnees RF Wi-Fi/Bluetooth
comme si elles etaient des tests FE.'''

if old not in content:
    raise SystemExit("Bloc non trouve.")

content = content.replace(old, new)
path.write_text(content, encoding="utf-8")
print("OK: regle anti-hallucination FE ajoutee.")