#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extracteur universel FE (DVB-C, J83.B, DVB-S/S2, DVB-T/T2) depuis un ICP PDF.
Objectif: générer un JSON "FE_Tests" identique aux exports existants,
avec une seule évolution **sans régression** :
 - Lorsque l'ICP indique **N/A** pour Min/Max (ex.: Test_2_BER @ 1550MHz 8PSK DVB-S2),
   écrire "Min": "N/A", "Max": "N/A" dans le JSON (au lieu de nombres vides).

Correctifs 2025-12-09 :
 - RE_FREQ_LINE accepte désormais "7MHz / 8MHz" (bande passante) **ou** QAM/QPSK/8PSK
   après le "/" (format TNT de l’ICP DTIW393).
 - RE_LABEL_LINE autorise le caractère '.' (compat FE_J83.B pour DCIW377) et reste permissif.
 - RE_UNIT accepte les deux variantes BER ".10^-7" et ".10-7".
 - Alternatives regex écrites avec '|' (plus robustes).
"""

import sys
import os
import re
import json

try:
    import fitz  # PyMuPDF
except Exception as e:
    raise SystemExit("PyMuPDF (fitz) requis. Installez-le avec: pip install pymupdf")

# ---------------------------------------------------------------------------
# Regex (robustes, mais conservatrices vis‑à‑vis de la logique existante)
# ---------------------------------------------------------------------------

RE_TEST_HEADER = re.compile(r"Test\#\s*(\d+)", re.IGNORECASE)

# ex.: "Frequency 198.5MHz / 7MHz DVB-T test signal" ou "Frequency 586MHz / 64QAM DVB-T"
RE_FREQ_LINE = re.compile(
    r"Frequency\s*([0-9]+(?:\.[0-9]+)?)\s*MHz\s*/\s*"
    r"(?:(\d+(?:MHz)?)|(QPSK|8PSK|(?:\d+QAM)))\s*"
    r"(DVB[\s-]?T2|DVB[\s-]?T|DVB[\s-]?S2|DVB[\s-]?S|DVB-?C|J83\.B)",
    re.IGNORECASE,
)

# ex.: "FEDVB-TT2 198.5MHz : Viterbi BER" / "FE_J83.B 111MHz: RSSI" / "FE SAT 1550 MHz: ..."
RE_LABEL_LINE = re.compile(
    r"(?:FE[\w\-\.\s]*|FEDVB[\w\-\.\s]*)\s*[0-9]+(?:\.[0-9]+)?\s*MHz\s*:\s*(.+)",
    re.IGNORECASE,
)

RE_NUMBER = re.compile(r"-?\d+(?:[.,]\d+)?")

# Unités (inclut l’écriture de BER ".10^-7" et ".10-7")
RE_UNIT = re.compile(r"\b(dBm|dB|kHz|ppm|%|none|\.10\^-?7|\.10-7|Hz)\b", re.IGNORECASE)

EXPECTED_PARAMS = [
    "Viterbi BER",
    "Uncorrected blocks",
    "RSSI",
    "Carrier-to-Noise Ratio",
    "Frequency Offset",
    "Rate Offset",
]

def norm(s: str) -> str:
    return (s or "").replace("\u00a0", " ").strip()

# ---------------------------------------------------------------------------
# Localiser la plage FE dans le PDF
# ---------------------------------------------------------------------------

def find_fe_range(doc):
    start = None
    end = None

    # 1) Page contenant le premier Test#
    for p in range(doc.page_count):
        if RE_TEST_HEADER.search(doc[p].get_text("text")):
            start = p
            break

    # 2) Fallback: première page contenant une ligne Frequency...
    if start is None:
        for p in range(doc.page_count):
            if RE_FREQ_LINE.search(doc[p].get_text("text")):
                start = p
                break

    # 3) Fallback: page contenant un préfixe FE connu
    if start is None:
        for p in range(doc.page_count):
            if re.search(r"(FE|FEDVB)", doc[p].get_text("text"), re.IGNORECASE):
                start = p
                break

    if start is None:
        raise ValueError("Section FE introuvable dans le PDF.")

    # Fin approximative: avant un chapitre fonctionnel générique
    for p in range(start + 1, doc.page_count):
        t = doc[p].get_text("text")
        if re.search(r"(GetPid|FUNCTIONAL TEST)", t, re.IGNORECASE):
            end = p
            break

    if end is None:
        end = min(start + 5, doc.page_count - 1)

    return start, end

# ---------------------------------------------------------------------------
# Extraction FE (+ gestion N/A)
# ---------------------------------------------------------------------------

def extract_fe_tests(text: str):
    lines = [norm(l) for l in text.splitlines() if norm(l)]
    tests = []
    current = None
    i = 0

    while i < len(lines):
        line = lines[i]

        # Détecter Test#
        mtest = RE_TEST_HEADER.search(line)
        if mtest:
            if current:
                tests.append(current)
            current = {
                "Test": f"Test#{mtest.group(1)}",
                "Frequency": "",
                "Modulation": "",
                "Limits": [],
            }

            # Chercher la ligne "Frequency ... / ..." dans les ~20 lignes suivantes
            for j in range(i, min(i + 20, len(lines))):
                mf = RE_FREQ_LINE.search(lines[j])
                if mf:
                    freq = f"{mf.group(1)}MHz"
                    scheme_or_bw = norm((mf.group(2) or mf.group(3))).upper()
                    system = norm(mf.group(4)).upper().replace(" ", "-")
                    current["Frequency"] = freq
                    current["Modulation"] = f"{scheme_or_bw} {system}"
                    break

            i += 1
            continue

        # Sinon, détecter une ligne de libellé "FE... MHz : Param"
        if current:
            mlabel = RE_LABEL_LINE.search(line)
            if mlabel:
                param = norm(mlabel.group(1))
                if param in EXPECTED_PARAMS:
                    nums = []
                    unit = ""
                    has_na = False

                    # Lire les ~6 lignes suivantes pour y trouver Min/Max ou N/A et l'unité
                    for k in range(i + 1, min(i + 7, len(lines))):
                        ln = lines[k]
                        nums += [n.replace(",", ".") for n in RE_NUMBER.findall(ln)]

                        mu = RE_UNIT.search(ln)
                        if mu and not unit:
                            unit = mu.group(1)

                        if re.search(r"\bN/?A\b", ln, re.IGNORECASE):
                            has_na = True

                        # Si une nouvelle étiquette ou un nouveau test commence, on s'arrête
                        if RE_LABEL_LINE.search(ln) or RE_TEST_HEADER.search(ln):
                            break

                    if has_na:
                        minv, maxv = "N/A", "N/A"
                    elif len(nums) >= 2:
                        minv, maxv = nums[0], nums[1]
                    else:
                        minv = maxv = ""

                    current["Limits"].append({
                        "Parameter": param,
                        "Min": minv,
                        "Max": maxv,
                        "Unit": unit,
                    })

        i += 1

    if current:
        tests.append(current)

    # Filtrer tests trop incomplets (cohérent avec logique initiale)
    tests = [t for t in tests if len(t.get("Limits", [])) >= 4]

    # Ordonner les limites selon EXPECTED_PARAMS
    order = {p: idx for idx, p in enumerate(EXPECTED_PARAMS)}
    for t in tests:
        t["Limits"].sort(key=lambda x: order.get(x.get("Parameter", ""), 99))

    return tests

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python ICP_FE_extract_v3.py <fichier.pdf> [--out <fic.json>]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    out_path = None
    if len(sys.argv) >= 4 and sys.argv[2] == "--out":
        out_path = sys.argv[3]

    doc = fitz.open(pdf_path)
    try:
        start, end = find_fe_range(doc)
        print(f"[DEBUG] FE pages détectées : {start} → {end}")
    except ValueError as e:
        print(f"[WARN] {e} -> analyse complète du document")
        start, end = 0, doc.page_count - 1

    text = "\n".join(doc[p].get_text("text") for p in range(start, end + 1))
    fe_tests = extract_fe_tests(text)

    if not out_path:
        base = os.path.splitext(os.path.basename(pdf_path))[0]
        out_path = base + "_FE_Tests.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"FE_Tests": fe_tests}, f, indent=2, ensure_ascii=False)

    # Rapport console minimal
    print("\n================ FE EXTRACTION REPORT ================")
    print(f"Source PDF : {pdf_path}")
    print(f"Total tests détectés : {len(fe_tests)}\n")
    for t in fe_tests:
        print(f"{t['Test']}  |  {t['Frequency']}  |  {t['Modulation']}")
        for lim in t["Limits"]:
            print(
                f"   - {lim['Parameter']}: Min={lim['Min']}  Max={lim['Max']}  Unit={lim['Unit']}"
            )
        print()
    print("======================================================")
    print(f"\n📄 JSON généré : {out_path}")
    print("======================================================\n")

if __name__ == "__main__":
    main()
