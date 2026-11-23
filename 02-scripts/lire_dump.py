# -*- coding: utf-8 -*-
"""
Lecture des tables du dump MariaDB sans passer par un serveur SQL.

Reprise de la version de l'article 1, avec une correction indispensable ici :
les sequences d'echappement sont restituees en caracteres reels. L'article 1
travaillait sur des identifiants et des montants, ou l'ecart etait sans effet ;
l'article 2 travaille sur du texte libre, ou un antislash-n mal interprete
produit un << rn >> colle au mot suivant et fabrique de fausses formes.

Fonction principale : charger(table) -> liste de dictionnaires.
"""
import os
import re

# Chemin du dump : variable d'environnement KANANGA_DUMP, sinon 01-donnees/dump.sql.
DUMP = os.environ.get("KANANGA_DUMP") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "01-donnees", "dump.sql")

ANTISLASH = chr(92)

# Table d'echappement de MySQL / MariaDB. Les sequences \% et \_ conservent
# leur antislash : c'est le comportement documente du moteur.
ECHAPPEMENTS = {
    "0": "\x00",
    "'": "'",
    '"': '"',
    "b": "\b",
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "Z": "\x1a",
    ANTISLASH: ANTISLASH,
    "%": ANTISLASH + "%",
    "_": ANTISLASH + "_",
}


def _scinder(corps):
    """Scinde le corps d'un tuple SQL en valeurs Python.

    Gere les chaines quotees, les echappements par antislash et les
    apostrophes doublees. Retourne None pour les valeurs SQL NULL.
    """
    valeurs, tampon = [], []
    i, n, dans_chaine = 0, len(corps), False
    while i < n:
        c = corps[i]
        if dans_chaine:
            if c == ANTISLASH and i + 1 < n:
                suivant = corps[i + 1]
                tampon.append(ECHAPPEMENTS.get(suivant, suivant))
                i += 2
                continue
            if c == "'":
                if i + 1 < n and corps[i + 1] == "'":
                    tampon.append("'")
                    i += 2
                    continue
                dans_chaine = False
                i += 1
                continue
            tampon.append(c)
            i += 1
            continue
        if c == "'":
            dans_chaine = True
            i += 1
            continue
        if c == ",":
            valeurs.append("".join(tampon).strip())
            tampon = []
            i += 1
            continue
        tampon.append(c)
        i += 1
    valeurs.append("".join(tampon).strip())
    return [None if v == "NULL" else v for v in valeurs]


def charger(table, chemin=None):
    """Charge une table du dump et retourne une liste de dictionnaires."""
    chemin = chemin or DUMP
    motif = re.compile(r"^INSERT INTO `" + re.escape(table) + r"` \((.*?)\) VALUES")
    colonnes, lignes, dans_bloc = None, [], False

    with open(chemin, encoding="utf-8", errors="replace") as f:
        for ligne in f:
            if ligne.startswith("INSERT INTO `"):
                m = motif.match(ligne)
                if m:
                    colonnes = [c.strip(" `") for c in m.group(1).split(",")]
                    dans_bloc = True
                else:
                    dans_bloc = False
                continue
            if dans_bloc and ligne.startswith("("):
                corps = ligne.rstrip("\r\n").rstrip(";").rstrip(",")
                corps = corps[1:-1] if corps.endswith(")") else corps[1:]
                valeurs = _scinder(corps)
                if len(valeurs) == len(colonnes):
                    lignes.append(dict(zip(colonnes, valeurs)))
            elif dans_bloc:
                dans_bloc = False
    return lignes


if __name__ == "__main__":
    import sys
    t = sys.argv[1]
    r = charger(t)
    print("%s : %d lignes" % (t, len(r)))
    if r:
        print("colonnes :", ", ".join(r[0].keys()))
