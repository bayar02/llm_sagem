<<<<<<< HEAD
# llm_sagem
=======
# 📡 Telecom Validation Platform

Système automatisé de validation et d'analyse de tests pour équipements de télécommunication.

## Installation

```bash
pip install -r requirements.txt
```

## Lancement

```bash
streamlit run app.py
```

## Workflow en 7 étapes

### Partie 1 — ICP

| Étape | Action |
|-------|--------|
| 🔧 Config Produit | Nom, version, modules (FE / RF Wi-Fi / BT) + parsers / extractors / tests |
| 📄 Extraction ICP | Upload du PDF ICP → extraction automatique des limites FE + RF |
| 📋 Validation Logs | Upload des fichiers logs → comparaison log ↔ limites ICP |
| 📊 Rapport ICP | Rapport consolidé avec graphiques + export JSON/Excel |

### Partie 2 — MTP

| Étape | Action |
|-------|--------|
| 📑 Analyse MTP | Upload PDF MTP → analyse IA (Claude API) → rapport MTP structuré |
| 🔄 Comparaison | ICP vs MTP via IA → anomalies + recommandations |
| 🏁 Rapport Final | Rapport de conformité complet + export JSON/Excel |

## Modules ICP supportés

- **FE** : DVB-C, DVB-S/S2, DVB-T/T2
- **RF Wi-Fi** : 2.4 GHz, 5 GHz (EVM, Power, PER, Frequency Tolerance)
- **RF Bluetooth** : BR, EDR, BLE (Power, BER, Drift, Deviation)

## Prompts IA

### Prompt 1 — Extraction MTP
Extrait les résultats de tests depuis les PDF MTP :
- Informations équipement (produit, version, date, opérateur)
- Résultats FE (BER, SNR, RSSI, Symbol Rate, Frequency Offset)
- Résultats RF (Power, EVM, PER, BER par bande)
- Statut PASS/FAIL/N/A par paramètre

### Prompt 2 — Comparaison ICP vs MTP
Compare les spécifications ICP avec les mesures MTP :
- Corrélation test par test (Frequency + Modulation)
- Conformité paramètre par paramètre
- Détection d'anomalies (CRITICAL / WARNING / INFO)
- Recommandations actionnables

## Structure du projet

```
telecom_validator/
├── app.py                    # Application Streamlit principale
├── requirements.txt
├── modules/
│   ├── icp_fe_extract.py     # Extracteur FE depuis PDF ICP
│   ├── icp_wifi_extract.py   # Extracteur RF/BT depuis PDF ICP
│   ├── check_fe_log.py       # Validateur logs FE
│   ├── check_rf_log.py       # Validateur logs RF/BT
│   └── mtp_analyzer.py       # Analyseur MTP via IA + prompts
└── README.md
```
>>>>>>> 464f586 (Initial commit)
