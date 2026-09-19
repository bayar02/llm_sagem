from pathlib import Path

path = Path("rag_env/modules_rag/rag_extractor_rf.py")
content = path.read_text(encoding="utf-8")

old_test_field = '''{"Test": "libelle du test tel qu'ecrit dans le document (ex: TX: MCS0 HT20, RX PER: LE 1M PRBS)",'''
new_test_field = '''{"Test": "libelle du test UNIQUE tel qu'ecrit dans le document (ex: TX: MCS0 HT20). Ne jamais combiner plusieurs tests avec une virgule.",'''

old_minmax_rule = '''Regle importante pour lire les valeurs Min/Max : chaque parametre est suivi de ses valeurs
(Min puis Max, ou une valeur cible unique) IMMEDIATEMENT apres son libelle. Si tu vois ensuite
une ligne isolee de nombres qui ne suit pas directement un libelle de parametre, IGNORE-la :
c'est un artefact de mise en page du PDF.'''

new_minmax_rule = '''Regle importante pour lire les valeurs Min/Max : dans les tableaux RF, un parametre est souvent
suivi de TROIS nombres dans cet ordre precis : Target (valeur cible), Min, Max -- et non de deux.
Le JSON attend uniquement Min et Max : ce sont le 2eme et le 3eme nombre de la sequence, jamais
les deux premiers. Ne confonds jamais Target avec Min. Si un parametre n'a que deux nombres,
ce sont bien Min puis Max. Si tu vois ensuite une ligne isolee de nombres qui ne suit pas
directement un libelle de parametre, IGNORE-la : c'est un artefact de mise en page du PDF.'''

assert old_test_field in content, "texte 'Test field' non trouve"
assert old_minmax_rule in content, "texte 'Min/Max rule' non trouve"

content = content.replace(old_test_field, new_test_field)
content = content.replace(old_minmax_rule, new_minmax_rule)

path.write_text(content, encoding="utf-8")
print("OK: prompt RF corrige (Test field + regle Min/Max/Target).")