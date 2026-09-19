#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ICP to MTP Analysis and Reporting Tool
Système automatisé de validation et d'analyse de tests pour équipements de télécommunication.
"""

import streamlit as st
import json, io, re, sys, os, tempfile, time, copy, traceback
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import pandas as pd
import plotly.graph_objects as go

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "modules"))
sys.path.insert(0, str(ROOT / "rag_env" / "modules_rag"))

try:
    import fitz; FITZ_OK = True
except ImportError:
    FITZ_OK = False

try:
    from demo_data import (DEMO_PRODUCT, DEMO_VERSION, DEMO_FE_LIMITS,
                           DEMO_RF_LIMITS, DEMO_FE_REPORT, DEMO_RF_REPORT,
                           DEMO_MTP_REPORT, DEMO_COMPARISON)
    DEMO_OK = True
except ImportError:
    DEMO_OK = False

from config_store import (
    load_config, save_config,
    list_products, get_product, create_product, update_product, delete_product,
    list_modules, create_module, update_module, delete_module,
    list_parsers, create_parser, update_parser, delete_parser,
    list_extractors, create_extractor, update_extractor, delete_extractor,
    list_test_rules, create_test_rule, update_test_rule, delete_test_rule,
    list_regexes, list_regexes_by_scope, get_regex,
    create_regex, update_regex, delete_regex,
    test_regex, export_regexes_as_python, REGEX_SCOPES,
    suggest_parser_for_log, suggest_by_filename, suggest_extractor_for_pdf, validate_product_config
)

# ─────────────────────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ICP to MTP Analysis and Reporting Tool",
    page_icon="🛰️", layout="wide", initial_sidebar_state="expanded"
)

st.markdown("""
<style>
:root{--primary:#0057b8;--primary-light:#e8f0fb;--success:#16a34a;
      --fail:#dc2626;--warn:#d97706;--neutral:#64748b;--card:#f8fafc;--border:#e2e8f0;}
.main-header{background:linear-gradient(135deg,#0057b8,#003d80);color:white;
  padding:1.4rem 2rem;border-radius:12px;margin-bottom:1.2rem;display:flex;align-items:center;gap:1rem;}
.main-header h1{margin:0;font-size:1.45rem;font-weight:800;}
.main-header p{margin:0;opacity:.82;font-size:.85rem;}
.stepper-wrap{display:flex;align-items:center;margin:1.2rem 0;overflow-x:auto;padding-bottom:4px;}
.step-circle{width:30px;height:30px;border-radius:50%;display:flex;align-items:center;
  justify-content:center;font-weight:700;font-size:.8rem;border:2px solid #cbd5e1;
  background:white;color:#94a3b8;flex-shrink:0;}
.step-circle.done{background:#16a34a;border-color:#16a34a;color:white;}
.step-circle.active{background:#0057b8;border-color:#0057b8;color:white;}
.step-label{font-size:.75rem;color:#64748b;white-space:nowrap;}
.step-label.active{color:#0057b8;font-weight:700;}.step-label.done{color:#16a34a;}
.step-item{display:flex;align-items:center;gap:5px;}
.step-line{flex:1;height:2px;background:#e2e8f0;min-width:18px;max-width:50px;margin:0 3px;}
.step-line.done{background:#16a34a;}
.metric-card{background:var(--card);border:1px solid var(--border);border-radius:10px;
  padding:.9rem 1rem;text-align:center;}
.metric-card .val{font-size:1.9rem;font-weight:800;}
.metric-card .lbl{font-size:.78rem;color:var(--neutral);margin-top:2px;}
.val-pass{color:var(--success);}.val-fail{color:var(--fail);}.val-warn{color:var(--warn);}.val-info{color:var(--primary);}
.badge{display:inline-block;padding:2px 9px;border-radius:999px;font-size:.73rem;font-weight:600;}
.badge-pass{background:#dcfce7;color:#166534;}.badge-fail{background:#fee2e2;color:#991b1b;}
.badge-warn{background:#fef3c7;color:#92400e;}.badge-neutral{background:#f1f5f9;color:#475569;}
.badge-blue{background:#dbeafe;color:#1e40af;}
.section-title{font-size:1.05rem;font-weight:700;color:#0f172a;padding-bottom:5px;
  border-bottom:2px solid var(--primary);margin-bottom:.9rem;}
.upload-hint{background:var(--primary-light);border:2px dashed #93c5fd;border-radius:10px;
  padding:.9rem;text-align:center;color:#1e40af;font-size:.85rem;margin-bottom:.9rem;}
.crud-card{background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:.9rem;margin-bottom:.6rem;}
.crud-card.builtin{border-left:4px solid #0057b8;}.crud-card.custom{border-left:4px solid #16a34a;}
.anomaly-critical{background:#fff1f2;border-left:4px solid #dc2626;padding:8px;margin-bottom:4px;border-radius:4px;}
.anomaly-warning{background:#fffbeb;border-left:4px solid #d97706;padding:8px;margin-bottom:4px;border-radius:4px;}
.anomaly-info{background:#f0f9ff;border-left:4px solid #0ea5e9;padding:8px;margin-bottom:4px;border-radius:4px;}
.suggest-box{background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:.75rem;margin:.5rem 0;}
.warn-box{background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:.75rem;margin:.5rem 0;}
.error-box{background:#fff1f2;border:1px solid #fca5a5;border-radius:8px;padding:.75rem;margin:.5rem 0;}
.info-box{background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:.75rem;margin:.5rem 0;}
.file-badge{background:#f1f5f9;border:1px solid #cbd5e1;border-radius:6px;padding:3px 8px;
  font-size:.78rem;display:inline-block;margin:2px;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────────────────────
def _init():
    d = {"step":0,"cfg":None,"active_product_id":None,"demo_mode":False,
         "icp_fe_limits":None,"icp_rf_limits":None,"icp_ft_tests":None,
         "icp_pdf_name":"","icp_pdf_text":"",
         "log_results":{},"fe_report":None,"rf_report":None,"icp_report_combined":None,
         "meta_logs_text":None,"unified_log_rows":None,
         "mtp_reports":[],"mtp_combined":None,"comparison_report":None}
    for k,v in d.items():
        if k not in st.session_state: st.session_state[k]=v
    if st.session_state.cfg is None:
        st.session_state.cfg = load_config()
_init()
cfg = st.session_state.cfg

# ─────────────────────────────────────────────────────────────
#  UI HELPERS
# ─────────────────────────────────────────────────────────────
STEPS=[("🔧","Config Produit"),("📄","Extraction ICP"),("📋","Validation Logs"),
       ("📊","Rapport ICP"),("📑","Analyse MTP"),("🔄","Comparaison"),("🏁","Rapport Final")]

def render_stepper(cur):
    parts=[]
    for i,(icon,label) in enumerate(STEPS):
        st_="done" if i<cur else ("active" if i==cur else "")
        ico="✓" if i<cur else str(i+1)
        parts.append(f'<div class="step-item"><div class="step-circle {st_}">{ico}</div>'
                     f'<span class="step-label {st_}">{icon} {label}</span></div>')
        if i<len(STEPS)-1:
            parts.append(f'<div class="step-line {"done" if i<cur else ""}"></div>')
    st.markdown(f'<div class="stepper-wrap">{"".join(parts)}</div>',unsafe_allow_html=True)

def section_title(t): st.markdown(f'<div class="section-title">{t}</div>',unsafe_allow_html=True)
def mc(v,l,k="info"): return f'<div class="metric-card"><div class="val val-{k}">{v}</div><div class="lbl">{l}</div></div>'

def nav(prev=None,nxt=None,nxt_label="Suivant →",disabled=False,prev_label="← Précédent"):
    c1,_,c3=st.columns([1,4,1])
    with c1:
        if prev is not None and st.button(prev_label,use_container_width=True):
            st.session_state.step=prev; st.rerun()
    with c3:
        if nxt is not None and st.button(nxt_label,use_container_width=True,
                                          disabled=disabled,type="primary"):
            st.session_state.step=nxt; st.rerun()

def safe_temp_write(content:bytes, suffix:str) -> str:
    """Crée un fichier temporaire en fermant explicitement le fd (évite PermissionError Windows)."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        os.write(fd, content)
    finally:
        os.close(fd)
    return path

def safe_temp_delete(path:str):
    try:
        if path and os.path.exists(path): os.unlink(path)
    except PermissionError:
        pass

def build_icp_combined():
    prod = get_product(cfg, st.session_state.active_product_id or "") or {}
    return {"product":prod.get("name",""),"version":prod.get("version",""),
            "operator":prod.get("operator",""),"generated_at":datetime.now().isoformat(),
            "modules":prod.get("modules",[]),
            "FE_Limits":st.session_state.icp_fe_limits,
            "RF_Limits":st.session_state.icp_rf_limits,
            "FE_Validation":st.session_state.fe_report,
            "RF_Validation":st.session_state.rf_report,
            "log_results":st.session_state.log_results}

def _merge_fe_reports(fe_list):
    merged=[]; tp=tf=tm=tc=0; mt=[]; mp=[]
    for item in fe_list:
        r=item["report"]; s=r.get("Summary",{})
        tp+=s.get("Pass",0); tf+=s.get("Fail",0)
        tm+=s.get("MissingInLog",0); tc+=s.get("CheckedParams",0)
        for t in r.get("Tests",[]): t["_source"]=item["file"]; merged.append(t)
        md=r.get("MissingDetails",{})
        mt.extend(md.get("MissingTests",[])); mp.extend(md.get("MissingParams",[]))
    return {"Summary":{"Tests":len(merged),"CheckedParams":tc,"Pass":tp,"Fail":tf,
                        "MissingTests":len(mt),"MissingParams":len(mp),
                        "MissingInLog":tm,"SourceFiles":len(fe_list)},
            "Tests":merged,"MissingDetails":{"MissingTests":mt,"MissingParams":mp}}

def _merge_rf_reports(rf_list):
    merged=[]; tp=tf=tm=tc=0; miss=[]; mm=[]
    for item in rf_list:
        r=item["report"]; s=r.get("Summary",{})
        tp+=s.get("PassVsJSON_Count",0); tf+=s.get("JSON_Fails_Count",0)
        tm+=s.get("MissingInLog_Count",0); tc+=s.get("CheckedParams",0)
        for t in r.get("Tests",[]): t["_source"]=item["file"]; merged.append(t)
        miss.extend(r.get("MissingInLog",[])); mm.extend(r.get("MismatchDetails",[]))
    return {"Summary":{"Tests":len(merged),"CheckedParams":tc,"PassVsJSON_Count":tp,
                        "JSON_Fails_Count":tf,"LimitsMismatch_Count":len(mm),
                        "MissingInLog_Count":tm,"SourceFiles":len(rf_list)},
            "Tests":merged,"MissingInLog":miss,"MismatchDetails":mm,"JSONFailDetails":[]}

def _static_compare():
    icp=st.session_state.icp_report_combined or {}
    mtp=st.session_state.mtp_combined or {}
    fe_icp=icp.get("FE_Limits") or []; fe_mtp=mtp.get("FE_Results") or []
    matched=0; unmatched=0; fe_comp=[]
    icp_idx={(t.get("Frequency",""),t.get("Modulation","")):t for t in fe_icp}
    mtp_idx={(t.get("Frequency",""),t.get("Modulation","")):t for t in fe_mtp}
    for key,icp_t in icp_idx.items():
        mtp_t=mtp_idx.get(key); params=[]
        if mtp_t:
            matched+=1
            for lim in icp_t.get("Limits",[]):
                mv=next((r.get("Value") for r in mtp_t.get("Results",[]) if r.get("Parameter")==lim["Parameter"]),None)
                try:
                    vf=float(str(mv).replace(",",".")) if mv is not None else None
                    lo=float(lim.get("Min","nan")); hi=float(lim.get("Max","nan"))
                    ok=(lo<=vf<=hi) if vf is not None else None
                    delta=round(vf-hi,2) if vf and vf>hi else (round(vf-lo,2) if vf and vf<lo else None)
                except: vf=mv; ok=None; delta=None
                params.append({"Parameter":lim["Parameter"],"ICP_Min":lim.get("Min"),
                                "ICP_Max":lim.get("Max"),"MTP_Value":vf,"Compliant":ok,"Delta":delta,"Note":""})
            fe_comp.append({"Frequency":key[0],"Modulation":key[1],"Status":"MATCHED","Parameters":params})
        else:
            unmatched+=1
            fe_comp.append({"Frequency":key[0],"Modulation":key[1],"Status":"ICP_ONLY","Parameters":[]})
    tc=sum(1 for t in fe_comp for p in t["Parameters"] if p.get("Compliant") is True)
    tnc=sum(1 for t in fe_comp for p in t["Parameters"] if p.get("Compliant") is False)
    return {"comparison_summary":{"total_icp_specs":len(fe_icp),"total_mtp_results":len(fe_mtp),
                                    "matched":matched,"unmatched_icp":unmatched,"compliant":tc,
                                    "non_compliant":tnc,"not_tested":unmatched,
                                    "global_status":"PASS" if tnc==0 and unmatched==0 else ("FAIL" if tnc>0 else "PARTIAL")},
            "FE_Comparison":fe_comp,"RF_Comparison":{},
            "anomalies":[{"type":"MISSING_IN_MTP","severity":"CRITICAL",
                           "description":f"Test {t['Frequency']} {t['Modulation']} absent du MTP",
                           "frequency":t["Frequency"],"modulation":t["Modulation"],"parameter":""}
                          for t in fe_comp if t["Status"]=="ICP_ONLY"],
            "recommendations":["Vérifier la couverture des tests MTP.",
                               "S'assurer que tous les tests obligatoires sont exécutés."]}

# ─────────────────────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""<div style='text-align:center;padding:.8rem 0;'>
      <span style='font-size:2.2rem'>🛰️</span>
      <h3 style='margin:.3rem 0 0;color:#0057b8;font-size:1rem;'>ICP→MTP Tool</h3>
      <p style='font-size:.72rem;color:#64748b;margin:0;'>Analysis & Reporting</p>
    </div>""",unsafe_allow_html=True)
    st.divider()
    st.markdown("**Navigation**")
    for i,(icon,label) in enumerate(STEPS):
        if st.button(f"{icon} {label}",key=f"nav_{i}",use_container_width=True,
                     disabled=(i==st.session_state.step)):
            st.session_state.step=i; st.rerun()
    st.divider()
    products=list_products(cfg)
    if products:
        st.markdown("**Produit actif**")
        pnames={p["id"]:f"{p['name']} ({p['version']})" for p in products}
        sel=st.selectbox("",options=list(pnames.keys()),format_func=lambda x:pnames[x],
                         key="sidebar_prod",label_visibility="collapsed")
        if sel!=st.session_state.active_product_id:
            st.session_state.active_product_id=sel; st.rerun()
        st.divider()
    if DEMO_OK:
        st.markdown("**🎮 Démonstration**")
        if st.button("⚡ Charger données démo",use_container_width=True):
            st.session_state.demo_mode=True
            demo_pid="prod_demo"
            cfg["products"][demo_pid]={"id":demo_pid,"name":"DCIW378-DEMO","version":"HW_Rev_B",
                "operator":"EST Telecom","modules":["FE","RF_WiFi","RF_BT"],
                "parser_map":{"FE":"parse_fe_v2","RF_WiFi":"parse_rf_v15","RF_BT":"parse_rf_v15"},
                "extractor_map":{"FE":"extract_fe_v2","RF_WiFi":"extract_rf_v3","RF_BT":"extract_rf_v3"},
                "test_rule_map":{"FE":"fe_standard","RF_WiFi":"rf_all_tests","RF_BT":"rf_mandatory_only"},
                "notes":"Démo","created_at":datetime.now().isoformat(),"updated_at":datetime.now().isoformat()}
            st.session_state.active_product_id=demo_pid
            st.session_state.icp_fe_limits=DEMO_FE_LIMITS
            st.session_state.icp_rf_limits=DEMO_RF_LIMITS
            st.session_state.fe_report=DEMO_FE_REPORT
            st.session_state.rf_report=DEMO_RF_REPORT
            st.session_state.icp_report_combined=build_icp_combined()
            st.session_state.mtp_reports=[DEMO_MTP_REPORT]
            st.session_state.mtp_combined={"sources":["MTP_DCIW378_DEMO.pdf"],
                "generated_at":datetime.now().isoformat(),
                "FE_Results":DEMO_MTP_REPORT["FE_Results"],
                "RF_Results":DEMO_MTP_REPORT["RF_Results"],
                "individual_reports":[DEMO_MTP_REPORT]}
            st.session_state.comparison_report=DEMO_COMPARISON
            st.session_state.step=6; st.rerun()
        st.divider()
    with st.expander("⚙️ Config JSON"):
        st.download_button("💾 Exporter",data=json.dumps(cfg,indent=2,ensure_ascii=False).encode(),
                           file_name="telecom_config.json",mime="application/json",use_container_width=True)
        imp=st.file_uploader("Importer",type=["json"],key="cfg_imp",label_visibility="collapsed")
        if imp:
            try:
                loaded=json.loads(imp.read())
                for sec in ("products","modules","parsers","extractors","test_rules"):
                    cfg[sec].update(loaded.get(sec,{}))
                save_config(cfg); st.success("Importé!"); st.rerun()
            except Exception as e: st.error(str(e))
    if st.session_state.icp_report_combined: st.success("✅ Rapport ICP prêt")
    if st.session_state.comparison_report:   st.success("✅ Rapport final prêt")
    if st.session_state.get("demo_mode"):    st.info("🎮 Mode démo actif")

# ─────────────────────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────────────────────
step=st.session_state.step
icon_s,label_s=STEPS[step]
st.markdown(f"""<div class="main-header">
  <span style='font-size:2rem'>🛰️</span>
  <div><h1>ICP to MTP Analysis and Reporting Tool</h1>
  <p>Étape {step+1}/{len(STEPS)} · {icon_s} {label_s}</p></div>
</div>""",unsafe_allow_html=True)
render_stepper(step)
if st.session_state.get("demo_mode"):
    st.info("🎮 **Mode Démonstration** — données synthétiques.")
st.divider()

# ═══════════════════════════════════════════════════════════════
#  ÉTAPE 0 — CONFIGURATION PRODUIT (CRUD complet)
# ═══════════════════════════════════════════════════════════════
if step==0:
    section_title("🔧 Configuration Produit")
    tab_prod,tab_mod,tab_par,tab_ext,tab_rule,tab_rx=st.tabs(
        ["🏭 Produits","🧩 Modules","🔍 Parsers","📦 Extractors","✅ Règles de Test","🔣 Regex Expressions"])

    # ── PRODUITS ──
    with tab_prod:
        col_list,col_form=st.columns([2,3])
        with col_list:
            section_title("Produits configurés")
            prods=list_products(cfg)
            if not prods:
                st.markdown('<div class="info-box">Aucun produit. Créez-en un →</div>',unsafe_allow_html=True)
            for prod in prods:
                micons=" ".join(cfg["modules"].get(m,{}).get("icon","?") for m in prod.get("modules",[]))
                is_act=(prod["id"]==st.session_state.active_product_id)
                lbl=f"{'✅ ' if is_act else ''}{prod['name']} — {prod['version']}"
                c1,c2,c3=st.columns([5,1,1])
                with c1:
                    if st.button(lbl,key=f"sel_{prod['id']}",use_container_width=True):
                        st.session_state.active_product_id=prod["id"]
                        st.session_state.pop("edit_prod_id",None); st.rerun()
                    st.caption(f"{micons}  {prod.get('operator','')}")
                with c2:
                    if st.button("✏️",key=f"ep_{prod['id']}",help="Modifier"):
                        st.session_state["edit_prod_id"]=prod["id"]; st.rerun()
                with c3:
                    if st.button("🗑️",key=f"dp_{prod['id']}",help="Supprimer"):
                        if delete_product(cfg,prod["id"]):
                            if st.session_state.active_product_id==prod["id"]:
                                st.session_state.active_product_id=None
                            st.rerun()

        with col_form:
            edit_id=st.session_state.get("edit_prod_id")
            edit_prod=get_product(cfg,edit_id) if edit_id else None
            section_title("✏️ Modifier" if edit_prod else "➕ Nouveau produit")
            with st.form("prod_form"):
                pname=st.text_input("Nom *",value=edit_prod.get("name","") if edit_prod else "")
                pver=st.text_input("Version",value=edit_prod.get("version","") if edit_prod else "")
                poper=st.text_input("Opérateur",value=edit_prod.get("operator","") if edit_prod else "")
                pnotes=st.text_area("Notes",value=edit_prod.get("notes","") if edit_prod else "",height=55)
                st.markdown("**Modules à activer**")
                all_mods=list_modules(cfg); cur_mods=edit_prod.get("modules",[]) if edit_prod else ["FE","RF_WiFi","RF_BT"]
                sel_mods=[]; mcols=st.columns(min(len(all_mods),3))
                for i,mod in enumerate(all_mods):
                    with mcols[i%len(mcols)]:
                        if st.checkbox(f"{mod['icon']} {mod['name']}",value=(mod["id"] in cur_mods),key=f"mc_{mod['id']}"):
                            sel_mods.append(mod["id"])
                parser_map={}; extractor_map={}; test_rule_map={}
                if sel_mods:
                    st.markdown("**Configuration par module**")
                    for mid in sel_mods:
                        mod_def=cfg["modules"].get(mid,{})
                        cp=[p for p in list_parsers(cfg) if mid in p.get("compatible_modules",[])]
                        ce=[e for e in list_extractors(cfg) if mid in e.get("compatible_modules",[])]
                        cr=[r for r in list_test_rules(cfg) if mid in r.get("compatible_modules",[])]
                        with st.expander(f"{mod_def.get('icon','🔷')} {mod_def.get('name',mid)}",expanded=True):
                            dp=edit_prod.get("parser_map",{}).get(mid) if edit_prod else mod_def.get("default_parser","")
                            de=edit_prod.get("extractor_map",{}).get(mid) if edit_prod else mod_def.get("default_extractor","")
                            dr=edit_prod.get("test_rule_map",{}).get(mid) if edit_prod else mod_def.get("default_test_rule","")
                            if cp:
                                po={p["id"]:p["name"] for p in cp}
                                ps=st.selectbox("Parser",list(po.keys()),format_func=lambda x:po[x],
                                                index=list(po.keys()).index(dp) if dp in po else 0,key=f"ps_{mid}")
                                parser_map[mid]=ps
                                pd_=cfg["parsers"].get(ps,{}); st.caption(f"ℹ️ {pd_.get('description','')}")
                                pats=pd_.get("detection_patterns",[])[:5]
                                if pats: st.caption(f"🔍 Patterns: `{'` `'.join(pats)}`")
                            else: st.warning(f"Aucun parser compatible avec {mid}")
                            if ce:
                                eo={e["id"]:e["name"] for e in ce}
                                es=st.selectbox("Extractor ICP",list(eo.keys()),format_func=lambda x:eo[x],
                                                index=list(eo.keys()).index(de) if de in eo else 0,key=f"es_{mid}")
                                extractor_map[mid]=es
                                ed_=cfg["extractors"].get(es,{}); st.caption(f"ℹ️ {ed_.get('description','')}")
                                mks=ed_.get("pdf_markers",[])[:5]
                                if mks: st.caption(f"📄 Marqueurs PDF: `{'` `'.join(mks)}`")
                            else:
                                st.caption("📦 Aucun extractor ICP requis pour ce module (logs uniquement)")
                            if cr:
                                ro={r["id"]:r["name"] for r in cr}
                                rs=st.selectbox("Règle de test",list(ro.keys()),format_func=lambda x:ro[x],
                                                index=list(ro.keys()).index(dr) if dr in ro else 0,key=f"rs_{mid}")
                                test_rule_map[mid]=rs
                                rd_=cfg["test_rules"].get(rs,{}); st.caption(f"ℹ️ {rd_.get('description','')}")
                            else:
                                st.caption("✅ Aucune règle de validation numérique requise pour ce module")
                sub=st.form_submit_button("💾 Enregistrer",type="primary")
                if sub:
                    if not pname.strip(): st.error("Le nom est obligatoire.")
                    elif edit_prod:
                        update_product(cfg,edit_id,name=pname.strip(),version=pver.strip(),
                                       operator=poper.strip(),notes=pnotes.strip(),modules=sel_mods,
                                       parser_map=parser_map,extractor_map=extractor_map,test_rule_map=test_rule_map)
                        st.success(f"✅ '{pname}' mis à jour."); st.session_state.pop("edit_prod_id",None); st.rerun()
                    else:
                        p=create_product(cfg,pname.strip(),pver.strip(),poper.strip(),sel_mods,
                                         parser_map,extractor_map,test_rule_map,pnotes.strip())
                        st.session_state.active_product_id=p["id"]; st.success(f"✅ '{pname}' créé."); st.rerun()
            if edit_prod and st.button("✖ Annuler"):
                st.session_state.pop("edit_prod_id",None); st.rerun()
            active_prod=get_product(cfg,st.session_state.active_product_id or "")
            if active_prod:
                issues=validate_product_config(active_prod,cfg)
                if issues:
                    st.markdown("**Validation :**")
                    for iss in issues:
                        cls="error-box" if iss["level"]=="error" else "warn-box"
                        ico="❌" if iss["level"]=="error" else "⚠️"
                        st.markdown(f'<div class="{cls}">{ico} {iss["msg"]}</div>',unsafe_allow_html=True)
                else:
                    st.markdown('<div class="suggest-box">✅ Configuration valide.</div>',unsafe_allow_html=True)

    # ── MODULES ──
    with tab_mod:
        section_title("🧩 Catalogue des Modules"); cl,cf=st.columns([2,3])
        with cl:
            for mod in list_modules(cfg):
                cls_="crud-card builtin" if mod.get("builtin") else "crud-card custom"
                ext_name=cfg["extractors"].get(mod.get("default_extractor",""),{}).get("name","—")
                rule_name=cfg["test_rules"].get(mod.get("default_test_rule",""),{}).get("name","—")
                par_name=cfg["parsers"].get(mod.get("default_parser",""),{}).get("name","—")
                st.markdown(f'<div class="{cls_}"><b>{mod["icon"]} {mod["name"]}</b> '
                            f'<span class="badge badge-{"blue" if mod.get("builtin") else "pass"}">'
                            f'{"Intégré" if mod.get("builtin") else "Custom"}</span><br>'
                            f'<small style="color:#64748b">{mod["description"]}</small><br>'
                            f'<small>🔍 {par_name} · 📦 {ext_name} · ✅ {rule_name}</small></div>',
                            unsafe_allow_html=True)
                # Bouton édition pour TOUS les modules (builtin inclus, pour changer les défauts)
                if st.button("✏️ Modifier défauts",key=f"em_{mod['id']}",use_container_width=True):
                    st.session_state["edit_mod_id"]=mod["id"]; st.rerun()
                if not mod.get("builtin"):
                    if st.button("🗑️ Supprimer",key=f"dm_{mod['id']}",use_container_width=True):
                        delete_module(cfg,mod["id"]); st.rerun()
        with cf:
            emid=st.session_state.get("edit_mod_id"); em=cfg["modules"].get(emid)
            section_title("✏️ Modifier module" if em else "➕ Nouveau Module")
            with st.form("mod_form"):
                mid_=st.text_input("ID *",value=em.get("id","") if em else "",
                                   disabled=bool(em and em.get("builtin")))
                mn_=st.text_input("Nom *",value=em.get("name","") if em else "")
                mi_=st.text_input("Icône",value=em.get("icon","🔷") if em else "🔷")
                md_=st.text_area("Description",value=em.get("description","") if em else "",height=60)
                mc_=st.color_picker("Couleur",value=em.get("color","#64748b") if em else "#64748b")
                st.markdown("**Associations par défaut**")
                c1,c2,c3=st.columns(3)
                with c1:
                    mp_opts={"":"(aucun)"}; mp_opts.update({p["id"]:p["name"] for p in list_parsers(cfg)})
                    cur_mp=em.get("default_parser","") if em else ""
                    mp_=st.selectbox("Parser défaut",list(mp_opts.keys()),
                                     format_func=lambda x:mp_opts[x],
                                     index=list(mp_opts.keys()).index(cur_mp) if cur_mp in mp_opts else 0,
                                     key="mpd")
                with c2:
                    me_opts={"":"(aucun)"}; me_opts.update({e["id"]:e["name"] for e in list_extractors(cfg)})
                    cur_me=em.get("default_extractor","") if em else ""
                    me_=st.selectbox("Extractor défaut",list(me_opts.keys()),
                                     format_func=lambda x:me_opts[x],
                                     index=list(me_opts.keys()).index(cur_me) if cur_me in me_opts else 0,
                                     key="med")
                with c3:
                    mr_opts={"":"(aucun)"}; mr_opts.update({r["id"]:r["name"] for r in list_test_rules(cfg)})
                    cur_mr=em.get("default_test_rule","") if em else ""
                    mr_=st.selectbox("Règle défaut",list(mr_opts.keys()),
                                     format_func=lambda x:mr_opts[x],
                                     index=list(mr_opts.keys()).index(cur_mr) if cur_mr in mr_opts else 0,
                                     key="mrd")
                sub_mod=st.form_submit_button("💾 Enregistrer",type="primary")
                if sub_mod:
                    if not mn_.strip(): st.error("Le Nom est obligatoire.")
                    elif em:
                        update_module(cfg,emid,name=mn_,icon=mi_,description=md_,color=mc_,
                                      default_parser=mp_,default_extractor=me_,default_test_rule=mr_)
                        st.success(f"✅ Module '{mn_}' mis à jour.")
                        st.session_state.pop("edit_mod_id",None); st.rerun()
                    else:
                        if not mid_.strip(): st.error("L'ID est obligatoire.")
                        else:
                            create_module(cfg,mid_.strip(),mn_,mi_,md_,mc_,mp_,me_,mr_)
                            st.success(f"✅ Module '{mn_}' créé."); st.rerun()
            if em and st.button("✖ Annuler",key="cancel_mod"):
                st.session_state.pop("edit_mod_id",None); st.rerun()

    # ── PARSERS ──
    with tab_par:
        section_title("🔍 Catalogue des Parsers"); cl,cf=st.columns([2,3])
        with cl:
            for par in list_parsers(cfg):
                cls_="crud-card builtin" if par.get("builtin") else "crud-card custom"
                compat=", ".join(par.get("compatible_modules",[]))
                st.markdown(f'<div class="{cls_}"><b>{par["name"]}</b> '
                            f'<span class="badge badge-{"blue" if par.get("builtin") else "pass"}">'
                            f'{"Intégré" if par.get("builtin") else "Custom"}</span><br>'
                            f'<small style="color:#64748b">{par["description"]}</small><br>'
                            f'<small>📁 <code>{par["module_file"]}::{par["function"]}</code> · <b>{compat}</b></small></div>',
                            unsafe_allow_html=True)
                c1,c2=st.columns(2)
                with c1:
                    if st.button("✏️",key=f"epar_{par['id']}",use_container_width=True):
                        st.session_state["edit_par_id"]=par["id"]; st.rerun()
                if not par.get("builtin"):
                    with c2:
                        if st.button("🗑️",key=f"dpar_{par['id']}",use_container_width=True):
                            delete_parser(cfg,par["id"]); st.rerun()
        with cf:
            epid=st.session_state.get("edit_par_id"); ep=cfg["parsers"].get(epid)
            section_title("✏️ Modifier" if ep else "➕ Nouveau Parser")
            with st.form("par_form"):
                pid_=st.text_input("ID *",value=ep.get("id","") if ep else "",
                                   disabled=bool(ep))
                pn_=st.text_input("Nom *",value=ep.get("name","") if ep else "")
                pd2_=st.text_area("Description",value=ep.get("description","") if ep else "",height=60)
                pf_=st.text_input("Fichier module",value=ep.get("module_file","") if ep else "",
                                  placeholder="parse_boardlevel_v1.py")
                pfn_=st.text_input("Fonction",value=ep.get("function","") if ep else "",
                                   placeholder="parse_log")
                # Safe multiselect: filter defaults to only valid options
                all_mod_ids=[m["id"] for m in list_modules(cfg)]
                cur_compat=ep.get("compatible_modules",[]) if ep else []
                valid_defaults=[x for x in cur_compat if x in all_mod_ids]
                pcomp_=st.multiselect("Modules compatibles",all_mod_ids,default=valid_defaults)
                ppat_=st.text_input("Patterns détection (virgule séparés)",
                                    value=", ".join(ep.get("detection_patterns",[]) if ep else []))
                sub_par=st.form_submit_button("💾 Enregistrer",type="primary")
                if sub_par:
                    pats=[x.strip() for x in ppat_.split(",") if x.strip()]
                    if not pn_.strip(): st.error("Le Nom est obligatoire.")
                    elif ep:
                        update_parser(cfg,epid,name=pn_,description=pd2_,module_file=pf_,
                                      function=pfn_,compatible_modules=pcomp_,detection_patterns=pats)
                        st.success(f"✅ Parser '{pn_}' mis à jour.")
                        st.session_state.pop("edit_par_id",None); st.rerun()
                    else:
                        if not pid_.strip(): st.error("L'ID est obligatoire.")
                        elif pid_.strip() in cfg["parsers"]: st.error(f"L'ID '{pid_}' existe déjà.")
                        else:
                            create_parser(cfg,pid_.strip(),pn_,pd2_,pf_,pfn_,pcomp_,pats)
                            st.success(f"✅ Parser '{pn_}' créé."); st.rerun()
            if ep and st.button("✖ Annuler",key="cancel_par"):
                st.session_state.pop("edit_par_id",None); st.rerun()

    # ── EXTRACTORS ──
    with tab_ext:
        section_title("📦 Catalogue des Extractors"); cl,cf=st.columns([2,3])
        with cl:
            for ext in list_extractors(cfg):
                cls_="crud-card builtin" if ext.get("builtin") else "crud-card custom"
                compat=", ".join(ext.get("compatible_modules",[]))
                st.markdown(f'<div class="{cls_}"><b>{ext["name"]}</b> '
                            f'<span class="badge badge-{"blue" if ext.get("builtin") else "pass"}">'
                            f'{"Intégré" if ext.get("builtin") else "Custom"}</span><br>'
                            f'<small style="color:#64748b">{ext["description"]}</small><br>'
                            f'<small>📁 <code>{ext["module_file"]}::{ext["function"]}</code> · <b>{compat}</b></small></div>',
                            unsafe_allow_html=True)
                c1,c2=st.columns(2)
                with c1:
                    if st.button("✏️",key=f"eext_{ext['id']}",use_container_width=True):
                        st.session_state["edit_ext_id"]=ext["id"]; st.rerun()
                if not ext.get("builtin"):
                    with c2:
                        if st.button("🗑️",key=f"dext_{ext['id']}",use_container_width=True):
                            delete_extractor(cfg,ext["id"]); st.rerun()
        with cf:
            eeid=st.session_state.get("edit_ext_id"); ee=cfg["extractors"].get(eeid)
            section_title("✏️ Modifier" if ee else "➕ Nouveau Extractor")
            with st.form("ext_form"):
                eid_=st.text_input("ID *",value=ee.get("id","") if ee else "",disabled=bool(ee))
                en_=st.text_input("Nom *",value=ee.get("name","") if ee else "")
                ed2_=st.text_area("Description",value=ee.get("description","") if ee else "",height=60)
                ef_=st.text_input("Fichier module",value=ee.get("module_file","") if ee else "")
                efn_=st.text_input("Fonction",value=ee.get("function","") if ee else "")
                all_mod_ids=[m["id"] for m in list_modules(cfg)]
                cur_ecomp=ee.get("compatible_modules",[]) if ee else []
                valid_edefaults=[x for x in cur_ecomp if x in all_mod_ids]
                ecomp_=st.multiselect("Modules compatibles",all_mod_ids,default=valid_edefaults)
                emar_=st.text_input("Marqueurs PDF (virgule séparés)",
                                    value=", ".join(ee.get("pdf_markers",[]) if ee else []))
                sub_ext=st.form_submit_button("💾 Enregistrer",type="primary")
                if sub_ext:
                    mks=[x.strip() for x in emar_.split(",") if x.strip()]
                    if not en_.strip(): st.error("Le Nom est obligatoire.")
                    elif ee:
                        update_extractor(cfg,eeid,name=en_,description=ed2_,module_file=ef_,
                                         function=efn_,compatible_modules=ecomp_,pdf_markers=mks)
                        st.success(f"✅ Extractor '{en_}' mis à jour.")
                        st.session_state.pop("edit_ext_id",None); st.rerun()
                    else:
                        if not eid_.strip(): st.error("L'ID est obligatoire.")
                        elif eid_.strip() in cfg["extractors"]: st.error(f"L'ID '{eid_}' existe déjà.")
                        else:
                            create_extractor(cfg,eid_.strip(),en_,ed2_,ef_,efn_,ecomp_,mks)
                            st.success(f"✅ Extractor '{en_}' créé."); st.rerun()
            if ee and st.button("✖ Annuler",key="cancel_ext"):
                st.session_state.pop("edit_ext_id",None); st.rerun()

    # ── RÈGLES ──
    with tab_rule:
        section_title("✅ Règles de Validation"); cl,cf=st.columns([2,3])
        with cl:
            for rule in list_test_rules(cfg):
                cls_="crud-card builtin" if rule.get("builtin") else "crud-card custom"
                compat=", ".join(rule.get("compatible_modules",[]))
                settings_str=" · ".join(f"{k}={v}" for k,v in rule.get("settings",{}).items())
                st.markdown(f'<div class="{cls_}"><b>{rule["name"]}</b> '
                            f'<span class="badge badge-{"blue" if rule.get("builtin") else "pass"}">'
                            f'{"Intégré" if rule.get("builtin") else "Custom"}</span><br>'
                            f'<small style="color:#64748b">{rule["description"]}</small><br>'
                            f'<small>⚙️ {settings_str} · <b>{compat}</b></small></div>',unsafe_allow_html=True)
                c1,c2=st.columns(2)
                with c1:
                    if st.button("✏️",key=f"erule_{rule['id']}",use_container_width=True):
                        st.session_state["edit_rule_id"]=rule["id"]; st.rerun()
                if not rule.get("builtin"):
                    with c2:
                        if st.button("🗑️",key=f"drule_{rule['id']}",use_container_width=True):
                            delete_test_rule(cfg,rule["id"]); st.rerun()
        with cf:
            erid=st.session_state.get("edit_rule_id"); er=cfg["test_rules"].get(erid)
            section_title("✏️ Modifier" if er else "➕ Nouvelle Règle")
            with st.form("rule_form"):
                rid_=st.text_input("ID *",value=er.get("id","") if er else "",disabled=bool(er))
                rn_=st.text_input("Nom *",value=er.get("name","") if er else "")
                rd2_=st.text_area("Description",value=er.get("description","") if er else "",height=60)
                all_mod_ids=[m["id"] for m in list_modules(cfg)]
                cur_rcomp=er.get("compatible_modules",[]) if er else []
                valid_rdefaults=[x for x in cur_rcomp if x in all_mod_ids]
                rcomp_=st.multiselect("Modules compatibles",all_mod_ids,default=valid_rdefaults)
                st.markdown("**Paramètres**")
                c1,c2=st.columns(2)
                with c1:
                    rs_=st.checkbox("Mode strict",value=(er or {}).get("settings",{}).get("strict_mode",False))
                    ro_=st.checkbox("Ignorer Mandatory=false",value=(er or {}).get("settings",{}).get("opt_mode",False))
                with c2:
                    rf_=st.number_input("Tolérance fréq. (MHz)",value=int((er or {}).get("settings",{}).get("freq_tolerance_mhz",1)),min_value=0)
                    mp_vals=["warning","fail","ignore"]
                    mp_cur=(er or {}).get("settings",{}).get("missing_policy","warning")
                    rm_=st.selectbox("Politique manquants",mp_vals,index=mp_vals.index(mp_cur))
                sub_rule=st.form_submit_button("💾 Enregistrer",type="primary")
                if sub_rule:
                    settings={"strict_mode":rs_,"opt_mode":ro_,"freq_tolerance_mhz":rf_,"missing_policy":rm_}
                    if not rn_.strip(): st.error("Le Nom est obligatoire.")
                    elif er:
                        update_test_rule(cfg,erid,name=rn_,description=rd2_,compatible_modules=rcomp_,settings=settings)
                        st.success(f"✅ Règle '{rn_}' mise à jour.")
                        st.session_state.pop("edit_rule_id",None); st.rerun()
                    else:
                        if not rid_.strip(): st.error("L'ID est obligatoire.")
                        elif rid_.strip() in cfg["test_rules"]: st.error(f"L'ID '{rid_}' existe déjà.")
                        else:
                            create_test_rule(cfg,rid_.strip(),rn_,rd2_,rcomp_,settings)
                            st.success(f"✅ Règle '{rn_}' créée."); st.rerun()
            if er and st.button("✖ Annuler",key="cancel_rule"):
                st.session_state.pop("edit_rule_id",None); st.rerun()

    # ── REGEX EXPRESSIONS ──────────────────────────────────
    with tab_rx:
        section_title("🔣 Catalogue des Expressions Régulières")
        st.markdown("""
        <div class="info-box">
          Ce catalogue recense toutes les expressions régulières utilisées par les parsers et extractors.
          Les regex <b>intégrées</b> (issues des scripts Python) sont éditables mais non supprimables.
          Vous pouvez créer des regex <b>personnalisées</b> pour vos propres parsers.
        </div>""", unsafe_allow_html=True)

        # ── Filtres ──
        fc1, fc2, fc3 = st.columns([2, 2, 3])
        with fc1:
            scope_filter = st.selectbox(
                "Filtrer par scope",
                options=["Tous"] + list(REGEX_SCOPES.keys()),
                format_func=lambda x: "🔍 Tous les scopes" if x == "Tous" else REGEX_SCOPES.get(x, x),
                key="rx_scope_filter"
            )
        with fc2:
            type_filter = st.selectbox(
                "Type",
                options=["Tous", "Intégrées", "Personnalisées"],
                key="rx_type_filter"
            )
        with fc3:
            search_term = st.text_input("🔍 Rechercher (nom / pattern / description)", key="rx_search",
                                        placeholder="ex: DVB, Viterbi, POWER…")

        # Filtrage
        all_rx = list_regexes(cfg)
        if scope_filter != "Tous":
            all_rx = [r for r in all_rx if r.get("scope") == scope_filter]
        if type_filter == "Intégrées":
            all_rx = [r for r in all_rx if r.get("builtin")]
        elif type_filter == "Personnalisées":
            all_rx = [r for r in all_rx if not r.get("builtin")]
        if search_term:
            term = search_term.lower()
            all_rx = [r for r in all_rx if
                      term in r["name"].lower() or
                      term in r.get("pattern","").lower() or
                      term in r.get("description","").lower()]

        # Compteurs par scope
        scope_counts = {}
        for r in list_regexes(cfg):
            s = r.get("scope","custom")
            scope_counts[s] = scope_counts.get(s, 0) + 1
        scols = st.columns(len(REGEX_SCOPES))
        for col, (sc_id, sc_label) in zip(scols, REGEX_SCOPES.items()):
            with col:
                count = scope_counts.get(sc_id, 0)
                st.markdown(mc(count, sc_label.split(" ", 1)[-1], "info"), unsafe_allow_html=True)
        st.divider()

        col_list, col_form = st.columns([3, 2])

        with col_list:
            st.markdown(f"**{len(all_rx)} regex{'es' if len(all_rx)>1 else ''} affichée{'s' if len(all_rx)>1 else ''}**")
            for rx in all_rx:
                scope_label = REGEX_SCOPES.get(rx.get("scope","custom"), "Custom")
                is_builtin = rx.get("builtin", False)
                border_col = "#0057b8" if is_builtin else "#16a34a"
                tag_cls = "badge-blue" if is_builtin else "badge-pass"
                tag_lbl = "Intégrée" if is_builtin else "Custom"
                flag_str = " | ".join(rx.get("flags", [])) or "—"
                groups_str = ", ".join(rx.get("groups", [])) or "—"

                with st.container():
                    st.markdown(f"""
                    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-left:4px solid {border_col};
                                border-radius:8px;padding:.75rem;margin-bottom:.5rem;">
                      <div style="display:flex;align-items:center;gap:.5rem;margin-bottom:4px;">
                        <b>{rx['name']}</b>
                        <span class="badge {tag_cls}">{tag_lbl}</span>
                        <span class="badge badge-neutral">{scope_label}</span>
                      </div>
                      <div style="font-size:.8rem;color:#64748b;margin-bottom:4px;">{rx.get('description','')}</div>
                      <div style="font-family:monospace;font-size:.78rem;background:#1e293b;color:#7dd3fc;
                                  padding:5px 8px;border-radius:5px;word-break:break-all;margin-bottom:4px;">
                        {rx['pattern']}
                      </div>
                      <div style="font-size:.75rem;color:#64748b;">
                        🏷 Flags: <code>{flag_str}</code> &nbsp;·&nbsp;
                        📌 Groupes: <code>{groups_str}</code>
                        {'&nbsp;·&nbsp; 📁 <code>' + rx.get('used_in','') + '</code>' if rx.get('used_in') else ''}
                      </div>
                      {'<div style="font-size:.75rem;color:#0891b2;margin-top:3px;">💬 Ex: <i>' + rx.get("example","") + '</i></div>' if rx.get("example") else ''}
                    </div>""", unsafe_allow_html=True)

                    # Actions
                    btn_cols = st.columns([1, 1, 1, 1] if not is_builtin else [1, 1, 2])
                    with btn_cols[0]:
                        if st.button("🧪 Tester", key=f"test_rx_{rx['id']}", use_container_width=True):
                            st.session_state["test_rx_id"] = rx["id"]; st.rerun()
                    with btn_cols[1]:
                        if st.button("✏️ Éditer", key=f"edit_rx_{rx['id']}", use_container_width=True):
                            st.session_state["edit_rx_id"] = rx["id"]
                            st.session_state.pop("test_rx_id", None); st.rerun()
                    if not is_builtin:
                        with btn_cols[2]:
                            if st.button("🗑️ Supprimer", key=f"del_rx_{rx['id']}", use_container_width=True):
                                delete_regex(cfg, rx["id"]); st.rerun()

        with col_form:
            edit_rx_id = st.session_state.get("edit_rx_id")
            test_rx_id = st.session_state.get("test_rx_id")
            edit_rx    = get_regex(cfg, edit_rx_id) if edit_rx_id else None

            # ── Mode test ──────────────────────────────────
            if test_rx_id:
                test_rx_obj = get_regex(cfg, test_rx_id)
                if test_rx_obj:
                    section_title(f"🧪 Tester : {test_rx_obj['name']}")
                    st.markdown(f'<div style="font-family:monospace;font-size:.8rem;background:#1e293b;'
                                f'color:#7dd3fc;padding:8px;border-radius:6px;word-break:break-all;margin-bottom:.6rem;">'
                                f'{test_rx_obj["pattern"]}</div>', unsafe_allow_html=True)
                    flags_disp = " | ".join(test_rx_obj.get("flags", [])) or "aucun"
                    st.caption(f"Flags : `{flags_disp}` · Scope : {REGEX_SCOPES.get(test_rx_obj.get('scope','custom'),'')}")

                    test_text = st.text_area(
                        "Texte à tester",
                        value=test_rx_obj.get("example", ""),
                        height=100,
                        key=f"test_area_{test_rx_id}",
                        placeholder="Collez ici un extrait de log ou PDF à analyser…"
                    )

                    if st.button("▶ Lancer le test", type="primary", use_container_width=True):
                        result = test_regex(test_rx_obj["pattern"], test_rx_obj.get("flags", []), test_text)
                        if not result["ok"]:
                            st.markdown(f'<div class="error-box">❌ Erreur regex : <code>{result["error"]}</code></div>',
                                        unsafe_allow_html=True)
                        elif result["match_count"] == 0:
                            st.markdown('<div class="warn-box">⚠️ Aucune correspondance trouvée.</div>',
                                        unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div class="suggest-box">✅ <b>{result["match_count"]} correspondance(s)</b> trouvée(s).</div>',
                                        unsafe_allow_html=True)
                            for i, m in enumerate(result["matches"]):
                                with st.expander(f"Match #{i+1} : `{m['full'][:60]}`", expanded=(i == 0)):
                                    st.markdown(f"**Correspondance complète :** `{m['full']}`")
                                    st.markdown(f"**Position :** caractères {m['span'][0]}–{m['span'][1]}")
                                    groups = test_rx_obj.get("groups", [])
                                    if m["groups"]:
                                        st.markdown("**Groupes capturés :**")
                                        for j, g in enumerate(m["groups"]):
                                            gname = groups[j] if j < len(groups) else f"groupe {j+1}"
                                            st.markdown(f"- `{gname}` → `{g}`")
                                    if m["groupdict"]:
                                        st.markdown("**Groupes nommés :**")
                                        for k, v in m["groupdict"].items():
                                            st.markdown(f"- `{k}` → `{v}`")

                    if st.button("✖ Fermer le test", use_container_width=True):
                        st.session_state.pop("test_rx_id", None); st.rerun()

            # ── Mode édition / création ────────────────────
            else:
                section_title("✏️ Modifier" if edit_rx else "➕ Nouvelle Regex")
                is_builtin_edit = edit_rx.get("builtin", False) if edit_rx else False
                if is_builtin_edit:
                    st.markdown('<div class="info-box">ℹ️ Cette regex est <b>intégrée</b>. '
                                'Vous pouvez modifier pattern, flags et description sans la supprimer.</div>',
                                unsafe_allow_html=True)

                with st.form("rx_form", clear_on_submit=False):
                    rid_  = st.text_input("ID unique *",
                                          value=edit_rx.get("id","") if edit_rx else "",
                                          disabled=bool(edit_rx),
                                          help="Identifiant unique sans espaces, ex: my_parser_freq")
                    rn_   = st.text_input("Nom *",
                                          value=edit_rx.get("name","") if edit_rx else "")
                    rdesc_= st.text_area("Description",
                                         value=edit_rx.get("description","") if edit_rx else "",
                                         height=60)
                    rpat_ = st.text_area("Pattern (raw string) *",
                                         value=edit_rx.get("pattern","") if edit_rx else "",
                                         height=80,
                                         help="Écrivez le pattern sans les r\"…\". Les backslashes sont conservés tels quels.")
                    rflags_ = st.multiselect(
                        "Flags Python re.*",
                        options=["IGNORECASE","MULTILINE","DOTALL","VERBOSE"],
                        default=edit_rx.get("flags",[]) if edit_rx else [],
                        format_func=lambda x: {"IGNORECASE":"re.I — insensible à la casse",
                                                "MULTILINE":"re.M — ^ $ par ligne",
                                                "DOTALL":"re.S — . inclut \\n",
                                                "VERBOSE":"re.X — espaces ignorés"}.get(x, x)
                    )
                    rscope_ = st.selectbox(
                        "Scope (contexte d'utilisation)",
                        options=list(REGEX_SCOPES.keys()),
                        format_func=lambda x: REGEX_SCOPES.get(x, x),
                        index=list(REGEX_SCOPES.keys()).index(edit_rx.get("scope","custom")) if edit_rx else 4,
                        disabled=is_builtin_edit
                    )
                    rgroups_ = st.text_input(
                        "Noms des groupes (virgule, dans l'ordre des parenthèses capturantes)",
                        value=", ".join(edit_rx.get("groups",[]) if edit_rx else []),
                        placeholder="ex: frequency_mhz, modulation, dvb_standard"
                    )
                    col_ui1, col_ui2 = st.columns(2)
                    with col_ui1:
                        rused_  = st.text_input("Utilisée dans (fichier::variable)",
                                                value=edit_rx.get("used_in","") if edit_rx else "",
                                                placeholder="check_fe_log.py::RE_CONNECT_CAB",
                                                disabled=is_builtin_edit)
                    with col_ui2:
                        rexample_ = st.text_input("Exemple de ligne à matcher",
                                                   value=edit_rx.get("example","") if edit_rx else "",
                                                   placeholder="FE_ConnectCab 0 498 …")

                    # Prévisualisation inline
                    if rpat_ and rexample_:
                        result_prev = test_regex(rpat_, rflags_, rexample_)
                        if result_prev["ok"] and result_prev["match_count"] > 0:
                            st.markdown(f'<div class="suggest-box" style="margin-top:.4rem;font-size:.8rem;">'
                                        f'✅ <b>Pattern valide</b> — {result_prev["match_count"]} match(es) sur l\'exemple.'
                                        f'</div>', unsafe_allow_html=True)
                        elif result_prev["ok"]:
                            st.markdown('<div class="warn-box" style="margin-top:.4rem;font-size:.8rem;">'
                                        '⚠️ Pattern compilé mais 0 match sur l\'exemple fourni.</div>',
                                        unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div class="error-box" style="margin-top:.4rem;font-size:.8rem;">'
                                        f'❌ Erreur : {result_prev["error"]}</div>', unsafe_allow_html=True)

                    sub_rx = st.form_submit_button("💾 Enregistrer", type="primary")
                    if sub_rx:
                        if not rn_.strip() or not rpat_.strip():
                            st.error("Nom et Pattern sont obligatoires.")
                        else:
                            groups_list = [g.strip() for g in rgroups_.split(",") if g.strip()]
                            # Validate pattern
                            val = test_regex(rpat_, rflags_, "")
                            if not val["ok"]:
                                st.error(f"❌ Pattern invalide : {val['error']}")
                            elif edit_rx:
                                try:
                                    update_regex(cfg, edit_rx_id,
                                                 name=rn_.strip(), description=rdesc_.strip(),
                                                 pattern=rpat_.strip(), flags=rflags_,
                                                 groups=groups_list,
                                                 example=rexample_.strip())
                                    if not is_builtin_edit:
                                        update_regex(cfg, edit_rx_id, used_in=rused_.strip(), scope=rscope_)
                                    st.success(f"✅ Regex '{rn_}' mise à jour.")
                                    st.session_state.pop("edit_rx_id", None); st.rerun()
                                except Exception as e:
                                    st.error(f"Erreur : {e}")
                            else:
                                if not rid_.strip():
                                    st.error("L'ID est obligatoire.")
                                elif rid_.strip() in cfg.get("regexes", {}):
                                    st.error(f"L'ID '{rid_}' existe déjà.")
                                else:
                                    try:
                                        create_regex(cfg, rid_.strip(), rn_.strip(), rdesc_.strip(),
                                                     rpat_.strip(), rflags_, groups_list, rscope_,
                                                     rused_.strip(), rexample_.strip())
                                        st.success(f"✅ Regex '{rn_}' créée.")
                                        st.session_state.pop("edit_rx_id", None); st.rerun()
                                    except Exception as e:
                                        st.error(f"Erreur : {e}")

                if edit_rx and st.button("✖ Annuler", key="cancel_rx_edit"):
                    st.session_state.pop("edit_rx_id", None); st.rerun()

        # ── Export Python ──
        st.divider()
        ec1, ec2 = st.columns([3, 1])
        with ec1:
            section_title("📤 Export Python")
            st.markdown("Génère un bloc `import re` + toutes les `re.compile(…)` prêt à coller dans vos scripts.")
        with ec2:
            python_code = export_regexes_as_python(cfg)
            st.download_button(
                "⬇️ Télécharger .py",
                data=python_code.encode("utf-8"),
                file_name="regex_catalogue.py",
                mime="text/x-python",
                use_container_width=True
            )
        with st.expander("👁 Prévisualiser le code Python exporté", expanded=False):
            st.code(python_code, language="python")

    st.divider()
    prod_ok=bool(st.session_state.active_product_id)
    if not prod_ok: st.warning("⚠️ Sélectionnez ou créez un produit.")
    nav(nxt=1,nxt_label="Passer à l'extraction ICP →",disabled=not prod_ok)

# ═══════════════════════════════════════════════════════════════
#  ÉTAPE 1 — EXTRACTION ICP
# ═══════════════════════════════════════════════════════════════
elif step==1:
    section_title("📄 Extraction des Spécifications depuis le PDF ICP")
    if not FITZ_OK: st.error("❌ PyMuPDF non installé : `pip install PyMuPDF`"); nav(prev=0); st.stop()
    active_prod=get_product(cfg,st.session_state.active_product_id or "")
    if not active_prod: st.warning("Aucun produit sélectionné."); nav(prev=0); st.stop()

    st.markdown(f'<div class="info-box"><b>Produit :</b> {active_prod["name"]} — {active_prod["version"]}<br>'
                f'<b>Modules actifs :</b> {", ".join(cfg["modules"].get(m,{}).get("icon","")+" "+cfg["modules"].get(m,{}).get("name",m) for m in active_prod.get("modules",[]))}'
                f'</div>',unsafe_allow_html=True)

    col1,col2=st.columns([3,2])
    with col1:
        icp_file=st.file_uploader("📁 Charger le PDF ICP",type=["pdf"])
        if icp_file: st.success(f"✅ {icp_file.name} ({icp_file.size/1024:.1f} KB)"); st.session_state.icp_pdf_name=icp_file.name
    with col2:
        st.markdown('<div class="upload-hint"><b>📋 Format attendu</b><br>PDF ICP avec sections :<br>• Tests FE (DVB-C/S/T)<br>• Tests RF (Wi-Fi 2.4/5 GHz)<br>• Tests Bluetooth</div>',unsafe_allow_html=True)

    if icp_file:
        pdf_bytes=icp_file.read(); tmp_pdf=None
        try:
            doc=fitz.open(stream=pdf_bytes,filetype="pdf")
            pdf_text="\n".join(doc[p].get_text("text") for p in range(doc.page_count))
            st.session_state.icp_pdf_text=pdf_text; doc.close()
        except Exception as e: pdf_text=""; st.warning(f"Lecture texte : {e}")

        if pdf_text:
            suggs=suggest_extractor_for_pdf(pdf_text,cfg)
            if suggs:
                best=suggs[0]; ext_def=best["extractor"]
                compat_ok=any(m in active_prod.get("modules",[]) for m in ext_def.get("compatible_modules",[]))
                st.markdown(f'<div class="suggest-box">💡 <b>Suggestion automatique :</b> L\'extractor '
                            f'<b>"{ext_def["name"]}"</b> correspond à {best["matched"]}/{best["total"]} marqueurs. '
                            f'{"✅ Compatible avec ce produit." if compat_ok else "⚠️ Vérifiez la compatibilité."}'
                            f'</div>',unsafe_allow_html=True)

        issues=validate_product_config(active_prod,cfg)
        errs=[i for i in issues if i["level"]=="error"]; warns=[i for i in issues if i["level"]=="warning"]
        if errs:
            st.markdown("**❌ Erreurs de configuration :**")
            for iss in errs: st.markdown(f'<div class="error-box">❌ {iss["msg"]}</div>',unsafe_allow_html=True)
            nav(prev=0); st.stop()
        if warns:
            with st.expander(f"⚠️ {len(warns)} avertissement(s)"):
                for iss in warns: st.markdown(f'<div class="warn-box">⚠️ {iss["msg"]}</div>',unsafe_allow_html=True)

        use_rag = st.checkbox("🧪 Utiliser l'extraction RAG (experimental, necessite Ollama + Qdrant lances)", value=False)
        if st.button("🚀 Lancer l'extraction ICP",type="primary",use_container_width=True):
            prog=st.progress(0,"Préparation…"); results={}; errors_run={}
            try:
                tmp_pdf=safe_temp_write(pdf_bytes,".pdf"); prog.progress(10,"Fichier créé…")
                for mid in active_prod.get("modules",[]):
                    mod_name=cfg["modules"].get(mid,{}).get("name",mid)
                    prog.progress(30,f"Extraction {mod_name}…")
                    try:
                        if mid=="FE":
                            if use_rag:
                                from ingest import extract_pages, chunk_text, index_chunks
                                from rag_extractor import extract_fe_tests_rag
                                product_id = active_prod.get("name", "UNKNOWN")
                                pages_rag = extract_pages(tmp_pdf)
                                chunks_rag = []
                                for pr in pages_rag:
                                    chunks_rag.extend(chunk_text(pr["text"], source_pdf=os.path.basename(tmp_pdf), page=pr["page"], product=product_id))
                                index_chunks(chunks_rag)
                                rag_result = extract_fe_tests_rag(tmp_pdf, product_id)
                                fe_tests = rag_result.get("FE_Tests", [])
                            else:
                                from icp_fe_extract import find_fe_range,extract_fe_tests
                                doc2=fitz.open(tmp_pdf)
                                try: s2,e2=find_fe_range(doc2)
                                except ValueError: s2,e2=0,doc2.page_count-1
                                text="\n".join(doc2[p].get_text("text") for p in range(s2,e2+1)); doc2.close()
                                fe_tests=extract_fe_tests(text)
                            results["FE"]=fe_tests; st.session_state.icp_fe_limits=fe_tests
                        elif mid in ("RF_WiFi","RF_BT") and "RF" not in results:
                            from icp_wifi_extract import extract_rf_limits
                            rf_limits=extract_rf_limits(tmp_pdf)
                            results["RF"]=rf_limits; st.session_state.icp_rf_limits=rf_limits
                        elif mid=="FT" and "FT" not in results:
                            try:
                                from icp_ft_extract import extract_tests as ft_extract
                                ft_tests=ft_extract(tmp_pdf)
                                results["FT"]=ft_tests; st.session_state.icp_ft_tests=ft_tests
                            except Exception as e_ft:
                                errors_run["FT"]={"error":str(e_ft),"trace":traceback.format_exc()}
                    except Exception as e:
                        errors_run[mid]={"error":str(e),"trace":traceback.format_exc()}
                prog.progress(100); time.sleep(0.3); prog.empty()
            finally:
                safe_temp_delete(tmp_pdf)

            for mid,ei in errors_run.items():
                mod_name=cfg["modules"].get(mid,{}).get("name",mid)
                with st.expander(f"❌ Erreur — {mod_name}"):
                    st.error(ei["error"])
                    err_low=ei["error"].lower()
                    if "page" in err_low or "range" in err_low:
                        st.info("💡 Le PDF ne contient peut-être pas de section FE détectable. Vérifiez que le PDF est complet et non chiffré.")
                    elif "attribute" in err_low:
                        st.info("💡 L'extractor n'est peut-être pas compatible avec ce format PDF. Essayez un autre extractor dans la config produit.")
                    elif "permission" in err_low or "winerror" in err_low:
                        st.info("💡 Erreur d'accès fichier temporaire. Relancez l'extraction.")
                    else:
                        st.info("💡 Vérifiez la compatibilité de l'extractor avec le module et le format PDF.")
                    with st.expander("Traceback"): st.code(ei["trace"])

            fe_count=len(results.get("FE",[])); rf_data=results.get("RF",{})
            cols=st.columns(4)
            for col,(v,l) in zip(cols,[(fe_count,"Tests FE"),(len(rf_data.get("2.4GHz",[])),"Wi-Fi 2.4GHz"),
                                       (len(rf_data.get("5GHz",[])),"Wi-Fi 5GHz"),(len(rf_data.get("Bluetooth",[])),"Bluetooth")]):
                with col: st.markdown(mc(v,l,"info"),unsafe_allow_html=True)
            if results.get("FE"):
                with st.expander(f"📺 Aperçu FE ({fe_count} tests)",expanded=True):
                    st.dataframe(pd.DataFrame([{"Test":t["Test"],"Fréquence":t["Frequency"],
                        "Modulation":t["Modulation"],"# Params":len(t.get("Limits",[]))} for t in results["FE"]]),
                        use_container_width=True)
            if results.get("RF"):
                with st.expander("📶 Aperçu RF/BT",expanded=False):
                    for band in ("2.4GHz","5GHz","Bluetooth"):
                        entries=rf_data.get(band,[])
                        if entries:
                            st.markdown(f"**{band}** ({len(entries)} entrées)")
                            st.dataframe(pd.DataFrame(entries[:6]),use_container_width=True)
            if results: st.success("✅ Extraction terminée !")

    elif st.session_state.icp_fe_limits or st.session_state.icp_rf_limits:
        st.info(f"✅ Extraction disponible : **{st.session_state.icp_pdf_name}**")
        c1,c2,c3=st.columns(3)
        rf_d=st.session_state.icp_rf_limits or {}
        with c1: st.metric("Tests FE",len(st.session_state.icp_fe_limits or []))
        with c2: st.metric("Wi-Fi entries",len(rf_d.get("2.4GHz",[]))+len(rf_d.get("5GHz",[])))
        with c3: st.metric("BT entries",len(rf_d.get("Bluetooth",[])))

    can_next=bool(st.session_state.icp_fe_limits or st.session_state.icp_rf_limits)
    nav(prev=0,nxt=2,disabled=not can_next)

# ═══════════════════════════════════════════════════════════════
#  ÉTAPE 2 — VALIDATION DES LOGS (Concat Pipeline)
# ═══════════════════════════════════════════════════════════════
elif step==2:
    section_title("📋 Validation des Logs d'Équipement")
    active_prod=get_product(cfg,st.session_state.active_product_id or "")
    if not active_prod: st.warning("Aucun produit sélectionné."); nav(prev=1); st.stop()
    if not (st.session_state.icp_fe_limits or st.session_state.icp_rf_limits):
        st.warning("⚠️ Aucune spécification ICP. Retournez à l'étape 1."); nav(prev=1); st.stop()

    section_title("📁 Import des fichiers logs")
    st.markdown('<div class="upload-hint">Importez <b>tous vos fichiers logs simultanément</b>.<br>'
                'Le système les <b>concatène en un seul fichier</b>, applique les parsers sur le fichier consolidé '
                'et présente les résultats dans un tableau unifié avec indication de la source.</div>',
                unsafe_allow_html=True)
    log_files=st.file_uploader("Sélectionnez un ou plusieurs fichiers logs",
                               type=["txt","log","TXT","LOG"],accept_multiple_files=True)

    if log_files:
        st.markdown(f"**{len(log_files)} fichier(s) chargé(s)**")

        # ── Informational auto-detection table (display only) ──────
        det_rows=[]
        for lf in log_files:
            hit=suggest_by_filename(lf.name,cfg)
            if hit:
                method="📁 nom de fichier"; conf="100%"
            else:
                sample=lf.read(3000).decode("utf-8",errors="ignore"); lf.seek(0)
                suggs=suggest_parser_for_log(sample,cfg,filename=lf.name)
                hit=suggs[0] if suggs else None
                method="🔍 contenu" if hit else "⚠️ non reconnu"
                conf=f"{round(100*hit['matched']/hit['total'])}%" if hit and hit.get('total') else "—"
            det_rows.append({"Fichier":lf.name,
                             "Taille":f"{lf.size/1024:.1f} KB",
                             "Détection":method,"Confiance":conf})
        st.dataframe(pd.DataFrame(det_rows),use_container_width=True,
                     height=min(250,len(det_rows)*40+50))

        opt_mode=st.checkbox("Ignorer tests Mandatory=false (RF)",value=False)

        if st.button("▶ Lancer la validation (concat)",type="primary",use_container_width=True):
            prog=st.progress(0,"Concaténation des fichiers…")

            # ── 1. Build META_LOGS — track char offsets per source file ─
            meta_lines=[]; file_sections=[]  # list of (filename, char_start, char_end)
            for lf in log_files:
                content=lf.read().decode("utf-8",errors="ignore"); lf.seek(0)
                # Write header separator
                for hl in [f"{'='*60}",f"Fichier : {lf.name}",f"{'='*60}"]:
                    meta_lines.append(hl)
                char_start=sum(len(l)+1 for l in meta_lines)
                for line in content.splitlines():
                    meta_lines.append(line)
                char_end=sum(len(l)+1 for l in meta_lines)
                file_sections.append((lf.name, char_start, char_end))
                meta_lines.append(""); meta_lines.append("")
            meta_logs_text="\n".join(meta_lines)

            def find_origin(key_text):
                """Map a text fragment back to (source_filename, approx_line)."""
                if not key_text: return "—", 0
                pos=meta_logs_text.find(str(key_text))
                if pos==-1: return "—", 0
                for fname,cstart,cend in file_sections:
                    if cstart<=pos<cend:
                        return fname, meta_logs_text[cstart:pos].count("\n")+1
                return "—", 0

            prog.progress(20,"Application des parsers sur le fichier consolidé…")

            # ── 2. Run ALL product modules directly on META_LOGS ────────
            # No per-file grouping — each module's parser runs once on the
            # full concatenated text.
            product_modules=active_prod.get("modules",[])
            all_results={}; fe_l=[]; rf_l=[]
            unified_rows=[]; seen_keys=set()

            for i,mid in enumerate(product_modules):
                prog.progress(20+int(65*i/max(len(product_modules),1)),
                              f"Module {mid} sur fichier consolidé…")
                result={"module":mid,"error":None,"report":None,"trace":None}
                try:
                    if mid=="FE":
                        from check_fe_log import parse_log as fep, compare as fec
                        parsed=fep(meta_logs_text)
                        report=fec(parsed,st.session_state.icp_fe_limits or [])
                        result["report"]=report
                        fe_l.append({"file":"META_LOGS","report":report})
                        for t in (report or {}).get("Tests",[]):
                            for p in t.get("Parameters",[]):
                                rk=f"FE|{t['Frequency']}|{t['Modulation']}|{p['Name']}"
                                if rk in seen_keys: continue
                                seen_keys.add(rk)
                                fname,ln=find_origin(str(t["Frequency"]))
                                unified_rows.append({
                                    "Module":"FE","Fréq.":t["Frequency"],
                                    "Modulation":t["Modulation"],"Paramètre":p["Name"],
                                    "Valeur":p["Value"],"Min":p["Limits"]["Min"],
                                    "Max":p["Limits"]["Max"],
                                    "Statut":"✅ PASS" if p["Pass"] else "❌ FAIL",
                                    "Fichier source":fname,"Ligne":ln})

                    elif mid in ("RF_WiFi","RF_BT"):
                        # Run RF parser once — avoid double-running for WiFi+BT
                        if f"RF_done" in seen_keys:
                            result["report"]=all_results.get("RF_WiFi",
                                             all_results.get("RF_BT",{})).get("report")
                        else:
                            seen_keys.add("RF_done")
                            from check_rf_log import parse_log as rfp, build_report as rfb
                            rf_lims=dict(st.session_state.icp_rf_limits or {}); ign=0
                            if opt_mode:
                                for band in rf_lims:
                                    orig=len(rf_lims[band])
                                    rf_lims[band]=[e for e in rf_lims[band] if e.get("Mandatory",True)]
                                    ign+=orig-len(rf_lims[band])
                            parsed=rfp(meta_logs_text)
                            report=rfb(parsed,rf_lims,ign,opt_mode)
                            result["report"]=report
                            rf_l.append({"file":"META_LOGS","report":report})
                            for t in (report or {}).get("Tests",[]):
                                for p in t.get("Parameters",[]):
                                    rk=f"RF|{t.get('Frequency')}|{t.get('ModulationHeader')}|{p['Name']}"
                                    if rk in seen_keys: continue
                                    seen_keys.add(rk)
                                    fname,ln=find_origin(str(t.get("Frequency","")))
                                    unified_rows.append({
                                        "Module":mid,"Fréq.":t.get("Frequency"),
                                        "Modulation":t.get("ModulationHeader",""),
                                        "Dir.":t.get("Dir",""),"Ant.":t.get("Antenna",""),
                                        "Paramètre":p["Name"],"Valeur":p["Value"],
                                        "Min":(p.get("JSONLimits") or {}).get("min"),
                                        "Max":(p.get("JSONLimits") or {}).get("max"),
                                        "Statut":"✅" if p.get("PassVsJSON") else ("❌" if p.get("PassVsJSON") is False else "—"),
                                        "Fichier source":fname,"Ligne":ln})

                    elif mid=="BoardLevel":
                        from parse_boardlevel_v1 import parse_log as blp, compare as blc
                        parsed=blp(meta_logs_text); report=blc(parsed)
                        result["report"]=report
                        for t in (report or {}).get("Tests",[]):
                            rk=f"BL|{t['Name']}|{t.get('Group','')}"
                            if rk in seen_keys: continue
                            seen_keys.add(rk)
                            fname,ln=find_origin(t["Name"][:20])
                            if t.get("Source") in ("validation","sagemtest","step"):
                                unified_rows.append({
                                    "Module":"BoardLevel","Fréq.":"—","Modulation":"—",
                                    "Paramètre":f"[{t.get('Group','')}] {t['Name']}",
                                    "Valeur":t.get("Value","—"),"Min":t.get("Min"),"Max":t.get("Max"),
                                    "Statut":"✅ PASS" if t["Pass"] else "❌ FAIL",
                                    "Fichier source":fname,"Ligne":ln})

                    elif mid=="System":
                        from parse_system_v1 import parse_log as sysp, compare as sysc
                        parsed=sysp(meta_logs_text); report=sysc(parsed)
                        result["report"]=report
                        for t in (report or {}).get("Tests",[]):
                            rk=f"SYS|{t['Name']}"
                            if rk in seen_keys: continue
                            seen_keys.add(rk)
                            fname,ln=find_origin(t["Name"][:20])
                            unified_rows.append({
                                "Module":"System","Fréq.":"—","Modulation":"—",
                                "Paramètre":t["Name"],"Valeur":t.get("Value","—"),
                                "Min":t.get("Min"),"Max":t.get("Max"),
                                "Statut":"✅ PASS" if t["Pass"] else "❌ FAIL",
                                "Fichier source":fname,"Ligne":ln})

                    elif mid=="FW_Upgrade":
                        from parse_fwfinal_v1 import parse_log as fwp, compare as fwc
                        parsed=fwp(meta_logs_text); report=fwc(parsed)
                        result["report"]=report
                        for t in (report or {}).get("Tests",[]):
                            rk=f"FW|{t['Name']}"
                            if rk in seen_keys: continue
                            seen_keys.add(rk)
                            fname,ln=find_origin(t["Name"][:20])
                            unified_rows.append({
                                "Module":"FW_Upgrade","Fréq.":"—","Modulation":"—",
                                "Paramètre":t["Name"],"Valeur":t.get("Value","—"),
                                "Min":t.get("Min"),"Max":t.get("Max"),
                                "Statut":"✅ PASS" if t["Pass"] else "❌ FAIL",
                                "Fichier source":fname,"Ligne":ln})

                    elif mid=="FT":
                        ft_tests_dict=st.session_state.get("icp_ft_tests")
                        if ft_tests_dict:
                            from check_ft_log import analyze_in_memory
                            report=analyze_in_memory(ft_tests_dict,meta_logs_text)
                            result["report"]=report
                            for tname,tres in (report or {}).get("Details",{}).items():
                                rk=f"FT|{tname}"
                                if rk in seen_keys: continue
                                seen_keys.add(rk)
                                fname,ln=find_origin(tname[:20])
                                unified_rows.append({
                                    "Module":"FT","Fréq.":"—","Modulation":"—",
                                    "Paramètre":tname,
                                    "Valeur":"PASS" if tres.get("passed") else "FAIL",
                                    "Min":"—","Max":"—",
                                    "Statut":"✅ PASS" if tres.get("passed") else "❌ FAIL",
                                    "Fichier source":fname,"Ligne":ln})
                        else:
                            st.info("ℹ️ Module FT : aucun test ICP FT chargé (étape 1).")

                    else:
                        # Generic fallback: try boardlevel parser
                        from parse_boardlevel_v1 import parse_log as blp, compare as blc
                        parsed=blp(meta_logs_text); report=blc(parsed)
                        result["report"]=report

                except Exception as e:
                    result["error"]=str(e); result["trace"]=traceback.format_exc()

                all_results[mid]=result

            prog.progress(90,"Consolidation…")

            # ── 3. Build log_results compatible with ÉTAPE 3 ────────────
            # Keyed by "MODULE:mid" to avoid collisions; each entry is
            # guaranteed never None.
            log_results_compat={}
            for mid,res in all_results.items():
                key=f"MODULE:{mid}"
                log_results_compat[key]={
                    "module": mid,
                    "file":   key,
                    "error":  res.get("error"),
                    "report": res.get("report") or {},
                    "trace":  res.get("trace"),
                }

            st.session_state.log_results=log_results_compat
            st.session_state.meta_logs_text=meta_logs_text
            st.session_state.unified_log_rows=unified_rows
            if fe_l: st.session_state.fe_report=_merge_fe_reports(fe_l)
            if rf_l: st.session_state.rf_report=_merge_rf_reports(rf_l)

            prog.progress(100); time.sleep(0.2); prog.empty()
            n_total=len(unified_rows)
            n_pass=sum(1 for r in unified_rows if "✅" in str(r.get("Statut","")))
            n_fail=sum(1 for r in unified_rows if "❌" in str(r.get("Statut","")))
            st.success(f"✅ Validation terminée — {n_total} tests extraits "
                       f"({n_pass} PASS / {n_fail} FAIL)")

        # ── Unified result table ─────────────────────────────────────
        if st.session_state.get("unified_log_rows"):
            st.divider(); section_title("📊 Tableau unifié — Fichier consolidé")
            unified=st.session_state.unified_log_rows
            df_u=pd.DataFrame(unified)

            n_tot=len(df_u)
            n_p=df_u["Statut"].str.contains("✅",na=False).sum()
            n_f=df_u["Statut"].str.contains("❌",na=False).sum()
            n_nd=n_tot-n_p-n_f
            pct=round(100*n_p/n_tot) if n_tot else 0
            cols=st.columns(5)
            for col,(v,l,k) in zip(cols,[
                    (n_tot,"Tests extraits","info"),(n_p,"PASS","pass"),
                    (n_f,"FAIL","fail"),(n_nd,"Indéterminés","warn"),
                    (f"{pct}%","Conformité","pass" if pct>=80 else "fail")]):
                with col: st.markdown(mc(v,l,k),unsafe_allow_html=True)
            st.divider()

            # Filters
            fc1,fc2,fc3=st.columns(3)
            with fc1:
                fmod=st.multiselect("Module",df_u["Module"].unique().tolist(),
                                    default=df_u["Module"].unique().tolist(),key="uf_mod")
            with fc2:
                fstat=st.multiselect("Statut",["✅ PASS","❌ FAIL","✅","❌","—"],
                                     default=["✅ PASS","❌ FAIL","✅","❌","—"],key="uf_stat")
            with fc3:
                fsrc=st.multiselect("Fichier source",df_u["Fichier source"].unique().tolist(),
                                    default=df_u["Fichier source"].unique().tolist(),key="uf_src")

            df_view=df_u[df_u["Module"].isin(fmod) & df_u["Fichier source"].isin(fsrc)]
            if fstat:
                df_view=df_view[df_view["Statut"].isin(fstat)]

            display_cols=["Fichier source","Ligne","Module","Paramètre","Fréq.","Modulation",
                          "Valeur","Min","Max","Statut"]
            display_cols=[c for c in display_cols if c in df_view.columns]
            st.dataframe(df_view[display_cols],use_container_width=True,
                         height=min(600,len(df_view)*36+60))

            # Errors + META_LOGS download
            st.divider()
            c1,c2=st.columns(2)
            with c1:
                if st.session_state.get("meta_logs_text"):
                    st.download_button("📥 META_LOGS.txt (consolidé)",
                        data=st.session_state.meta_logs_text.encode("utf-8","replace"),
                        file_name="META_LOGS.txt",mime="text/plain",use_container_width=True)
            with c2:
                err_entries=[(mid,r) for mid,r in (st.session_state.log_results or {}).items()
                             if r and r.get("error")]
                if err_entries:
                    with st.expander(f"⚠️ {len(err_entries)} module(s) en erreur",expanded=False):
                        for mid,r in err_entries:
                            st.markdown(f"**{mid}** — {r['error']}")
                            with st.expander("Traceback"): st.code(r.get("trace",""))
    else:
        st.info("Chargez au moins un fichier log pour commencer.")

    can_next=bool(st.session_state.log_results)
    nav(prev=1,nxt=3,disabled=not can_next)

#  ÉTAPE 3 — RAPPORT ICP
# ═══════════════════════════════════════════════════════════════
elif step==3:
    section_title("📊 Rapport de Validation ICP")
    icp_report=build_icp_combined(); st.session_state.icp_report_combined=icp_report
    fe_rpt=st.session_state.fe_report or {}; rf_rpt=st.session_state.rf_report or {}
    fe_summ=fe_rpt.get("Summary",{}); rf_summ=rf_rpt.get("Summary",{})
    log_results=st.session_state.log_results or {}

    # Agrégation globale de TOUS les modules
    tp=fe_summ.get("Pass",0)+rf_summ.get("PassVsJSON_Count",0)
    tf=fe_summ.get("Fail",0)+rf_summ.get("JSON_Fails_Count",0)
    tm=fe_summ.get("MissingInLog",0)+rf_summ.get("MissingInLog_Count",0)
    tc=fe_summ.get("CheckedParams",0)+rf_summ.get("CheckedParams",0)

    # Ajouter Board Level, System, FW_Upgrade depuis log_results
    for fname,res in log_results.items():
        if res is None: continue
        mid=res.get("module",""); rpt=res.get("report") or {}; s=rpt.get("Summary",{}) if rpt else {}
        if mid in ("BoardLevel","System","FW_Upgrade","FT") and not res.get("error"):
            tp+=s.get("Pass",0); tf+=s.get("Fail",0); tc+=s.get("Tests",0)

    pct=round(100*tp/tc) if tc else 0
    gs="PASS" if tf==0 and tm==0 else ("FAIL" if tf>0 else "PARTIAL")
    sc={"PASS":"#16a34a","FAIL":"#dc2626","PARTIAL":"#d97706"}[gs]
    prod=get_product(cfg,st.session_state.active_product_id or "") or {}
    nf=len(log_results)
    st.markdown(f'<div style="background:linear-gradient(135deg,#f8fafc,#e8f0fb);border:2px solid {sc};'
                f'border-radius:12px;padding:1.5rem;margin-bottom:1rem;display:flex;align-items:center;justify-content:space-between;">'
                f'<div><div style="font-size:.85rem;color:#64748b">Produit : <b>{prod.get("name","")} · {prod.get("version","")}</b></div>'
                f'<div style="font-size:.82rem;color:#64748b">{nf} fichier(s) · {datetime.now().strftime("%d/%m/%Y %H:%M")}</div></div>'
                f'<div style="text-align:center"><div style="font-size:2.5rem;font-weight:900;color:{sc};">{gs}</div>'
                f'<div style="font-size:.85rem;color:#64748b">{pct}% conformité</div></div></div>',unsafe_allow_html=True)
    cols=st.columns(5)
    for col,(v,l,k) in zip(cols,[(tc,"Tests vérifiés","info"),(tp,"PASS","pass"),
                                  (tf,"FAIL","fail"),(tm,"Manquants","warn"),(f"{pct}%","Conformité","pass" if pct>=80 else "fail")]):
        with col: st.markdown(mc(v,l,k),unsafe_allow_html=True)
    st.divider()
    cg1,cg2,cg3=st.columns(3)
    with cg1:
        if tc>0:
            fig=go.Figure(go.Pie(labels=["PASS","FAIL","Manquants"],values=[tp,tf,tm],hole=.55,
                                  marker_colors=["#16a34a","#dc2626","#d97706"],textinfo="label+percent"))
            fig.update_layout(title="Distribution globale",height=270,margin=dict(t=40,b=10)); st.plotly_chart(fig,use_container_width=True)
    with cg2:
        # Graphique par module — tous modules
        mod_labels=[]; mod_pass=[]; mod_fail=[]
        for mod_id in ["FE","RF_WiFi","RF_BT","BoardLevel","System","FW_Upgrade"]:
            mres=[res for res in log_results.values() if res and res.get("module")==mod_id and not res.get("error") and res.get("report")]
            if mres:
                mod_info=cfg["modules"].get(mod_id,{}); icon=mod_info.get("icon","")
                sp=sum((res["report"] or {}).get("Summary",{}).get("Pass",0)+(res["report"] or {}).get("Summary",{}).get("PassVsJSON_Count",0) for res in mres)
                sf=sum((res["report"] or {}).get("Summary",{}).get("Fail",0)+(res["report"] or {}).get("Summary",{}).get("JSON_Fails_Count",0) for res in mres)
                mod_labels.append(f"{icon} {mod_id}"); mod_pass.append(sp); mod_fail.append(sf)
        if mod_labels:
            fig2=go.Figure()
            fig2.add_trace(go.Bar(name="PASS",x=mod_labels,y=mod_pass,marker_color="#16a34a"))
            fig2.add_trace(go.Bar(name="FAIL",x=mod_labels,y=mod_fail,marker_color="#dc2626"))
            fig2.update_layout(barmode="group",title="Par module",height=270,
                               margin=dict(t=40,b=10),xaxis=dict(tickangle=-20))
            st.plotly_chart(fig2,use_container_width=True)
    with cg3:
        if log_results:
            lbs=[]; vp=[]; vf_=[]
            for fn,res in log_results.items():
                if not res or res.get("error"): continue
                r=res.get("report") or {}; s=r.get("Summary",{}) if r else {}
                mid=res.get("module","")
                lbs.append(os.path.basename(fn)[:18])
                p=s.get("Pass",0)+s.get("PassVsJSON_Count",0)
                f=s.get("Fail",0)+s.get("JSON_Fails_Count",0)
                vp.append(p); vf_.append(f)
            if lbs:
                fig3=go.Figure()
                fig3.add_trace(go.Bar(name="PASS",x=lbs,y=vp,marker_color="#16a34a"))
                fig3.add_trace(go.Bar(name="FAIL",x=lbs,y=vf_,marker_color="#dc2626"))
                fig3.update_layout(barmode="stack",title="Par fichier",height=270,
                                   margin=dict(t=40,b=10),xaxis=dict(tickangle=-30))
                st.plotly_chart(fig3,use_container_width=True)
    fe_tests_d=fe_rpt.get("Tests",[])
    if fe_tests_d:
        pm={}; pt={}
        for t in fe_tests_d:
            for p in t.get("Parameters",[]):
                n=p["Name"]; pt[n]=pt.get(n,0)+1
                if p["Pass"]: pm[n]=pm.get(n,0)+1
        pa=list(pt.keys()); pv=[round(100*pm.get(p,0)/pt[p]) for p in pa]
        if len(pa)>=3:
            figr=go.Figure(go.Scatterpolar(r=pv+[pv[0]],theta=pa+[pa[0]],fill="toself",
                fillcolor="rgba(0,87,184,0.15)",line=dict(color="#0057b8",width=2)))
            figr.update_layout(polar=dict(radialaxis=dict(range=[0,100],ticksuffix="%")),
                               title="Conformité par paramètre FE",height=310,margin=dict(t=50,b=20))
            st.plotly_chart(figr,use_container_width=True)
    with st.expander("📋 Détails FE",expanded=False):
        rows=[{"Fichier":t.get("_source",""),"Fréq.":t["Frequency"],"Modulation":t["Modulation"],
               "Param.":p["Name"],"Valeur":p["Value"],"Min ICP":p["Limits"]["Min"],"Max ICP":p["Limits"]["Max"],
               "Statut":"✅ PASS" if p["Pass"] else "❌ FAIL"}
              for t in fe_tests_d for p in t.get("Parameters",[])]
        if rows: st.dataframe(pd.DataFrame(rows),use_container_width=True,height=350)
    with st.expander("📋 Détails RF/BT",expanded=False):
        rows=[{"Fichier":t.get("_source",""),"Dir":t["Dir"],"Fréq.":t["Frequency"],
               "Modulation":t["ModulationHeader"],"Ant.":t.get("Antenna",""),"Param.":p["Name"],"Valeur":p["Value"],
               "Min JSON":(p.get("JSONLimits") or {}).get("min"),"Max JSON":(p.get("JSONLimits") or {}).get("max"),
               "Statut":"✅" if p.get("PassVsJSON") else ("❌" if p.get("PassVsJSON") is False else "—")}
              for t in rf_rpt.get("Tests",[]) for p in t.get("Parameters",[])]
        if rows: st.dataframe(pd.DataFrame(rows),use_container_width=True,height=350)
    st.divider(); section_title("💾 Télécharger le Rapport ICP")
    c1,c2=st.columns(2)
    with c1:
        st.download_button("📥 JSON",data=json.dumps(icp_report,indent=2,ensure_ascii=False).encode("utf-8"),
                           file_name=f"ICP_Report_{prod.get('name','')}_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                           mime="application/json",use_container_width=True)
    with c2:
        try:
            buf=io.BytesIO()
            with pd.ExcelWriter(buf,engine="openpyxl") as writer:
                pd.DataFrame([{"Produit":prod.get("name"),"Version":prod.get("version"),
                                "Global":gs,"PASS":tp,"FAIL":tf,"Manquants":tm,"Conformité%":pct}
                              ]).to_excel(writer,sheet_name="Résumé",index=False)
                if fe_tests_d:
                    fe_rows=[{"Fréquence":t["Frequency"],"Modulation":t["Modulation"],
                               "Paramètre":p["Name"],"Valeur":p["Value"],
                               "Min":p["Limits"]["Min"],"Max":p["Limits"]["Max"],
                               "Statut":"PASS" if p["Pass"] else "FAIL"}
                              for t in fe_tests_d for p in t.get("Parameters",[])]
                    pd.DataFrame(fe_rows).to_excel(writer,sheet_name="FE Tests",index=False)
            buf.seek(0)
            st.download_button("📥 Excel",data=buf.getvalue(),
                               file_name=f"ICP_Report_{prod.get('name','')}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True)
        except Exception as e: st.error(f"Export Excel : {e}")
    nav(prev=2,nxt=4,nxt_label="Passer à l'analyse MTP →")

# ═══════════════════════════════════════════════════════════════
#  ÉTAPE 4 — ANALYSE MTP
# ═══════════════════════════════════════════════════════════════
elif step==4:
    section_title("📑 Analyse des Documents MTP")
    from mtp_analyzer import (PROMPT_MTP_EXTRACT_SYSTEM,PROMPT_MTP_EXTRACT_USER,
                               analyze_mtp_pdf,extract_pdf_text)
    col1,col2=st.columns([3,2])
    with col1:
        mtp_files=st.file_uploader("📁 Charger les documents MTP (PDF)",type=["pdf"],accept_multiple_files=True)
    with col2:
        st.markdown('<div class="upload-hint"><b>⚙️ Analyse par code</b><br>'
                    'Extraction automatique des limites MTP par parsing PDF — <b>double moteur : regex + pdfplumber pour ICT</b>.</div>',
                    unsafe_allow_html=True)
    with st.expander("🔍 Logique d'extraction MTP",expanded=False):
        st.markdown("**Sections extraites automatiquement :**")
        st.markdown("""
- ⚡ **Board Level ICT** : tensions (Signal, TestPoint, Min, Max en V) — extraction dual regex + pdfplumber pour ICT (union best-effort)
- 📶 **Wi-Fi TX/RX** : puissance (dBm), EVM (dB), PER (%), tolérance fréq. (ppm) — 2.4GHz & 5GHz
- 🔵 **Bluetooth TX/RX** : puissance, drift, déviation, BER/PER
- 🖥️ **System** : USB, Ethernet, HDMI, LED, boutons, température
- 💾 **FW Upgrade / Final** : étapes PASS/FAIL
        """)
        st.markdown("**Prompt Extraction :**"); st.code(PROMPT_MTP_EXTRACT_SYSTEM,language="text")

    if mtp_files:
        st.success(f"✅ {len(mtp_files)} fichier(s) chargé(s)")
        if st.button("⚙️ Lancer l'analyse MTP",type="primary",use_container_width=True):
            mtp_reports=[]; prog=st.progress(0)
            for i,f in enumerate(mtp_files):
                prog.progress(int(100*i/len(mtp_files)),f"Extraction : {f.name}…")
                pb=f.read()
                try:
                    r=analyze_mtp_pdf(pb, pdf_filename=f.name)
                    r["_source_file"]=f.name; mtp_reports.append(r)
                    st.success(f"✅ {f.name} — {r['summary'].get('total_tests', r['summary'].get('total', 0))} spécifications extraites")
                except Exception as e:
                    st.error(f"❌ {f.name}: {e}"); mtp_reports.append({"_source_file":f.name,"error":str(e)})
            prog.progress(100); st.session_state.mtp_reports=mtp_reports

            # Agréger pour mtp_combined
            cfe=[]; crf={"2.4GHz":[],"5GHz":[],"Bluetooth":[]}
            for r in mtp_reports:
                cfe.extend(r.get("FE_Results",[]))
                for band in ("2.4GHz","5GHz","Bluetooth"):
                    crf[band].extend((r.get("RF_Results") or {}).get(band,[]))
            st.session_state.mtp_combined={
                "sources":          [f.name for f in mtp_files],
                "generated_at":     datetime.now().isoformat(),
                "FE_Results":       cfe,
                "RF_Results":       crf,
                "individual_reports": mtp_reports,
            }

    if st.session_state.mtp_reports:
        st.divider(); section_title("📊 Spécifications MTP extraites")
        for rpt in st.session_state.mtp_reports:
            with st.expander(f"📄 {rpt.get('_source_file','')}",expanded=True):
                if rpt.get("error"): st.error(rpt["error"]); continue

                dev  = rpt.get("device_info",{})
                summ = rpt.get("summary",{})

                # En-tête produit
                c1,c2,c3,c4 = st.columns(4)
                with c1: st.metric("Produit",  dev.get("product","—"))
                with c2: st.metric("Version",  dev.get("version","—"))
                with c3: st.metric("Date",     dev.get("date","—"))
                with c4: st.metric("ICP Ref",  dev.get("icp_ref","—"))

                # Métriques par section
                m1,m2,m3,m4,m5 = st.columns(5)
                with m1: st.metric("⚡ BoardLevel", summ.get("boardlevel",0), help="Tensions ICT")
                with m2: st.metric("📶 Wi-Fi",      summ.get("wifi",0),       help="Tests TX/RX Wi-Fi")
                with m3: st.metric("🔵 Bluetooth",  summ.get("bluetooth",0),  help="Tests TX/RX BT")
                with m4: st.metric("🖥️ System",     summ.get("system",0),     help="Tests fonctionnels")
                with m5: st.metric("💾 FW",         summ.get("fw_upgrade",0), help="Tests FW/Final")

                # Board Level voltages
                bl = rpt.get("BoardLevel",[])
                if bl:
                    with st.expander(f"⚡ Tensions ICT ({len(bl)} mesures)",expanded=True):
                        df_bl=pd.DataFrame([{
                            "Signal":v["Signal"],"TestPoint":v["TestPoint"],
                            "Min (V)":v["Min"],"Max (V)":v["Max"]
                        } for v in bl])
                        st.dataframe(df_bl,use_container_width=True,height=min(300,len(bl)*38+50))

                # Wi-Fi tests
                rf_res = rpt.get("RF_Results",{})
                wifi_tx_24 = [w for w in rf_res.get("2.4GHz",[]) if w.get("Direction")=="TX"]
                wifi_tx_5  = [w for w in rf_res.get("5GHz",[])   if w.get("Direction")=="TX"]
                wifi_rx_24 = [w for w in rf_res.get("2.4GHz",[]) if w.get("Direction")=="RX"]
                wifi_rx_5  = [w for w in rf_res.get("5GHz",[])   if w.get("Direction")=="RX"]
                wifi_params = rf_res.get("WiFi_Params",[])

                if wifi_tx_24 or wifi_tx_5:
                    with st.expander(f"📶 Wi-Fi TX ({len(wifi_tx_24)} × 2.4GHz / {len(wifi_tx_5)} × 5GHz)",expanded=False):
                        rows=[]
                        for w in wifi_tx_24 + wifi_tx_5:
                            rows.append({"Bande":w.get("Band",""),"Fréq. (MHz)":w.get("Frequency"),
                                         "Modulation":w.get("Modulation","")[:30],
                                         "Min (dBm)":w.get("Min"),"Max (dBm)":w.get("Max")})
                        if rows: st.dataframe(pd.DataFrame(rows),use_container_width=True,height=min(300,len(rows)*38+50))

                if wifi_rx_24 or wifi_rx_5:
                    with st.expander(f"📶 Wi-Fi RX PER ({len(wifi_rx_24+wifi_rx_5)} tests)",expanded=False):
                        rows=[{"Bande":w.get("Band",""),"Fréq.":w.get("Frequency"),
                               "Modulation":w.get("Modulation","")[:30],"Min (%)":w.get("Min"),"Max (%)":w.get("Max")}
                              for w in wifi_rx_24+wifi_rx_5]
                        if rows: st.dataframe(pd.DataFrame(rows),use_container_width=True,height=min(200,len(rows)*38+50))

                # Bluetooth
                bt = rf_res.get("Bluetooth",[])
                bt_tx = [b for b in bt if b.get("Direction")=="TX"]
                bt_par = [b for b in bt if b.get("Direction")!="TX"]
                if bt:
                    with st.expander(f"🔵 Bluetooth ({len(bt_tx)} TX + {len(bt_par)} params)",expanded=False):
                        rows=[{"Dir.":b.get("Direction"),"Fréq. (MHz)":b.get("Frequency"),
                               "Modulation":b.get("Modulation",""),"Paramètre":b.get("Parameter",""),
                               "Min":b.get("Min"),"Max":b.get("Max"),"Unité":b.get("Unit","")}
                              for b in bt]
                        if rows: st.dataframe(pd.DataFrame(rows),use_container_width=True,height=min(250,len(rows)*38+50))

                # System
                sys_items = rpt.get("System",[])
                if sys_items:
                    with st.expander(f"🖥️ System ({len(sys_items)} tests)",expanded=False):
                        rows=[{"Test":s.get("Name",""),"Remarque":s.get("Remark",""),
                               "Min":s.get("Min","PASS/FAIL") if s.get("Min") is not None else "PASS/FAIL",
                               "Max":s.get("Max","PASS/FAIL") if s.get("Max") is not None else "PASS/FAIL",
                               "Unité":s.get("Unit","")} for s in sys_items]
                        if rows: st.dataframe(pd.DataFrame(rows),use_container_width=True,height=min(250,len(rows)*38+50))

        if st.session_state.mtp_combined:
            st.download_button("📥 Rapport MTP (JSON)",
                data=json.dumps(st.session_state.mtp_combined,indent=2,ensure_ascii=False).encode("utf-8"),
                file_name=f"MTP_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json",use_container_width=True)
    nav(prev=3,nxt=5,disabled=not bool(st.session_state.mtp_combined))

# ═══════════════════════════════════════════════════════════════
#  ÉTAPE 5 — COMPARAISON
# ═══════════════════════════════════════════════════════════════
elif step==5:
    section_title("🔄 Comparaison ICP ↔ MTP")
    from mtp_analyzer import PROMPT_COMPARE_SYSTEM,PROMPT_COMPARE_USER,compare_icp_mtp
    if not st.session_state.icp_report_combined: st.warning("Rapport ICP manquant."); nav(prev=4); st.stop()
    if not st.session_state.mtp_combined: st.warning("Rapport MTP manquant."); nav(prev=4); st.stop()
    with st.expander("🔍 Logique de comparaison",expanded=False):
        st.code(PROMPT_COMPARE_SYSTEM,language="text")
    c1,c2=st.columns(2)
    with c1:
        ir=st.session_state.icp_report_combined
        n_fe = len(ir.get("FE_Limits") or [])
        n_rf = sum(len(v) for v in (ir.get("RF_Limits") or {}).values() if isinstance(v,list))
        st.info(f"📊 ICP · {n_fe} tests FE · {n_rf} tests RF")
    with c2:
        mr=st.session_state.mtp_combined
        indiv = mr.get("individual_reports",[])
        total_mtp = sum(r.get("summary",{}).get("total",0) for r in indiv if not r.get("error"))
        st.info(f"📑 MTP · {len(mr.get('sources',[]))} PDF · {total_mtp} spécifications extraites")

    if st.button("⚙️ Lancer la comparaison ICP ↔ MTP",type="primary",use_container_width=True):
        with st.spinner("Comparaison en cours…"):
            try:
                # Enrichir icp_combined avec les limites RF et les log_results
                icp_full = dict(st.session_state.icp_report_combined)
                icp_full["icp_rf_limits"]  = st.session_state.icp_rf_limits or {}
                icp_full["icp_fe_limits"]  = st.session_state.icp_fe_limits or []
                icp_full["log_results"]    = st.session_state.log_results or {}

                # mtp_combined contient individual_reports — agréger en un rapport unique
                mtp_c = st.session_state.mtp_combined or {}
                indiv = [r for r in mtp_c.get("individual_reports",[]) if not r.get("error")]

                if not indiv:
                    raise ValueError("Aucun rapport MTP valide disponible.")

                # Fusionner plusieurs PDFs en un seul rapport agrégé
                merged_raw = {
                    "metadata":   indiv[0].get("_raw",{}).get("metadata", indiv[0].get("device_info",{})),
                    "boardlevel": [],
                    "bluetooth":  [],
                    "wifi":       [],
                    "system":     [],
                    "fw_upgrade": [],
                    "summary":    {"total":0,"boardlevel":0,"bluetooth":0,"wifi":0,"system":0,"fw_upgrade":0},
                }
                for r in indiv:
                    raw = r.get("_raw") or r
                    for key in ("boardlevel","bluetooth","wifi","system","fw_upgrade"):
                        merged_raw[key].extend(raw.get(key,[]))
                    for key in ("total","boardlevel","bluetooth","wifi","system","fw_upgrade"):
                        merged_raw["summary"][key] = merged_raw["summary"].get(key,0) + \
                            raw.get("summary",{}).get(key, 0)

                mtp_single = {"_raw": merged_raw, "_method": "code",
                              "device_info": merged_raw["metadata"],
                              "summary": merged_raw["summary"]}

                comp=compare_icp_mtp(icp_full, mtp_single)
                st.session_state.comparison_report=comp; st.success("✅ Comparaison terminée !")
            except Exception as e:
                st.warning(f"Erreur : {e} — rapport de base généré.")
                st.session_state.comparison_report=_static_compare()

    if st.session_state.comparison_report:
        comp=st.session_state.comparison_report; summ=comp.get("comparison_summary",{})
        gs=summ.get("global_status","PARTIAL"); sc={"PASS":"#16a34a","FAIL":"#dc2626","PARTIAL":"#d97706"}.get(gs,"#64748b")
        st.markdown(f'<div style="text-align:center;background:#f8fafc;border:2px solid {sc};border-radius:12px;'
                    f'padding:1rem;margin:1rem 0;"><span style="font-size:2rem;font-weight:900;color:{sc};">Statut : {gs}</span></div>',
                    unsafe_allow_html=True)
        cols=st.columns(5)
        for col,(v,l,k) in zip(cols,[
                (summ.get("total_mtp_items",0),   "Items MTP",      "info"),
                (summ.get("total_compared",0),     "Comparés",       "info"),
                (summ.get("compliant",0),          "Conformes",      "pass"),
                (summ.get("non_compliant",0),      "Non conformes",  "fail"),
                (summ.get("limit_mismatches",0),   "Divergences limites","warn")]):
            with col: st.markdown(mc(v,l,k),unsafe_allow_html=True)

        # Tableau des résultats par section
        all_res = comp.get("_all_results",[])
        if all_res:
            # Sections
            sections = sorted(set(r["Section"] for r in all_res))
            for sec in sections:
                sec_rows = [r for r in all_res if r["Section"]==sec]
                n_ok = sum(1 for r in sec_rows if r.get("Pass") is True)
                n_ko = sum(1 for r in sec_rows if r.get("Pass") is False)
                badge = "✅" if n_ko==0 else "❌"
                with st.expander(f"{badge} **{sec}** — {len(sec_rows)} tests · {n_ok}P / {n_ko}F",expanded=(n_ko>0)):
                    df_rows=[{
                        "Signal":      r.get("Signal",""),
                        "Paramètre":   r.get("Param",""),
                        "MTP Min":     r.get("MTP_Min"),
                        "MTP Max":     r.get("MTP_Max"),
                        "ICP Min":     r.get("ICP_Min") or r.get("Log_Min"),
                        "ICP Max":     r.get("ICP_Max") or r.get("Log_Max"),
                        "Unité":       r.get("Unit",""),
                        "Mesuré":      r.get("Measured"),
                        "Statut":      "✅" if r.get("Pass") else ("❌" if r.get("Pass") is False else "ℹ️"),
                        "Limites OK":  "✅" if r.get("LimitsMatch") else ("❌" if r.get("LimitsMatch") is False else "—"),
                    } for r in sec_rows]
                    if df_rows: st.dataframe(pd.DataFrame(df_rows),use_container_width=True,
                                             height=min(300,len(df_rows)*38+50))

        # Anomalies
        for a in comp.get("anomalies",[]):
            sev=a.get("Severity","INFO"); cls={"CRITICAL":"anomaly-critical","WARNING":"anomaly-warning"}.get(sev,"anomaly-info")
            ico={"CRITICAL":"🔴","WARNING":"🟡"}.get(sev,"🔵")
            st.markdown(f'<div class="{cls}">{ico} <b>[{sev}]</b> {a.get("Detail",a.get("description",""))}'
                        f'<br><small>{a.get("Section","")} · {a.get("Item","")}</small></div>',
                        unsafe_allow_html=True)

        # Extra / Manquants
        extra = comp.get("_extra_mtp",[])
        miss  = comp.get("_missing_mtp",[])
        if extra or miss:
            with st.expander(f"ℹ️ Tests supplémentaires / manquants ({len(extra)} extra · {len(miss)} manquants)"):
                if extra:
                    st.markdown("**Tests présents dans le MTP mais absents de l'ICP :**")
                    st.dataframe(pd.DataFrame(extra),use_container_width=True)
                if miss:
                    st.markdown("**Tests ICP non couverts par le MTP :**")
                    st.dataframe(pd.DataFrame(miss),use_container_width=True)

        # Recommandations
        recs=comp.get("recommendations",[])
        if recs:
            with st.expander("💡 Recommandations",expanded=True):
                for r in recs: st.markdown(f"- {r}")

        # Note analyste
        if comp.get("analyst_notes"):
            st.caption(f"📝 {comp['analyst_notes']}")

# ═══════════════════════════════════════════════════════════════
#  ÉTAPE 6 — RAPPORT FINAL
# ═══════════════════════════════════════════════════════════════
elif step==6:
    section_title("🏁 Rapport Final Consolidé ICP vs MTP")
    if not st.session_state.comparison_report: st.warning("Rapport de comparaison manquant."); nav(prev=5); st.stop()
    comp  = st.session_state.comparison_report
    icp_r = st.session_state.icp_report_combined or {}
    summ  = comp.get("comparison_summary",{})
    gs    = summ.get("global_status","PARTIAL")
    sc    = {"PASS":"#16a34a","FAIL":"#dc2626","PARTIAL":"#d97706"}.get(gs,"#64748b")
    is_code = comp.get("_method") == "code"
    all_res = comp.get("_all_results",[])
    extra_mtp  = comp.get("_extra_mtp",[])
    missing_mtp= comp.get("_missing_mtp",[])
    anomalies  = comp.get("anomalies",[])
    prod_name = icp_r.get("product","") or ""
    prod_ver  = icp_r.get("version","") or ""
    active_prod = get_product(cfg,st.session_state.active_product_id or "") or {}

    # ── Global status banner ───────────────────────────────────────
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#0f172a,#1e3a5f);color:white;'
        f'border-radius:16px;padding:2rem;margin-bottom:1.5rem;text-align:center;">'
        f'<div style="font-size:.85rem;opacity:.7;margin-bottom:6px;">RAPPORT DE CONFORMITÉ FINAL · ICP to MTP Analysis and Reporting Tool</div>'
        f'<div style="font-size:3rem;font-weight:900;color:{sc};">{gs}</div>'
        f'<div style="font-size:1.05rem;font-weight:600;margin-top:6px;">{prod_name} {prod_ver}</div>'
        f'<div style="font-size:.82rem;opacity:.7">{datetime.now().strftime("%d/%m/%Y à %H:%M")}</div></div>',
        unsafe_allow_html=True)

    # ── Metrics ───────────────────────────────────────────────────
    total_items = summ.get("total_mtp_items",0)
    total_comp  = summ.get("total_compared",0)
    n_conform   = summ.get("compliant",0)
    n_non_conf  = summ.get("non_compliant",0)
    n_miss_mtp  = len(missing_mtp)
    n_extra_mtp = len(extra_mtp)
    cols=st.columns(6)
    for col,(v,l,k) in zip(cols,[
            (total_items,"Items MTP","info"),(total_comp,"Comparés","info"),
            (n_conform,"Conformes","pass"),(n_non_conf,"Non conformes","fail"),
            (n_miss_mtp,"Absents MTP","warn"),(n_extra_mtp,"Extras MTP","info")]):
        with col: st.markdown(mc(v,l,k),unsafe_allow_html=True)
    st.divider()

    # ── Heatmap ───────────────────────────────────────────────────
    if all_res:
        section_title("🗺️ Heatmap de Conformité — ICP vs MTP")
        sections_u=list(dict.fromkeys(r.get("Section","") for r in all_res if r.get("Section")))
        freqs_u=list(dict.fromkeys(str(r.get("Frequency","") or r.get("Signal","")) for r in all_res))[:40]
        z=[]; hover=[]
        for sec in sections_u:
            row=[]; hrow=[]
            for fq in freqs_u:
                matches=[r for r in all_res if r.get("Section")==sec and
                         (str(r.get("Frequency",""))==fq or str(r.get("Signal",""))==fq)]
                if not matches: row.append(-1); hrow.append("—")
                else:
                    r2=matches[0]
                    txt=(f"MTP: ({r2.get('MTP_Min')}, {r2.get('MTP_Max')}) {r2.get('Unit','')}"
                         f"<br>ICP: ({r2.get('ICP_Min')}, {r2.get('ICP_Max')})")
                    if r2.get("Compliant") is None: row.append(0.5); hrow.append(f"⚠️ {txt}")
                    elif r2.get("Compliant") is True: row.append(1); hrow.append(f"✅ {txt}")
                    elif r2.get("Compliant") is False: row.append(0); hrow.append(f"❌ {txt}")
                    else: row.append(-1); hrow.append("—")
            z.append(row); hover.append(hrow)
        if z and any(v!=[-1]*len(freqs_u) for v in z):
            fig_h=go.Figure(go.Heatmap(z=z,x=freqs_u,y=sections_u,customdata=hover,
                colorscale=[[0,"#fee2e2"],[0.4,"#fef3c7"],[0.6,"#fef3c7"],[1,"#dcfce7"]],
                zmin=0,zmax=1,hovertemplate="%{customdata}<extra></extra>",showscale=False))
            fig_h.update_layout(height=max(200,len(sections_u)*60+60),
                                margin=dict(t=20,b=60,l=120,r=20),
                                xaxis=dict(tickangle=-30))
            st.plotly_chart(fig_h,use_container_width=True)
        st.divider()

    # ── Section 1: Tests présents dans ICP mais absents du MTP ────
    section_title("⚠️ Tests ICP absents du MTP")
    if missing_mtp:
        df_miss=pd.DataFrame([{
            "Section":r.get("Section","—"),"Fréquence":r.get("Frequency","—"),
            "Modulation":r.get("Modulation","—"),"Signal":r.get("Signal","—"),
            "ICP Min":r.get("ICP_Min","—"),"ICP Max":r.get("ICP_Max","—"),
            "Sévérité":"🔴 CRITIQUE"
        } for r in missing_mtp])
        st.dataframe(df_miss,use_container_width=True,height=min(300,len(df_miss)*38+50))
        st.markdown(f'<div class="anomaly-critical">🔴 {len(missing_mtp)} test(s) ICP sans correspondance dans le MTP.</div>',unsafe_allow_html=True)
    else:
        st.markdown('<div class="suggest-box">✅ Tous les tests ICP ont une correspondance dans le MTP.</div>',unsafe_allow_html=True)
    st.divider()

    # ── Section 2: Tests présents dans MTP mais absents de l'ICP ──
    section_title("ℹ️ Tests MTP extras (absents de l'ICP)")
    if extra_mtp:
        df_extra=pd.DataFrame([{
            "Section":r.get("Section","—"),"Fréquence":r.get("Frequency","—"),
            "Signal":r.get("Signal","—"),"MTP Min":r.get("MTP_Min","—"),
            "MTP Max":r.get("MTP_Max","—"),"Note":"Présent MTP — absent ICP"
        } for r in extra_mtp])
        st.dataframe(df_extra,use_container_width=True,height=min(250,len(df_extra)*38+50))
    else:
        st.markdown('<div class="suggest-box">✅ Aucun test MTP extra.</div>',unsafe_allow_html=True)
    st.divider()

    # ── Section 3: Tableau comparatif détaillé par section ────────
    section_title("📋 Comparaison détaillée ICP ↔ MTP")
    if all_res:
        sections_list=list(dict.fromkeys(r.get("Section","") for r in all_res))
        for sec in sections_list:
            sec_rows=[r for r in all_res if r.get("Section")==sec]
            n_ok=sum(1 for r in sec_rows if r.get("Compliant") is True)
            n_ko=sum(1 for r in sec_rows if r.get("Compliant") is False)
            n_nd=sum(1 for r in sec_rows if r.get("Compliant") is None)
            icon="✅" if n_ko==0 else "❌"
            with st.expander(f"{icon} **{sec}** — {len(sec_rows)} tests · {n_ok} OK / {n_ko} KO / {n_nd} N/D",
                             expanded=(n_ko>0)):
                trows=[]
                for r in sec_rows:
                    # Threshold proximity warning
                    val=r.get("MTP_Value"); lo=r.get("ICP_Min") or r.get("MTP_Min")
                    hi=r.get("ICP_Max") or r.get("MTP_Max")
                    proximity_warn=""
                    try:
                        val_f=float(val); lo_f=float(lo); hi_f=float(hi)
                        rng=hi_f-lo_f
                        if rng>0:
                            prox_lo=abs(val_f-lo_f)/rng; prox_hi=abs(hi_f-val_f)/rng
                            if min(prox_lo,prox_hi)<0.05:
                                proximity_warn="⚡ Proche limite"
                    except: pass
                    compl=r.get("Compliant")
                    if compl is True: status="✅ Conforme"
                    elif compl is False: status="❌ Hors limite"
                    else: status="—"
                    trows.append({
                        "Test":r.get("Signal","") or r.get("Frequency",""),
                        "Modulation":r.get("Modulation","") or r.get("Parameter",""),
                        "ICP Min":r.get("ICP_Min"),
                        "ICP Max":r.get("ICP_Max"),
                        "MTP Min":r.get("MTP_Min"),
                        "MTP Max":r.get("MTP_Max"),
                        "Valeur MTP":r.get("MTP_Value"),
                        "Unité":r.get("Unit",""),
                        "Statut":status,
                        "Note":r.get("Note","") or proximity_warn,
                    })
                if trows:
                    df_sec=pd.DataFrame(trows)
                    st.dataframe(df_sec,use_container_width=True,height=min(350,len(trows)*38+50))
        st.divider()

    # ── Section 4: Anomalies ──────────────────────────────────────
    if anomalies:
        section_title("🚨 Anomalies détectées")
        for an in anomalies[:20]:
            sev=an.get("severity","INFO").upper()
            cls="anomaly-critical" if sev=="CRITICAL" else ("anomaly-warning" if sev=="WARNING" else "anomaly-info")
            ico={"CRITICAL":"🔴","WARNING":"🟡","INFO":"🔵"}.get(sev,"ℹ️")
            st.markdown(f'<div class="{cls}">{ico} <b>[{sev}]</b> {an.get("description","")}</div>',unsafe_allow_html=True)
        if len(anomalies)>20:
            st.caption(f"+{len(anomalies)-20} anomalies supplémentaires dans le JSON.")
        st.divider()

    # ── Export JSON ───────────────────────────────────────────────
    section_title("💾 Export du Rapport Final")
    final_json={
        "title":"Rapport Final — ICP to MTP Analysis and Reporting Tool",
        "generated_at":datetime.now().isoformat(),
        "product":{"name":active_prod.get("name",""),"version":active_prod.get("version",""),
                   "operator":active_prod.get("operator","")},
        "global_status":gs,"summary":summ,
        "missing_in_mtp":missing_mtp,"extra_in_mtp":extra_mtp,
        "all_results":all_res,"anomalies":anomalies,
        "ICP_Report":icp_r,"MTP_Report":st.session_state.mtp_combined,
        "Comparison":comp
    }
    c1,c2,c3=st.columns(3)
    with c1:
        st.download_button("📥 JSON complet",
            data=json.dumps(final_json,indent=2,ensure_ascii=False).encode("utf-8"),
            file_name=f"Rapport_Final_{active_prod.get('name','')}_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json",use_container_width=True)

    with c2:
        # ── Excel export (multi-sheet) ─────────────────────────────
        try:
            buf_xl=io.BytesIO()
            with pd.ExcelWriter(buf_xl,engine="openpyxl") as writer:
                # Sheet 1: Résumé
                pd.DataFrame([{"Produit":active_prod.get("name"),"Version":active_prod.get("version"),
                                "Opérateur":active_prod.get("operator"),"Statut Global":gs,
                                "Conformes":n_conform,"Non conformes":n_non_conf,
                                "Absents MTP":n_miss_mtp,"Extras MTP":n_extra_mtp,
                                "Générée le":datetime.now().strftime("%d/%m/%Y %H:%M")}
                ]).to_excel(writer,sheet_name="Résumé",index=False)
                # Sheet 2: Comparaison détaillée
                if all_res:
                    rows_xl=[]
                    for r in all_res:
                        compl=r.get("Compliant")
                        val=r.get("MTP_Value"); lo=r.get("ICP_Min") or r.get("MTP_Min")
                        hi=r.get("ICP_Max") or r.get("MTP_Max")
                        prox=""
                        try:
                            vf=float(val); lf=float(lo); hf=float(hi); rng=hf-lf
                            if rng>0 and min(abs(vf-lf)/rng,abs(hf-vf)/rng)<0.05: prox="⚡ Proche limite"
                        except: pass
                        rows_xl.append({"Section":r.get("Section"),"Test":r.get("Signal","") or r.get("Frequency",""),
                            "Modulation":r.get("Modulation",""),"ICP Min":r.get("ICP_Min"),
                            "ICP Max":r.get("ICP_Max"),"MTP Min":r.get("MTP_Min"),
                            "MTP Max":r.get("MTP_Max"),"Valeur MTP":r.get("MTP_Value"),
                            "Unité":r.get("Unit",""),"Conforme":("OUI" if compl else ("NON" if compl is False else "N/D")),
                            "Note":r.get("Note","") or prox})
                    pd.DataFrame(rows_xl).to_excel(writer,sheet_name="Comparaison",index=False)
                # Sheet 3: Absents MTP
                if missing_mtp:
                    pd.DataFrame([{"Section":r.get("Section"),"Fréquence":r.get("Frequency",""),
                        "Signal":r.get("Signal",""),"Modulation":r.get("Modulation",""),
                        "ICP Min":r.get("ICP_Min"),"ICP Max":r.get("ICP_Max")}
                        for r in missing_mtp]).to_excel(writer,sheet_name="Absents MTP",index=False)
                # Sheet 4: Extras MTP
                if extra_mtp:
                    pd.DataFrame([{"Section":r.get("Section"),"Signal":r.get("Signal",""),
                        "MTP Min":r.get("MTP_Min"),"MTP Max":r.get("MTP_Max")}
                        for r in extra_mtp]).to_excel(writer,sheet_name="Extras MTP",index=False)
                # Sheet 5: Anomalies
                if anomalies:
                    pd.DataFrame([{"Sévérité":a.get("severity"),"Type":a.get("type"),
                        "Description":a.get("description")} for a in anomalies]
                        ).to_excel(writer,sheet_name="Anomalies",index=False)
                # Sheet 6: Logs unifiés
                if st.session_state.get("unified_log_rows"):
                    pd.DataFrame(st.session_state.unified_log_rows).to_excel(
                        writer,sheet_name="Logs validés",index=False)
            buf_xl.seek(0)
            st.download_button("📥 Excel multi-onglets",data=buf_xl.getvalue(),
                file_name=f"Rapport_Final_{active_prod.get('name','')}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True)
        except Exception as e: st.error(f"Erreur Excel : {e}")

    with c3:
        # ── PDF export via reportlab ───────────────────────────────
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import (SimpleDocTemplate,Paragraph,Spacer,
                                             Table,TableStyle,HRFlowable)
            from reportlab.lib.enums import TA_CENTER,TA_LEFT

            buf_pdf=io.BytesIO()
            doc=SimpleDocTemplate(buf_pdf,pagesize=A4,
                                  rightMargin=1.5*cm,leftMargin=1.5*cm,
                                  topMargin=2*cm,bottomMargin=2*cm)
            styles=getSampleStyleSheet()
            h1=ParagraphStyle("h1",parent=styles["Heading1"],fontSize=16,spaceAfter=8,alignment=TA_CENTER)
            h2=ParagraphStyle("h2",parent=styles["Heading2"],fontSize=12,spaceBefore=12,spaceAfter=6)
            body=ParagraphStyle("body",parent=styles["Normal"],fontSize=9,leading=13)
            small=ParagraphStyle("small",parent=styles["Normal"],fontSize=8,textColor=colors.grey)

            story=[]
            # Title
            story.append(Paragraph("Rapport Final — ICP vs MTP",h1))
            story.append(Paragraph(f"{active_prod.get('name','')} {active_prod.get('version','')} · Généré le {datetime.now().strftime('%d/%m/%Y %H:%M')}",small))
            story.append(Spacer(1,0.4*cm))
            story.append(HRFlowable(width="100%",thickness=2,color=colors.HexColor("#0057b8")))
            story.append(Spacer(1,0.3*cm))

            # Status
            status_color={"PASS":colors.HexColor("#16a34a"),"FAIL":colors.HexColor("#dc2626"),
                          "PARTIAL":colors.HexColor("#d97706")}.get(gs,colors.grey)
            story.append(Paragraph(f'Statut Global : <font color="{status_color.hexval() if hasattr(status_color,"hexval") else "#666"}">{gs}</font>',h2))

            # Summary table
            sum_data=[["Métrique","Valeur"],
                      ["Items MTP",str(total_items)],["Comparés",str(total_comp)],
                      ["Conformes",str(n_conform)],["Non conformes",str(n_non_conf)],
                      ["Absents MTP",str(n_miss_mtp)],["Extras MTP",str(n_extra_mtp)]]
            t_sum=Table(sum_data,colWidths=[7*cm,4*cm])
            t_sum.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0057b8")),
                ("TEXTCOLOR",(0,0),(-1,0),colors.white),
                ("FONTSIZE",(0,0),(-1,-1),9),("GRID",(0,0),(-1,-1),0.5,colors.lightgrey),
                ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f8fafc")]),
            ]))
            story.append(t_sum); story.append(Spacer(1,0.5*cm))

            # Missing in MTP
            if missing_mtp:
                story.append(Paragraph("⚠️ Tests ICP absents du MTP",h2))
                miss_data=[["Section","Fréquence / Signal","ICP Min","ICP Max"]]
                for r in missing_mtp[:50]:
                    miss_data.append([r.get("Section","—"),
                                      str(r.get("Frequency","") or r.get("Signal","—")),
                                      str(r.get("ICP_Min","—")),str(r.get("ICP_Max","—"))])
                t_miss=Table(miss_data,colWidths=[3*cm,6*cm,2.5*cm,2.5*cm])
                t_miss.setStyle(TableStyle([
                    ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#fee2e2")),
                    ("FONTSIZE",(0,0),(-1,-1),8),("GRID",(0,0),(-1,-1),0.4,colors.lightgrey),
                ]))
                story.append(t_miss); story.append(Spacer(1,0.4*cm))

            # Comparison (first 80 rows)
            if all_res:
                story.append(Paragraph("📋 Comparaison ICP ↔ MTP (extraits)",h2))
                cmp_data=[["Section","Test","ICP Min","ICP Max","MTP Min","MTP Max","Conforme"]]
                for r in all_res[:80]:
                    compl=r.get("Compliant")
                    cmp_data.append([
                        str(r.get("Section",""))[:18],
                        str(r.get("Signal","") or r.get("Frequency",""))[:20],
                        str(r.get("ICP_Min",""))[:8],str(r.get("ICP_Max",""))[:8],
                        str(r.get("MTP_Min",""))[:8],str(r.get("MTP_Max",""))[:8],
                        "OUI" if compl else ("NON" if compl is False else "N/D"),
                    ])
                t_cmp=Table(cmp_data,colWidths=[2.5*cm,3.5*cm,1.8*cm,1.8*cm,1.8*cm,1.8*cm,1.5*cm])
                t_cmp.setStyle(TableStyle([
                    ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0057b8")),
                    ("TEXTCOLOR",(0,0),(-1,0),colors.white),
                    ("FONTSIZE",(0,0),(-1,-1),7.5),("GRID",(0,0),(-1,-1),0.4,colors.lightgrey),
                    ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f8fafc")]),
                ]))
                story.append(t_cmp); story.append(Spacer(1,0.3*cm))
                if len(all_res)>80:
                    story.append(Paragraph(f"… {len(all_res)-80} lignes supplémentaires dans le JSON.",small))

            doc.build(story)
            buf_pdf.seek(0)
            st.download_button("📥 PDF rapport",data=buf_pdf.getvalue(),
                file_name=f"Rapport_Final_{active_prod.get('name','')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",use_container_width=True)
        except ImportError:
            st.info("💡 Installez reportlab pour l'export PDF : `pip install reportlab`")
        except Exception as e:
            st.error(f"Erreur PDF : {e}")

    st.divider()
    if st.button("🔄 Nouvelle analyse",use_container_width=True):
        for k in [k for k in list(st.session_state.keys()) if k!="cfg"]: del st.session_state[k]
        _init(); st.rerun()
    nav(prev=5)
