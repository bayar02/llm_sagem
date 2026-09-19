#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validation FE: DVB-C, DVB-S/S2, DVB-T/T2
Comparaison log FE <-> limites JSON
Version v4 (2025-12-09) — correctif:
- Capture robuste des blocs "FE_GetSignalInfos 0" (tolère les prompts 'TT>'
  et s'arrête proprement au prochain 'TT>' ou à la fin de segment).
- Regex SAT assouplie: polarisation 'V'/'H' sans crochets.
- Conversion tolérante pour limites JSON (ignore Min/Max non numériques).
"""
import json
import re
from pathlib import Path
from collections import defaultdict

# =====================================================================
# MAPPINGS LOG -> JSON
# =====================================================================
NAME_MAP = {
    "Viterbi Bit Error Rate": "Viterbi BER",
    "Signal to Noise Ratio": "Carrier-to-Noise Ratio",
    "Number of uncorrected blocks": "Uncorrected blocks",
    "Frequency Offset": "Frequency Offset",
    "Symbol Rate Offset": "Rate Offset",
    "Power in dBm": "RSSI",
}

def _norm_mod(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip().upper()

def _norm_freq(freq_str: str) -> float:
    """Convertit '198.5MHz' -> 198.5 (float)"""
    return float(re.sub(r"[^0-9.]", "", freq_str))

# ---------------------- Canonicalisation des modulations ----------------------
J83_PATTERNS = ["J83.B", "J83B", "J.83/B", "J83-B"]

def _canon_mod(mod: str) -> str:
    s = _norm_mod(mod)
    s_clean = s.replace('_', ' ').replace('-', ' ')
    tokens = s_clean.split()

    def any_contains(substrs):
        sc = s_clean
        return any(substr in sc for substr in substrs)

    # Detect QAM value
    qam_val = None
    for i, t in enumerate(tokens):
        if 'QAM' in t:
            m = re.match(r"(\d+)QAM", t)
            if m:
                qam_val = m.group(1); break
        elif i > 0 and re.match(r"^\d+$", tokens[i - 1]):
            qam_val = tokens[i - 1]; break
        elif re.match(r"^\d+QAM$", t):
            qam_val = re.match(r"^(\d+)QAM$", t).group(1); break

    # CABLE
    if any_contains(['DVB C', 'DVB-C']) or any_contains(J83_PATTERNS) or ('QAM' in tokens) or (qam_val is not None):
        if qam_val is None:
            for t in tokens:
                m = re.match(r"^(\d+)$", t)
                if m:
                    qam_val = m.group(1); break
        if qam_val is None:
            qam_val = '64'
        return f"{qam_val}QAM J83.B".upper()

    # SAT
    if any_contains(['DVB S2', 'DVB-S2']): return '8PSK DVB-S2'
    if any_contains(['DVB S', 'DVB-S']): return 'QPSK DVB-S'

    # TERRESTRIAL
    bw = None
    for t in tokens:
        m = re.match(r"^(\d+)MHZ$", t)
        if m: bw = int(m.group(1)); break
    if any_contains(['DVB T2', 'DVB-T2']):
        return f"{bw}MHz DVB-T2".upper() if bw else 'DVB-T2'
    if any_contains(['DVB T', 'DVB-T']):
        return f"{bw}MHz DVB-T".upper() if bw else 'DVB-T'
    return s

# =====================================================================
# REGEX MODES (tolérantes aux préfixes)
# =====================================================================
RE_CONNECT_CAB = re.compile(
    r"FE_ConnectCab\s+\d+\s+(\d+)\s+\d+\s+FE_\w+\s+FE_QAM(\d+)",
    re.MULTILINE,
)
RE_CONNECT_SAT = re.compile(
    r"FE_ConnectSat\s+\d+\s+(\d+)\s+\d+\s+\[VH\]\s+OPAL_FE_(DVB_S2|DVB_S)",
    re.MULTILINE,
)
RE_CONNECT_TNT = re.compile(
    r"FE_Connect\s+TER\s+\d+\s+(\d+)\s+FE_DVB_(T2|T)(?:\s+FE_BAND_(\d+)MHZ)?",
    re.MULTILINE,
)

# ✅ Correctif: capture robuste des blocs FE_GetSignalInfos (TT> optionnel, CRLF ok)
RE_SIGINFOS_BLOCK = re.compile(r"(?:TT>)?FE_GetSignalInfos\s+0.*?(?=\r?\nTT>|$)", re.S)

REGEX_MAP = {
    "Viterbi Bit Error Rate": re.compile(r"Viterbi\s+Bit\s+Error\s+Rate\s*=\s*(\d+)E-7"),
    "Signal to Noise Ratio": re.compile(r"Signal\s+to\s+Noise\s+Ratio\s*=\s*([\d\.]+)"),
    "Number of uncorrected blocks": re.compile(r"Number\s+of\s+uncorrected\s+blocks\s*=\s*(\d+)", re.I),
    "Frequency Offset": re.compile(r"Frequency\s+Offset\s*=\s*(-?\d+)", re.I),
    "Symbol Rate Offset": re.compile(r"Symbol\s+Rate\s*Offset\s*=\s*(-?\d+)", re.I),
    "Power in dBm": re.compile(r"Power\s+in\s+dBm\s*=\s*(-?\d+)", re.I),
}
REGEX_BANDWIDTH_PARAM = re.compile(r"Bandwidth\s*\[MHz\]\s*=\s*(\d+)")

# =====================================================================
# PARSE LOG
# =====================================================================
def parse_log(log_text: str):
    matches = []
    for m in RE_CONNECT_CAB.finditer(log_text): matches.append(("CAB", m))
    for m in RE_CONNECT_SAT.finditer(log_text): matches.append(("SAT", m))
    for m in RE_CONNECT_TNT.finditer(log_text): matches.append(("TNT", m))
    matches.sort(key=lambda x: x[1].start())

    grouped = defaultdict(list)
    for idx, (mode, m) in enumerate(matches):
        if mode == "CAB":
            freq_khz = int(m.group(1)); qam = m.group(2)
            freq_mhz = round(freq_khz / 1000)
            modulation = f"{qam}QAM J83.B"
        elif mode == "SAT":
            freq_khz = int(m.group(1))
            rf_mhz = freq_khz / 1000
            lo = 9750 if rf_mhz < 11700 else 10600
            freq_mhz = round(rf_mhz - lo)
            modulation = "QPSK DVB-S" if m.group(2) == "DVB_S" else "8PSK DVB-S2"
        else:  # TNT
            freq_khz = int(m.group(1))
            freq_mhz = freq_khz / 1000
            type_t = m.group(2); bw_decl = m.group(3)
            if bw_decl:
                bw = int(bw_decl)
                modulation = f"{bw}MHz DVB-T" if type_t == "T" else f"{bw}MHz DVB-T2"
            else:
                modulation = "DVB-T" if type_t == "T" else "DVB-T2"

        start = m.end()
        end = matches[idx + 1][1].start() if idx + 1 < len(matches) else len(log_text)
        segment = log_text[start:end]

        blocks = RE_SIGINFOS_BLOCK.findall(segment)

        if ("DVB-T" in modulation) and ("MHz" not in modulation):
            bw = REGEX_BANDWIDTH_PARAM.search(segment)
            if bw:
                bw = int(bw.group(1))
                modulation = f"{bw}MHz DVB-T2" if "T2" in modulation else f"{bw}MHz DVB-T"

        grouped[(freq_mhz, _canon_mod(modulation))].extend(blocks)

    parsed = []
    for (freq, mod), blocks in grouped.items():
        vals = {}
        for block in blocks:
            for name, reg in REGEX_MAP.items():
                mm = reg.search(block)
                if mm:
                    vals[NAME_MAP[name]] = float(mm.group(1))
        parsed.append({"Frequency": freq, "Modulation": mod, "Values": vals})
    return parsed

# =====================================================================
# CHARGE JSON
# =====================================================================
def load_limits(path):
    data = json.loads(Path(path).read_text(encoding="utf-8", errors="ignore"))
    return data["FE_Tests"]

# =====================================================================
# COMPARE LOG/JSON
# =====================================================================
def compare(parsed, fe_tests):
    report_tests = []
    total_params = pass_count = fail_count = 0
    idx_json = {}

    def _to_float(x):
        try: return float(str(x).replace(',', '.'))
        except (ValueError, TypeError): return None

    # index JSON par (freq MHz, modulation canonique)
    for e in fe_tests:
        fq = int(_norm_freq(e["Frequency"]))
        md = _canon_mod(e.get("Modulation", ""))
        idx_json[(fq, md)] = e

    found = set()
    missing_params = []
    for pt in parsed:
        fq = int(round(pt["Frequency"]))
        md_norm = _canon_mod(pt["Modulation"])
        vals = pt["Values"]
        jentry = idx_json.get((fq, md_norm))
        params_out = []
        if jentry:
            found.add((fq, md_norm))
            expected = {}
            for l in jentry["Limits"]:
                lo = _to_float(l.get("Min")); hi = _to_float(l.get("Max"))
                if (lo is None) or (hi is None): continue  # N/A -> ignorer
                expected[l["Parameter"]] = (lo, hi)
            for pname, val in vals.items():
                if pname in expected:
                    lo, hi = expected[pname]
                    ok = lo <= val <= hi
                    total_params += 1
                    pass_count += 1 if ok else 0
                    fail_count += 0 if ok else 1
                    params_out.append({
                        "Name": pname, "Value": val,
                        "Limits": {"Min": lo, "Max": hi}, "Pass": ok,
                    })
            for ename in expected:
                if ename not in vals:
                    missing_params.append({
                        "Frequency": jentry["Frequency"],
                        "Modulation": jentry["Modulation"],
                        "Parameter": ename,
                        "Reason": "Missing parameter in log",
                    })
        report_tests.append({"Frequency": fq, "Modulation": pt["Modulation"], "Parameters": params_out})

    missing_tests = []
    for e in fe_tests:
        fq = int(_norm_freq(e["Frequency"]))
        md = _canon_mod(e.get("Modulation", ""))
        if (fq, md) not in found:
            missing_tests.append({
                "Frequency": e["Frequency"], "Modulation": e["Modulation"],
                "Reason": "No FE_Connect found in log",
            })

    summary = {
        "Tests": len(report_tests), "CheckedParams": total_params,
        "Pass": pass_count, "Fail": fail_count,
        "MissingTests": len(missing_tests), "MissingParams": len(missing_params),
        "MissingInLog": len(missing_tests) + len(missing_params),
    }
    return {"Summary": summary, "Tests": report_tests,
            "MissingDetails": {"MissingTests": missing_tests, "MissingParams": missing_params}}

# =====================================================================
# MAIN
# =====================================================================
def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--limits", required=True)
    ap.add_argument("--out", default="fe_validation_report.json")
    args = ap.parse_args()

    log_txt = Path(args.log).read_text(encoding="utf-8", errors="ignore")
    limits = load_limits(args.limits)
    if not limits:
        raise SystemExit(f"[ERREUR] Aucune entrée 'FE_Tests' chargée depuis {args.limits}.")

    parsed = parse_log(log_txt)
    report = compare(parsed, limits)

    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("✅ Rapport généré :", args.out)
    print("Résumé :", report["Summary"])

    # --- Affichage explicite des paramètres en échec ---
    failures = []
    for t in report.get("Tests", []):
        fq = t.get("Frequency")
        md = t.get("Modulation", "")
        for p in t.get("Parameters", []):
            if p.get("Pass") is False:
                failures.append({
                    "Frequency": fq,
                    "Modulation": md,
                    "Parameter": p.get("Name"),
                    "Value": p.get("Value"),
                    "Min": p.get("Limits", {}).get("Min"),
                    "Max": p.get("Limits", {}).get("Max"),
                })

    if failures:
        print("\n=== PARAMÈTRES EN ÉCHEC (HORS LIMITES) ===")
        for f in failures:
            print(
                " - {param} à {freq} MHz / {mod} : valeur = {val}  "
                "(min = {mn}, max = {mx})".format(
                    param=f["Parameter"], freq=f["Frequency"], mod=f["Modulation"],
                    val=f["Value"], mn=f["Min"], mx=f["Max"]
                )
            )
        print("==========================================\n")

    # --- Affichage explicite des tests/paramètres manquants ---
    missing_tests = report["MissingDetails"]["MissingTests"]
    missing_params = report["MissingDetails"]["MissingParams"]

    if missing_tests or missing_params:
        print("=== TESTS / PARAMÈTRES MANQUANTS DANS LE LOG ===")

        if missing_tests:
            print("\nTests manquants :")
            for t in missing_tests:
                freq = t.get('Frequency', '')
                mod = t.get('Modulation', '')
                reason = t.get('Reason', 'N/A')
                print(f" - Fréquence : {freq}, Modulation : {mod}, Raison : {reason}")

        if missing_params:
            print("\nParamètres manquants :")
            for p in missing_params:
                freq = p.get('Frequency', '')
                mod = p.get('Modulation', '')
                param = p.get('Parameter', '')
                reason = p.get('Reason', 'N/A')
                print(f" - {param} manquant pour {freq} / {mod} (Raison : {reason})")

        print("=================================================\n")
    else:
        if not failures:
            print("\nAucun test ou paramètre manquant, aucun échec.\n")

if __name__ == "__main__":
    main()