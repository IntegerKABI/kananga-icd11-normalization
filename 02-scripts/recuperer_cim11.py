# -*- coding: utf-8 -*-
"""
Récupération de la CIM-11, linéarisation MMS, à partir du fichier de diffusion
publié par l'OMS.

Première version de ce script : parcours en largeur de l'API, deux requêtes par
entité. Abandonné après mesure. La MMS compte 37 153 entités ; à deux langues,
le parcours demandait plus de soixante-dix mille requêtes, pour un débit observé
d'environ une entité par seconde. L'OMS publie par ailleurs la tabulation
complète en accès libre, cinq mégaoctets, sans jeton : c'est la même
classification, dans la même version, obtenue en une requête.

Le fichier français porte les deux libellés, français et anglais, ce qui permet
de mesurer la couverture francophone réelle. Cette mesure importe : un article
sur le codage en français ne peut pas passer sous silence la part d'entités dont
le libellé français n'a jamais été traduit.

L'archive téléchargée est conservée telle quelle dans 01-donnees/ : elle est la
preuve de la version effectivement utilisée pour l'évaluation.

Sorties
-------
    01-donnees/SimpleTabulation-ICD-11-MMS-fr.zip   archive source
    01-donnees/cim11_mms.csv                        une ligne par entité
    04-resultats/couverture_cim11.csv               indicateurs de couverture

Usage
-----
    python recuperer_cim11.py [--version 2026-01] [--reprendre]

`--reprendre` réutilise l'archive déjà téléchargée.
"""
import argparse
import collections
import csv
import io
import os
import re
import sys
import urllib.request
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
DONNEES = os.path.join(BASE, "..", "01-donnees")
RESULTATS = os.path.join(BASE, "..", "04-resultats")

DIFFUSION = ("https://icdcdn.who.int/static/releasefiles/%s/"
             "SimpleTabulation-ICD-11-MMS-fr.zip")
VERSION_DEFAUT = "2026-01"

# Les libellés de regroupement portent leur profondeur en préfixe : « - » pour
# un bloc de premier niveau, « - - » pour le deuxième, et ainsi de suite.
PREFIXE_PROFONDEUR = re.compile(r"^(?:-\s*)+")

# Reconnaissance du debut d'un enregistrement. Le cas courant est une URI de
# fondation ; les categories residuelles, elles, n'ont pas d'entite de fondation
# et leur ligne commence donc par une tabulation, puis l'URI de linearisation.
# Les confondre avec des continuations de ligne ferait disparaitre du corpus les
# quelque cinq mille categories << autre precise >> et << sans precision >>.
DEBUTS_ENREGISTREMENT = ("http://id.who.int/icd/entity/",
                         "\thttp://id.who.int/icd/release/")


def debute_enregistrement(ligne):
    return ligne.startswith(DEBUTS_ENREGISTREMENT)


def telecharger(version, reprendre):
    """Récupère l'archive de diffusion, ou réutilise celle déjà présente."""
    os.makedirs(DONNEES, exist_ok=True)
    chemin = os.path.join(DONNEES, "SimpleTabulation-ICD-11-MMS-fr.zip")
    if reprendre and os.path.exists(chemin):
        print("archive locale reutilisee : %s" % os.path.normpath(chemin))
        return open(chemin, "rb").read()
    url = DIFFUSION % version
    print("telechargement : %s" % url)
    contenu = urllib.request.urlopen(url, timeout=180).read()
    with open(chemin, "wb") as f:
        f.write(contenu)
    print("%.1f Mo ecrits" % (len(contenu) / 1048576.0))
    return contenu


def recoller(texte):
    """Recolle les enregistrements scindés par un retour à la ligne parasite.

    Quelques notes de codage contiennent un saut de ligne qui n'est pas protégé
    par des guillemets : l'enregistrement se retrouve coupé en deux, et la
    seconde moitié se lit comme une entité fantôme dont l'URI de fondation
    contient en réalité du texte français. Toute ligne qui ne débute pas un
    enregistrement, au sens de `debute_enregistrement`, appartient donc à la
    précédente. Sur la version 2026-01, 78 enregistrements sont dans ce cas.
    """
    recollees, coupures = [], 0
    for ligne in texte.split("\n"):
        ligne = ligne.rstrip("\r")
        if not recollees or len(recollees) == 1 or debute_enregistrement(ligne):
            recollees.append(ligne)
        elif ligne.strip():
            recollees[-1] += " " + ligne
            coupures += 1
    return "\n".join(recollees), coupures


def _champ(brut):
    """Retire les guillemets encadrants et rétablit les guillemets doublés."""
    valeur = brut.strip()
    if len(valeur) >= 2 and valeur[0] == '"' and valeur[-1] == '"':
        valeur = valeur[1:-1]
    return valeur.replace('""', '"')


def lire_tabulation(contenu):
    """Déplie la tabulation en liste de dictionnaires.

    Le découpage est fait à la main plutôt que par le module csv. Le fichier
    mêle des champs correctement quotés et des champs qui ne le sont pas tout en
    contenant des guillemets, comme la note qui cite le code d'extension
    « Cause d'effet tardif ». Aucun analyseur respectant la norme ne peut lire
    les deux à la fois. Le séparateur étant la tabulation, et aucun libellé
    n'en contenant, le découpage brut est ici plus sûr que le conforme.
    """
    z = zipfile.ZipFile(io.BytesIO(contenu))
    # L'archive contient aussi un readme : c'est la tabulation qu'il faut.
    nom = next(n for n in z.namelist()
               if n.endswith(".txt") and "SimpleTabulation" in n)
    texte, coupures = recoller(z.read(nom).decode("utf-8-sig"))

    lignes = [l for l in texte.split("\n") if l.strip()]
    entetes = [_champ(c) for c in lignes[0].split("\t")]
    enregistrements = []
    for ligne in lignes[1:]:
        champs = [_champ(c) for c in ligne.split("\t")]
        champs += [""] * (len(entetes) - len(champs))
        enregistrements.append(dict(zip(entetes, champs)))
    return enregistrements, nom, coupures


def ecrire(chemin, entetes, lignes):
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(entetes)
        w.writerows(lignes)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--version", default=VERSION_DEFAUT,
                    help="version de la linearisation, par exemple 2026-01")
    ap.add_argument("--reprendre", action="store_true",
                    help="reutiliser l'archive deja telechargee")
    args = ap.parse_args()

    brut, nom_fichier, coupures = lire_tabulation(
        telecharger(args.version, args.reprendre))
    # La derniere colonne du fichier porte l'horodatage exact de la version.
    colonne_version = next((c for c in brut[0] if c.startswith("Version:")),
                           "")
    print("fichier : %s" % nom_fichier)
    print("%s" % colonne_version)
    print("enregistrements recolles : %d" % coupures)

    lignes = []
    par_genre = collections.Counter()
    par_chapitre = collections.Counter()
    # Deux défauts de traduction bien distincts, qu'il serait trompeur
    # d'additionner : le titre français absent, réduit aux tirets de
    # profondeur, et le titre français recopié de l'anglais.
    titre_fr_vide = 0
    titre_fr_anglais = 0
    residuels = 0

    for e in brut:
        titre_fr = PREFIXE_PROFONDEUR.sub("", (e.get("Title") or "").strip())
        titre_en = PREFIXE_PROFONDEUR.sub("", (e.get("TitleEN") or "").strip())
        if not titre_fr and not titre_en:
            continue
        genre = (e.get("ClassKind") or "").strip()
        residuel = (e.get("IsResidual") or "").strip().lower() == "true"
        par_genre[genre] += 1
        par_chapitre[(e.get("ChapterNo") or "").strip()] += 1
        if residuel:
            residuels += 1
        if not titre_fr:
            titre_fr_vide += 1
        elif titre_fr == titre_en:
            titre_fr_anglais += 1
        lignes.append([
            (e.get("Code") or "").strip(),
            (e.get("BlockId") or "").strip(),
            (e.get("Linearization URI") or "").strip(),
            (e.get("Foundation URI") or "").strip(),
            genre,
            (e.get("DepthInKind") or "").strip(),
            (e.get("ChapterNo") or "").strip(),
            "oui" if residuel else "non",
            "oui" if (e.get("isLeaf") or "").strip().lower() == "true" else "non",
            titre_fr,
            titre_en,
            (e.get("Parent") or "").strip(),
        ])

    ecrire(os.path.join(DONNEES, "cim11_mms.csv"),
           ["code", "block_id", "uri", "uri_fondation", "genre", "profondeur",
            "chapitre", "residuel", "feuille", "titre_fr", "titre_en",
            "parent_uri"], lignes)

    codes = sum(1 for l in lignes if l[0])
    couverture = [
        ["Version de la linearisation", args.version, colonne_version],
        ["Entites de la MMS", len(lignes), "titres francais et anglais"],
        ["Enregistrements recolles a la lecture", coupures,
         "sauts de ligne non proteges dans les notes de codage"],
        ["Entites portant un code", codes,
         "%.1f %% du total" % (100.0 * codes / len(lignes))],
        ["Categories residuelles", residuels,
         "%.1f %% du total ; autre precise et sans precision"
         % (100.0 * residuels / len(lignes))],
        ["Entites au titre francais vide", titre_fr_vide,
         "%.2f %% du total ; le champ ne porte que les tirets de profondeur"
         % (100.0 * titre_fr_vide / len(lignes))],
        ["Entites au titre francais recopie de l'anglais", titre_fr_anglais,
         "%.1f %% du total" % (100.0 * titre_fr_anglais / len(lignes))],
        ["Entites sans libelle francais exploitable",
         titre_fr_vide + titre_fr_anglais,
         "%.1f %% du total" % (100.0 * (titre_fr_vide + titre_fr_anglais)
                               / len(lignes))],
    ] + [["Entites de genre %s" % (g or "non renseigne"), n, ""]
         for g, n in par_genre.most_common()] + [
        ["Chapitres", len([c for c in par_chapitre if c]), ""],
    ]
    ecrire(os.path.join(RESULTATS, "couverture_cim11.csv"),
           ["indicateur", "valeur", "precision"], couverture)

    for libelle, val, precision in couverture:
        print("%-42s %8s  %s" % (libelle, val, precision))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
