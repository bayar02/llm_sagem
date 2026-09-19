#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Données de démonstration pour la Telecom Validation Platform.
Permet de tester l'application sans fichiers réels.
"""

DEMO_PRODUCT = "DCIW378-DEMO"
DEMO_VERSION = "HW_Rev_B · SW_v3.2.1"
DEMO_OPERATOR = "EST Telecom"

# ── Limites ICP FE (DVB-C / DVB-S/S2 / DVB-T/T2) ──
DEMO_FE_LIMITS = [
    {
        "Test": "Test#1",
        "Frequency": "498MHz",
        "Modulation": "256QAM DVB-C",
        "Limits": [
            {"Parameter": "Viterbi BER",            "Min": "0",   "Max": "100",  "Unit": ".10-7"},
            {"Parameter": "Uncorrected blocks",      "Min": "0",   "Max": "5",    "Unit": "none"},
            {"Parameter": "RSSI",                    "Min": "-65", "Max": "-35",  "Unit": "dBm"},
            {"Parameter": "Carrier-to-Noise Ratio",  "Min": "28",  "Max": "50",   "Unit": "dB"},
            {"Parameter": "Frequency Offset",        "Min": "-100","Max": "100",  "Unit": "kHz"},
            {"Parameter": "Rate Offset",             "Min": "-200","Max": "200",  "Unit": "ppm"},
        ]
    },
    {
        "Test": "Test#2",
        "Frequency": "754MHz",
        "Modulation": "256QAM DVB-C",
        "Limits": [
            {"Parameter": "Viterbi BER",            "Min": "0",   "Max": "100",  "Unit": ".10-7"},
            {"Parameter": "Uncorrected blocks",      "Min": "0",   "Max": "5",    "Unit": "none"},
            {"Parameter": "RSSI",                    "Min": "-65", "Max": "-35",  "Unit": "dBm"},
            {"Parameter": "Carrier-to-Noise Ratio",  "Min": "28",  "Max": "50",   "Unit": "dB"},
            {"Parameter": "Frequency Offset",        "Min": "-100","Max": "100",  "Unit": "kHz"},
            {"Parameter": "Rate Offset",             "Min": "-200","Max": "200",  "Unit": "ppm"},
        ]
    },
    {
        "Test": "Test#3",
        "Frequency": "1474MHz",
        "Modulation": "QPSK DVB-S",
        "Limits": [
            {"Parameter": "Viterbi BER",            "Min": "0",   "Max": "200",  "Unit": ".10-7"},
            {"Parameter": "Uncorrected blocks",      "Min": "0",   "Max": "10",   "Unit": "none"},
            {"Parameter": "RSSI",                    "Min": "-75", "Max": "-30",  "Unit": "dBm"},
            {"Parameter": "Carrier-to-Noise Ratio",  "Min": "5",   "Max": "25",   "Unit": "dB"},
            {"Parameter": "Frequency Offset",        "Min": "-500","Max": "500",  "Unit": "kHz"},
            {"Parameter": "Rate Offset",             "Min": "-300","Max": "300",  "Unit": "ppm"},
        ]
    },
    {
        "Test": "Test#4",
        "Frequency": "1858MHz",
        "Modulation": "8PSK DVB-S2",
        "Limits": [
            {"Parameter": "Viterbi BER",            "Min": "0",   "Max": "50",   "Unit": ".10-7"},
            {"Parameter": "Uncorrected blocks",      "Min": "0",   "Max": "3",    "Unit": "none"},
            {"Parameter": "RSSI",                    "Min": "-75", "Max": "-30",  "Unit": "dBm"},
            {"Parameter": "Carrier-to-Noise Ratio",  "Min": "9",   "Max": "30",   "Unit": "dB"},
            {"Parameter": "Frequency Offset",        "Min": "-500","Max": "500",  "Unit": "kHz"},
            {"Parameter": "Rate Offset",             "Min": "-300","Max": "300",  "Unit": "ppm"},
        ]
    },
    {
        "Test": "Test#5",
        "Frequency": "474MHz",
        "Modulation": "8MHz DVB-T2",
        "Limits": [
            {"Parameter": "Viterbi BER",            "Min": "0",   "Max": "100",  "Unit": ".10-7"},
            {"Parameter": "Uncorrected blocks",      "Min": "0",   "Max": "0",    "Unit": "none"},
            {"Parameter": "RSSI",                    "Min": "-80", "Max": "-30",  "Unit": "dBm"},
            {"Parameter": "Carrier-to-Noise Ratio",  "Min": "15",  "Max": "40",   "Unit": "dB"},
            {"Parameter": "Frequency Offset",        "Min": "-500","Max": "500",  "Unit": "kHz"},
            {"Parameter": "Rate Offset",             "Min": "-300","Max": "300",  "Unit": "ppm"},
        ]
    },
]

# ── Limites ICP RF (Wi-Fi + BT) ──
DEMO_RF_LIMITS = {
    "2.4GHz": [
        {
            "EntryKind": "TX: MCS7 HT20",
            "Frequency": 2412,
            "Modulation": "MCS7 HT20",
            "Mandatory": True,
            "Power Target": 17.0,
            "Power Min": 14.0,
            "Power Max": 20.0,
            "EVM Max": -28.0,
            "Frequency Tolerance Min": -25.0,
            "Frequency Tolerance Max": 25.0,
        },
        {
            "EntryKind": "TX: MCS7 HT20",
            "Frequency": 2437,
            "Modulation": "MCS7 HT20",
            "Mandatory": True,
            "Power Target": 17.0,
            "Power Min": 14.0,
            "Power Max": 20.0,
            "EVM Max": -28.0,
            "Frequency Tolerance Min": -25.0,
            "Frequency Tolerance Max": 25.0,
        },
        {
            "EntryKind": "RX PER: MCS7 HT20",
            "Frequency": 2412,
            "Modulation": "MCS7 HT20",
            "Mandatory": True,
            "PER Max (%)": 10.0,
        },
    ],
    "5GHz": [
        {
            "EntryKind": "TX: MCS7 vHT80",
            "Frequency": 5180,
            "Modulation": "MCS7 vHT80",
            "Mandatory": True,
            "Power Target": 15.0,
            "Power Min": 12.0,
            "Power Max": 18.0,
            "EVM Max": -28.0,
            "Frequency Tolerance Min": -25.0,
            "Frequency Tolerance Max": 25.0,
        },
        {
            "EntryKind": "TX: MCS7 vHT80",
            "Frequency": 5500,
            "Modulation": "MCS7 vHT80",
            "Mandatory": True,
            "Power Target": 15.0,
            "Power Min": 12.0,
            "Power Max": 18.0,
            "EVM Max": -28.0,
            "Frequency Tolerance Min": -25.0,
            "Frequency Tolerance Max": 25.0,
        },
    ],
    "Bluetooth": [
        {
            "EntryKind": "TX: BR GFSK",
            "Frequency": 2402,
            "Modulation": "GFSK",
            "Mandatory": True,
            "Power Min": -6.0,
            "Power Max": 4.0,
            "BT Frequency Drift Min (kHz)": -25.0,
            "BT Frequency Drift Max (kHz)": 25.0,
        },
    ]
}

# ── Rapport FE simulé (résultat de validation log) ──
DEMO_FE_REPORT = {
    "Summary": {
        "Tests": 5, "CheckedParams": 28, "Pass": 24,
        "Fail": 2, "MissingTests": 0, "MissingParams": 2, "MissingInLog": 2
    },
    "Tests": [
        {
            "Frequency": 498, "Modulation": "256QAM DVB-C",
            "Parameters": [
                {"Name": "Viterbi BER",           "Value": 12.0,  "Limits": {"Min": 0.0,    "Max": 100.0}, "Pass": True},
                {"Name": "Uncorrected blocks",     "Value": 0.0,   "Limits": {"Min": 0.0,    "Max": 5.0},   "Pass": True},
                {"Name": "RSSI",                   "Value": -50.0, "Limits": {"Min": -65.0,  "Max": -35.0}, "Pass": True},
                {"Name": "Carrier-to-Noise Ratio", "Value": 35.0,  "Limits": {"Min": 28.0,   "Max": 50.0},  "Pass": True},
                {"Name": "Frequency Offset",       "Value": -45.0, "Limits": {"Min": -100.0, "Max": 100.0}, "Pass": True},
                {"Name": "Rate Offset",            "Value": 88.0,  "Limits": {"Min": -200.0, "Max": 200.0}, "Pass": True},
            ]
        },
        {
            "Frequency": 754, "Modulation": "256QAM DVB-C",
            "Parameters": [
                {"Name": "Viterbi BER",           "Value": 45.0,  "Limits": {"Min": 0.0,    "Max": 100.0}, "Pass": True},
                {"Name": "Uncorrected blocks",     "Value": 0.0,   "Limits": {"Min": 0.0,    "Max": 5.0},   "Pass": True},
                {"Name": "RSSI",                   "Value": -48.0, "Limits": {"Min": -65.0,  "Max": -35.0}, "Pass": True},
                {"Name": "Carrier-to-Noise Ratio", "Value": 34.0,  "Limits": {"Min": 28.0,   "Max": 50.0},  "Pass": True},
                {"Name": "Frequency Offset",       "Value": 12.0,  "Limits": {"Min": -100.0, "Max": 100.0}, "Pass": True},
                {"Name": "Rate Offset",            "Value": -65.0, "Limits": {"Min": -200.0, "Max": 200.0}, "Pass": True},
            ]
        },
        {
            "Frequency": 1474, "Modulation": "QPSK DVB-S",
            "Parameters": [
                {"Name": "Viterbi BER",           "Value": 155.0, "Limits": {"Min": 0.0,    "Max": 200.0}, "Pass": True},
                {"Name": "Uncorrected blocks",     "Value": 0.0,   "Limits": {"Min": 0.0,    "Max": 10.0},  "Pass": True},
                {"Name": "RSSI",                   "Value": -55.0, "Limits": {"Min": -75.0,  "Max": -30.0}, "Pass": True},
                {"Name": "Carrier-to-Noise Ratio", "Value": 14.0,  "Limits": {"Min": 5.0,    "Max": 25.0},  "Pass": True},
                {"Name": "Frequency Offset",       "Value": 210.0, "Limits": {"Min": -500.0, "Max": 500.0}, "Pass": True},
            ]
        },
        {
            "Frequency": 1858, "Modulation": "8PSK DVB-S2",
            "Parameters": [
                {"Name": "Viterbi BER",           "Value": 8.0,   "Limits": {"Min": 0.0,    "Max": 50.0},  "Pass": True},
                {"Name": "Uncorrected blocks",     "Value": 6.0,   "Limits": {"Min": 0.0,    "Max": 3.0},   "Pass": False},  # FAIL
                {"Name": "RSSI",                   "Value": -52.0, "Limits": {"Min": -75.0,  "Max": -30.0}, "Pass": True},
                {"Name": "Carrier-to-Noise Ratio", "Value": 18.0,  "Limits": {"Min": 9.0,    "Max": 30.0},  "Pass": True},
                {"Name": "Frequency Offset",       "Value": -88.0, "Limits": {"Min": -500.0, "Max": 500.0}, "Pass": True},
                {"Name": "Rate Offset",            "Value": -45.0, "Limits": {"Min": -300.0, "Max": 300.0}, "Pass": True},
            ]
        },
        {
            "Frequency": 474, "Modulation": "8MHz DVB-T2",
            "Parameters": [
                {"Name": "Viterbi BER",           "Value": 0.0,   "Limits": {"Min": 0.0,    "Max": 100.0}, "Pass": True},
                {"Name": "Uncorrected blocks",     "Value": 0.0,   "Limits": {"Min": 0.0,    "Max": 0.0},   "Pass": True},
                {"Name": "RSSI",                   "Value": -28.0, "Limits": {"Min": -80.0,  "Max": -30.0}, "Pass": False},  # FAIL
                {"Name": "Carrier-to-Noise Ratio", "Value": 28.0,  "Limits": {"Min": 15.0,   "Max": 40.0},  "Pass": True},
                {"Name": "Frequency Offset",       "Value": -32.0, "Limits": {"Min": -500.0, "Max": 500.0}, "Pass": True},
            ]
        },
    ],
    "MissingDetails": {
        "MissingTests": [],
        "MissingParams": [
            {"Frequency": "1474MHz", "Modulation": "QPSK DVB-S", "Parameter": "Rate Offset",  "Reason": "Missing parameter in log"},
            {"Frequency": "474MHz",  "Modulation": "8MHz DVB-T2", "Parameter": "Rate Offset", "Reason": "Missing parameter in log"},
        ]
    }
}

# ── Rapport RF simulé ──
DEMO_RF_REPORT = {
    "Summary": {
        "Tests": 5, "CheckedParams": 12,
        "PassVsJSON_Count": 11, "JSON_Fails_Count": 1,
        "LimitsMismatch_Count": 0, "MissingInLog_Count": 1,
        "IgnoredTests_Count": 0, "OptMode": False
    },
    "Tests": [
        {
            "TestHeader": "TEST_VERIFY EVM MASK POWER SPECTRUM 2412 MCS7 HT20 ANT1",
            "Dir": "TX", "Frequency": 2412, "ModulationHeader": "MCS7 HT20", "Antenna": "ANT1",
            "JSON": {"Band": "2.4GHz", "EntryKind": "TX: MCS7 HT20", "Modulation": "MCS7 HT20", "Mandatory": True},
            "Parameters": [
                {"Name": "POWER_AVG_DBM", "Value": 16.8, "Unit": "dBm",
                 "LogLimits": {"min": 14.0, "max": 20.0}, "JSONLimits": {"min": 14.0, "max": 20.0},
                 "LimitsMatch": {"min": "OK", "max": "OK"}, "PassVsJSON": True, "Antenna": "ANT1"},
                {"Name": "EVM_DB_AVG_S1", "Value": -31.2, "Unit": "dB",
                 "LogLimits": {"min": None, "max": -28.0}, "JSONLimits": {"min": None, "max": -28.0},
                 "LimitsMatch": {"min": None, "max": "OK"}, "PassVsJSON": True, "Antenna": "ANT1"},
            ]
        },
        {
            "TestHeader": "TEST_VERIFY EVM MASK POWER SPECTRUM 2412 MCS7 HT20 ANT2",
            "Dir": "TX", "Frequency": 2412, "ModulationHeader": "MCS7 HT20", "Antenna": "ANT2",
            "JSON": {"Band": "2.4GHz", "EntryKind": "TX: MCS7 HT20", "Modulation": "MCS7 HT20", "Mandatory": True},
            "Parameters": [
                {"Name": "POWER_AVG_DBM", "Value": 15.9, "Unit": "dBm",
                 "LogLimits": {"min": 14.0, "max": 20.0}, "JSONLimits": {"min": 14.0, "max": 20.0},
                 "LimitsMatch": {"min": "OK", "max": "OK"}, "PassVsJSON": True, "Antenna": "ANT2"},
                {"Name": "EVM_DB_AVG_S1", "Value": -29.8, "Unit": "dB",
                 "LogLimits": {"min": None, "max": -28.0}, "JSONLimits": {"min": None, "max": -28.0},
                 "LimitsMatch": {"min": None, "max": "OK"}, "PassVsJSON": True, "Antenna": "ANT2"},
            ]
        },
        {
            "TestHeader": "TEST_VERIFY EVM MASK POWER SPECTRUM 5180 MCS7 vHT80 ANT1",
            "Dir": "TX", "Frequency": 5180, "ModulationHeader": "MCS7 vHT80", "Antenna": "ANT1",
            "JSON": {"Band": "5GHz", "EntryKind": "TX: MCS7 vHT80", "Modulation": "MCS7 vHT80", "Mandatory": True},
            "Parameters": [
                {"Name": "POWER_AVG_DBM", "Value": 10.2, "Unit": "dBm",
                 "LogLimits": {"min": 12.0, "max": 18.0}, "JSONLimits": {"min": 12.0, "max": 18.0},
                 "LimitsMatch": {"min": "OK", "max": "OK"}, "PassVsJSON": False, "Antenna": "ANT1"},  # FAIL
                {"Name": "EVM_DB_AVG_S1", "Value": -30.5, "Unit": "dB",
                 "LogLimits": {"min": None, "max": -28.0}, "JSONLimits": {"min": None, "max": -28.0},
                 "LimitsMatch": {"min": None, "max": "OK"}, "PassVsJSON": True, "Antenna": "ANT1"},
            ]
        },
    ],
    "MissingInLog": [
        {"Band": "5GHz", "EntryKind": "TX: MCS7 vHT80", "Frequency": 5500,
         "Modulation": "MCS7 vHT80", "Mandatory": True, "Reason": "missing ANT1 & ANT2"}
    ],
    "MismatchDetails": [],
    "JSONFailDetails": []
}

# ── Rapport MTP simulé ──
DEMO_MTP_REPORT = {
    "_source_file": "MTP_DCIW378_DEMO.pdf",
    "device_info": {
        "product": "DCIW378-DEMO",
        "version": "HW_Rev_B",
        "date": "2025-11-15",
        "operator": "EST Telecom"
    },
    "FE_Results": [
        {
            "Frequency": "498MHz",
            "Modulation": "256QAM DVB-C",
            "Results": [
                {"Parameter": "Viterbi BER",           "Value": "15",   "Unit": ".10-7", "Status": "PASS"},
                {"Parameter": "Uncorrected blocks",     "Value": "0",    "Unit": "none",  "Status": "PASS"},
                {"Parameter": "RSSI",                   "Value": "-51",  "Unit": "dBm",   "Status": "PASS"},
                {"Parameter": "Carrier-to-Noise Ratio", "Value": "34.5", "Unit": "dB",    "Status": "PASS"},
                {"Parameter": "Frequency Offset",       "Value": "-42",  "Unit": "kHz",   "Status": "PASS"},
                {"Parameter": "Rate Offset",            "Value": "92",   "Unit": "ppm",   "Status": "PASS"},
            ]
        },
        {
            "Frequency": "754MHz",
            "Modulation": "256QAM DVB-C",
            "Results": [
                {"Parameter": "Viterbi BER",           "Value": "38",   "Unit": ".10-7", "Status": "PASS"},
                {"Parameter": "Uncorrected blocks",     "Value": "0",    "Unit": "none",  "Status": "PASS"},
                {"Parameter": "RSSI",                   "Value": "-49",  "Unit": "dBm",   "Status": "PASS"},
                {"Parameter": "Carrier-to-Noise Ratio", "Value": "33.8", "Unit": "dB",    "Status": "PASS"},
                {"Parameter": "Frequency Offset",       "Value": "18",   "Unit": "kHz",   "Status": "PASS"},
                {"Parameter": "Rate Offset",            "Value": "-70",  "Unit": "ppm",   "Status": "PASS"},
            ]
        },
        {
            "Frequency": "1474MHz",
            "Modulation": "QPSK DVB-S",
            "Results": [
                {"Parameter": "Viterbi BER",           "Value": "148",  "Unit": ".10-7", "Status": "PASS"},
                {"Parameter": "Uncorrected blocks",     "Value": "0",    "Unit": "none",  "Status": "PASS"},
                {"Parameter": "RSSI",                   "Value": "-56",  "Unit": "dBm",   "Status": "PASS"},
                {"Parameter": "Carrier-to-Noise Ratio", "Value": "13.8", "Unit": "dB",    "Status": "PASS"},
                {"Parameter": "Frequency Offset",       "Value": "215",  "Unit": "kHz",   "Status": "PASS"},
            ]
        },
        {
            "Frequency": "1858MHz",
            "Modulation": "8PSK DVB-S2",
            "Results": [
                {"Parameter": "Viterbi BER",           "Value": "9",    "Unit": ".10-7", "Status": "PASS"},
                {"Parameter": "Uncorrected blocks",     "Value": "7",    "Unit": "none",  "Status": "FAIL"},
                {"Parameter": "RSSI",                   "Value": "-54",  "Unit": "dBm",   "Status": "PASS"},
                {"Parameter": "Carrier-to-Noise Ratio", "Value": "17.5", "Unit": "dB",    "Status": "PASS"},
            ]
        },
        {
            "Frequency": "474MHz",
            "Modulation": "8MHz DVB-T2",
            "Results": [
                {"Parameter": "Viterbi BER",           "Value": "0",    "Unit": ".10-7", "Status": "PASS"},
                {"Parameter": "Uncorrected blocks",     "Value": "0",    "Unit": "none",  "Status": "PASS"},
                {"Parameter": "RSSI",                   "Value": "-27",  "Unit": "dBm",   "Status": "FAIL"},
                {"Parameter": "Carrier-to-Noise Ratio", "Value": "27.8", "Unit": "dB",    "Status": "PASS"},
            ]
        },
    ],
    "RF_Results": {"2.4GHz": [], "5GHz": [], "Bluetooth": []},
    "summary": {"total_tests": 28, "passed": 25, "failed": 3, "not_tested": 0}
}

# ── Rapport comparaison simulé ──
DEMO_COMPARISON = {
    "comparison_summary": {
        "total_icp_specs": 30,
        "total_mtp_results": 27,
        "matched": 5,
        "unmatched_icp": 0,
        "unmatched_mtp": 0,
        "compliant": 23,
        "non_compliant": 2,
        "not_tested": 3,
        "global_status": "PARTIAL"
    },
    "FE_Comparison": [
        {
            "Frequency": "498MHz", "Modulation": "256QAM DVB-C", "Status": "MATCHED",
            "Parameters": [
                {"Parameter": "Viterbi BER",           "ICP_Min": "0",   "ICP_Max": "100",  "MTP_Value": 15.0,  "Compliant": True,  "Delta": None, "Note": ""},
                {"Parameter": "Uncorrected blocks",     "ICP_Min": "0",   "ICP_Max": "5",    "MTP_Value": 0.0,   "Compliant": True,  "Delta": None, "Note": ""},
                {"Parameter": "RSSI",                   "ICP_Min": "-65", "ICP_Max": "-35",  "MTP_Value": -51.0, "Compliant": True,  "Delta": None, "Note": ""},
                {"Parameter": "Carrier-to-Noise Ratio", "ICP_Min": "28",  "ICP_Max": "50",   "MTP_Value": 34.5,  "Compliant": True,  "Delta": None, "Note": ""},
                {"Parameter": "Frequency Offset",       "ICP_Min": "-100","ICP_Max": "100",  "MTP_Value": -42.0, "Compliant": True,  "Delta": None, "Note": ""},
                {"Parameter": "Rate Offset",            "ICP_Min": "-200","ICP_Max": "200",  "MTP_Value": 92.0,  "Compliant": True,  "Delta": None, "Note": ""},
            ]
        },
        {
            "Frequency": "1858MHz", "Modulation": "8PSK DVB-S2", "Status": "MATCHED",
            "Parameters": [
                {"Parameter": "Viterbi BER",           "ICP_Min": "0",   "ICP_Max": "50",   "MTP_Value": 9.0,   "Compliant": True,  "Delta": None, "Note": ""},
                {"Parameter": "Uncorrected blocks",     "ICP_Min": "0",   "ICP_Max": "3",    "MTP_Value": 7.0,   "Compliant": False, "Delta": 4.0,  "Note": "Valeur MTP dépasse Max ICP"},
                {"Parameter": "RSSI",                   "ICP_Min": "-75", "ICP_Max": "-30",  "MTP_Value": -54.0, "Compliant": True,  "Delta": None, "Note": ""},
                {"Parameter": "Carrier-to-Noise Ratio", "ICP_Min": "9",   "ICP_Max": "30",   "MTP_Value": 17.5,  "Compliant": True,  "Delta": None, "Note": ""},
            ]
        },
        {
            "Frequency": "474MHz", "Modulation": "8MHz DVB-T2", "Status": "MATCHED",
            "Parameters": [
                {"Parameter": "Viterbi BER",           "ICP_Min": "0",   "ICP_Max": "100",  "MTP_Value": 0.0,   "Compliant": True,  "Delta": None, "Note": ""},
                {"Parameter": "Uncorrected blocks",     "ICP_Min": "0",   "ICP_Max": "0",    "MTP_Value": 0.0,   "Compliant": True,  "Delta": None, "Note": ""},
                {"Parameter": "RSSI",                   "ICP_Min": "-80", "ICP_Max": "-30",  "MTP_Value": -27.0, "Compliant": False, "Delta": 3.0,  "Note": "RSSI trop élevé (+3 dBm au-dessus du Max)"},
                {"Parameter": "Carrier-to-Noise Ratio", "ICP_Min": "15",  "ICP_Max": "40",   "MTP_Value": 27.8,  "Compliant": True,  "Delta": None, "Note": ""},
            ]
        },
    ],
    "RF_Comparison": {"2.4GHz": [], "5GHz": [], "Bluetooth": []},
    "anomalies": [
        {
            "type": "OUT_OF_SPEC", "severity": "CRITICAL",
            "description": "Uncorrected blocks = 7 dépasse la limite ICP Max=3",
            "frequency": "1858MHz", "modulation": "8PSK DVB-S2", "parameter": "Uncorrected blocks"
        },
        {
            "type": "OUT_OF_SPEC", "severity": "CRITICAL",
            "description": "RSSI = -27 dBm dépasse la limite ICP Max=-30 dBm (delta +3 dBm)",
            "frequency": "474MHz", "modulation": "8MHz DVB-T2", "parameter": "RSSI"
        },
        {
            "type": "MISSING_IN_MTP", "severity": "WARNING",
            "description": "Paramètre Rate Offset non mesuré dans le MTP pour DVB-S",
            "frequency": "1474MHz", "modulation": "QPSK DVB-S", "parameter": "Rate Offset"
        },
        {
            "type": "MISSING_IN_MTP", "severity": "WARNING",
            "description": "Tests RF 5GHz (5500 MHz) absents du rapport MTP",
            "frequency": "5500 MHz", "modulation": "MCS7 vHT80", "parameter": "Tous"
        },
    ],
    "recommendations": [
        "🔴 CRITIQUE : Investiguer l'anomalie sur les blocs non corrigés DVB-S2 1858 MHz — vérifier le niveau de signal RF et la qualité du câblage.",
        "🔴 CRITIQUE : Le RSSI DVB-T2 474 MHz est trop élevé (-27 dBm vs Max -30 dBm) — ajuster l'atténuateur ou la source de signal.",
        "🟡 Compléter les tests MTP avec le paramètre Rate Offset pour DVB-S 1474 MHz.",
        "🟡 Ajouter les tests Wi-Fi 5 GHz (5500 MHz) au plan MTP pour couvrir l'intégralité des spécifications ICP.",
        "ℹ️ Globalement 23/25 paramètres mesurés sont conformes (92%) — niveau de qualité acceptable, mais les 2 anomalies critiques doivent être résolues avant validation finale.",
    ],
    "analyst_notes": (
        "L'analyse IA révèle une bonne corrélation générale entre les spécifications ICP et les mesures MTP. "
        "Les deux non-conformités détectées (DVB-S2 blocs non corrigés et DVB-T2 RSSI) sont probablement liées "
        "à des conditions de test RF insuffisamment contrôlées plutôt qu'à des défauts produit. "
        "Une mesure de répétabilité (3 unités minimum) est recommandée avant décision de conformité finale."
    )
}
