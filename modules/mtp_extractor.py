#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MTP Extractor — Analyse code des PDFs MTP PEGATRON
===================================================
Extrait les spécifications de test depuis les PDFs Manufacturing Test Plan
au format PEGATRON (produits Sagemcom DIW252, DIW253, DCIW377, DCIW378…).

Sections extraites :
  - Board Level ICT : tensions (Signal / TestPoint / Min / Max)
  - RF Test         : Bluetooth TX/RX et Wi-Fi TX/RX (2.4GHz + 5GHz)
  - System Test     : USB, Ethernet, HDMI, LED, BT radiated, Wi-Fi radiated
  - FW Upgrade      : PASS/FAIL items
  - Final Check     : PASS/FAIL items
  - Métadonnées     : produit, version, date, ICP ref

Format de sortie : dict JSON-sérialisable, structuré par section.
"""

import re
import io
from typing import Any, Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────
#  PATTERNS GLOBAUX
# ─────────────────────────────────────────────────────────────

# Tension ICT : SIGNAL\nPTXXXX\nMIN\nMAX[\nICP_REF]
RE_VOLTAGE = re.compile(
    r'([A-Z][A-Z0-9_]{2,35})\s*\n'      # Signal name
    r'(PT\d+\w*)\s*\n'                   # Test point
    r'(-?[\d.,]+)\s*\n'                  # Lower limit
    r'(-?[\d.,]+)\s*\n',                 # Upper limit
    re.MULTILINE
)

# BT TX power line : BTTXxxx\nF: XXXX MHz\nMODULATION\n...target: X\nMIN\nMAX
RE_BT_TX = re.compile(
    r'(BTTX\d+)\s*\n'
    r'F\s*:\s*(\d+)\s*MHz\s*\n'
    r'([\w\s\-]+?PRBS)\s*\n'
    r'.*?target:\s*([\d.]+)\s*\n'
    r'(-?[\d.]+)\s*\n'
    r'(-?[\d.]+)',
    re.MULTILINE | re.DOTALL
)

# BT parameter line : BTTXxxx/BTRXxxx\nPARAMETER\nMIN\nMAX
RE_BT_PARAM = re.compile(
    r'(BTTX\d+|BTRX\d+)\s*\n'
    r'([^\n]{4,60}?)\s*\n'
    r'(-?[\d.]+)\s*\n'
    r'(-?[\d.]+)',
    re.MULTILINE
)

# Wi-Fi TX test block header : "Test TX_2G_1 : MCS0 HT20 …"
RE_WIFI_TX_HEADER = re.compile(
    r'Test\s+(TX_\w+)\s*:?\s*(.+?)\n'
    r'.*?Frequency:\s*(\d+)\s*\n'
    r'.*?(?:Power|Average Power)[^:\n]*:?\s*([\d.]+)\s*\n'
    r'(-?[\d.]+\s*dBm?)\s*\n'
    r'(-?[\d.]+\s*dBm?)',
    re.MULTILINE | re.IGNORECASE | re.DOTALL
)

# Wi-Fi WFTX parameter lines : WFTXxxx\nEVM, Target...\nNA\n-5 dB
RE_WIFI_PARAM = re.compile(
    r'(WFTX\d+|WFRX\d+)\s*\n'
    r'([^\n]{3,60}?)\s*\n'
    r'([^\n]{1,20}?)\s*\n'
    r'([^\n]{1,20})',
    re.MULTILINE
)

# Wi-Fi RX : "Test RX_2G_1 … Frequency:2412 … MCS0 HT20 -93dBm \n 0 \n 10"
RE_WIFI_RX = re.compile(
    r'Test\s+(RX_\w+)\s*:?\s*(.+?)\n'
    r'(?:.*?)\n'
    r'RX Power@PER<10%\s*\n'
    r'Frequency:\s*(\d+)\s*\n'
    r'(.+?)\s*\n'
    r'(-?[\d.]+)\s*\n'
    r'(-?[\d.]+)',
    re.MULTILINE | re.IGNORECASE | re.DOTALL
)

# Alternative RX pattern (inline)
RE_WIFI_RX2 = re.compile(
    r'(WFTX\d+|WFRX\d+)\s*\n'
    r'RX Power@PER<\s*10%\s*\n'
    r'Frequency:\s*(\d+)\s*\n'
    r'(.+?-\d+dBm.*?)\s*\n'
    r'(-?[\d.]+)\s*\n'
    r'(-?[\d.]+)',
    re.MULTILINE | re.DOTALL
)

# System test items (numeric limits)
RE_SYS_NUMERIC = re.compile(
    r'((?:WIFI|BT|USB|Ethernet|Check Temp)[^\n]+)\s*\n'
    r'([^\n]+)\s*\n'
    r'(-?[\d.]+)\s*\n'
    r'(-?[\d.]+)',
    re.MULTILINE | re.IGNORECASE
)

# PASS/FAIL items
RE_PASS_FAIL = re.compile(
    r'([^\n]{5,60}?)\s*\n'
    r'([^\n]{3,40}?)\s*\n'
    r'PASS/FAIL',
    re.MULTILINE
)

# Product metadata
RE_VERSION = re.compile(r'Version\s+number\s+([\d.]+)', re.IGNORECASE)
RE_RELEASE  = re.compile(r'Release\s+Date\s+(\d{4}/\d{2}/\d{2})', re.IGNORECASE)
RE_PRODUCT  = re.compile(r'SAGEMCOM\s+([\w_]+)', re.IGNORECASE)
RE_ICP_REF  = re.compile(r'ICP[_\s]+(V?[\d.]+)', re.IGNORECASE)


# ─────────────────────────────────────────────────────────────
#  UTILITAIRES
# ─────────────────────────────────────────────────────────────

def _to_float(s: str) -> Optional[float]:
    """Convertit une string (ex: '17.5 dBm', '-25 ppm', 'NA') en float."""
    if not s: return None
    s = s.strip().upper()
    if s in ('NA', 'N/A', 'PASS', ''):
        return None
    # Extraire le premier nombre
    m = re.search(r'-?[\d.]+', s)
    if m:
        try:
            return float(m.group())
        except ValueError:
            pass
    return None


def _clean(s: str) -> str:
    """Nettoie une string de texte."""
    return re.sub(r'\s+', ' ', s.strip())


def _extract_pdf_text(pdf_input) -> str:
    """
    Extrait le texte de toutes les pages d'un PDF.
    pdf_input peut être : bytes, str (chemin), ou objet fitz.Document.
    """
    try:
        import fitz
        if isinstance(pdf_input, bytes):
            doc = fitz.open(stream=pdf_input, filetype="pdf")
        elif isinstance(pdf_input, str):
            doc = fitz.open(pdf_input)
        else:
            doc = pdf_input  # Already a fitz.Document

        pages = []
        for i in range(doc.page_count):
            pages.append(doc[i].get_text("text"))
        return "\n".join(pages)
    except Exception as e:
        return f"[PDF extraction error: {e}]"


def _find_section(text: str, *markers: str) -> Tuple[int, int]:
    """
    Trouve la position d'une section dans le texte.
    Retourne (start, end) ou (-1, -1) si non trouvé.
    """
    for marker in markers:
        idx = text.lower().find(marker.lower())
        if idx >= 0:
            return idx, len(text)
    return -1, -1


# ─────────────────────────────────────────────────────────────
#  EXTRACTEURS PAR SECTION
# ─────────────────────────────────────────────────────────────

def _extract_voltages(text: str) -> List[Dict]:
    """Extrait les tensions ICT (BoardLevel section)."""
    results = []
    seen = set()

    for m in RE_VOLTAGE.finditer(text):
        signal = m.group(1).strip()
        tp     = m.group(2).strip()
        vmin   = _to_float(m.group(3))
        vmax   = _to_float(m.group(4))

        # Filtrer les faux positifs (test points AI, NI, etc.)
        if any(x in signal for x in ['NI', 'AI', 'Dev', 'Qty', 'ICP']):
            continue
        if vmin is None or vmax is None:
            continue
        # Éviter les doublons (même signal + mêmes limites)
        key = f"{signal}_{vmin}_{vmax}"
        if key in seen:
            continue
        seen.add(key)

        results.append({
            "Signal":    signal,
            "TestPoint": tp,
            "Min":       vmin,
            "Max":       vmax,
            "Unit":      "V",
            "Category":  "voltage",
        })

    return results


def _extract_bt_tests(text: str) -> List[Dict]:
    """Extrait les tests Bluetooth TX et RX."""
    results = []
    seen = set()

    # TX power entries
    for m in RE_BT_TX.finditer(text):
        item_id    = m.group(1)
        freq       = int(m.group(2))
        modulation = _clean(m.group(3))
        target     = _to_float(m.group(4))
        vmin       = _to_float(m.group(5))
        vmax       = _to_float(m.group(6))
        key = f"TX_{freq}_{modulation}_{vmin}_{vmax}"
        if key in seen: continue
        seen.add(key)
        results.append({
            "ItemID":     item_id,
            "Direction":  "TX",
            "Frequency":  freq,
            "Modulation": modulation,
            "Parameter":  "Average Power",
            "Target":     target,
            "Min":        vmin,
            "Max":        vmax,
            "Unit":       "dBm",
            "Category":   "bluetooth",
        })

    # TX/RX parameter lines (freq drift, BER, PER, etc.)
    current_freq = None
    current_mod  = None
    for m in RE_BT_PARAM.finditer(text):
        item_id = m.group(1)
        param   = _clean(m.group(2))
        vmin    = _to_float(m.group(3))
        vmax    = _to_float(m.group(4))

        # Filtrer les entrées déjà couvertes par la puissance
        if "power" in param.lower() or vmin is None or vmax is None:
            continue
        if vmin == vmax and vmin == 0:
            continue

        direction = "RX" if item_id.startswith("BTRX") else "TX"
        key = f"{item_id}_{param}_{vmin}_{vmax}"
        if key in seen: continue
        seen.add(key)

        unit = "%" if "ber" in param.lower() or "per" in param.lower() else (
               "kHz" if "drift" in param.lower() or "deviation" in param.lower() else "")

        results.append({
            "ItemID":     item_id,
            "Direction":  direction,
            "Frequency":  None,
            "Modulation": None,
            "Parameter":  param,
            "Target":     None,
            "Min":        vmin,
            "Max":        vmax,
            "Unit":       unit,
            "Category":   "bluetooth",
        })

    return results


def _extract_wifi_tests(text: str) -> List[Dict]:
    """Extrait les tests Wi-Fi TX et RX (2.4GHz et 5GHz)."""
    results = []
    seen    = set()

    # TX blocks
    for m in RE_WIFI_TX_HEADER.finditer(text):
        test_name  = m.group(1)
        modulation = _clean(m.group(2))
        freq       = int(m.group(3))
        target     = _to_float(m.group(4))
        vmin       = _to_float(m.group(5))
        vmax       = _to_float(m.group(6))
        band       = "5GHz" if freq >= 5000 else "2.4GHz"

        if vmin is None or vmax is None: continue
        key = f"TX_{freq}_{modulation}_{vmin}_{vmax}"
        if key in seen: continue
        seen.add(key)

        results.append({
            "TestName":   test_name,
            "Direction":  "TX",
            "Band":       band,
            "Frequency":  freq,
            "Modulation": modulation,
            "Parameter":  "Power",
            "Target":     target,
            "Min":        vmin,
            "Max":        vmax,
            "Unit":       "dBm",
            "Category":   "wifi",
        })

    # WFTX parameter lines (EVM, MASK, Freq tolerance, Carrier suppression)
    for m in RE_WIFI_PARAM.finditer(text):
        item_id = m.group(1)
        param   = _clean(m.group(2))
        v_low   = m.group(3).strip()
        v_high  = m.group(4).strip()

        # Skip TX power entries (already captured) and PASS/PASS
        if "power" in param.lower(): continue
        if v_low.upper() in ("PASS","NA","") and v_high.upper() in ("PASS","NA",""): continue

        vmin = _to_float(v_low)
        vmax = _to_float(v_high)
        if vmin is None and vmax is None: continue

        unit = ""
        if "evm" in param.lower(): unit = "dB"
        elif "ppm" in v_low.lower() or "ppm" in v_high.lower(): unit = "ppm"
        elif "db" in v_high.lower(): unit = "dB"

        key = f"{item_id}_{param}_{vmin}_{vmax}"
        if key in seen: continue
        seen.add(key)

        results.append({
            "TestName":   item_id,
            "Direction":  "TX",
            "Band":       None,
            "Frequency":  None,
            "Modulation": None,
            "Parameter":  param,
            "Target":     None,
            "Min":        vmin,
            "Max":        vmax,
            "Unit":       unit,
            "Category":   "wifi",
        })

    # RX blocks (PER)
    for m in RE_WIFI_RX.finditer(text):
        test_name  = m.group(1)
        modulation = _clean(m.group(2))
        freq       = int(m.group(3))
        spec_str   = _clean(m.group(4))
        vmin       = _to_float(m.group(5))
        vmax       = _to_float(m.group(6))
        band       = "5GHz" if freq >= 5000 else "2.4GHz"

        if vmin is None or vmax is None: continue
        key = f"RX_{freq}_{modulation}_{vmin}_{vmax}"
        if key in seen: continue
        seen.add(key)

        results.append({
            "TestName":   test_name,
            "Direction":  "RX",
            "Band":       band,
            "Frequency":  freq,
            "Modulation": _clean(spec_str),
            "Parameter":  "PER",
            "Target":     None,
            "Min":        vmin,
            "Max":        vmax,
            "Unit":       "%",
            "Category":   "wifi",
        })

    # Alternative RX pattern
    for m in RE_WIFI_RX2.finditer(text):
        item_id = m.group(1)
        freq    = int(m.group(2))
        spec    = _clean(m.group(3))
        vmin    = _to_float(m.group(4))
        vmax    = _to_float(m.group(5))
        band    = "5GHz" if freq >= 5000 else "2.4GHz"

        if vmin is None or vmax is None: continue
        key = f"RX2_{freq}_{spec}_{vmin}_{vmax}"
        if key in seen: continue
        seen.add(key)

        results.append({
            "TestName":   item_id,
            "Direction":  "RX",
            "Band":       band,
            "Frequency":  freq,
            "Modulation": spec,
            "Parameter":  "PER",
            "Target":     None,
            "Min":        vmin,
            "Max":        vmax,
            "Unit":       "%",
            "Category":   "wifi",
        })

    return results


def _extract_system_tests(text: str) -> List[Dict]:
    """Extrait les tests System (items numériques + PASS/FAIL)."""
    results = []
    seen    = set()

    # Rechercher la section System Test
    sys_start, _ = _find_section(text, "Test Items & criteria\nTest Item", "TEST ITEMS & CRITERIA")
    if sys_start < 0:
        sys_start = 0
    section = text[sys_start:sys_start + 5000]

    # Items numériques
    for m in RE_SYS_NUMERIC.finditer(section):
        name  = _clean(m.group(1))
        remark = _clean(m.group(2))
        vmin   = _to_float(m.group(3))
        vmax   = _to_float(m.group(4))

        if vmin is None or vmax is None: continue
        key = f"{name}_{vmin}_{vmax}"
        if key in seen: continue
        seen.add(key)

        # Déterminer catégorie et unité
        nl = name.lower()
        unit = ("dBm" if "bt" in nl or "wifi" in nl else
                "ms"  if "ethernet" in nl or "ping" in nl else
                "kB/s" if "usb" in nl and "read" in nl else "")

        results.append({
            "Name":     name,
            "Remark":   remark,
            "Min":      vmin,
            "Max":      vmax,
            "Unit":     unit,
            "Pass_Fail": False,
            "Category": "system",
        })

    # Items PASS/FAIL
    for m in RE_PASS_FAIL.finditer(section):
        name   = _clean(m.group(1))
        remark = _clean(m.group(2))
        # Filtrer les faux positifs
        if any(x in name.lower() for x in ['copyright', 'version', 'pegatron', 'page', 'limit']):
            continue
        if len(name) < 4: continue
        key = f"PF_{name}"
        if key in seen: continue
        seen.add(key)

        results.append({
            "Name":      name,
            "Remark":    remark,
            "Min":       None,
            "Max":       None,
            "Unit":      "",
            "Pass_Fail": True,
            "Category":  "system",
        })

    return results


def _extract_fw_tests(text: str) -> List[Dict]:
    """Extrait les items FW Upgrade et Final Check (PASS/FAIL)."""
    results = []
    seen    = set()

    # Chercher section FW Upgrade
    fw_start = text.lower().find("fw upgrade")
    if fw_start < 0:
        fw_start = text.lower().find("fw upgrade")
    if fw_start < 0:
        fw_start = 0

    section = text[fw_start:fw_start + 3000]

    for m in RE_PASS_FAIL.finditer(section):
        name   = _clean(m.group(1))
        remark = _clean(m.group(2))
        if any(x in name.lower() for x in ['copyright', 'version number', 'pegatron', 'screen', 'cable']):
            continue
        if len(name) < 4: continue
        key = f"FW_{name}"
        if key in seen: continue
        seen.add(key)

        results.append({
            "Name":     name,
            "Remark":   remark,
            "Category": "fw_upgrade",
        })

    return results


def _extract_metadata(text: str) -> Dict[str, str]:
    """Extrait les métadonnées du document MTP."""
    meta = {}

    m = RE_VERSION.search(text[:2000])
    if m: meta["version"] = m.group(1).strip()

    m = RE_RELEASE.search(text[:2000])
    if m: meta["release_date"] = m.group(1).strip()

    m = RE_PRODUCT.search(text[:1000])
    if m: meta["product"] = m.group(1).strip()

    m = RE_ICP_REF.search(text)
    if m: meta["icp_ref"] = m.group(1).strip()

    return meta


# ─────────────────────────────────────────────────────────────
#  PDFPLUMBER-BASED ICT EXTRACTION (parallel to regex)
# ─────────────────────────────────────────────────────────────

def _extract_voltages_plumber(pdf_input) -> List[Dict]:
    """
    pdfplumber-based Board Level ICT extraction.
    Uses character-level Y-position grouping for precise column reading.
    Returns same schema as _extract_voltages().
    """
    try:
        import pdfplumber
        import io as _io

        if isinstance(pdf_input, (bytes, bytearray)):
            pdf_file = _io.BytesIO(pdf_input)
        else:
            pdf_file = str(pdf_input)

        results: List[Dict] = []
        seen: set = set()

        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                chars = page.chars
                if not chars:
                    continue

                # Group characters by Y-row (tolerance = 3pt)
                rows: Dict[int, list] = {}
                for c in chars:
                    y_key = round(c["top"] / 3)
                    rows.setdefault(y_key, []).append(c)

                for _y, row_chars in sorted(rows.items()):
                    row_chars_sorted = sorted(row_chars, key=lambda c: c["x0"])
                    text = "".join(c["text"] for c in row_chars_sorted).strip()

                    # Must contain a test-point identifier
                    m_tp = re.search(r"\b(PT\d+\w*)\b", text)
                    if not m_tp:
                        continue

                    tp = m_tp.group(1)

                    # Extract all decimal numbers on the line
                    nums = re.findall(r"-?\d+[.,]\d+", text)
                    if len(nums) < 2:
                        continue

                    nums_f = [float(n.replace(",", ".")) for n in nums]
                    min_v = nums_f[-2]
                    max_v = nums_f[-1]

                    # Sanity check: valid voltage range
                    if not (-30 <= min_v <= max_v <= 30):
                        continue

                    key = f"{tp}_{min_v}_{max_v}"
                    if key in seen:
                        continue
                    seen.add(key)

                    # Best-effort signal name: text before PT identifier
                    before_tp = text[: text.find(tp)].strip()
                    signal_tokens = before_tp.split()
                    signal = signal_tokens[-1] if signal_tokens else tp

                    results.append({
                        "Signal":    signal,
                        "TestPoint": tp,
                        "Min":       min_v,
                        "Max":       max_v,
                        "Unit":      "V",
                        "Category":  "voltage",
                        "_method":   "pdfplumber",
                    })

        return results

    except ImportError:
        return []
    except Exception:
        return []


def _merge_voltages(regex_list: List[Dict], plumber_list: List[Dict]) -> List[Dict]:
    """
    Merge two voltage lists (regex + pdfplumber). Strategy:
    - Index both by TestPoint
    - For each TestPoint present in only one list: keep it
    - For TestPoints present in both: prefer pdfplumber (column-accurate)
      unless the regex entry has a Signal name that looks more informative
    """
    by_tp: Dict[str, Dict] = {}

    # First pass: regex results as baseline
    for v in regex_list:
        tp = v.get("TestPoint", "").upper()
        if tp:
            by_tp[tp] = dict(v)
            by_tp[tp]["_method"] = "regex"

    # Second pass: pdfplumber supplements / overrides
    for v in plumber_list:
        tp = v.get("TestPoint", "").upper()
        if not tp:
            continue
        if tp not in by_tp:
            # New entry found only by pdfplumber
            by_tp[tp] = dict(v)
        else:
            # Both found same TP — prefer pdfplumber Min/Max, keep regex Signal if better
            existing = by_tp[tp]
            merged = dict(existing)
            merged["Min"] = v["Min"]
            merged["Max"] = v["Max"]
            merged["_method"] = "merged"
            # Prefer the signal name that looks like a real net name (longer, contains alpha)
            sig_r = existing.get("Signal", "")
            sig_p = v.get("Signal", "")
            if len(sig_r) >= 3 and any(c.isalpha() for c in sig_r):
                merged["Signal"] = sig_r
            else:
                merged["Signal"] = sig_p
            by_tp[tp] = merged

    return list(by_tp.values())


# ─────────────────────────────────────────────────────────────
#  FONCTION PRINCIPALE
# ─────────────────────────────────────────────────────────────

def extract_mtp(pdf_input) -> Dict[str, Any]:
    """
    Analyse complète d'un PDF MTP PEGATRON par code classique.

    Args:
        pdf_input: bytes du PDF, chemin fichier (str), ou bytes-like

    Returns:
        Dict avec structure :
          {
            "metadata":      {...},
            "boardlevel":    [{"Signal", "TestPoint", "Min", "Max", "Unit"}...],
            "bluetooth":     [{"ItemID", "Direction", "Frequency", "Parameter", "Min", "Max"}...],
            "wifi":          [{"TestName", "Direction", "Band", "Frequency", "Parameter", "Min", "Max"}...],
            "system":        [{"Name", "Remark", "Min", "Max", "Pass_Fail"}...],
            "fw_upgrade":    [{"Name", "Remark"}...],
            "summary":       {"total": N, "boardlevel": N, "bt": N, "wifi": N, "system": N, "fw": N}
          }
    """
    # Extraction du texte
    if isinstance(pdf_input, (bytes, bytearray)):
        text = _extract_pdf_text(pdf_input)
    elif isinstance(pdf_input, str):
        text = _extract_pdf_text(pdf_input)
    else:
        text = str(pdf_input)

    if not text or len(text) < 100:
        return {
            "metadata":   {"error": "Texte PDF vide ou illisible"},
            "boardlevel": [], "bluetooth": [], "wifi": [],
            "system":     [], "fw_upgrade": [],
            "summary":    {"total": 0, "error": "Extraction impossible"},
        }

    # Extraction par section
    metadata   = _extract_metadata(text)
    voltages_regex = _extract_voltages(text)
    bt_tests   = _extract_bt_tests(text)
    wifi_tests = _extract_wifi_tests(text)
    sys_tests  = _extract_system_tests(text)
    fw_tests   = _extract_fw_tests(text)

    # pdfplumber parallel extraction for BoardLevel ICT — merge for best-effort union
    voltages_plumber = _extract_voltages_plumber(pdf_input)
    voltages = _merge_voltages(voltages_regex, voltages_plumber)

    total = len(voltages) + len(bt_tests) + len(wifi_tests) + len(sys_tests) + len(fw_tests)

    return {
        "metadata":   metadata,
        "boardlevel": voltages,
        "bluetooth":  bt_tests,
        "wifi":       wifi_tests,
        "system":     sys_tests,
        "fw_upgrade": fw_tests,
        "summary": {
            "total":      total,
            "boardlevel": len(voltages),
            "bluetooth":  len(bt_tests),
            "wifi":       len(wifi_tests),
            "system":     len(sys_tests),
            "fw_upgrade": len(fw_tests),
        },
    }


# ─────────────────────────────────────────────────────────────
#  COMPARATEUR MTP vs ICP
# ─────────────────────────────────────────────────────────────

def compare_mtp_vs_icp(mtp_report: Dict, icp_data: Dict) -> Dict[str, Any]:
    """
    Compare les spécifications MTP avec les limites ICP.

    icp_data peut contenir :
      - icp_rf_limits  : {"2.4GHz": [...], "5GHz": [...], "Bluetooth": [...]}
      - icp_fe_limits  : [...]
      - log_results    : résultats des logs (BoardLevel, System…)

    Retourne un rapport de conformité structuré.
    """
    results    : List[Dict] = []
    anomalies  : List[Dict] = []
    missing_mtp: List[Dict] = []
    extra_mtp  : List[Dict] = []

    icp_rf  = icp_data.get("icp_rf_limits",  {})
    icp_fe  = icp_data.get("icp_fe_limits",  [])
    log_res = icp_data.get("log_results",     {})

    # ── 1. Voltages BoardLevel : comparer MTP vs log (valeurs réelles) ──
    if mtp_report.get("boardlevel") and log_res:
        bl_logs = {
            fname: res
            for fname, res in log_res.items()
            if res.get("module") == "BoardLevel" and not res.get("error")
        }
        mtp_voltages = {v["Signal"].upper(): v for v in mtp_report["boardlevel"]}

        for signal, mtp_spec in mtp_voltages.items():
            # Chercher la valeur mesurée dans les logs
            measured = None
            for res in bl_logs.values():
                for test in res.get("report", {}).get("Tests", []):
                    pname = test.get("Name", "").upper()
                    # Correspondance partielle : le signal MTP doit être dans le nom de param
                    sig_clean = re.sub(r"[_\-]PT\d+.*", "", signal)
                    if sig_clean in pname or pname.startswith(sig_clean[:8]):
                        measured = test
                        break
                if measured: break

            if measured and measured.get("Value") not in (None, "PASS", "FAIL"):
                val  = float(measured["Value"])
                mmin = mtp_spec["Min"]
                mmax = mtp_spec["Max"]
                ok   = mmin <= val <= mmax if mmin is not None and mmax is not None else True

                # Comparer aussi les limites MTP vs limites log
                log_min = measured.get("Min")
                log_max = measured.get("Max")
                lim_match = (
                    abs(log_min - mmin) < 0.01 and abs(log_max - mmax) < 0.01
                    if log_min is not None and log_max is not None else None
                )

                results.append({
                    "Section":   "BoardLevel",
                    "Signal":    mtp_spec["Signal"],
                    "Param":     "Voltage",
                    "Measured":  val,
                    "MTP_Min":   mmin,
                    "MTP_Max":   mmax,
                    "Log_Min":   log_min,
                    "Log_Max":   log_max,
                    "Unit":      "V",
                    "Pass":      ok,
                    "LimitsMatch": lim_match,
                })
                if lim_match is False:
                    anomalies.append({
                        "Type":     "LIMIT_MISMATCH",
                        "Severity": "WARNING",
                        "Section":  "BoardLevel",
                        "Item":     mtp_spec["Signal"],
                        "Detail":   f"MTP({mmin},{mmax}) ≠ LOG({log_min},{log_max})",
                    })
            else:
                extra_mtp.append({"Section": "BoardLevel", "Signal": mtp_spec["Signal"],
                                   "Reason": "Non mesuré dans les logs"})

    # ── 2. Wi-Fi : comparer MTP TX limits vs ICP RF limits ──
    wifi_mtp = [t for t in mtp_report.get("wifi", []) if t["Direction"] == "TX" and t.get("Frequency")]
    for mtp_item in wifi_mtp:
        freq = mtp_item["Frequency"]
        band = mtp_item["Band"] or ("5GHz" if freq >= 5000 else "2.4GHz")
        mod  = mtp_item.get("Modulation", "")
        param = mtp_item.get("Parameter", "Power")
        mmin = mtp_item.get("Min")
        mmax = mtp_item.get("Max")

        # Chercher dans icp_rf_limits
        icp_band = icp_rf.get(band, [])
        matched_icp = None
        for icp_e in icp_band:
            icp_freq = icp_e.get("Frequency") or icp_e.get("Freq")
            if icp_freq and abs(int(str(icp_freq)) - freq) <= 5:
                icp_mod = icp_e.get("Modulation", "")
                if not mod or not icp_mod or any(
                    part.upper() in icp_mod.upper() for part in str(mod).split() if len(part) > 3
                ):
                    matched_icp = icp_e
                    break

        if matched_icp:
            icp_min = matched_icp.get("Min") or matched_icp.get("min")
            icp_max = matched_icp.get("Max") or matched_icp.get("max")
            if icp_min is not None and icp_max is not None and mmin is not None and mmax is not None:
                lim_ok = abs(float(icp_min) - mmin) < 0.6 and abs(float(icp_max) - mmax) < 0.6
            else:
                lim_ok = True

            results.append({
                "Section":    band,
                "Signal":     f"{freq}MHz {mod}",
                "Param":      param,
                "Measured":   None,
                "MTP_Min":    mmin,
                "MTP_Max":    mmax,
                "ICP_Min":    icp_min,
                "ICP_Max":    icp_max,
                "Unit":       "dBm",
                "Pass":       lim_ok,
                "LimitsMatch": lim_ok,
            })
            if not lim_ok:
                anomalies.append({
                    "Type":     "LIMIT_MISMATCH",
                    "Severity": "WARNING",
                    "Section":  band,
                    "Item":     f"{freq}MHz {mod} Power",
                    "Detail":   f"MTP({mmin},{mmax}) vs ICP({icp_min},{icp_max})",
                })
        else:
            extra_mtp.append({
                "Section": band,
                "Signal":  f"{freq}MHz {mod}",
                "Reason":  "Test présent dans MTP mais absent de l'ICP",
            })

    # ── 3. Bluetooth : comparer MTP TX limits vs ICP RF Bluetooth ──
    bt_mtp = [t for t in mtp_report.get("bluetooth", []) if t["Direction"] == "TX" and t.get("Frequency")]
    icp_bt = icp_rf.get("Bluetooth", [])

    for mtp_item in bt_mtp:
        freq  = mtp_item["Frequency"]
        mod   = mtp_item.get("Modulation", "")
        param = mtp_item.get("Parameter", "Power")
        mmin  = mtp_item.get("Min")
        mmax  = mtp_item.get("Max")

        matched_icp = None
        for icp_e in icp_bt:
            icp_freq = icp_e.get("Frequency") or icp_e.get("Freq")
            if icp_freq and abs(int(str(icp_freq)) - freq) <= 5:
                matched_icp = icp_e
                break

        if matched_icp and mmin is not None and mmax is not None:
            icp_min = matched_icp.get("Min") or matched_icp.get("min")
            icp_max = matched_icp.get("Max") or matched_icp.get("max")
            if icp_min is not None and icp_max is not None:
                lim_ok = abs(float(icp_min) - mmin) < 0.6 and abs(float(icp_max) - mmax) < 0.6
            else:
                lim_ok = True

            results.append({
                "Section":    "Bluetooth",
                "Signal":     f"BT {freq}MHz {mod}",
                "Param":      param,
                "Measured":   None,
                "MTP_Min":    mmin,
                "MTP_Max":    mmax,
                "ICP_Min":    icp_min,
                "ICP_Max":    icp_max,
                "Unit":       "dBm",
                "Pass":       lim_ok,
                "LimitsMatch": lim_ok,
            })
            if not lim_ok:
                anomalies.append({
                    "Type":     "LIMIT_MISMATCH",
                    "Severity": "WARNING",
                    "Section":  "Bluetooth",
                    "Item":     f"BT {freq}MHz {mod}",
                    "Detail":   f"MTP({mmin},{mmax}) vs ICP({icp_min},{icp_max})",
                })

    # ── 4. System tests — vérifier couverture ──
    system_tests_mtp = mtp_report.get("system", [])
    for st in system_tests_mtp:
        results.append({
            "Section":    "System",
            "Signal":     st.get("Name", ""),
            "Param":      st.get("Remark", ""),
            "Measured":   None,
            "MTP_Min":    st.get("Min"),
            "MTP_Max":    st.get("Max"),
            "ICP_Min":    None,
            "ICP_Max":    None,
            "Unit":       st.get("Unit", ""),
            "Pass":       True,   # Coverage check only
            "LimitsMatch": None,
        })

    # ── Résumé ──
    n_pass   = sum(1 for r in results if r["Pass"] is True)
    n_fail   = sum(1 for r in results if r["Pass"] is False)
    n_mism   = sum(1 for a in anomalies if a["Type"] == "LIMIT_MISMATCH")
    global_s = "PASS" if n_fail == 0 and n_mism == 0 else ("FAIL" if n_fail > 0 else "PARTIAL")

    recommendations = []
    if n_mism > 0:
        recommendations.append(f"⚠️ {n_mism} divergence(s) de limites détectée(s) entre MTP et ICP — vérifier la version de référence.")
    if extra_mtp:
        recommendations.append(f"ℹ️ {len(extra_mtp)} test(s) présent(s) dans le MTP sans correspondance ICP — à valider.")
    if missing_mtp:
        recommendations.append(f"❌ {len(missing_mtp)} test(s) ICP non couverts par le MTP.")
    if not recommendations:
        recommendations.append("✅ Tous les tests MTP sont conformes aux spécifications ICP.")

    total = (mtp_report.get("summary", {}).get("total")
             or mtp_report.get("summary", {}).get("total_tests", 0))

    return {
        "comparison_summary": {
            "total_mtp_items":  total,
            "total_compared":   len(results),
            "compliant":        n_pass,
            "non_compliant":    n_fail,
            "limit_mismatches": n_mism,
            "extra_in_mtp":     len(extra_mtp),
            "missing_in_mtp":   len(missing_mtp),
            "global_status":    global_s,
        },
        "results":         results,
        "anomalies":       anomalies,
        "extra_in_mtp":    extra_mtp,
        "missing_in_mtp":  missing_mtp,
        "recommendations": recommendations,
        "analyst_notes":   (
            f"Analyse par code classique — MTP v{mtp_report['metadata'].get('version','?')} "
            f"({mtp_report['metadata'].get('release_date','?')}). "
            f"Produit : {mtp_report['metadata'].get('product','?')}."
        ),
    }
