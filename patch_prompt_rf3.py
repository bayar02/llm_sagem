from pathlib import Path

path = Path("rag_env/modules_rag/rag_extractor_rf.py")
content = path.read_text(encoding="utf-8")

old_example = "(ex: TX: MCS0 HT20). Ne jamais combiner plusieurs tests avec une virgule dans ce champ"
new_example = ". Ne jamais utiliser un exemple generique ou un texte fixe : chaque entree doit avoir un libelle different, copie exactement depuis le passage du document qui la concerne. Ne jamais combiner plusieurs tests avec une virgule dans ce champ"

old_anchor = "jamais Target avec Min."
insertion = """jamais Target avec Min.

Exemple d'application : si le texte affiche "Power 5 2 7.5 dBm" pour un parametre Power, cela
correspond a Target=5, Min=2, Max=7.5 -- tu dois retourner Min:"2", Max:"7.5". Ne retourne
JAMAIS Min:"5" dans ce cas.

Cas particulier "RX Power" : ce parametre est souvent une valeur UNIQUE de sensibilite (un seul
nombre en dBm), pas une paire Min/Max. Si tu ne vois qu'un seul nombre pour RX Power, mets ce
meme nombre en Min ET en Max. Le parametre "PER" (en %) est une paire Min/Max SEPAREE et
distincte de RX Power -- ne melange jamais les deux parametres, et n'utilise jamais une valeur
de PER pour completer RX Power ou inversement."""

assert old_example in content, "ancre 'old_example' non trouvee"
assert old_anchor in content, "ancre 'old_anchor' non trouvee"
assert content.count(old_anchor) == 1, "ancre 'old_anchor' ambigue"

content = content.replace(old_example, new_example)
content = content.replace(old_anchor, insertion)

path.write_text(content, encoding="utf-8")
print("OK: prompt RF affine (Test label + RX Power/PER + exemple Target/Min/Max).")