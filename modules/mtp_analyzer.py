#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module MTP Analyzer — Analyse par code classique (sans IA)
===========================================================
Conserve la même interface que la version IA :
  - analyze_mtp_pdf()       : analyse le PDF MTP et retourne un rapport structuré
  - compare_icp_mtp()       : compare le rapport ICP et le rapport MTP
  - extract_pdf_text()      : utilitaire extraction texte PDF

En arrière-plan, utilise mtp_extractor.py (regex + parsing) au lieu d'un LLM.
Les prompts, le design et les boutons de l'interface restent identiques.
"""

import json
import re
from typing import Optional, Dict, Any

from mtp_extractor import extract_mtp, compare_mtp_vs_icp


# ─────────────────────────────────────────────────────────────
#  PROMPTS — conservés pour affichage dans l'interface
# ─────────────────────────────────────────────────────────────

PROMPT_MTP_EXTRACT_SYSTEM = """Tu es un expert en validation de tests pour équipements de télécommunication.
Tu analyses un document MTP (Manufacturing Test Plan) PEGATRON pour Sagemcom.
Le document contient les spécifications de test définies par le sous-traitant.

Sections extraites automatiquement par le moteur de code :
  • Board Level ICT : tensions d'alimentation (Signal, TestPoint, Min/Max)
  • RF Test         : Bluetooth TX/RX + Wi-Fi 2.4GHz/5GHz TX/RX
  • System Test     : USB, Ethernet, HDMI, LED, boutons, température
  • FW Upgrade      : étapes PASS/FAIL (flash, personnalisation, MACs)
  • Final Check     : vérifications finales
"""

PROMPT_MTP_EXTRACT_USER = """Voici le document MTP à analyser :

{mtp_text}

[Analyse effectuée par le moteur de code classique — résultat JSON structuré retourné]
"""

PROMPT_COMPARE_SYSTEM = """Tu es un expert en qualification d'équipements de télécommunication.
Tu compares les spécifications du MTP (Manufacturing Test Plan PEGATRON)
avec les spécifications de l'ICP (Inspection Control Plan Sagemcom).

La comparaison vérifie :
  1. Correspondance des limites (Min/Max identiques entre MTP et ICP)
  2. Couverture des tests (tous les tests ICP présents dans le MTP)
  3. Tests supplémentaires dans le MTP
"""

PROMPT_COMPARE_USER = """=== RAPPORT ICP (Spécifications Sagemcom) ===
{icp_report}

=== RAPPORT MTP (Spécifications PEGATRON) ===
{mtp_report}

[Comparaison effectuée par le moteur de code classique]
"""


# ─────────────────────────────────────────────────────────────
#  API PUBLIQUE (même signature que la version IA)
# ─────────────────────────────────────────────────────────────

def analyze_mtp_pdf(pdf_bytes: bytes,
                    pdf_text:  str = "",
                    pdf_filename: str = "mtp.pdf") -> dict:
    """
    Analyse un PDF MTP par code classique (regex + parsing).

    Paramètres identiques à la version IA — l'interface ne change pas.

    Returns:
        dict avec :
          device_info, boardlevel, bluetooth, wifi, system,
          fw_upgrade, summary, _raw (rapport complet extractor)
    """
    # Utiliser les bytes si disponibles, sinon le chemin
    pdf_input = pdf_bytes if pdf_bytes else pdf_text

    mtp_raw = extract_mtp(pdf_input if pdf_bytes else pdf_filename)

    # Adapter au format attendu par l'interface (compatible format IA)
    result = {
        "device_info": {
            "product":  mtp_raw["metadata"].get("product", "Inconnu"),
            "version":  mtp_raw["metadata"].get("version", "—"),
            "date":     mtp_raw["metadata"].get("release_date", "—"),
            "icp_ref":  mtp_raw["metadata"].get("icp_ref", "—"),
            "operator": "",
        },
        "BoardLevel": mtp_raw["boardlevel"],
        "RF_Results": {
            "2.4GHz":   [w for w in mtp_raw["wifi"] if w.get("Band") == "2.4GHz"],
            "5GHz":     [w for w in mtp_raw["wifi"] if w.get("Band") == "5GHz"],
            "Bluetooth": mtp_raw["bluetooth"],
            "WiFi_Params": [w for w in mtp_raw["wifi"] if not w.get("Frequency")],
        },
        "System": mtp_raw["system"],
        "FW_Upgrade": mtp_raw["fw_upgrade"],
        "summary": {
            "total_tests":  mtp_raw["summary"]["total"],
            "boardlevel":   mtp_raw["summary"]["boardlevel"],
            "bluetooth":    mtp_raw["summary"]["bluetooth"],
            "wifi":         mtp_raw["summary"]["wifi"],
            "system":       mtp_raw["summary"]["system"],
            "fw_upgrade":   mtp_raw["summary"]["fw_upgrade"],
        },
        "_raw": mtp_raw,
        "_method": "code",  # Indicateur : analyse par code, pas par IA
    }

    return result


def compare_icp_mtp(icp_report: dict, mtp_report: dict) -> dict:
    """
    Compare le rapport ICP et le rapport MTP par code classique.

    Paramètres identiques à la version IA.

    Returns:
        dict avec comparison_summary, results, anomalies, recommendations
    """
    # mtp_report peut venir de analyze_mtp_pdf() ou directement de extract_mtp()
    raw_mtp = mtp_report.get("_raw") or mtp_report

    # icp_data : construire depuis le format de l'interface
    icp_data = {
        "icp_rf_limits": icp_report.get("RF_Limits",
                         icp_report.get("icp_rf_limits", {})),
        "icp_fe_limits": icp_report.get("FE_Limits",
                         icp_report.get("icp_fe_limits", [])),
        "log_results":   icp_report.get("log_results", {}),
    }

    result = compare_mtp_vs_icp(raw_mtp, icp_data)

    # Adapter au format attendu par l'interface (compatible format IA)
    return {
        "comparison_summary": result["comparison_summary"],
        "FE_Comparison":   [],   # Non applicable (MTP PEGATRON ne couvre pas le FE DVB)
        "RF_Comparison":   {
            "2.4GHz":    [r for r in result["results"] if r["Section"] == "2.4GHz"],
            "5GHz":      [r for r in result["results"] if r["Section"] == "5GHz"],
            "Bluetooth": [r for r in result["results"] if r["Section"] == "Bluetooth"],
        },
        "BoardLevel_Comparison": [r for r in result["results"] if r["Section"] == "BoardLevel"],
        "System_Comparison":     [r for r in result["results"] if r["Section"] == "System"],
        "anomalies":             result["anomalies"],
        "recommendations":       result["recommendations"],
        "analyst_notes":         result["analyst_notes"],
        "_method":               "code",
        "_all_results":          result["results"],
        "_extra_mtp":            result["extra_in_mtp"],
        "_missing_mtp":          result["missing_in_mtp"],
    }


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extrait le texte brut d'un PDF (inchangé)."""
    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages = [doc[p].get_text("text") for p in range(doc.page_count)]
        return "\n\n--- PAGE BREAK ---\n\n".join(pages)
    except Exception as e:
        return f"[Erreur extraction PDF: {e}]"
