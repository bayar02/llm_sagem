# -*- coding: utf-8 -*-
"""
check_FT_log_v1.py — Version Option A‑Color (2026)
Inclut :
 - support complet Windows ANSI (Python 3.14)
 - correctifs parsing Pegatron/Altice pour boutons
 - maintien de toutes les couleurs console
"""

import argparse
import os
import re
import json
from glob import glob
from typing import List, Dict, Any, Tuple, Optional

# ============================================================
# ACTIVATION ANSI WINDOWS (Colorama + fallback WinAPI)
# ============================================================
if os.name == "nt":
    try:
        import colorama
        colorama.just_fix_windows_console()
    except Exception:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        h = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint()
        kernel32.GetConsoleMode(h, ctypes.byref(mode))
        mode.value |= 0x0004  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
        kernel32.SetConsoleMode(h, mode)

# ============================================================
# CONSTANTES
# ============================================================
USB_SPEED_MIN = 10000
ETH_GIGA_MAX_MS = 3.0
ETH_FAST_MAX_MS = 30.0
WIFI_POWER_RANGE = (10, 20)
WIFI_PATHLOSS_RANGE = (0, 99)
BT_POWER_RANGE = (-5, 5)
BT_PATHLOSS_RANGE = (0, 99)

# ============================================================
# LECTURE LOGS
# ============================================================
def load_lines_from_path(path: str) -> List[str]:
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().splitlines()
    if os.path.isdir(path):
        lines = []
        for p in sorted(glob(os.path.join(path, "*.log"))) + \
                 sorted(glob(os.path.join(path, "*.txt"))):
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    lines.extend(f.read().splitlines())
            except:
                pass
        return lines
    raise FileNotFoundError(f"Chemin --log introuvable : {path}")

# ============================================================
# UTILITAIRES
# ============================================================
def last_occurrence_line(lines: List[str], keyword: str) -> Optional[str]:
    key = keyword.lower()
    last = None
    for l in lines:
        if key in l.lower():
            last = l
    return last

def last_occurrence_pass(lines: List[str], keyword: str) -> Tuple[bool, Optional[str]]:
    l = last_occurrence_line(lines, keyword)
    if not l:
        return False, None
    return bool(re.search(r"\bPASS(ED)?\b", l, re.IGNORECASE)), l

def last_regex_line(lines: List[str], pattern: str) -> Optional[str]:
    reg = re.compile(pattern, re.IGNORECASE)
    last = None
    for l in lines:
        if reg.search(l):
            last = l
    return last

def extract_last_value_key(lines: List[str], key: str) -> Optional[float]:
    reg = re.compile(rf"{re.escape(key)}\s*=\s*([0-9.\-]+)", re.IGNORECASE)
    vals = []
    for l in lines:
        m = reg.search(l)
        if m:
            vals.append(float(m.group(1)))
    return vals[-1] if vals else None

def extract_last_kbps(lines):
    vals = []
    for l in lines:
        m = re.search(r"=\s*([0-9]+)\s*kB/s", l)
        if m:
            vals.append(int(m.group(1)))
    return vals[-1] if vals else None

def extract_last_ping_avg(lines):
    reg = re.compile(r"round-trip.*=\s*([0-9.]+)/([0-9.]+)/([0-9.]+) ms")
    vals = []
    for l in lines:
        m = reg.search(l)
        if m:
            vals.append(float(m.group(2)))
    return vals[-1] if vals else None

# ============================================================
# LED — DISABLE ALL
# ============================================================
def detect_disable_all_pass(lines, idx):
    PAT = r"\[SAGEMTESTS\].*FT_LED\s*-?\s*PASSED"
    for i in range(idx, min(idx + 40, len(lines))):
        if re.search(PAT, lines[i], re.IGNORECASE):
            return lines[i], True
    return None, False

# ============================================================
# USB
# ============================================================
def check_usb_device_detection(lines):
    ok, last = last_occurrence_pass(lines, "FT_USB_CheckDevices")
    return ok, {"FT_USB_CheckDevices_last": last}

def check_usb_file_reading(lines):
    kbps = extract_last_kbps(lines)
    return kbps is not None and kbps >= USB_SPEED_MIN, {
        "hdparm_last_kBps": kbps,
        "threshold_kBps": USB_SPEED_MIN
    }

def check_usb_overcurrent(lines):
    last_10 = None
    last_1 = None
    for l in lines:
        m = re.search(r"USB_Voltage\s*=\s*([0-9.]+)", l)
        if m:
            v = float(m.group(1))
            if 4.3 <= v <= 5.2:
                last_10 = v
            elif 0 <= v <= 1.2:
                last_1 = v
    ok10 = last_10 is not None and 4.5 <= last_10 <= 5.0
    ok1 = last_1 is not None and last_1 <= 1.0
    return ok10 and ok1, {"last_10ohm_voltage": last_10, "last_1ohm_voltage": last_1}

# ============================================================
# Ethernet
# ============================================================
def check_eth(lines, giga, fast):
    avg = extract_last_ping_avg(lines)
    r = {}
    if giga:
        r["Giga_Ethernet_ping_test"] = avg is not None and avg < ETH_GIGA_MAX_MS
    if fast:
        r["Fast_Ethernet_ping_test"] = avg is not None and avg < ETH_FAST_MAX_MS
    return r, {"last_ping_avg_ms": avg}

# ============================================================
# NAND
# ============================================================
def check_nand(lines):
    validation_last = None
    uart_cmd = None
    uart_ret = None
    for l in lines:
        u = l.upper()
        if "SAGEMTESTS" in u and "NAND" in u and "PASS" in u:
            validation_last = l
        if "(UART" in u and "> NAND" in u:
            uart_cmd = l
        if "(UART" in u and "< NAND" in u:
            uart_ret = l
    return validation_last is not None, {
        "validation_last": validation_last,
        "uart_cmd_last": uart_cmd,
        "uart_ret_last": uart_ret,
    }

# ============================================================
# WiFi / BT
# ============================================================
def check_wifi(lines, freq):
    block = [l for l in lines if freq in l]
    pwr = extract_last_value_key(block, "Test_Power")
    path = extract_last_value_key(block, "Test_pathloss")
    ok = (
        pwr is not None and WIFI_POWER_RANGE[0] <= pwr <= WIFI_POWER_RANGE[1]
        and path is not None and WIFI_PATHLOSS_RANGE[0] <= path <= WIFI_PATHLOSS_RANGE[1]
    )
    return ok, {"last_power": pwr, "last_pathloss": path}

def check_bt(lines):
    block = [l for l in lines if "BT TX" in l]
    pwr = extract_last_value_key(block, "Test_Power")
    path = extract_last_value_key(block, "Test_pathloss")
    ok = (
        pwr is not None and BT_POWER_RANGE[0] <= pwr <= BT_POWER_RANGE[1]
        and path is not None and BT_PATHLOSS_RANGE[0] <= path <= BT_PATHLOSS_RANGE[1]
    )
    return ok, {"last_power": pwr, "last_pathloss": path}

# ============================================================
# HDMI
# ============================================================
def check_hdmi_edid(lines):
    ok, last = last_occurrence_pass(lines, "FT_HDMI_ReceiverEdid")
    return ok, {"last": last}

def check_hdmi_cec(lines):
    ok, last = last_occurrence_pass(lines, "FT_HDMI_CEC")
    return ok, {"last": last}

def check_hdmi_videopattern(lines):
    mire_ok, mire_last = last_occurrence_pass(lines, "HDMI_MireTest")
    mire4k = last_occurrence_line(lines, "MireTest 4K Test is Pass")
    return mire_ok, {"HDMI_MireTest_last": mire_last, "MireTest4K_last": mire4k}

# ============================================================
# IR
# ============================================================
def check_ir(lines):
    enable_re = re.compile(r"\bFT_IR\s+ENABLE\b", re.IGNORECASE)
    pass_re = re.compile(r"\bFT_IR\b.*\bPASS(ED)?\b", re.IGNORECASE)
    rc_re = re.compile(r"RC#\s*(\d+)\s+pressed", re.IGNORECASE)

    seq = []
    enable_i = None
    enable_l = None
    pass_i = None
    pass_l = None

    for idx, l in enumerate(lines):
        if enable_i is None and enable_re.search(l):
            enable_i = idx
            enable_l = l
            continue
        if pass_i is None and pass_re.search(l):
            pass_i = idx
            pass_l = l
            continue

        m = rc_re.search(l)
        if m:
            seq.append({
                "enable_index": enable_i,
                "enable_line": enable_l,
                "passed_index": pass_i,
                "passed_line": pass_l,
                "rc_index": idx,
                "rc_line": l,
                "rc_code": int(m.group(1)),
            })
            enable_i = None
            pass_i = None

    return len(seq) > 0, {
        "sequences_found": len(seq),
        "sequences": seq,
        "FT_IR_last": seq[-1]["passed_line"] if seq else None,
        "has_RC_pressed": bool(seq),
    }

# ============================================================
# SWITCH — Option A‑Color
# ============================================================
def check_switch_button(lines: List[str], name: str):
    detect_ok, detect_line = last_occurrence_pass(lines, "FT_DetectSwitches - PASSED")

    # Mute_button = slider validé par audio
    if name == "Mute_button":
        audio_ok, audio_line = last_occurrence_pass(lines, "FT_AUDIO_TEST_MICS_LED")
        if audio_ok:
            return True, {
                "validated_by": "FT_AUDIO_TEST_MICS_LED",
                "audio_line": audio_line,
                "detect_pass_last": detect_line,
            }

    base = name.replace("_button", "").replace("_", " ").strip()

    patterns_press = [
        rf"{re.escape(base)}\s+button\s+Pressed",
        rf"Fixture\s+{re.escape(base)}\s+button\s+Pressed",
        rf"{re.escape(base)}\s+button\s+test:END",
        r"switch\s+\d+\s+pressed",
    ]

    patterns_release = [
        rf"{re.escape(base)}\s+button\s+release:END",
        r"switch\s+\d+\s+released",
    ]

    press_line = None
    release_line = None

    for p in patterns_press:
        l = last_regex_line(lines, p)
        if l:
            press_line = l

    for p in patterns_release:
        l = last_regex_line(lines, p)
        if l:
            release_line = l

    uart_line = None
    if press_line:
        try:
            idx = lines.index(press_line)
        except:
            idx = None
        if idx is not None:
            for l in lines[max(0, idx-10): min(idx+20, len(lines))]:
                if "(UART" in l:
                    uart_line = l
                    break

    ok = detect_ok and (press_line is not None) and (release_line is not None or uart_line is not None)

    return ok, {
        "detect_pass_last": detect_line,
        "button_press_last": press_line,
        "button_release_last": release_line,
        "uart_validation_last": uart_line,
        "rule": "detect_pass AND press AND (release OR uart)"
    }

# ============================================================
# LED
# ============================================================
def check_led(lines):
    enable_seen = set()
    enable_evts = []
    for i, l in enumerate(lines):
        m = re.search(r"FT_LED\s+ENABLE\s+LED(\d+)", l, re.IGNORECASE)
        if m:
            led = f"LED{m.group(1)}"
            if led not in enable_seen:
                enable_seen.add(led)
                enable_evts.append((i, led, l))

    pairs = []
    seen = set()
    colors = set()
    pat = re.compile(r"LED_([A-Z0-9]+)_TEST\s+Test\s+is\s+Pass", re.IGNORECASE)

    for idx, led, enl in enable_evts:
        for j in range(idx+1, min(idx+120, len(lines))):
            m = pat.search(lines[j])
            if m:
                key = (led, m.group(1))
                if key not in seen:
                    seen.add(key)
                    pairs.append({
                        "led": led,
                        "color": m.group(1),
                        "enable_line": enl,
                        "test_line": lines[j],
                    })
                    colors.add(m.group(1))

    disable_last = None
    disable_val = None
    disable_ok = False
    for i, l in enumerate(lines):
        if "FT_LED DISABLE ALL" in l.upper():
            disable_last = l
            disable_val, disable_ok = detect_disable_all_pass(lines, i+1)

    return True, {
        "pairs_count": len(pairs),
        "pairs": pairs,
        "colors_passed": sorted(colors),
        "disable_all_last": disable_last,
        "disable_all_validation": disable_val,
        "disable_all_pass": disable_ok,
    }

# ============================================================
# ANALYSE
# ============================================================
def analyze(json_file, log_path, out_path):
    with open(json_file, "r", encoding="utf-8") as f:
        req = json.load(f)

    required = []
    for cat, tests in req.items():
        for t, v in tests.items():
            if isinstance(v, dict):
                if v.get("test", "").lower() == "true":
                    required.append((cat, t))
            else:
                if str(v).lower() == "true":
                    required.append((cat, t))

    lines = load_lines_from_path(log_path)
    results = {}

    for cat, test in required:
        if cat == "USB":
            if test == "USB_device_detection_test":
                ok, d = check_usb_device_detection(lines)
            elif test == "USB_file_reading_test":
                ok, d = check_usb_file_reading(lines)
            elif test == "USB_overcurrent_test":
                ok, d = check_usb_overcurrent(lines)
            else:
                ok, d = False, {}

        elif cat == "Ethernet":
            giga = req["Ethernet"].get("Giga_Ethernet_ping_test", "false") == "true"
            fast = req["Ethernet"].get("Fast_Ethernet_ping_test", "false") == "true"
            sts, d = check_eth(lines, giga, fast)
            ok = sts.get(test, False)

        elif cat == "LED":
            ok, d = check_led(lines)

        elif cat == "NAND":
            ok, d = check_nand(lines)

        elif cat == "RADIATED":
            if test == "WiFi2G_radiated_test":
                ok, d = check_wifi(lines, "2412")
            elif test == "WiFi5G_radiated_test":
                ok, d = check_wifi(lines, "5180")
            elif test == "Bluetooth_radiated_test":
                ok, d = check_bt(lines)
            else:
                ok, d = False, {}

        elif cat == "HDMI":
            if test == "EDID_test":
                ok, d = check_hdmi_edid(lines)
            elif test == "CEC_test":
                ok, d = check_hdmi_cec(lines)
            elif test == "VideoPattern_test":
                ok, d = check_hdmi_videopattern(lines)
            else:
                ok, d = False, {}

        elif cat == "IR":
            ok, d = check_ir(lines)

        elif cat == "SWITCH":
            ok, d = check_switch_button(lines, test)

        else:
            ok, d = False, {"note": "Catégorie non gérée"}

        results[test] = {"present": True, "passed": ok, "details": d}

    summary = {
        "OK": sorted([t for t, r in results.items() if r["passed"]]),
        "PresentButFailing": sorted([t for t, r in results.items() if not r["passed"]]),
        "MissingInLog": []
    }

    final = {
        "Input_JSON": json_file,
        "Input_Log": log_path,
        "Summary": summary,
        "Details": results,
    }

    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(final, f, indent=4, ensure_ascii=False)
        print("[INFO] Rapport sauvegardé dans :", out_path)

    # ========================================================
    # AFFICHAGE AVEC COULEURS ANSI
    # ========================================================
    BOLD = "\033[1m"
    RESET = "\033[0m"
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"

    print(f"{BOLD}========== RÉSUMÉ FINAL =========={RESET}")
    print(f"{YELLOW}Total tests requis :{RESET} {len(summary['OK']) + len(summary['PresentButFailing'])}")
    print(f"{GREEN}PASS : {len(summary['OK'])} {RESET}")
    print(f"{RED}FAIL : {len(summary['PresentButFailing'])} {RESET}")

    print("\n--- PASS ---")
    for t in summary["OK"]:
        print(f" • {GREEN}{t}{RESET}")

    print("\n--- FAIL ---")
    for t in summary["PresentButFailing"]:
        print(f" • {RED}{t}{RESET}")

    print(f"{BOLD}==================================={RESET}")

# ============================================================
# CLI
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="Vérificateur FT DIW/VSB/DTIW — Version Option A‑Color")
    parser.add_argument("json")
    parser.add_argument("--log", required=True)
    parser.add_argument("--out", required=False)
    args = parser.parse_args()

    if not os.path.exists(args.json):
        raise SystemExit("JSON introuvable : " + args.json)
    if not os.path.exists(args.log):
        raise SystemExit("Chemin --log introuvable : " + args.log)

    analyze(args.json, args.log, args.out)

if __name__ == "__main__":
    main()

# ============================================================
# STREAMLIT INTEGRATION WRAPPERS
# Added for telecom_validator integration — keeps CLI intact
# ============================================================

def parse_log(log_text: str) -> list:
    """
    Wrapper: split log text into lines for use with analyze_in_memory().
    Returns a list of strings (lines), compatible with load_lines_from_path().
    """
    return log_text.splitlines()


def analyze_in_memory(ft_tests_dict: dict, log_text: str) -> dict:
    """
    Run FT analysis entirely in memory (no file I/O).

    Args:
        ft_tests_dict: output of icp_ft_extract.extract_tests() — {category: {test: "true"/"false"}}
        log_text:      concatenated log text (META_LOGS or single file)

    Returns:
        Same structure as analyze() — {Summary: {OK, PresentButFailing, MissingInLog}, Details: {...}}
    """
    lines = log_text.splitlines()
    req = ft_tests_dict

    required = []
    for cat, tests in req.items():
        for t, v in tests.items():
            if isinstance(v, dict):
                if v.get("test", "").lower() == "true":
                    required.append((cat, t))
            else:
                if str(v).lower() == "true":
                    required.append((cat, t))

    results = {}

    for cat, test in required:
        ok, d = False, {}

        if cat == "USB":
            if test == "USB_device_detection_test":
                ok, d = check_usb_device_detection(lines)
            elif test == "USB_file_reading_test":
                ok, d = check_usb_file_reading(lines)
            elif test == "USB_overcurrent_test":
                ok, d = check_usb_overcurrent(lines)

        elif cat == "Ethernet":
            giga = req["Ethernet"].get("Giga_Ethernet_ping_test", "false") == "true"
            fast = req["Ethernet"].get("Fast_Ethernet_ping_test", "false") == "true"
            sts, d = check_eth(lines, giga, fast)
            ok = sts.get(test, False)

        elif cat == "LED":
            ok, d = check_led(lines)

        elif cat == "NAND":
            ok, d = check_nand(lines)

        elif cat == "RADIATED":
            if test == "WiFi2G_radiated_test":
                ok, d = check_wifi(lines, "2412")
            elif test == "WiFi5G_radiated_test":
                ok, d = check_wifi(lines, "5180")
            elif test == "Bluetooth_radiated_test":
                ok, d = check_bt(lines)

        elif cat == "HDMI":
            if test == "EDID_test":
                ok, d = check_hdmi_edid(lines)
            elif test == "CEC_test":
                ok, d = check_hdmi_cec(lines)
            elif test == "VideoPattern_test":
                ok, d = check_hdmi_videopattern(lines)

        elif cat == "IR":
            ok, d = check_ir(lines)

        elif cat == "SWITCH":
            ok, d = check_switch_button(lines, test)

        results[test] = {"present": True, "passed": ok, "details": d}

    summary = {
        "OK": sorted([t for t, r in results.items() if r["passed"]]),
        "PresentButFailing": sorted([t for t, r in results.items() if not r["passed"]]),
        "MissingInLog": [],
        "Tests": len(required),
        "Pass": sum(1 for r in results.values() if r["passed"]),
        "Fail": sum(1 for r in results.values() if not r["passed"]),
        "MissingInLog_count": 0,
    }

    return {
        "Summary": summary,
        "Details": results,
    }
