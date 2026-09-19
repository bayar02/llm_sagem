from pathlib import Path

path = Path("rag_env/modules_rag/rag_extractor_rf.py")
content = path.read_text(encoding="utf-8")

old_schema_line = "libelle du test tel qu"
assert old_schema_line in content, "ancre schema non trouvee"

old_full = content[content.index('{"Test":'):content.index('"Frequency": "...MHz"')]
new_full = '{"Test": "...", '

content = content.replace(old_full, new_full)

old_rule_anchor = "Parametres possibles - utiliser EXACTEMENT ces libelles"
new_rule_prefix = """Pour le champ "Test" : recopie EXACTEMENT le libelle du test tel qu'il apparait dans le
document (ex. son nom de code reel comme on le voit dans le texte). N'ecris jamais un texte
generique, un exemple, ou une description a la place -- chaque entree doit avoir un libelle
different et reel. Ne combine jamais plusieurs tests avec une virgule dans ce champ.

"""

assert old_rule_anchor in content, "ancre regle non trouvee"
content = content.replace(old_rule_anchor, new_rule_prefix + old_rule_anchor)

path.write_text(content, encoding="utf-8")
print("OK: placeholder Test simplifie en '...', explication deplacee hors du schema JSON.")