# -*- coding: utf-8 -*-
"""
check_RF_log_v18.py
Version avec coloration ANSI ciblée des valeurs (couleurs forcées) :
- Rouge : JSON_Fails_Count, LimitsMismatch_Count, MissingInLog_Count (toujours, même à 0) + valeurs correspondantes dans les sections détaillées
- Vert : CheckedParams, PassVsJSON_Count
- Blanc : tout le reste (titres, libellés, autres champs)
"""

import argparse, json, re, sys, os
import html
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

# ---------------------------------------------------------------------
# Pré-traitement ligne log (strip timestamp + unescape HTML)
# ---------------------------------------------------------------------
TS_PREFIX = re.compile(r'^\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}\s+\[\d+\]\t')

def _payload(line: str) -> str:
    """Partie utile d'une ligne : sans timestamp + unescape HTML."""
    s = TS_PREFIX.sub("", line, count=1)
    s = html.unescape(s)
    return s.strip()


# ---------------------------------------------------------------------
# Couleurs ANSI : FORCÉES (toujours actives)
# ---------------------------------------------------------------------
# Sous Windows, active le support des séquences ANSI (VT100)
if os.name == "nt":
    os.system("")

def _use_color() -> bool:
    # Couleurs toujours actives
    return True

RESET = "\033[0m"
FG = {
    "red": "\033[91m",
    "green": "\033[92m",
}

def _c(text: str, color: Optional[str] = None) -> str:
    if color not in FG:
        return text
    return FG[color] + text + RESET

def _cred(text: Any) -> str:
    return _c(str(text), "red")

def _cgreen(text: Any) -> str:
    return _c(str(text), "green")

def color_value(label: str, value: Any) -> str:
    """
    Colore uniquement les *valeurs* selon la règle demandée.
    - Rouge : JSON_Fails_Count, LimitsMismatch_Count, MissingInLog_Count (toujours, même à 0)
    - Vert : CheckedParams, PassVsJSON_Count
    - Blanc : le reste
    """
    # Erreurs -> rouge (toujours, même si 0)
    if label in ("JSON_Fails_Count", "LimitsMismatch_Count", "MissingInLog_Count"):
        return f"{label} {_cred(value)}"
    # Succès -> vert
    if label in ("CheckedParams", "PassVsJSON_Count"):
        return f"{label} {_cgreen(value)}"
    # Neutre -> blanc
    return f"{label} {value}"

# ---------------------------------------------------------------------
# Utilitaires internes
# ---------------------------------------------------------------------
def _to_float(x: Optional[str]) -> Optional[float]:
    if x is None:
        return None
    return float(str(x).replace(",", "."))

def _norm_mod(s: str) -> str:
    import re as _re
    return _re.sub(r'[^A-Z0-9]', '', (s or '').upper())

def _within(val: Optional[float], lo: Optional[float], hi: Optional[float]) -> Optional[bool]:
    if val is None:
        return None
    if lo is None and hi is None:
        return None
    if lo is None:
        return val <= hi
    if hi is None:
        return val >= lo
    return lo <= val <= hi

# ---------------------------------------------------------------------
# Regex Wi‑Fi
# ---------------------------------------------------------------------
WIFI_SPECTRUM = re.compile(r'TEST\_VERIFY\s+EVM\s+MASK\s+POWER\s+SPECTRUM', re.I)
WIFI_PER = re.compile(r'TEST\_VERIFY\s+PER', re.I)
FREQ_PAT = re.compile(r'(\d{4,5})')
ANT_PAT = re.compile(r'\bANT[\s\-]?(\d)\b', re.I)
PARAM1_STRICT = re.compile(
    r'(?P<name>[A-Z0-9_]+)\s*:\s*(?P<val>-?\d+(?:\.\d+)?)\s*(?P<unit>[a-zA-Z%/ ]+)?\s*'
    r'\(\s*(?P<min>-?\d+(?:\.\d+)?)?\s*,\s*(?P<max>-?\d+(?:\.\d+)?)?\s*\)'
)
PARAM_SIMPLE = re.compile(
    r'(?P<name>[A-Z0-9_]+)\s*:\s*(?P<val>-?\d+(?:\.\d+)?)\s*(?P<unit>[a-zA-Z%/ ]+)?'
)
PARAM1_FLEX = re.compile(
    r'(?P<name>[A-Z0-9_]+)\s*:\s*(?P<val>-?\d+(?:\.\d+)?)\s*(?P<unit>[^\(\)]+?)?\s*'
    r'\(\s*(?P<min>-?\d+(?:\.\d+)?)\s*,\s*(?P<max>-?\d+(?:\.\d+)?)\s*\)'
)

# ---------------------------------------------------------------------
# Regex Bluetooth
# ---------------------------------------------------------------------
BT_TEST_HDR = re.compile(
    r'^(?:\d+\.)?\s*(?P<dir>TX|RX)_(?P<phy>BDR|EDR|LE)\s+(?P<freq>\d{4})\s+(?P<mod>[A-Z0-9\-]+)\b',
    re.I
)

def _bt_norm_mod(phy: str, mod: str) -> str:
    pu = (phy or '').upper()
    mu = (mod or '').upper().replace('_', '')
    if pu == 'LE':
        # Normalisation simple: on force "LE 1M PRBS" comme token représentatif
        return 'LE 1M PRBS'
    return mu

# ---------------------------------------------------------------------
# Mapping paramètres
# ---------------------------------------------------------------------
PARAM_TO_JSON = {
    # Wi‑Fi
    "TX_POWER_DBM": ("Power Target", "Power Target"),
    "POWER_AVG_DBM": ("Power Min", "Power Max"),
    "RX_POWER_DBM": ("RX Power (dBm)", "RX Power (dBm)"),
    "POWER_RMS_AVG_VSA1": ("Power Min", "Power Max"),
    "POWER_DBM_RMS_AVG_S1": ("Power Min", "Power Max"),
    "POWER_DBM_RMS_AVG_VSA1": ("Power Min", "Power Max"),
    "EVM_DB_AVG_S1": (None, "EVM Max"),
    "EVM_DB_ALL": (None, "EVM Max"),
    "FREQ_ERROR_AVG": ("Frequency Tolerance Min", "Frequency Tolerance Max"),
    "LO_LEAKAGE_VSA1": ("LO Leakage Min", "LO Leakage Max"),
    "LO_LEAKAGE_DBC_VSA1": ("LO Leakage Min", "LO Leakage Max"),
    "RX_PER": (None, "PER Max (%)"),
    # Bluetooth
    "POWER_AVERAGE_DBM": ("Power Min", "Power Max"),
    "FREQ_DRIFT": ("BT Frequency Drift Min (kHz)", "BT Frequency Drift Max (kHz)"),
    "MAX_FREQ_DRIFT_RATE": (None, "BT Max Drift Rate (kHz/50us)"),
    "FREQ_DEVIATION": ("BT Freq Deviation df2 Min (kHz)", None),
    "EDR_EXTREME_OMEGA_I0": ("BT Frequency Stability Min (kHz)", "BT Frequency Stability Max (kHz)"),
    "BER": (None, "BER Max (%)"),
    "PER": (None, "PER Max (%)"),
}

# ---------------------------------------------------------------------
# Normalisation header Wi‑Fi
# ---------------------------------------------------------------------
def _wifi_norm_from_body(body: str) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    fm = FREQ_PAT.search(body)
    freq = int(fm.group(1)) if fm else None

    ant = None
    am = ANT_PAT.search(body)
    if am:
        ant = f"ANT{am.group(1)}".upper()

    u = body.upper().replace("_", " ")
    m = re.search(r'\bMCS(\d+)\b', u)
    bw_m = re.search(r'BW[\-\s]?(\d+)', u)
    mcs_idx = m.group(1) if m else None
    bw = int(bw_m.group(1)) if bw_m else 20

    is_he = " HE" in (" " + u) or "HE " in u
    is_vht = " VHT" in (" " + u)
    is_ht  = " HT" in (" " + u) or "HT " in u or "HT_MF" in u

    if not mcs_idx:
        return freq, None, ant

    if is_he:
        mod_norm = f"HE-MCS{mcs_idx} {'HT20' if bw == 20 else f'vHT{bw}'}"
    elif is_vht:
        mod_norm = f"MCS{mcs_idx} vHT{bw}"
    elif is_ht:
        mod_norm = f"MCS{mcs_idx} HT{bw}"
    else:
        mod_norm = None

    return freq, mod_norm, ant


# ---------------------------------------------------------------------
# Parser principal
# ---------------------------------------------------------------------
def parse_log(text: str):
    tests: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None

    lines = text.splitlines()
    for i, raw in enumerate(lines):
        line = raw.rstrip("\n")
        payload = _payload(line)

        # Filtre : lignes d'orchestration / extraction (pas des mesures)
        if payload.startswith(("Do ", "Run ", ">", "<")) or "ReadLogValue" in payload:
            continue


        # Wi‑Fi
        if WIFI_SPECTRUM.search(payload) or WIFI_PER.search(payload):
            if i + 1 < len(lines) and lines[i+1].strip().lower().startswith("skipped"):
                current = None
                continue
            freq, mod_norm, ant = _wifi_norm_from_body(payload)
            if not freq or not mod_norm:
                current = None
                continue
            dir_ = "RX" if WIFI_PER.search(payload) else "TX"
            current = {
                "TestHeader": line.strip(),
                "Dir": dir_,
                "Frequency": freq,
                "ModulationHeader": mod_norm,
                "Antenna": ant,
                "Parameters": []
            }
            tests.append(current)
            continue

        # Bluetooth
        bm = BT_TEST_HDR.search(payload)
        if bm:
            if i + 1 < len(lines) and lines[i+1].strip().lower().startswith("skipped"):
                current = None
                continue
            dir_ = bm.group("dir").upper()
            phy = bm.group("phy").upper()
            freq = int(bm.group("freq"))
            mod_token = _bt_norm_mod(phy, bm.group("mod"))
            current = {
                "TestHeader": line.strip(),
                "Dir": dir_,
                "Frequency": freq,
                "ModulationHeader": mod_token,
                "Antenna": None,
                "Parameters": []
            }
            tests.append(current)
            continue

        if not current:
            continue

        # v19 : extraction du RX Power (dBm)
        if "rx power" in line.lower():
            m = re.search(r"RX\s*Power\s*([-\d]+)\s*dBm", line, re.I)
            if m:
                current["Parameters"].append({
                    "Name": "RX_POWER_DBM",
                    "Value": int(m.group(1)),
                    "Unit": "dBm",
                    "Min_Log": None,
                    "Max_Log": None
                })
            continue

        # Paramètres standard
        pm = PARAM1_STRICT.search(line) or PARAM_SIMPLE.search(line) or PARAM1_FLEX.search(line)
        if pm:
            g = pm.groupdict()
            current["Parameters"].append({
                "Name": g["name"],
                "Value": _to_float(g["val"]),
                "Unit": (g.get("unit") or "").strip(),
                "Min_Log": _to_float(g.get("min")) if g.get("min") else None,
                "Max_Log": _to_float(g.get("max")) if g.get("max") else None
            })

    return tests

# ---------------------------------------------------------------------
# Recherche entrée JSON
# ---------------------------------------------------------------------
def find_json_entry(freq: int, mod_token: str, dir_: str, limits: Dict[str, List[dict]]):
    mod_u = _norm_mod(mod_token)
    for band in ("2.4GHz", "5GHz", "Bluetooth"):
        for e in limits.get(band, []):
            if e.get("Frequency") != freq:
                continue
            emod = _norm_mod(e.get("Modulation", ""))
            if mod_u and (mod_u in emod or emod in mod_u):
                ek = (e.get("EntryKind", "") or "").upper()
                if dir_ == "TX" and "TX" not in ek:
                    continue
                if dir_ == "RX" and "RX" not in ek:
                    continue
                out = dict(e)
                out["Band"] = band
                return out
    return None

# ---------------------------------------------------------------------
# Rapport
# ---------------------------------------------------------------------
def build_report(tests, limits, ignored_count=0, opt_mode=False):
    out_tests = []
    pass_json_cnt = 0
    total_params = 0
    limits_mismatch_cnt = 0
    json_fail_cnt = 0

    wifi_seen: Dict[Tuple[str, int, str], set] = {}
    mismatches = []
    json_fails = []

    for t in tests:
        freq = t["Frequency"]
        mod = t["ModulationHeader"]
        dir_ = t["Dir"]
        ant = t.get("Antenna")

        jentry = find_json_entry(freq, mod, dir_, limits)

        # Comptage antennes Wi‑Fi
        if jentry and jentry.get("Band") in ("2.4GHz", "5GHz"):
            key = (dir_, freq, _norm_mod(mod))
            s = wifi_seen.setdefault(key, set())
            if ant in ("ANT1", "ANT2"):
                s.add(ant)

        params_out = []
        for p in t["Parameters"]:
            keymin, keymax = PARAM_TO_JSON.get(p["Name"], (None, None))
            if not jentry or (not keymin and not keymax):
                continue

            min_json = jentry.get(keymin) if keymin else None
            max_json = jentry.get(keymax) if keymax else None
            if min_json is None and max_json is None:
                continue

            total_params += 1
            pass_json = _within(p["Value"], min_json, max_json)
            if pass_json is False:
                json_fail_cnt += 1
                json_fails.append((t, p, min_json, max_json))
            if pass_json is True:
                pass_json_cnt += 1

            match_min = None
            match_max = None
            if p["Min_Log"] is not None and min_json is not None:
                match_min = "OK" if abs(p["Min_Log"] - min_json) < 1e-12 else "DIFF"
                if match_min == "DIFF":
                    limits_mismatch_cnt += 1
                    mismatches.append((t, p, min_json, max_json))
            if p["Max_Log"] is not None and max_json is not None:
                match_max = "OK" if abs(p["Max_Log"] - max_json) < 1e-12 else "DIFF"
                if match_max == "DIFF":
                    limits_mismatch_cnt += 1
                    mismatches.append((t, p, min_json, max_json))

            params_out.append({
                "Name": p["Name"],
                "Value": p["Value"],
                "Unit": p["Unit"],
                "Antenna": ant,
                "LogLimits": {"min": p["Min_Log"], "max": p["Max_Log"]},
                "JSONLimits": {"min": min_json, "max": max_json},
                "LimitsMatch": {"min": match_min, "max": match_max},
                "PassVsJSON": pass_json
            })

        # Ne garder que les tests qui ont au moins un paramètre exploitable
        if not params_out:
            continue

        if jentry:
            out_tests.append({
                "TestHeader": t["TestHeader"],
                "Dir": dir_,
                "Frequency": freq,
                "ModulationHeader": mod,
                "Antenna": ant,
                "JSON": {
                    "Band": jentry.get("Band"),
                    "EntryKind": jentry.get("EntryKind"),
                    "Modulation": jentry.get("Modulation"),
                    "Mandatory": jentry.get("Mandatory", True)
                },
                "Parameters": params_out
            })

    # Tests manquants (Wi‑Fi)
    missing = []
    for band in ("2.4GHz", "5GHz"):
        for e in limits.get(band, []):
            ek = (("RX" if "RX" in (e.get("EntryKind", "")).upper() else "TX"),
                  e.get("Frequency"),
                  _norm_mod(e.get("Modulation", "")))
            ants = wifi_seen.get(ek, set())
            if ants != {"ANT1", "ANT2"}:
                reason = "missing ANT1 & ANT2" if not ants else \
                         ("missing ANT2" if ants == {"ANT1"} else "missing ANT1")
                missing.append({
                    "Band": band,
                    "EntryKind": e.get("EntryKind"),
                    "Frequency": e.get("Frequency"),
                    "Modulation": e.get("Modulation"),
                    "Mandatory": bool(e.get("Mandatory", True)),
                    "Reason": reason
                })

    summary = {
        "Tests": len(out_tests),
        "CheckedParams": total_params,
        "PassVsJSON_Count": pass_json_cnt,
        "JSON_Fails_Count": json_fail_cnt,
        "LimitsMismatch_Count": limits_mismatch_cnt,
        "MissingInLog_Count": len(missing),
        "IgnoredTests_Count": ignored_count,
        "OptMode": opt_mode
    }

    return {
        "Summary": summary,
        "Tests": out_tests,
        "MissingInLog": missing,
        "MismatchDetails": mismatches,
        "JSONFailDetails": json_fails
    }

# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Validation RF JSON-only stricte (Wi‑Fi + Bluetooth) — v18 (colorisation ciblée des valeurs, couleurs forcées)")
    ap.add_argument("--log", required=True)
    ap.add_argument("--limits", required=True)
    ap.add_argument("--out", default="rf_validation_report.json")
    ap.add_argument("--max-lines", type=int, default=50)
    ap.add_argument("--opt", action="store_true", help="Ignore tests with Mandatory=false in JSON limits")
    args = ap.parse_args()

    # Lecture
    text = Path(args.log).read_text(encoding="utf-8", errors="ignore")
    limits = json.loads(Path(args.limits).read_text(encoding="utf-8"))

    # Option --opt
    ignored_count = 0
    if args.opt:
        for band in list(limits.keys()):
            original_len = len(limits[band])
            limits[band] = [e for e in limits[band] if e.get("Mandatory", True)]
            ignored_count += original_len - len(limits[band])
        print(f"[INFO] --opt actif : {ignored_count} tests ignorés (Mandatory=false)")

    # Rapport
    report = build_report(parse_log(text), limits, ignored_count, opt_mode=args.opt)
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    # -----------------------------
    # Affichage console demandé
    # -----------------------------
    print("=" * 60)
    print("Exécution de :", "check_RF_log_v18.py")
    print("Rapport JSON :", args.out)

    # Résumé (valeurs colorées selon règle)
    summary = report["Summary"]
    print("Résumé :")
    for key in ("Tests",
                "CheckedParams",
                "PassVsJSON_Count",
                "JSON_Fails_Count",
                "LimitsMismatch_Count",
                "MissingInLog_Count",
                "IgnoredTests_Count",
                "OptMode"):
        if key in summary:
            print("  ", "-", color_value(key, summary[key]))

    # Détails
    if summary.get("LimitsMismatch_Count", 0) > 0:
        print("\nLimites Log ≠ JSON détectées :", _cred(summary["LimitsMismatch_Count"]))
        for t, p, minj, maxj in report["MismatchDetails"][:args.max_lines]:
            min_log = _cred(p['Min_Log']) if p['Min_Log'] is not None else _cred("None")
            max_log = _cred(p['Max_Log']) if p['Max_Log'] is not None else _cred("None")
            min_json = _cred(minj) if minj is not None else _cred("None")
            max_json = _cred(maxj) if maxj is not None else _cred("None")
            print(f" • {t['Dir']} {t['Frequency']} {t['ModulationHeader']} {t.get('Antenna','')} — {p['Name']}: "
                  f"Log(min,max)=({min_log},{max_log}) vs JSON(min,max)=({min_json},{max_json})")

    if summary.get("JSON_Fails_Count", 0) > 0:
        print("\nValeurs hors bornes JSON :", _cred(summary["JSON_Fails_Count"]))
        for t, p, minj, maxj in report["JSONFailDetails"][:args.max_lines]:
            val_red = _cred(p['Value'])
            min_json = _cred(minj) if minj is not None else _cred("None")
            max_json = _cred(maxj) if maxj is not None else _cred("None")
            print(f" • {t['Dir']} {t['Frequency']} {t['ModulationHeader']} {t.get('Antenna','')} — "
                  f"{p['Name']}={val_red} (limites JSON: {min_json}..{max_json})")

    if summary.get("MissingInLog_Count", 0) > 0:
        print("\nTests obligatoires manquants (Wi‑Fi):", _cred(summary["MissingInLog_Count"]))
        for m in report["MissingInLog"][:args.max_lines]:
            print(f" • {m['EntryKind']} {m['Frequency']} {m['Modulation']} — {_cred(m['Reason'])}")

if __name__ == "__main__":
    main()