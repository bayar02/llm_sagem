#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parser System v1
================
Analyse les logs 1+System-*.log / 1+SYSTEM-*.log.

Couvre : HDMI, Ethernet, USB, LED, Boutons, IR,
         Wi-Fi radiated, BT radiated, Température CPU.

Les limites sont EMBARQUÉES dans le log via CurrentTestID.
"""

import re
from typing import Any, Dict, List, Optional

RE_VALIDATION = re.compile(
    r"CurrentTestID:(\S+)\s+-\s+The validation:\s+"
    r"(.+?)\s*=\s*(-?[\d.]+)\s*"
    r"\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)",
    re.IGNORECASE,
)
RE_STEP = re.compile(
    r"([0-9A-Za-z]+):\@STEP([^@]+)@(.+?)\s+Test is (Pass|Fail)\s*!\s*-----\s*([\d.]+)\s*Sec\.",
    re.IGNORECASE,
)
RE_SAGEMTEST = re.compile(
    r"\[SAGEMTESTS\]\s+=>\s+(\S+)\s+-\s+(PASSED|FAILED)\s+<=",
    re.IGNORECASE,
)
RE_SCRIPT_FILE    = re.compile(r"Script File is (.+)")
RE_SYSTEM_VERSION = re.compile(r"System Version is (.+)")
RE_SAGCSN         = re.compile(r"SAGCSN:\s*(\S+)")
RE_TT_VERSION     = re.compile(r"SagemTest Version\s*:\s*(\S+)")

# Catégorisation des paramètres
_CAT = {
    "hdmi":          ["HDMI","EDID","CEC"],
    "ethernet":      ["gams","gspeed","ETH","BWD_Ethernet","PING"],
    "usb":           ["USB","bUsb","Transfer","bUsbCurrent"],
    "led":           ["LED_R","LED_G","LED_B","LED_Intensity","LED_X","LED_Y",
                      "RED_LED","WHITE_LED","OFF_LED",
                      "RedOn","RedOff","GreenOn","GreenOff","BlueOn","BlueOff",
                      "WhiteOn","WhiteOff"],
    "button":        ["bBoutons","Switch","Button","scfpin"],
    "ir":            ["bIr","IR"],
    "wifi_radiated": ["WIFI","wifi"],
    "bt_radiated":   ["BT TX","BT_TX","BTsize","BT EDR"],
    "temperature":   ["CPUtemp","temp"],
    "memory":        ["WIFIsize","BTsize","NAND","EMMC","CID"],
}


def _cat(param: str) -> str:
    for cat, keys in _CAT.items():
        if any(k.lower() in param.lower() for k in keys):
            return cat
    return "other"


def _unit(param: str) -> str:
    p = param.upper()
    if any(k in p for k in ["POWER","DBM","LO_LEAK"]): return "dBm"
    if any(k in p for k in ["TEMP","CPU"]): return "°C"
    if any(k in p for k in ["GAMS","LATENCY","PING"]): return "ms"
    if "GSPEED" in p: return "KB/s"
    return ""


def parse_log(log_text: str) -> Dict[str, Any]:
    meta = {}
    seen: Dict[str, Dict] = {}
    steps, sagemtests = [], []

    for line in log_text.splitlines():
        ls = line.strip()

        for pat, key in [(RE_SCRIPT_FILE,"script_file"),(RE_SYSTEM_VERSION,"system_version"),
                         (RE_SAGCSN,"sagcsn"),(RE_TT_VERSION,"tt_version")]:
            m = pat.search(ls)
            if m and key not in meta: meta[key] = m.group(1).strip()

        m = RE_VALIDATION.search(ls)
        if m:
            try:
                tid=m.group(1); param=m.group(2).strip()
                val=float(m.group(3)); vmin=float(m.group(4)); vmax=float(m.group(5))
            except ValueError: continue
            key = f"{tid}_{param}"
            seen[key] = {"test_id":tid,"param":param,"value":val,"min":vmin,"max":vmax,
                         "passed":vmin<=val<=vmax,"unit":_unit(param),"category":_cat(param)}
            continue

        m = RE_STEP.search(ls)
        if m:
            steps.append({"run_id":m.group(1),"step_num":m.group(2).strip(),
                           "step_name":m.group(3).strip(),"passed":m.group(4).lower()=="pass",
                           "duration_s":float(m.group(5))})
            continue

        m = RE_SAGEMTEST.search(ls)
        if m: sagemtests.append({"command":m.group(1),"passed":m.group(2).upper()=="PASSED"})

    st_d={}
    for st in sagemtests: st_d[st["command"]]=st
    sagemtests=list(st_d.values())

    validations = list(seen.values())
    n_pass=sum(1 for v in validations if v["passed"])
    n_fail=sum(1 for v in validations if not v["passed"])
    s_pass=sum(1 for s in steps if s["passed"])
    s_fail=sum(1 for s in steps if not s["passed"])
    st_pass=sum(1 for st in sagemtests if st["passed"])
    st_fail=sum(1 for st in sagemtests if not st["passed"])

    by_cat={}
    for v in validations:
        c=v["category"]; bc=by_cat.setdefault(c,{"pass":0,"fail":0,"total":0})
        bc["total"]+=1; bc["pass" if v["passed"] else "fail"]+=1

    summary={
        "Tests": len(validations)+len(steps),
        "CheckedParams": len(validations),
        "Pass": n_pass, "Fail": n_fail, "MissingInLog": 0,
        "StepsPass": s_pass, "StepsFail": s_fail,
        "SagemTestsPass": st_pass, "SagemTestsFail": st_fail,
        "GlobalPass": n_fail==0 and s_fail==0 and st_fail==0,
        "ByCategory": by_cat,
    }
    return {"meta":meta,"validations":validations,"steps":steps,"sagemtests":sagemtests,"summary":summary}


def compare(parsed: Dict[str, Any], icp_limits: Optional[List] = None) -> Dict[str, Any]:
    """
    Rapport de validation System Functional.
    Toutes les limites sont embarquées dans le log.
    """
    validations = parsed.get("validations",[])
    steps       = parsed.get("steps",[])
    sagemtests  = parsed.get("sagemtests",[])
    summary_in  = parsed.get("summary",{})

    tests = []

    # Mesures numériques (LED, Ethernet, Wi-Fi radiated, BT, Temperature…)
    for v in validations:
        tests.append({
            "Group":   v["category"].replace("_"," ").title(),
            "Name":    v["param"],
            "Value":   v["value"],
            "Min":     v["min"],
            "Max":     v["max"],
            "Unit":    v["unit"],
            "Pass":    v["passed"],
            "Source":  "validation",
        })

    # Étapes @STEP
    for s in steps:
        tests.append({
            "Group":    "Steps",
            "Name":     s["step_name"],
            "Value":    "PASS" if s["passed"] else "FAIL",
            "Min":None,"Max":None,"Unit":"",
            "Pass":     s["passed"],
            "Source":   "step",
            "Duration": s["duration_s"],
        })

    # SagemTests
    for st in sagemtests:
        tests.append({
            "Group":   "SagemTests",
            "Name":    st["command"],
            "Value":   "PASS" if st["passed"] else "FAIL",
            "Min":None,"Max":None,"Unit":"",
            "Pass":    st["passed"],
            "Source":  "sagemtest",
        })

    n_pass=sum(1 for t in tests if t["Pass"])
    n_fail=sum(1 for t in tests if not t["Pass"])
    n_num =sum(1 for t in tests if t["Source"]=="validation")

    return {
        "Summary": {
            "Tests": len(tests),
            "CheckedParams": n_num,
            "Pass": n_pass,
            "Fail": n_fail,
            "MissingInLog": 0,
            "StepsPass":      summary_in.get("StepsPass",0),
            "StepsFail":      summary_in.get("StepsFail",0),
            "SagemTestsPass": summary_in.get("SagemTestsPass",0),
            "SagemTestsFail": summary_in.get("SagemTestsFail",0),
        },
        "Tests":      tests,
        "ByCategory": summary_in.get("ByCategory",{}),
        "Meta":       parsed.get("meta",{}),
    }
