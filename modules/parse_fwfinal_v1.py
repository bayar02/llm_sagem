#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parser FW_Upgrade / Final v1
=============================
Analyse les logs 1+FW_Upgrade-*.log, 2+FW_Upgrade-*.log et 1+Final-*.log.

Ces logs sont essentiellement PASS/FAIL par étape.
Les quelques validations numériques (version strings, checksums)
sont extraites quand elles existent.
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

RE_MAC_RESULT  = re.compile(r"(?:mac|MAC)\d+\s*=\s*([0-9a-fA-F:]{11,17})")
RE_TPID_RESULT = re.compile(r"TKL_ID\s*=\s*([0-9A-Fa-f\-]{30,})")
RE_STB_SN      = re.compile(r"(?:SAGCSTB|stbsn)\s*=\s*(\w+)", re.IGNORECASE)
RE_PCB_SN      = re.compile(r"(?:gsfispcb|PCB_SN)\s*=\s*(\w+)", re.IGNORECASE)
RE_SKIPPED     = re.compile(r"\@STEP([^@]+)\@[\w\s]+\s+Skipped\.", re.IGNORECASE)
RE_BOOTUP_TIME = re.compile(r"Check_bootup\s+Test is Pass\s*!\s*-----\s*([\d.]+)\s*Sec\.", re.IGNORECASE)


def parse_log(log_text: str) -> Dict[str, Any]:
    meta: Dict[str, Any] = {"macs": []}
    seen: Dict[str, Dict] = {}
    steps, sagemtests, skipped = [], [], []

    for line in log_text.splitlines():
        ls = line.strip()

        for pat, key in [(RE_SCRIPT_FILE,"script_file"),(RE_SYSTEM_VERSION,"system_version"),(RE_SAGCSN,"sagcsn")]:
            m = pat.search(ls)
            if m and key not in meta: meta[key] = m.group(1).strip()

        for m in RE_MAC_RESULT.finditer(ls):
            mac = m.group(1).strip()
            if mac not in meta["macs"]: meta["macs"].append(mac)

        m = RE_TPID_RESULT.search(ls)
        if m and "tpid" not in meta: meta["tpid"] = m.group(1).strip()

        m = RE_STB_SN.search(ls)
        if m and "stb_sn" not in meta: meta["stb_sn"] = m.group(1).strip()

        m = RE_PCB_SN.search(ls)
        if m and "pcb_sn" not in meta: meta["pcb_sn"] = m.group(1).strip()

        m = RE_BOOTUP_TIME.search(ls)
        if m and "bootup_time_s" not in meta: meta["bootup_time_s"] = float(m.group(1))

        m = RE_VALIDATION.search(ls)
        if m:
            try:
                tid=m.group(1); param=m.group(2).strip()
                val=float(m.group(3)); vmin=float(m.group(4)); vmax=float(m.group(5))
            except ValueError: continue
            seen[f"{tid}_{param}"] = {"test_id":tid,"param":param,"value":val,
                                       "min":vmin,"max":vmax,"passed":vmin<=val<=vmax}
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

    st_d={}
    for st in sagemtests: st_d[st["command"]]=st
    sagemtests=list(st_d.values())

    validations=list(seen.values())
    n_pass=sum(1 for v in validations if v["passed"])
    n_fail=sum(1 for v in validations if not v["passed"])
    s_pass=sum(1 for s in steps if s["passed"])
    s_fail=sum(1 for s in steps if not s["passed"])
    st_pass=sum(1 for st in sagemtests if st["passed"])
    st_fail=sum(1 for st in sagemtests if not st["passed"])

    summary={
        "Tests": len(validations)+len(steps),
        "CheckedParams": len(validations),
        "Pass": n_pass, "Fail": n_fail, "MissingInLog": 0,
        "StepsPass": s_pass, "StepsFail": s_fail, "StepsSkipped": len(skipped),
        "SagemTestsPass": st_pass, "SagemTestsFail": st_fail,
        "GlobalPass": n_fail==0 and s_fail==0 and st_fail==0,
    }
    return {"meta":meta,"validations":validations,"steps":steps,"sagemtests":sagemtests,
            "skipped":skipped,"summary":summary}


def compare(parsed: Dict[str, Any], icp_limits: Optional[List] = None) -> Dict[str, Any]:
    """
    Rapport de validation FW_Upgrade / Final.
    PASS/FAIL basé sur les étapes et SagemTests du log.
    """
    validations = parsed.get("validations",[])
    steps       = parsed.get("steps",[])
    sagemtests  = parsed.get("sagemtests",[])
    summary_in  = parsed.get("summary",{})

    tests = []

    # Mesures numériques (rares dans FW/Final, mais présentes parfois)
    for v in validations:
        tests.append({
            "Group":   "Validation",
            "Name":    v["param"],
            "Value":   v["value"],
            "Min":     v["min"],
            "Max":     v["max"],
            "Unit":    "",
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
        "Tests":    tests,
        "Meta":     parsed.get("meta",{}),
        "Skipped":  parsed.get("skipped",[]),
    }
