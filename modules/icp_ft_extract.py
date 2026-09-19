# -*- coding: utf-8 -*-
"""
ICP FT Extractor v1.3 – Cedric Edition (patched)
------------------------------------------------
- Extraction PDF robuste (pdfminer → PyPDF2)
- Extraction du bloc SWITCH compatible ICP (ignore sommaire)
- Détection DYNAMIQUE du type (button/slider) à partir du texte ICP
- JSON SWITCH :
  - si test == false -> {"test": "false"} (pas de "type")
  - si test == true  -> {"test": "true", "type": "button|slider"}
- PATCH: reconnaissance de "privacy" comme alias de "mute" pour typer "slider" si trouvé.
"""
import json
import re
import sys
import os

# ============================================================
# 1) Extraction texte robuste (pdfminer → fallback PyPDF2)
# ============================================================

def extract_text_from_pdf(pdf_path: str) -> str:
    """Essaye pdfminer, sinon fallback PyPDF2."""
    # pdfminer.six
    try:
        from pdfminer_high_level import extract_text as pdfminer_extract  # alias alternatif
    except Exception:
        pdfminer_extract = None
    if pdfminer_extract is None:
        try:
            from pdfminer.high_level import extract_text as pdfminer_extract
        except Exception:
            pdfminer_extract = None
    if pdfminer_extract is not None:
        try:
            txt = pdfminer_extract(pdf_path) or ""
            if txt.strip():
                return txt
        except Exception:
            pass
    # PyPDF2 fallback
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(pdf_path)
        parts = []
        for p in reader.pages:
            try:
                t = p.extract_text()
                if t:
                    parts.append(t)
            except Exception:
                continue
        return "\n".join(parts)
    except Exception:
        return ""

# ============================================================
# 2) Extraction du bloc SWITCH robuste (tous ICP)
# ============================================================
# Lignes de sommaire : ".... 13"
TOC_DOTS_RE = re.compile(r"\.{2,}\s*\d{1,4}\b")
# Début flexible : mots cassés, CR/LF, underscores, puces…
START_SWITCH_RE = re.compile(
    r"RQT[\W_\n]*SHW[\W_\n]*FPANEL[\W_\n]*SWITCH\b",
    re.IGNORECASE
)
# Fin préférée du bloc
END_RQT_RE = re.compile(r"\bRQT[\W_\n]*END\b", re.IGNORECASE)
# Fin de secours : prochain chapitre numéroté “7.2 / 7.2.1…”
NEXT_HEADING_RE = re.compile(r"^\s*\d+(?:\.\d+){1,}\b", re.MULTILINE)

def extract_switch_block(pdf_text: str) -> str:
    """
    Extrait le bloc réel SWITCH en ignorant le sommaire.
    - Start : RQT_SHW_FPANEL_SWITCH (tolérant)
    - Fin   : RQT_END ou prochain chapitre numéroté
    """
    for m in START_SWITCH_RE.finditer(pdf_text):
        start = m.start()
        after = m.end()
        # Sommaire ? (pointillés + numéro à proximité du titre)
        lookahead = pdf_text[start:start+200]
        is_toc = TOC_DOTS_RE.search(lookahead)
        # Vrai bloc si RQT_END existe à proximité
        rqt_end_ahead = END_RQT_RE.search(pdf_text, start, start + 4000)
        # Ligne du sommaire → on la saute
        if is_toc and not rqt_end_ahead:
            continue
        # 1) Fin = RQT_END
        if rqt_end_ahead:
            return pdf_text[start:rqt_end_ahead.end()]
        # 2) Fin de secours = prochain titre numéroté
        m_hdr = NEXT_HEADING_RE.search(pdf_text, after)
        if m_hdr:
            return pdf_text[start:m_hdr.start()]
    return ""

# ============================================================
# 3) SWITCH : présence + type dynamiques (basés ICP)
# ============================================================

def detect_switch_presence(block: str) -> dict:
    """
    Détecte la présence des fonctions (true/false) depuis le bloc :
    - Standby_button
    - Reset_button
    - Pairing_button
    - Mute_button (inclut alias privacy)
    """
    out = {
        "Standby_button": "false",
        "Reset_button": "false",
        "Pairing_button": "false",
        "Mute_button": "false"
    }
    if not block:
        return out
    # Présence Standby (certaines ICP mentionnent 'standby' ou 'power')
    if re.search(r'\bstandby\b|\bpower\b|\bservice2\b', block, re.IGNORECASE):
        out["Standby_button"] = "true"
    # Présence Reset / Service
    if re.search(r'\breset\b|\bservice\b|\bservice1\b', block, re.IGNORECASE):
        out["Reset_button"] = "true"
    # Présence Pairing
    if re.search(r'\bpair(?:ing)?\b', block, re.IGNORECASE):
        out["Pairing_button"] = "true"
    # Présence Mute / Privacy
    if re.search(r'\bmute\b|\bprivacy\b', block, re.IGNORECASE):
        out["Mute_button"] = "true"
    return out


def detect_switch_types(block: str) -> dict:
    """
    Détecte le TYPE (button/slider) des items tels qu'ils sont décrits dans l'ICP.
    Exemple d'ICP :
    - read button "reset"
    - top button "pairing"
    - top slider "privacy" (alias mute)

    Retourne un dict par nom canonique (sans suffixe '_button') :
    {"reset": "button", "pairing": "button", "mute": "slider"}
    """
    types = {}
    if not block:
        return types
    # Autorise quotes droits et typographiques
    # Capture (button|slider) puis un nom (reset|pairing|mute|standby|privacy)
    pattern = re.compile(
        r'(button|slider)[^a-zA-Z0-9]{0,50}["“]?\s*(standby|reset|pairing|mute|privacy)\s*["”]?',
        re.IGNORECASE
    )
    for m in pattern.finditer(block):
        ctrl_type = m.group(1).lower()  # "button" ou "slider"
        name = m.group(2).lower()       # "reset" / "pairing" / "mute" / "standby" / "privacy"
        # Normalisation : "privacy" est un alias de "mute"
        if name == "privacy":
            name = "mute"
        types[name] = ctrl_type

    # Heuristique complémentaire : si on voit explicitement 'slider' et 'privacy' à proximité (< 80 chars)
    if "mute" not in types:
        prox = re.search(r'slider[^\n]{0,80}privacy|privacy[^\n]{0,80}slider', block, re.IGNORECASE)
        if prox:
            types["mute"] = "slider"

    return types


def build_switch_json(block: str) -> dict:
    """
    Construit le JSON SWITCH final en appliquant les règles :
    - test == "false" -> {"test": "false"} (sans "type")
    - test == "true"  -> {"test": "true", "type": "<button|slider>"} si le type est déterminé
                          sinon fallback -> {"test": "true", "type": "button"}
      (fallback utile si l'ICP omet explicitement le type mais qu'on voit le test)
    """
    presence = detect_switch_presence(block)
    detected_types = detect_switch_types(block)  # clés : reset/pairing/mute/standby
    final = {}
    for key, present in presence.items():
        if present == "false":
            final[key] = {"test": "false"}
            continue
        # Ex: "Reset_button" -> base "reset"
        base = key.replace("_button", "").replace("_", "").lower()
        # Type depuis le texte ICP (prioritaire)
        ctrl_type = detected_types.get(base)
        # Si type non détecté mais feature présente → fallback "button"
        if ctrl_type:
            final[key] = {"test": "true", "type": ctrl_type}
        else:
            final[key] = {"test": "true", "type": "button"}
    return final

# ============================================================
# 4) Structures des autres tests FT
# ============================================================
TEST_STRUCTURE = {
    "HDMI": {
        "EDID_test": r"EDID|HDMI_ReceiverEdid",
        "CEC_test": r"\bCEC\b",
        "VideoPattern_test": r"HDMI[\W_\n]*VIDEO[\W_\n]*ANALYSIS"
    },
    "USB": {
        # Aligne le nom sur l'exemple d'exécution utilisateur
        "USB_device_detection_test": r"USB.*CheckDevice|USB device detection",
        "USB_file_reading_test": r"USB.*READING|transfer",
        "USB_overcurrent_test": r"over.?current|USB current"
    },
    "IR": {
        "Reception_IR_keycodes": r"INFRARED|IR receiver|IR key"
    },
    "LED": {
        "LED_test": r"\bLED\b"
    },
    "NAND": {
        "NAND_read_ID_test": r"NAND.*read.*ID|Flash.?NAND.*read.*ID"
    },
    "RADIATED": {
        "Bluetooth_radiated_test": r"RADIATED.*Bluetooth",
        "WiFi2G_radiated_test": r"RADIATED.*2\.4|2412MHz",
        "WiFi5G_radiated_test": r"RADIATED.*5G|5180MHz"
    }
}

# ============================================================
# 5) Extraction globale FT
# ============================================================


# ============================================================
# 4bis) Ethernet: détection Fast/Giga depuis la limite MAX de BWD_Ethernet_Ping_PC (ICP)
# ============================================================

def _to_float(s: str):
    """Convertit '30', '30.0' ou '30,0' en float, sinon None."""
    try:
        return float(s.replace(',', '.'))
    except Exception:
        return None

def _is_close(x: float, target: float, tol: float) -> bool:
    """Comparaison tolérante pour accepter les variantes (30/30.0/30,0, etc.)."""
    return x is not None and abs(x - target) <= tol

def detect_ethernet_from_icp_max_limit(pdf_text: str) -> dict:
    """
    ICP = spécification : pas de mesure réelle, uniquement des limites.
    On distingue Fast/Giga UNIQUEMENT via la limite MAX de BWD_Ethernet_Ping_PC.

    Règle Cedric (tolérante aux variantes) :
      - si MAX ≈ 30 ms => Fast_Ethernet_ping_test = true
      - si MAX ≈ 3  ms => Giga_Ethernet_ping_test = true

    Valeurs par défaut : false/false.
    """
    out = {
        "Giga_Ethernet_ping_test": "false",
        "Fast_Ethernet_ping_test": "false"
    }

    if not pdf_text:
        return out

    # Ancre tolérante aux underscores / espaces / retours lignes (extraction PDF)
    m_anchor = re.search(r"BWD[\W_\n]*Ethernet[\W_\n]*Ping[\W_\n]*PC", pdf_text, re.IGNORECASE)
    if not m_anchor:
        return out

    # Fenêtre après l'ancre : on y trouve généralement la table 'Measures' avec Min/Max/Unit.
    window = pdf_text[m_anchor.end(): m_anchor.end() + 1500]

    # On exige la présence de l'unité 'ms' pour éviter les faux positifs.
    if not re.search(r"\bms\b", window, re.IGNORECASE):
        return out

    max_val = None

    # Heuristique 1 (prioritaire) : 'Max ... <nombre>' si le mot 'Max' est bien extrait.
    m_max = re.search(r"\bMax\b.*?(\d+(?:[\.,]\d+)?)", window, re.IGNORECASE | re.DOTALL)
    if m_max:
        max_val = _to_float(m_max.group(1))

    # Heuristique 2 (fallback) : extraire des nombres proches dans la fenêtre et prendre le plus grand
    # dans une plage réaliste (0..200 ms) pour éviter d'attraper un numéro de chapitre.
    if max_val is None:
        nums = re.findall(r"(?<!\d)(\d+(?:[\.,]\d+)?)(?!\d)", window)
        candidates = []
        for s in nums:
            v = _to_float(s)
            if v is None:
                continue
            if 0 <= v <= 200:
                candidates.append(v)
        if candidates:
            max_val = max(candidates)

    if max_val is None:
        return out

    # Application de la règle Cedric, avec tolérances
    if _is_close(max_val, 3.0, tol=0.25):
        out["Giga_Ethernet_ping_test"] = "true"
    elif _is_close(max_val, 30.0, tol=0.5):
        out["Fast_Ethernet_ping_test"] = "true"

    return out

def extract_tests(pdf_path: str) -> dict:
    pdf_text = extract_text_from_pdf(pdf_path)
    json_output = {}

    # Tests génériques → "true"/"false"
    for category, tests in TEST_STRUCTURE.items():
        json_output[category] = {}
        for test_name, pattern in tests.items():
            json_output[category][test_name] = \
                "true" if re.search(pattern, pdf_text, re.IGNORECASE | re.DOTALL) else "false"
    # Ethernet (ICP) : Fast/Giga via la limite MAX de BWD_Ethernet_Ping_PC
    json_output["Ethernet"] = detect_ethernet_from_icp_max_limit(pdf_text)

    # SWITCH (format final demandé)
    switch_block = extract_switch_block(pdf_text)
    json_output["SWITCH"] = build_switch_json(switch_block)

    return json_output

# ============================================================
# 6) MAIN
# ============================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage : python ICP_FT_extract_v1.3.py <fichier_ICP.pdf>")
        sys.exit(1)
    pdf_file = sys.argv[1]
    base = os.path.splitext(os.path.basename(pdf_file))[0]
    output_json = base + "_FT_Tests.json"
    print(f"Analyse du fichier ICP : {pdf_file}")
    result = extract_tests(pdf_file)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4, ensure_ascii=False)
    print(f"\nFichier JSON généré : {output_json}\n")
    print("==================== FT TEST JSON ====================")
    print(json.dumps(result, indent=4, ensure_ascii=False))
    print("======================================================")