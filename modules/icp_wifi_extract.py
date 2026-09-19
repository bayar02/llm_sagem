#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ICP_wifi_extract_v7.1.py
Cedric BELKHEIR — Version 7.1
---------------------------------------------
Extraction complète des limites RF Wi-Fi / BT
Compatible checker v19 (RX Power obligatoire)
"""

import fitz
import re
import sys
import json
import os
from typing import Dict, List, Optional

# -------------------------------------------------------------------
# Regex & helpers identiques au v6 (inchangés)
# -------------------------------------------------------------------

RE_FREQ_MOD = re.compile(
    r"Frequency\s*([0-9]{4})\s*MHz.*?Modulation\s*([A-Za-z0-9\-\_/ ]+)",
    re.IGNORECASE | re.DOTALL,
)
RE_FLOAT = re.compile(r"-?\d+(?:[.,]\d+)?")
RE_POS_FLOAT = re.compile(r"\b\d+(?:[.,]\d+)?\b")
RE_INT = re.compile(r"-?\d+")
MINUS_CHARS = "-–—‑"
RE_TEST_LABEL = re.compile(r"\bTest\s+([A-Z0-9_]+)\s*:\s*(.+)")
RE_MAX_DRIFT_RATE = re.compile(
    r"max\s*drift\s*rate.*?(\d+(?:[.,]\d+)?)\s*kHz\s*/\s*50",
    re.IGNORECASE
)
RE_FREQ_STABILITY = re.compile(
    r"frequency\s*stability.*?([-\d]+).*?([-\d]+)\s*kHz",
    re.IGNORECASE | re.DOTALL
)
RE_FREQ_DRIFT = re.compile(
    r"frequency\s*drift.*?([-\d]+).*?([-\d]+)\s*kHz",
    re.IGNORECASE | re.DOTALL
)
RE_DF2 = re.compile(
    r"frequency\s*deviation\s*df2.*?([-\d]+)",
    re.IGNORECASE | re.DOTALL
)
# Bluetooth modulation detection (minimal fix)
RE_BT_MOD = re.compile(r"\b(DH\d|[13]-DH\d|LE\s*1M|BLE)\b", re.IGNORECASE)

def _to_float(s: str) -> float:
    return float(s.replace(",", "."))

def _norm_hyphens(s: str) -> str:
    return s.replace("–", "-").replace("—", "-").replace("‑", "-")

def _clean(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        if v is None:
            continue
        if isinstance(v, str) and v.strip() == "":
            continue
        if isinstance(v, (list, tuple, dict)) and not v:
            continue
        out[k] = v
    return out

# -------------------------------------------------------------------
# Mode page (BT / WIFI2 / WIFI5)
# -------------------------------------------------------------------

def _page_mode(text: str, fallback: Optional[str]) -> Optional[str]:
    t = _norm_hyphens(text).lower()
    t = t.replace("wi‑fi", "wi-fi").replace("wi fi", "wi-fi")
    if ("conducted tests" in t and "bluetooth" in t):
        return "BT"
    if ("conducted tests" in t and "wi-fi" in t and "2.4" in t):
        return "WIFI2"
    if ("conducted tests" in t and "wi-fi" in t and "5g" in t):
        return "WIFI5"
    return fallback

# -------------------------------------------------------------------
# Extraction principale
# -------------------------------------------------------------------

def parse_rf_limits_from_page(page) -> Dict[str, List[dict]]:
    blocks = sorted(page.get_text("blocks"), key=lambda b: (b[1], b[0]))

    tx_entries = []
    per_entries = []
    ber_entries = []

    i = 0
    while i < len(blocks):
        text = (blocks[i][4] or "").strip()

        # ------------------------- HEADER TABLE -------------------------
        if "Frequency" in text and "Modulation" in text:

            m = RE_FREQ_MOD.search(text) or (
                RE_FREQ_MOD.search(text + "\n" +
                (blocks[i+1][4] if i+1 < len(blocks) else ""))
            )
            if not m:
                i += 1
                continue

            try:
                freq = int(m.group(1))
            except Exception:
                i += 1
                continue

            modulation = m.group(2).strip()

            # Flags TX
            power_target = power_min = power_max = None
            evm_max = None
            freq_tol_min = freq_tol_max = None
            lo_leak_min = lo_leak_max = None

            # RX
            rx_power_dbm_per = None
            per_min = per_max = None

            # Fenêtre de parsing
            window_end = min(i + 22, len(blocks))
            j = i + 1

            while j < window_end:
                raw = (blocks[j][4] or "")
                t2 = raw
                t2_l = t2.lower()

                # Stop si nouvel en-tête
                if "frequency" in t2_l and "modulation" in t2_l and j != i:
                    break

                # ---------------------- RX PER extraction ----------------------
                if ("per" in t2_l) and ("rx power" in t2_l):
                    # 1) Extraction RX Power
                    mrx = re.search(
                        r"RX\s*Power\s*([-\d]+)\s*dBm",
                        t2,
                        re.IGNORECASE
                    )
                    if mrx:
                        try:
                            rx_power_dbm_per = int(_norm_hyphens(mrx.group(1)))
                        except Exception:
                            rx_power_dbm_per = None

                    # 2) Extraction PER min/max
                    cand = [_to_float(x) for x in RE_POS_FLOAT.findall(t2)]
                    if len(cand) >= 2:
                        per_min, per_max = cand[0], cand[1]

                # ---------------------- TX POWER extraction ----------------------
                if power_target is None and "power" in t2_l and ("rx power" not in t2_l) and ("per" not in t2_l) and ("ber" not in t2_l):
                    nums = RE_FLOAT.findall(t2)
                    if len(nums) >= 3:
                        pt, pmin, pmax = [_to_float(n) for n in nums[:3]]
                        power_target, power_min, power_max = pt, pmin, pmax

                # ---------------------- EVM ----------------------
                if evm_max is None and t2.upper().startswith("EVM"):
                    ivals = RE_INT.findall(t2)
                    if ivals:
                        evm_max = int(ivals[-1])

                # ---------------------- Frequency tolerance ----------------------
                if freq_tol_min is None and "frequency tolerance" in t2_l:
                    mm = RE_INT.findall(t2)
                    if len(mm) >= 2:
                        freq_tol_min, freq_tol_max = int(mm[0]), int(mm[1])

                # ---------------------- LO Leakage ----------------------
                if lo_leak_min is None and "lo leakage" in t2_l:
                    fvals = RE_FLOAT.findall(t2)
                    if len(fvals) >= 2:
                        lo_leak_min, lo_leak_max = (
                            _to_float(fvals[0]),
                            _to_float(fvals[1])
                        )

                j += 1

            # TX entry
            tx_entry = _clean({
                "EntryKind": f"TX: {modulation}",
                "Frequency": freq,
                "Modulation": modulation,
                "Power Target": power_target,
                "Power Min": power_min,
                "Power Max": power_max,
                "EVM Max": evm_max,
                "Frequency Tolerance Min": freq_tol_min,
                "Frequency Tolerance Max": freq_tol_max,
                "LO Leakage Min": lo_leak_min,
                "LO Leakage Max": lo_leak_max,
            })

            if any(k in tx_entry for k in [
                "Power Target", "EVM Max", "Frequency Tolerance Min",
                "LO Leakage Min"
            ]):
                tx_entries.append(tx_entry)

            # RX PER entry
            if (rx_power_dbm_per is not None) and (per_min is not None):
                per_entries.append(_clean({
                    "EntryKind": f"RX PER: {modulation}",
                    "Frequency": freq,
                    "Modulation": modulation,
                    "RX Power (dBm)": rx_power_dbm_per,
                    "PER Min (%)": per_min,
                    "PER Max (%)": per_max,
                }))

        i += 1

    return {"tx": tx_entries, "per": per_entries, "ber": ber_entries}

# -------------------------------------------------------------------
# Assemblage
# -------------------------------------------------------------------

def extract_rf_limits(pdf_path: str) -> Dict[str, List[dict]]:
    out = {"Bluetooth": [], "2.4GHz": [], "5GHz": []}
    doc = fitz.open(pdf_path)

    current_mode = None

    for p in range(doc.page_count):
        page = doc[p]
        text = page.get_text("text")
        current_mode = _page_mode(text, current_mode)

        parsed = parse_rf_limits_from_page(page)

        def route(e):
            modulation = e.get("Modulation", "")
            # Bluetooth must not be routed as Wi‑Fi 2.4GHz
            if modulation and RE_BT_MOD.search(modulation):
                return "Bluetooth"
            f = e.get("Frequency", 0)
            if f >= 5000:
                return "5GHz"
            return "2.4GHz"

        for e in parsed["tx"]:
            out[route(e)].append(e)

        for e in parsed["per"]:
            out[route(e)].append(e)


    # --- Nettoyage (Wi‑Fi) : supprimer les entrées TX "sensibilité" issues par erreur des tableaux RX/PER
    # Dans le flow, PER = RX uniquement. Une TX Wi‑Fi avec Power Target négatif correspond en réalité à RX Power.
    for band in ("2.4GHz", "5GHz"):
        out[band] = [e for e in out[band]
                     if not (str(e.get("EntryKind", "")).upper().startswith("TX:")
                             and isinstance(e.get("Power Target", None), (int, float))
                             and e.get("Power Target") < 0
                             and ("EVM Max" not in e)
                             and ("Frequency Tolerance Min" not in e)
                             and ("LO Leakage Min" not in e))]

    return out

def main():
    if len(sys.argv) < 2:
        print("Usage: python ICP_wifi_extract_v7.py <file.pdf>")
        sys.exit(1)

    pdf = sys.argv[1]
    data = extract_rf_limits(pdf)

    out_json = os.path.splitext(pdf)[0] + "_rf_limits.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"JSON généré : {out_json}")

if __name__ == "__main__":
    main()
