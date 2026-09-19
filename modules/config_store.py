#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Config Store — Gestion CRUD persistante (JSON) pour :
  - Produits
  - Modules (FE, RF_WiFi, RF_BT, Custom…)
  - Parsers
  - Extractors
  - Tests (règles de validation)

Les données sont stockées dans telecom_config.json dans le répertoire courant.
"""

import json
import copy
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

CONFIG_FILE = Path(__file__).parent.parent / "telecom_config.json"

# ─────────────────────────────────────────────────────────────
#  DÉFINITIONS PAR DÉFAUT (guides pour l'utilisateur)
# ─────────────────────────────────────────────────────────────

DEFAULT_PARSERS = {
    "parse_fe_v2": {
        "id": "parse_fe_v2",
        "name": "Parser FE v2 (DVB-C/S/T)",
        "description": "Extrait les blocs FE_ConnectCab / FE_ConnectSat / FE_Connect TER et FE_GetSignalInfos.",
        "module_file": "check_fe_log.py",
        "function": "parse_log",
        "compatible_modules": ["FE"],
        "detection_patterns": ["FE_Connect", "FE_GetSignalInfos", "DVB"],
        "builtin": True,
    },
    "parse_rf_v15": {
        "id": "parse_rf_v15",
        "name": "Parser RF v15 (Wi-Fi + BT)",
        "description": "Extrait TEST_VERIFY EVM/MASK/PER pour Wi-Fi 2.4/5 GHz et Bluetooth.",
        "module_file": "check_rf_log.py",
        "function": "parse_log",
        "compatible_modules": ["RF_WiFi", "RF_BT"],
        "detection_patterns": ["TEST_VERIFY", "EVM", "MASK", "POWER SPECTRUM", "ANT1", "ANT2"],
        "builtin": True,
    },
    "parse_ft_v1": {
        "id": "parse_ft_v1",
        "name": "Parser FT v1 (Functional Tests)",
        "description": "Analyse USB, Ethernet, LED, NAND, HDMI, IR, SWITCH, RADIATED depuis les logs System/Final/FW.",
        "module_file": "check_ft_log.py",
        "function": "analyze_in_memory",
        "compatible_modules": ["FT"],
        "detection_patterns": [
            "USB", "Ethernet", "HDMI", "LED", "NAND", "IR_test",
            "disable_all_test", "ping", "SWITCH",
        ],
        "builtin": True,
    },
}

DEFAULT_EXTRACTORS = {
    "extract_fe_v2": {
        "id": "extract_fe_v2",
        "name": "Extractor FE ICP v2",
        "description": "Extrait les tests FE depuis les PDF ICP. Supporte DVB-C, DVB-S/S2, DVB-T/T2.",
        "module_file": "icp_fe_extract.py",
        "function": "extract_fe_tests",
        "compatible_modules": ["FE"],
        "pdf_markers": ["Test#", "FE_SAT", "FE_DVB", "J83", "Frequency", "DVB-C", "DVB-S", "DVB-T"],
        "builtin": True,
    },
    "extract_rf_v3": {
        "id": "extract_rf_v3",
        "name": "Extractor RF/BT ICP v3",
        "description": "Extrait les limites Wi-Fi (2.4/5 GHz) et Bluetooth depuis les PDF ICP.",
        "module_file": "icp_wifi_extract.py",
        "function": "extract_rf_limits",
        "compatible_modules": ["RF_WiFi", "RF_BT"],
        "pdf_markers": ["Wi-Fi", "Bluetooth", "CONDUCTED TESTS", "Frequency", "Modulation", "EVM", "PER"],
        "builtin": True,
    },
    "extract_ft_v1": {
        "id": "extract_ft_v1",
        "name": "Extractor FT ICP v1 (Functional Tests)",
        "description": "Extrait USB, Ethernet, LED, HDMI, IR, SWITCH, RADIATED depuis les PDF ICP.",
        "module_file": "icp_ft_extract.py",
        "function": "extract_tests",
        "compatible_modules": ["FT"],
        "pdf_markers": ["USB", "Ethernet", "HDMI", "LED", "NAND", "IR", "SWITCH", "Radiated"],
        "builtin": True,
    },
}

DEFAULT_TEST_RULES = {
    "fe_strict": {
        "id": "fe_strict",
        "name": "FE Strict — Aucun paramètre manquant",
        "description": "Tous les paramètres ICP doivent être présents dans le log. Échec si manquant.",
        "compatible_modules": ["FE"],
        "settings": {"strict_mode": True, "freq_tolerance_mhz": 1, "missing_policy": "fail"},
        "builtin": True,
    },
    "fe_standard": {
        "id": "fe_standard",
        "name": "FE Standard — Avertissement si manquant",
        "description": "Paramètres manquants génèrent un avertissement mais pas d'échec global.",
        "compatible_modules": ["FE"],
        "settings": {"strict_mode": False, "freq_tolerance_mhz": 1, "missing_policy": "warning"},
        "builtin": True,
    },
    "rf_mandatory_only": {
        "id": "rf_mandatory_only",
        "name": "RF Mandatory Only (--opt)",
        "description": "Ignore les tests RF avec Mandatory=false dans les limites ICP.",
        "compatible_modules": ["RF_WiFi", "RF_BT"],
        "settings": {"opt_mode": True, "missing_policy": "warning"},
        "builtin": True,
    },
    "rf_all_tests": {
        "id": "rf_all_tests",
        "name": "RF All Tests",
        "description": "Valide tous les tests RF, y compris ceux avec Mandatory=false.",
        "compatible_modules": ["RF_WiFi", "RF_BT"],
        "settings": {"opt_mode": False, "missing_policy": "warning"},
        "builtin": True,
    },
}

DEFAULT_MODULES = {
    "FE": {
        "id": "FE",
        "name": "Front-End (FE)",
        "icon": "📺",
        "description": "Validation DVB-C, DVB-S/S2, DVB-T/T2",
        "color": "#0057b8",
        "default_parser": "parse_fe_v2",
        "default_extractor": "extract_fe_v2",
        "default_test_rule": "fe_standard",
        "builtin": True,
    },
    "RF_WiFi": {
        "id": "RF_WiFi",
        "name": "RF Wi-Fi",
        "icon": "📶",
        "description": "Validation Wi-Fi 2.4 GHz / 5 GHz (EVM, Power, PER)",
        "color": "#0891b2",
        "default_parser": "parse_rf_v15",
        "default_extractor": "extract_rf_v3",
        "default_test_rule": "rf_all_tests",
        "builtin": True,
    },
    "RF_BT": {
        "id": "RF_BT",
        "name": "Bluetooth",
        "icon": "🔵",
        "description": "Validation Bluetooth BR/EDR/BLE (Power, BER, Drift, Deviation)",
        "color": "#7c3aed",
        "default_parser": "parse_rf_v15",
        "default_extractor": "extract_rf_v3",
        "default_test_rule": "rf_mandatory_only",
        "builtin": True,
    },
    "FT": {
        "id": "FT",
        "name": "Functional Tests (FT)",
        "icon": "🧪",
        "description": "Tests fonctionnels : USB, Ethernet, LED, HDMI, IR, SWITCH, RADIATED",
        "color": "#0d9488",
        "default_parser": "parse_ft_v1",
        "default_extractor": "extract_ft_v1",
        "default_test_rule": "",
        "filename_patterns": [
            r"^\d+\+Final[-_]",
            r"^\d+\+FW[_-]Upgrade[-_]",
            r"^\d+\+SYSTEM[-_]",
        ],
        "builtin": True,
    },
}

DEFAULT_REGEXES = {
    # ── FE Log Parser (check_fe_log.py) ─────────────────────
    "fe_connect_cab": {
        "id": "fe_connect_cab",
        "name": "FE Connect Cable (DVB-C)",
        "description": "Détecte une ligne FE_ConnectCab : extrait la fréquence (MHz) et le niveau QAM (ex. QAM256).",
        "pattern": r"^FE_ConnectCab\s+\d+\s+(\d+)\s+\d+\s+FE_\w+\s+FE_QAM(\d+)",
        "flags": ["MULTILINE"],
        "groups": ["frequency_mhz", "qam_order"],
        "scope": "fe_log",
        "used_in": "check_fe_log.py::RE_CONNECT_CAB",
        "example": "FE_ConnectCab 0 498 6875 FE_J83_B FE_QAM256",
        "builtin": True,
    },
    "fe_connect_sat": {
        "id": "fe_connect_sat",
        "name": "FE Connect Satellite (DVB-S/S2)",
        "description": "Détecte FE_ConnectSat : extrait la fréquence (kHz) et le standard DVB (DVB_S ou DVB_S2).",
        "pattern": r"^FE_ConnectSat\s+\d+\s+(\d+)\s+\d+\s+[VH]\s+OPAL_FE_(DVB_S2|DVB_S)",
        "flags": ["MULTILINE"],
        "groups": ["frequency_khz", "dvb_standard"],
        "scope": "fe_log",
        "used_in": "check_fe_log.py::RE_CONNECT_SAT",
        "example": "FE_ConnectSat 0 1474000 27500 V OPAL_FE_DVB_S",
        "builtin": True,
    },
    "fe_connect_tnt": {
        "id": "fe_connect_tnt",
        "name": "FE Connect Terrestre (DVB-T/T2)",
        "description": "Détecte FE_Connect TER : extrait fréquence (kHz), génération T/T2, largeur de bande optionnelle.",
        "pattern": r"^FE_Connect\s+TER\s+\d+\s+(\d+)\s+FE_DVB_(T2|T)(?:\s+FE_BAND_(\d+)MHZ)?",
        "flags": ["MULTILINE"],
        "groups": ["frequency_khz", "dvb_gen", "bandwidth_mhz"],
        "scope": "fe_log",
        "used_in": "check_fe_log.py::RE_CONNECT_TNT",
        "example": "FE_Connect TER 0 474000 FE_DVB_T2 FE_BAND_8MHZ",
        "builtin": True,
    },
    "fe_siginfos_block": {
        "id": "fe_siginfos_block",
        "name": "FE GetSignalInfos Block",
        "description": "Isole le bloc complet FE_GetSignalInfos 0 … jusqu'au prochain prompt TT> ou fin de texte.",
        "pattern": r"FE_GetSignalInfos\s+0.*?(?=\nTT>|$)",
        "flags": ["DOTALL"],
        "groups": ["full_block"],
        "scope": "fe_log",
        "used_in": "check_fe_log.py::RE_SIGINFOS_BLOCK",
        "example": "FE_GetSignalInfos 0\nViterbi Bit Error Rate = 12E-7\n...",
        "builtin": True,
    },
    "fe_viterbi_ber": {
        "id": "fe_viterbi_ber",
        "name": "Viterbi BER",
        "description": "Extrait le taux d'erreur binaire Viterbi au format NE-7 (ex. 12E-7 → valeur 12).",
        "pattern": r"Viterbi\s+Bit\s+Error\s+Rate\s*=\s*(\d+)E-7",
        "flags": [],
        "groups": ["ber_value"],
        "scope": "fe_log",
        "used_in": "check_fe_log.py::REGEX_MAP[Viterbi Bit Error Rate]",
        "example": "Viterbi Bit Error Rate = 12E-7",
        "builtin": True,
    },
    "fe_snr": {
        "id": "fe_snr",
        "name": "Signal to Noise Ratio (SNR / CNR)",
        "description": "Extrait le rapport signal/bruit en dB (valeur décimale).",
        "pattern": r"Signal\s+to\s+Noise\s+Ratio\s*=\s*([\d\.]+)",
        "flags": [],
        "groups": ["snr_db"],
        "scope": "fe_log",
        "used_in": "check_fe_log.py::REGEX_MAP[Signal to Noise Ratio]",
        "example": "Signal to Noise Ratio = 34.5",
        "builtin": True,
    },
    "fe_uncorrected_blocks": {
        "id": "fe_uncorrected_blocks",
        "name": "Uncorrected Blocks",
        "description": "Extrait le nombre de blocs non corrigés (entier).",
        "pattern": r"uncorrected\s+blocks\s*=\s*(\d+)",
        "flags": [],
        "groups": ["block_count"],
        "scope": "fe_log",
        "used_in": "check_fe_log.py::REGEX_MAP[Number of uncorrected blocks]",
        "example": "Number of uncorrected blocks = 0",
        "builtin": True,
    },
    "fe_freq_offset": {
        "id": "fe_freq_offset",
        "name": "Frequency Offset (FE log)",
        "description": "Extrait l'écart de fréquence mesuré en kHz (entier signé).",
        "pattern": r"Frequency\s+Offset\s*=\s*(-?\d+)",
        "flags": [],
        "groups": ["offset_khz"],
        "scope": "fe_log",
        "used_in": "check_fe_log.py::REGEX_MAP[Frequency Offset]",
        "example": "Frequency Offset = -45",
        "builtin": True,
    },
    "fe_symbol_rate_offset": {
        "id": "fe_symbol_rate_offset",
        "name": "Symbol Rate Offset",
        "description": "Extrait le décalage de débit symbole en ppm (entier signé).",
        "pattern": r"Symbol\s+Rate\s+Offset\s*=\s*(-?\d+)",
        "flags": [],
        "groups": ["offset_ppm"],
        "scope": "fe_log",
        "used_in": "check_fe_log.py::REGEX_MAP[Symbol Rate Offset]",
        "example": "Symbol Rate Offset = 88",
        "builtin": True,
    },
    "fe_power_dbm": {
        "id": "fe_power_dbm",
        "name": "Power in dBm (RSSI)",
        "description": "Extrait la puissance reçue RSSI en dBm (entier signé).",
        "pattern": r"Power\s+in\s+dBm\s*=\s*(-?\d+)",
        "flags": [],
        "groups": ["power_dbm"],
        "scope": "fe_log",
        "used_in": "check_fe_log.py::REGEX_MAP[Power in dBm]",
        "example": "Power in dBm = -50",
        "builtin": True,
    },
    "fe_bandwidth": {
        "id": "fe_bandwidth",
        "name": "Bandwidth MHz",
        "description": "Extrait la largeur de bande DVB-T/T2 en MHz.",
        "pattern": r"Bandwidth\s*\[MHz\]\s*=\s*(\d+)",
        "flags": [],
        "groups": ["bandwidth_mhz"],
        "scope": "fe_log",
        "used_in": "check_fe_log.py::REGEX_BANDWIDTH_PARAM",
        "example": "Bandwidth [MHz] = 8",
        "builtin": True,
    },
    # ── RF Log Parser (check_rf_log.py) ─────────────────────
    "rf_test_evm_spectrum": {
        "id": "rf_test_evm_spectrum",
        "name": "RF Test EVM Mask Power Spectrum",
        "description": "Détecte les blocs TEST_VERIFY EVM MASK POWER SPECTRUM (Wi-Fi TX).",
        "pattern": r"TEST_VERIFY\s+EVM\s+MASK\s+POWER\s+SPECTRUM",
        "flags": ["IGNORECASE"],
        "groups": [],
        "scope": "rf_log",
        "used_in": "check_rf_log.py::WIFI_SPECTRUM",
        "example": "TEST_VERIFY EVM MASK POWER SPECTRUM 2412 MCS7 HT20 ANT1",
        "builtin": True,
    },
    "rf_test_per": {
        "id": "rf_test_per",
        "name": "RF Test PER (Packet Error Rate)",
        "description": "Détecte les blocs TEST_VERIFY PER (réception Wi-Fi/BT).",
        "pattern": r"TEST_VERIFY\s+PER",
        "flags": ["IGNORECASE"],
        "groups": [],
        "scope": "rf_log",
        "used_in": "check_rf_log.py::WIFI_PER",
        "example": "TEST_VERIFY PER 2412 MCS7 HT20",
        "builtin": True,
    },
    "rf_frequency": {
        "id": "rf_frequency",
        "name": "RF Frequency (4–5 digits)",
        "description": "Extrait une fréquence Wi-Fi/BT de 4 ou 5 chiffres (ex. 2412, 5180).",
        "pattern": r"(\d{4,5})",
        "flags": [],
        "groups": ["frequency_mhz"],
        "scope": "rf_log",
        "used_in": "check_rf_log.py::FREQ_PAT",
        "example": "TEST_VERIFY EVM MASK POWER SPECTRUM 2412 MCS7 HT20 ANT1",
        "builtin": True,
    },
    "rf_antenna": {
        "id": "rf_antenna",
        "name": "RF Antenna (ANT1 / ANT2)",
        "description": "Extrait l'identifiant d'antenne ANTx depuis l'en-tête de test RF.",
        "pattern": r"\bANT[\s\-]?(\d)\b",
        "flags": ["IGNORECASE"],
        "groups": ["antenna_index"],
        "scope": "rf_log",
        "used_in": "check_rf_log.py::ANT_PAT",
        "example": "TEST_VERIFY EVM MASK POWER SPECTRUM 2412 MCS7 HT20 ANT1",
        "builtin": True,
    },
    "rf_param_with_limits": {
        "id": "rf_param_with_limits",
        "name": "RF Paramètre avec limites (min, max)",
        "description": "Extrait un paramètre RF au format NOM: valeur unité (min, max).",
        "pattern": r"(?P<n>[A-Z0-9_]+)\s*:\s*(?P<val>-?\d+(?:\.\d+)?)\s*(?P<unit>[a-zA-Z%/ ]+)?\s*\(\s*(?P<min>-?\d+(?:\.\d+)?)?\s*,\s*(?P<max>-?\d+(?:\.\d+)?)?\s*\)",
        "flags": [],
        "groups": ["name", "value", "unit", "min", "max"],
        "scope": "rf_log",
        "used_in": "check_rf_log.py::PARAM1",
        "example": "POWER_AVG_DBM: 16.8 dBm (14.0, 20.0)",
        "builtin": True,
    },
    "rf_param_simple": {
        "id": "rf_param_simple",
        "name": "RF Paramètre simple (valeur + unité)",
        "description": "Extrait un paramètre RF sans limites, format NOM: valeur unité.",
        "pattern": r"(?P<n>[A-Z0-9_]+)\s*:\s*(?P<val>-?\d+(?:\.\d+)?)\s*(?P<unit>[a-zA-Z%/ ]+)?",
        "flags": [],
        "groups": ["name", "value", "unit"],
        "scope": "rf_log",
        "used_in": "check_rf_log.py::PARAM_SIMPLE",
        "example": "EVM_DB_AVG_S1: -31.2 dB",
        "builtin": True,
    },
    # ── ICP FE Extractor (icp_fe_extract.py) ─────────────────
    "icp_fe_test_header": {
        "id": "icp_fe_test_header",
        "name": "ICP FE En-tête de test (Test#N)",
        "description": "Détecte l'en-tête de section de test FE dans le PDF ICP (ex. Test#1).",
        "pattern": r"Test#\s*(\d+)",
        "flags": ["IGNORECASE"],
        "groups": ["test_number"],
        "scope": "icp_fe",
        "used_in": "icp_fe_extract.py::RE_TEST_HEADER",
        "example": "Test#1",
        "builtin": True,
    },
    "icp_fe_freq_line": {
        "id": "icp_fe_freq_line",
        "name": "ICP FE Ligne fréquence / modulation",
        "description": "Extrait fréquence (MHz), modulation (QAM/PSK) et standard DVB depuis le PDF ICP FE.",
        "pattern": r"Frequency\s*([0-9]+(?:\.[0-9]+)?)\s*MHz\s*/\s*([0-9]+(?:MHz)?|QPSK|8PSK|[0-9]+QAM)\s*(DVB[\s\-]T2|DVB[\s\-]T|DVB[\s\-]S2|DVB[\s\-]S|DVB\-C|J83\.B)",
        "flags": ["IGNORECASE"],
        "groups": ["frequency_mhz", "modulation", "dvb_standard"],
        "scope": "icp_fe",
        "used_in": "icp_fe_extract.py::RE_FREQ_LINE",
        "example": "Frequency 498 MHz / 256QAM DVB-C",
        "builtin": True,
    },
    "icp_fe_label_line": {
        "id": "icp_fe_label_line",
        "name": "ICP FE Ligne étiquette de section",
        "description": "Détecte les lignes FE_SAT / FE_DVB-C / FE_J83.B avec fréquence et libellé de test.",
        "pattern": r"(FE(?:_|[\s])?(?:SAT|DVB\-C|J83\.B|DVB\-TT2))\s*([0-9]+(?:\.[0-9]+)?)\s*MHz\s*:\s*(.+)",
        "flags": ["IGNORECASE"],
        "groups": ["fe_type", "frequency_mhz", "label"],
        "scope": "icp_fe",
        "used_in": "icp_fe_extract.py::RE_LABEL_LINE",
        "example": "FE_DVB-C 498 MHz : Viterbi BER",
        "builtin": True,
    },
    "icp_fe_number": {
        "id": "icp_fe_number",
        "name": "ICP FE Nombre (entier ou décimal signé)",
        "description": "Extrait tout nombre décimal signé dans une ligne du PDF ICP (limites Min/Max).",
        "pattern": r"-?\d+(?:[.,]\d+)?",
        "flags": [],
        "groups": ["number"],
        "scope": "icp_fe",
        "used_in": "icp_fe_extract.py::RE_NUMBER",
        "example": "-65  ou  34.5  ou  -200",
        "builtin": True,
    },
    "icp_fe_unit": {
        "id": "icp_fe_unit",
        "name": "ICP FE Unité de mesure",
        "description": "Détecte les unités valides dans le PDF ICP FE : dBm, dB, kHz, ppm, %, none, .10-7.",
        "pattern": r"\b(dBm|dB|kHz|ppm|%|none|\.10\-7|Hz)\b",
        "flags": ["IGNORECASE"],
        "groups": ["unit"],
        "scope": "icp_fe",
        "used_in": "icp_fe_extract.py::RE_UNIT",
        "example": "dBm  ou  kHz  ou  .10-7",
        "builtin": True,
    },
    # ── ICP RF/BT Extractor (icp_wifi_extract.py) ───────────
    "icp_rf_freq_mod_block": {
        "id": "icp_rf_freq_mod_block",
        "name": "ICP RF Bloc fréquence / modulation",
        "description": "Identifie un bloc de test RF dans le PDF ICP avec fréquence et modulation (Wi-Fi / BT).",
        "pattern": r"(\d{4,5})\s*MHz.*?(MCS\d+\s+(?:HT|VHT|HE)\d+|GFSK|DQPSK|8DPSK|QPSK)",
        "flags": ["IGNORECASE", "DOTALL"],
        "groups": ["frequency_mhz", "modulation"],
        "scope": "icp_rf",
        "used_in": "icp_wifi_extract.py::RE_FREQ_MOD",
        "example": "2412 MHz / MCS7 HT20",
        "builtin": True,
    },
    "icp_rf_float": {
        "id": "icp_rf_float",
        "name": "ICP RF Nombre décimal signé",
        "description": "Extrait tout nombre décimal signé dans le PDF ICP RF (puissances, EVM, PER…).",
        "pattern": r"-?\d+(?:[.,]\d+)?",
        "flags": [],
        "groups": ["value"],
        "scope": "icp_rf",
        "used_in": "icp_wifi_extract.py::RE_FLOAT",
        "example": "-28.0  ou  17.5",
        "builtin": True,
    },
    "icp_rf_test_label": {
        "id": "icp_rf_test_label",
        "name": "ICP RF Étiquette de test",
        "description": "Détecte les lignes 'Test NOM : description' dans les PDF ICP RF/BT.",
        "pattern": r"\bTest\s+([A-Z0-9_]+)\s*:\s*(.+)",
        "flags": [],
        "groups": ["test_name", "description"],
        "scope": "icp_rf",
        "used_in": "icp_wifi_extract.py::RE_TEST_LABEL",
        "example": "Test TX_POWER : Puissance TX mesurée",
        "builtin": True,
    },
    "icp_bt_freq_drift": {
        "id": "icp_bt_freq_drift",
        "name": "BT Frequency Drift (limites kHz)",
        "description": "Extrait les limites min/max de dérive de fréquence Bluetooth en kHz.",
        "pattern": r"frequency\s*drift.*?([\-\u2013\u2014]?\d+).*?([\-\u2013\u2014]?\d+)\s*kHz",
        "flags": ["IGNORECASE", "DOTALL"],
        "groups": ["drift_min_khz", "drift_max_khz"],
        "scope": "icp_rf",
        "used_in": "icp_wifi_extract.py::RE_FREQ_DRIFT",
        "example": "Frequency drift : -25 to +25 kHz",
        "builtin": True,
    },
    "icp_bt_max_drift_rate": {
        "id": "icp_bt_max_drift_rate",
        "name": "BT Max Drift Rate (kHz/50µs)",
        "description": "Extrait la limite de vitesse de dérive maximale Bluetooth (kHz par 50 µs).",
        "pattern": r"max\s*drift\s*rate.*?([0-9]+(?:[.,][0-9]+)?)\s*kHz\s*/\s*50",
        "flags": ["IGNORECASE"],
        "groups": ["drift_rate_khz_per_50us"],
        "scope": "icp_rf",
        "used_in": "icp_wifi_extract.py::RE_MAX_DRIFT_RATE",
        "example": "Max drift rate : 400 kHz/50",
        "builtin": True,
    },
    "icp_bt_freq_deviation": {
        "id": "icp_bt_freq_deviation",
        "name": "BT Frequency Deviation df2",
        "description": "Extrait la déviation de fréquence Bluetooth df2 (kHz).",
        "pattern": r"frequency\s*deviation\s*df2.*?([\-\u2013\u2014]?\d+)",
        "flags": ["IGNORECASE", "DOTALL"],
        "groups": ["deviation_khz"],
        "scope": "icp_rf",
        "used_in": "icp_wifi_extract.py::RE_DF2",
        "example": "Frequency Deviation df2 : -40 kHz",
        "builtin": True,
    },
}

DEFAULT_CONFIG: Dict[str, Any] = {
    "version": "2.0",
    "products": {},
    "modules": DEFAULT_MODULES,
    "parsers": DEFAULT_PARSERS,
    "extractors": DEFAULT_EXTRACTORS,
    "test_rules": DEFAULT_TEST_RULES,
    "regexes": DEFAULT_REGEXES,
}

# ─────────────────────────────────────────────────────────────
#  LOAD / SAVE
# ─────────────────────────────────────────────────────────────

def load_config() -> Dict[str, Any]:
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            # Merge defaults (keep user additions)
            cfg = copy.deepcopy(DEFAULT_CONFIG)
            for section in ("modules", "parsers", "extractors", "test_rules", "regexes", "products"):
                cfg[section].update(data.get(section, {}))
            return cfg
        except Exception:
            pass
    return copy.deepcopy(DEFAULT_CONFIG)


def save_config(cfg: Dict[str, Any]) -> None:
    CONFIG_FILE.write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


# ─────────────────────────────────────────────────────────────
#  PRODUCTS CRUD
# ─────────────────────────────────────────────────────────────

def list_products(cfg) -> List[Dict]:
    return list(cfg["products"].values())

def get_product(cfg, pid: str) -> Optional[Dict]:
    return cfg["products"].get(pid)

def create_product(cfg, name: str, version: str, operator: str,
                   module_ids: List[str],
                   parser_map: Dict[str, str],
                   extractor_map: Dict[str, str],
                   test_rule_map: Dict[str, str],
                   notes: str = "") -> Dict:
    pid = f"prod_{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    product = {
        "id": pid,
        "name": name,
        "version": version,
        "operator": operator,
        "modules": module_ids,
        "parser_map": parser_map,       # {module_id: parser_id}
        "extractor_map": extractor_map, # {module_id: extractor_id}
        "test_rule_map": test_rule_map, # {module_id: test_rule_id}
        "notes": notes,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    cfg["products"][pid] = product
    save_config(cfg)
    return product

def update_product(cfg, pid: str, **kwargs) -> Optional[Dict]:
    if pid not in cfg["products"]:
        return None
    cfg["products"][pid].update(kwargs)
    cfg["products"][pid]["updated_at"] = datetime.now().isoformat()
    save_config(cfg)
    return cfg["products"][pid]

def delete_product(cfg, pid: str) -> bool:
    if pid in cfg["products"]:
        del cfg["products"][pid]
        save_config(cfg)
        return True
    return False


# ─────────────────────────────────────────────────────────────
#  MODULES CRUD
# ─────────────────────────────────────────────────────────────

def list_modules(cfg) -> List[Dict]:
    return list(cfg["modules"].values())

def create_module(cfg, mid: str, name: str, icon: str, description: str,
                  color: str = "#64748b",
                  default_parser: str = "",
                  default_extractor: str = "",
                  default_test_rule: str = "") -> Dict:
    module = {
        "id": mid,
        "name": name,
        "icon": icon,
        "description": description,
        "color": color,
        "default_parser": default_parser,
        "default_extractor": default_extractor,
        "default_test_rule": default_test_rule,
        "builtin": False,
    }
    cfg["modules"][mid] = module
    save_config(cfg)
    return module

def update_module(cfg, mid: str, **kwargs) -> Optional[Dict]:
    if mid not in cfg["modules"]:
        return None
    cfg["modules"][mid].update(kwargs)
    save_config(cfg)
    return cfg["modules"][mid]

def delete_module(cfg, mid: str) -> bool:
    if mid in cfg["modules"] and not cfg["modules"][mid].get("builtin"):
        del cfg["modules"][mid]
        save_config(cfg)
        return True
    return False


# ─────────────────────────────────────────────────────────────
#  PARSERS CRUD
# ─────────────────────────────────────────────────────────────

def list_parsers(cfg) -> List[Dict]:
    return list(cfg["parsers"].values())

def create_parser(cfg, pid: str, name: str, description: str,
                  module_file: str, function: str,
                  compatible_modules: List[str],
                  detection_patterns: List[str]) -> Dict:
    parser = {
        "id": pid,
        "name": name,
        "description": description,
        "module_file": module_file,
        "function": function,
        "compatible_modules": compatible_modules,
        "detection_patterns": detection_patterns,
        "builtin": False,
    }
    cfg["parsers"][pid] = parser
    save_config(cfg)
    return parser

def update_parser(cfg, pid: str, **kwargs) -> Optional[Dict]:
    if pid not in cfg["parsers"]:
        return None
    cfg["parsers"][pid].update(kwargs)
    save_config(cfg)
    return cfg["parsers"][pid]

def delete_parser(cfg, pid: str) -> bool:
    if pid in cfg["parsers"] and not cfg["parsers"][pid].get("builtin"):
        del cfg["parsers"][pid]
        save_config(cfg)
        return True
    return False


# ─────────────────────────────────────────────────────────────
#  EXTRACTORS CRUD
# ─────────────────────────────────────────────────────────────

def list_extractors(cfg) -> List[Dict]:
    return list(cfg["extractors"].values())

def create_extractor(cfg, eid: str, name: str, description: str,
                     module_file: str, function: str,
                     compatible_modules: List[str],
                     pdf_markers: List[str]) -> Dict:
    extractor = {
        "id": eid,
        "name": name,
        "description": description,
        "module_file": module_file,
        "function": function,
        "compatible_modules": compatible_modules,
        "pdf_markers": pdf_markers,
        "builtin": False,
    }
    cfg["extractors"][eid] = extractor
    save_config(cfg)
    return extractor

def update_extractor(cfg, eid: str, **kwargs) -> Optional[Dict]:
    if eid not in cfg["extractors"]:
        return None
    cfg["extractors"][eid].update(kwargs)
    save_config(cfg)
    return cfg["extractors"][eid]

def delete_extractor(cfg, eid: str) -> bool:
    if eid in cfg["extractors"] and not cfg["extractors"][eid].get("builtin"):
        del cfg["extractors"][eid]
        save_config(cfg)
        return True
    return False


# ─────────────────────────────────────────────────────────────
#  TEST RULES CRUD
# ─────────────────────────────────────────────────────────────

def list_test_rules(cfg) -> List[Dict]:
    return list(cfg["test_rules"].values())

def create_test_rule(cfg, rid: str, name: str, description: str,
                     compatible_modules: List[str],
                     settings: Dict) -> Dict:
    rule = {
        "id": rid,
        "name": name,
        "description": description,
        "compatible_modules": compatible_modules,
        "settings": settings,
        "builtin": False,
    }
    cfg["test_rules"][rid] = rule
    save_config(cfg)
    return rule

def update_test_rule(cfg, rid: str, **kwargs) -> Optional[Dict]:
    if rid not in cfg["test_rules"]:
        return None
    cfg["test_rules"][rid].update(kwargs)
    save_config(cfg)
    return cfg["test_rules"][rid]

def delete_test_rule(cfg, rid: str) -> bool:
    if rid in cfg["test_rules"] and not cfg["test_rules"][rid].get("builtin"):
        del cfg["test_rules"][rid]
        save_config(cfg)
        return True
    return False


# ─────────────────────────────────────────────────────────────
#  SUGGESTION ENGINE
# ─────────────────────────────────────────────────────────────

def suggest_parser_for_log(log_text: str, cfg: Dict,
                           filename: str = "") -> List[Dict]:
    """
    Suggère les parsers compatibles pour un log donné.

    Stratégie en deux passes :
    1. Détection par nom de fichier (primaire — fiable à 100%)
    2. Détection par contenu (fallback si filename non reconnu)
    """
    # ── Passe 1 : nom de fichier ──────────────────────────────
    if filename:
        hit = suggest_by_filename(filename, cfg)
        if hit:
            # Retourner sous forme de liste compatible avec l'API existante
            return [{
                "parser": hit["parser"],
                "score":  hit["score"],
                "matched": hit["matched"],
                "total":   hit["total"],
                "method":  "filename",
            }]

    # ── Passe 2 : patterns dans le contenu ────────────────────
    # Utilise les 8000 premiers caractères pour une meilleure couverture
    sample = log_text[:8000].upper()
    scored = []
    for p in cfg["parsers"].values():
        patterns = p.get("detection_patterns", [])
        hits = sum(1 for pat in patterns if pat.upper() in sample)
        if hits > 0:
            scored.append({
                "parser":  p,
                "score":   hits,
                "matched": hits,
                "total":   len(patterns),
                "method":  "content",
            })
    scored.sort(key=lambda x: -x["score"])
    return scored


def suggest_extractor_for_pdf(pdf_text: str, cfg: Dict) -> List[Dict]:
    """
    Analyse le texte d'un PDF ICP et suggère les extractors compatibles
    en fonction des marqueurs PDF définis.
    """
    sample = pdf_text[:8000].upper()
    scored = []
    for e in cfg["extractors"].values():
        markers = e.get("pdf_markers", [])
        hits = sum(1 for m in markers if m.upper() in sample)
        if hits > 0:
            scored.append({"extractor": e, "score": hits, "matched": hits, "total": len(markers)})
    scored.sort(key=lambda x: -x["score"])
    return scored


# Modules qui ne nécessitent pas d'extractor ICP ni de règle numérique
LOG_ONLY_MODULES = {"BoardLevel", "System", "FW_Upgrade", "FT"}

def validate_product_config(product: Dict, cfg: Dict) -> List[Dict]:
    """
    Valide la cohérence de la configuration d'un produit.
    Retourne une liste d'avertissements/erreurs.
    """
    issues = []

    for mod_id in product.get("modules", []):
        if mod_id not in cfg["modules"]:
            issues.append({"level": "error",  "msg": f"Module '{mod_id}' introuvable dans le catalogue."})
            continue

        is_log_only = mod_id in LOG_ONLY_MODULES
        parser_id    = product.get("parser_map",    {}).get(mod_id)
        extractor_id = product.get("extractor_map", {}).get(mod_id)
        rule_id      = product.get("test_rule_map", {}).get(mod_id)

        # Parser : toujours requis
        if not parser_id:
            issues.append({"level": "warning", "msg": f"Module '{mod_id}' : aucun parser sélectionné."})
        elif parser_id not in cfg["parsers"]:
            issues.append({"level": "error",   "msg": f"Module '{mod_id}' : parser '{parser_id}' introuvable."})
        else:
            p = cfg["parsers"][parser_id]
            if mod_id not in p.get("compatible_modules", []):
                issues.append({"level": "warning", "msg": f"Module '{mod_id}' : parser '{p['name']}' n'est pas marqué compatible avec ce module."})

        # Extractor : seulement requis pour modules avec ICP PDF
        if not is_log_only:
            if not extractor_id:
                issues.append({"level": "warning", "msg": f"Module '{mod_id}' : aucun extractor ICP sélectionné."})
            elif extractor_id not in cfg["extractors"]:
                issues.append({"level": "error",   "msg": f"Module '{mod_id}' : extractor '{extractor_id}' introuvable."})
        else:
            if extractor_id and extractor_id not in ("", "extract_none") and extractor_id not in cfg["extractors"]:
                issues.append({"level": "error", "msg": f"Module '{mod_id}' : extractor '{extractor_id}' introuvable."})

        # Règle : seulement requise pour modules avec limites numériques
        if not is_log_only:
            if not rule_id:
                issues.append({"level": "warning", "msg": f"Module '{mod_id}' : aucune règle de test sélectionnée."})
            elif rule_id not in cfg["test_rules"]:
                issues.append({"level": "error",   "msg": f"Module '{mod_id}' : règle '{rule_id}' introuvable."})

    return issues


# ─────────────────────────────────────────────────────────────
#  REGEX EXPRESSIONS CRUD
# ─────────────────────────────────────────────────────────────

REGEX_SCOPES = {
    "fe_log":  "📺 FE Log Parser",
    "rf_log":  "📶 RF Log Parser",
    "icp_fe":  "📄 ICP FE Extractor",
    "icp_rf":  "📡 ICP RF/BT Extractor",
    "custom":  "🔧 Custom / Autre",
}

REGEX_FLAGS_AVAILABLE = ["IGNORECASE", "MULTILINE", "DOTALL", "VERBOSE"]

# ─────────────────────────────────────────────────────────────
#  FILENAME-BASED DETECTION (primary — most reliable)
# ─────────────────────────────────────────────────────────────

import re as _re_mod

# Ordered list of (regex_pattern, parser_id, module_ids)
# Applied to the filename ONLY — no content needed
FILENAME_RULES = [
    # RF log — "1+RF-" prefix
    (_re_mod.compile(r"^\d+\+RF[-_]", _re_mod.IGNORECASE),
     "parse_rf_v15", ["RF_WiFi", "RF_BT"]),
    # BoardLevel log
    (_re_mod.compile(r"^\d+\+BoardLevel[-_]", _re_mod.IGNORECASE),
     "parse_boardlevel_v1", ["BoardLevel"]),
    # System log (various casings: System, SYSTEM)
    (_re_mod.compile(r"^\d+\+SYSTEM[-_]", _re_mod.IGNORECASE),
     "parse_system_v1", ["System"]),
    # FW_Upgrade log
    (_re_mod.compile(r"^\d+\+FW[_-]Upgrade[-_]", _re_mod.IGNORECASE),
     "parse_fwfinal_v1", ["FW_Upgrade"]),
    # Final log — mapped to FT module (functional tests)
    (_re_mod.compile(r"^\d+\+Final[-_]", _re_mod.IGNORECASE),
     "parse_ft_v1", ["FT"]),
    # FE log (rare, legacy)
    (_re_mod.compile(r"^\d+\+FE[-_]", _re_mod.IGNORECASE),
     "parse_fe_v2", ["FE"]),
]


def suggest_by_filename(filename: str, cfg: Dict) -> Optional[Dict]:
    """
    Détermine le parser et le module depuis le nom du fichier.
    Méthode primaire — fiable à 100% pour les logs Sagemcom standard.

    Retourne None si le nom ne correspond à aucun pattern connu.
    """
    fname = _re_mod.sub(r".*[\\/]", "", filename)  # basename only

    for pattern, parser_id, module_ids in FILENAME_RULES:
        if pattern.search(fname):
            parser = cfg.get("parsers", {}).get(parser_id)
            if not parser:
                continue
            # Pick the first module_id that exists in the catalogue
            matched_module = None
            for mid in module_ids:
                if mid in cfg.get("modules", {}):
                    matched_module = mid
                    break
            if matched_module:
                return {
                    "parser":   parser,
                    "module":   matched_module,
                    "method":   "filename",
                    "pattern":  pattern.pattern,
                    "score":    100,
                    "matched":  1,
                    "total":    1,
                }
    return None

def list_regexes(cfg) -> List[Dict]:
    return list(cfg.get("regexes", {}).values())

def list_regexes_by_scope(cfg, scope: str) -> List[Dict]:
    return [r for r in cfg.get("regexes", {}).values() if r.get("scope") == scope]

def get_regex(cfg, rid: str) -> Optional[Dict]:
    return cfg.get("regexes", {}).get(rid)

def create_regex(cfg, rid: str, name: str, description: str,
                 pattern: str, flags: List[str],
                 groups: List[str], scope: str,
                 used_in: str = "", example: str = "") -> Dict:
    """Crée une nouvelle expression régulière dans le catalogue."""
    import re as _re
    # Validate pattern compiles
    flag_int = _build_flag_int(flags)
    _re.compile(pattern, flag_int)   # lève re.error si invalide

    regex = {
        "id": rid,
        "name": name,
        "description": description,
        "pattern": pattern,
        "flags": flags,
        "groups": groups,
        "scope": scope,
        "used_in": used_in,
        "example": example,
        "builtin": False,
    }
    if "regexes" not in cfg:
        cfg["regexes"] = {}
    cfg["regexes"][rid] = regex
    save_config(cfg)
    return regex

def update_regex(cfg, rid: str, **kwargs) -> Optional[Dict]:
    """Met à jour une regex existante (builtin ou custom)."""
    import re as _re
    if rid not in cfg.get("regexes", {}):
        return None
    if "pattern" in kwargs or "flags" in kwargs:
        pat = kwargs.get("pattern", cfg["regexes"][rid]["pattern"])
        flags = kwargs.get("flags", cfg["regexes"][rid]["flags"])
        _re.compile(pat, _build_flag_int(flags))   # validation
    cfg["regexes"][rid].update(kwargs)
    save_config(cfg)
    return cfg["regexes"][rid]

def delete_regex(cfg, rid: str) -> bool:
    """Supprime une regex. Les regex builtin ne peuvent pas être supprimées."""
    if rid in cfg.get("regexes", {}) and not cfg["regexes"][rid].get("builtin"):
        del cfg["regexes"][rid]
        save_config(cfg)
        return True
    return False

def test_regex(pattern: str, flags: List[str], text: str) -> Dict:
    """
    Teste une expression régulière sur un texte exemple.
    Retourne : {"ok": bool, "matches": [...], "error": str|None}
    """
    import re as _re
    try:
        flag_int = _build_flag_int(flags)
        compiled = _re.compile(pattern, flag_int)
        matches = []
        for m in compiled.finditer(text):
            matches.append({
                "full": m.group(0),
                "groups": list(m.groups()),
                "span": list(m.span()),
                "groupdict": m.groupdict(),
            })
        return {"ok": True, "matches": matches, "error": None,
                "match_count": len(matches)}
    except Exception as e:
        return {"ok": False, "matches": [], "error": str(e), "match_count": 0}

def _build_flag_int(flags: List[str]) -> int:
    import re as _re
    flag_map = {
        "IGNORECASE": _re.IGNORECASE,
        "MULTILINE":  _re.MULTILINE,
        "DOTALL":     _re.DOTALL,
        "VERBOSE":    _re.VERBOSE,
    }
    result = 0
    for f in flags:
        result |= flag_map.get(f, 0)
    return result

def export_regexes_as_python(cfg) -> str:
    """Génère un bloc Python prêt à coller dans un script parser/extractor."""
    lines = ["import re", "", "# ── Expressions régulières exportées depuis le Config Store ──", ""]
    for rx in sorted(cfg.get("regexes", {}).values(), key=lambda x: x.get("scope","") + x["id"]):
        scope_label = REGEX_SCOPES.get(rx.get("scope","custom"), "Custom")
        flag_str = " | ".join(f"re.{f}" for f in rx.get("flags", []))
        compile_args = f'r"{rx["pattern"]}"' + (f", {flag_str}" if flag_str else "")
        var_name = rx["id"].upper()
        lines.append(f"# {scope_label} — {rx['name']}")
        if rx.get("description"):
            lines.append(f"# {rx['description']}")
        if rx.get("example"):
            lines.append(f"# Exemple : {rx['example']}")
        lines.append(f"{var_name} = re.compile({compile_args})")
        if rx.get("groups"):
            lines.append(f"# Groupes : {', '.join(rx['groups'])}")
        lines.append("")
    return "\n".join(lines)
