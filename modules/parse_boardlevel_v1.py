#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parser BoardLevel v1
====================
Analyse les logs 1+BoardLevel-*.log.

Les limites min/max sont EMBARQUÉES dans le log via :
  CurrentTestID:XXXX - The validation: PARAM = val (min,max)

Le parser extrait et compare en une seule passe.
"""

import re
from typing import Any, Dict, List, Optional

RE_VALIDATION = re.compile(
    r"CurrentTestID:(\S+)\s+-\s+The validation:\s+"
    r"([A-Za-z0-9_.\- ]+?)\s*=\s*(-?[\d.]+)\s*"
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
RE_SKIPPED        = re.compile(r"\@STEP([^@]+)\@[\w\s]+\s+Skipped\.", re.IGNORECASE)


def _category(param: str) -> str:
    p = param.upper()
    if any(k in p for k in ["P12V","P5V","P3V","P1V","P0V","VDD","AON","VDAO","VTIL","DDR"]):
        return "voltage"
    if any(k in p for k in ["VBER","FREQOFF","SYMBOLRATE","UBLOCK","GETPIDTIME","POWER"]):
        return "fe_rf"
    if any(k in p for k in ["WIFISIZE","BTSIZE","CID","NAND","EMMC","USB_VOLTAGE"]):
        return "memory"
    if any(k in p for k in ["TEMP","CPUOTEMP"]):
        return "thermal"
    if any(k in p for k in ["GAMS","GSPEED"]):
        return "network"
    return "other"


def _unit(param: str) -> str:
    p = param.upper()
    if any(k in p for k in ["P12V","P5V","P3V","P1V","P0V","VDD","AON","VDAO","VTIL"]):
        return "V"
    if "TEMP" in p or "CPUOTEMP" in p: return "°C"
    if "SNR" in p: return "dB"
    if "GAMS" in p: return "ms"
    if "GSPEED" in p: return "KB/s"
    return ""


def parse_log(log_text: str) -> Dict[str, Any]:
    meta = {}
    seen: Dict[str, Dict] = {}
    steps, sagemtests, skipped = [], [], []

    for line in log_text.splitlines():
        ls = line.strip()

        for pat, key in [(RE_SCRIPT_FILE,"script_file"),(RE_SYSTEM_VERSION,"system_version"),(RE_SAGCSN,"sagcsn")]:
            m = pat.search(ls)
            if m and key not in meta: meta[key] = m.group(1).strip()

        m = RE_VALIDATION.search(ls)
        if m:
            try:
                tid=m.group(1); param=m.group(2).strip()
                val=float(m.group(3)); vmin=float(m.group(4)); vmax=float(m.group(5))
            except ValueError: continue
            seen[param] = {"test_id":tid,"param":param,"value":val,"min":vmin,"max":vmax,
                           "passed":vmin<=val<=vmax,"unit":_unit(param),"category":_category(param)}
            continue

        m = RE_STEP.search(ls)
        if m:
            steps.append({"run_id":m.group(1),"step_num":m.group(2).strip(),
                           "step_name":m.group(3).strip(),"passed":m.group(4).lower()=="pass",
                           "duration_s":float(m.group(5))})
            continue

        m = RE_SKIPPED.search(ls)
        if m: skipped.append(m.group(1).strip()); continue

        m = RE_SAGEMTEST.search(ls)
        if m: sagemtests.append({"command":m.group(1),"passed":m.group(2).upper()=="PASSED"})

    # Dédupliquer SagemTests
    st_d={};
    for st in sagemtests: st_d[st["command"]]=st
    sagemtests = list(st_d.values())

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
    return {"meta":meta,"validations":validations,"steps":steps,"sagemtests":sagemtests,
            "skipped":skipped,"summary":summary}


def compare(parsed: Dict[str, Any], icp_limits: Optional[List] = None) -> Dict[str, Any]:
    """
    Construit le rapport de validation BoardLevel.
    Les limites sont déjà dans 'parsed' (embarquées dans le log).
    """
    validations = parsed.get("validations",[])
    steps       = parsed.get("steps",[])
    sagemtests  = parsed.get("sagemtests",[])
    summary_in  = parsed.get("summary",{})

    tests = []

    # Mesures numériques (tensions, températures, etc.)
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
            "Min":      None, "Max":None, "Unit":"",
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
            "Min":     None, "Max":None, "Unit":"",
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
        "Skipped":    parsed.get("skipped",[]),
    }
