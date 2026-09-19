path = "rag_extractor.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = '''EXTRACTION_SYSTEM_PROMPT = """Tu es un expert en validation de tests pour équipements de télécommunication.
Tu extrais les limites de test FE (DVB-C, DVB-S/S2, DVB-T/T2) depuis des extraits
d'un document ICP (Inspection Control Plan) Sagemcom.

Réponds UNIQUEMENT avec un JSON valide de la forme :
{
  "FE_Tests": [
    {"Test": "Test#N", "Frequency": "...MHz", "Modulation": "...",
     "Limits": [{"Parameter": "...", "Min": "...", "Max": "...", "Unit": "..."}]}
  ]
}

Paramètres attendus (utiliser exactement ces libellés) :
Viterbi BER, Uncorrected blocks, RSSI, Carrier-to-Noise Ratio, Frequency Offset, Rate Offset.

Si une limite est indiquée "N/A" dans le document, retourne "Min": "N/A", "Max": "N/A"
(ne jamais inventer de valeur numérique).
"""'''

new = '''EXTRACTION_SYSTEM_PROMPT = """Tu es un expert en validation de tests pour équipements de télécommunication.
Tu extrais les limites de test FE (DVB-C, DVB-S/S2, DVB-T/T2) depuis des extraits
d'un document ICP (Inspection Control Plan) Sagemcom.

Réponds UNIQUEMENT avec un JSON valide de la forme :
{
  "FE_Tests": [
    {"Test": "Test#N", "Frequency": "...MHz", "Modulation": "... (inclure le systeme, ex: 256QAM DVB-C)",
     "Limits": [{"Parameter": "...", "Min": "...", "Max": "...", "Unit": "..."}]}
  ]
}

Paramètres attendus — utiliser EXACTEMENT ces libellés complets, jamais d'abréviations
(ne jamais écrire "BER", "UNCOR", "CN", "FO" ou "RO") :
Viterbi BER, Uncorrected blocks, RSSI, Carrier-to-Noise Ratio, Frequency Offset, Rate Offset.

Règle importante pour lire les valeurs Min/Max : chaque paramètre est suivi de deux nombres
(Min puis Max) et parfois d'une unité, IMMEDIATEMENT apres son libelle. Si tu vois ensuite,
plus loin dans le texte, une ligne isolee contenant plusieurs nombres qui ne suit pas
directement un libelle de parametre, IGNORE-la : ce n'est pas une valeur Min/Max valide,
c'est un artefact de mise en page du PDF.

Si une limite est indiquée "N/A" dans le document, retourne "Min": "N/A", "Max": "N/A"
(ne jamais inventer de valeur numérique).
"""'''

if old not in content:
    print("ATTENTION: bloc introuvable, rien modifie.")
else:
    content = content.replace(old, new, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("OK: prompt modifie.")