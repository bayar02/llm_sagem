from pathlib import Path

path = Path("rag_env/modules_rag/rag_extractor_rf.py")
content = path.read_text(encoding="utf-8")

old_example = "(ex: TX: MCS0 HT20, RX PER: LE 1M PRBS)"
new_example = "(ex: TX: MCS0 HT20). Ne jamais combiner plusieurs tests avec une virgule dans ce champ"

old_anchor = "artefact de mise en page du PDF."
insertion = """artefact de mise en page du PDF.

Attention, cas frequent en RF : un parametre peut etre suivi de TROIS nombres dans cet ordre
precis : Target (valeur cible), Min, Max -- et non de deux. Le JSON attend uniquement Min et
Max : ce sont le 2eme et le 3eme nombre de la sequence, jamais les deux premiers. Ne confonds
jamais Target avec Min."""

assert old_example in content, "ancre 'Test example' non trouvee"
assert old_anchor in content, "ancre 'artefact' non trouvee"
assert content.count(old_anchor) == 1, "ancre 'artefact' trouvee plusieurs fois, patch ambigu"

content = content.replace(old_example, new_example)
content = content.replace(old_anchor, insertion)

path.write_text(content, encoding="utf-8")
print("OK: prompt RF corrige (Test field + regle Target/Min/Max).")