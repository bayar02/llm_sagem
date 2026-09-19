from pathlib import Path

path = Path("rag_env/modules_rag/rag_extractor.py")
content = path.read_text(encoding="utf-8")

old = "c'est un artefact de mise en page du PDF."
new = (
    "c'est un artefact de mise en page du PDF.\n\n"
    "Pour le parametre \"Viterbi BER\" specifiquement, l'unite affichee dans le document\n"
    "est souvent une notation scientifique du type \".10-7\" et non \"dB\". Si le texte\n"
    "apres Min/Max pour Viterbi BER n'est pas une unite standard reconnaissable\n"
    "(dB, dBm, kHz, ppm), retourne \"Unit\": \"\" (chaine vide) plutot que d'inventer \"dB\"."
)

if old not in content:
    raise SystemExit("Bloc non trouve - le fichier a peut-etre deja ete modifie.")

content = content.replace(old, new)
path.write_text(content, encoding="utf-8")
print("OK: regle Viterbi BER Unit ajoutee.")