# -*- coding: utf-8 -*-
"""
Article 2, ligne de base : appariement lexical du lexique sur la CIM-11.

C'est la mesure à battre. Aucun apprentissage, aucune ressource extérieure à la
classification elle-même : quatre passes, de l'égalité stricte à l'appariement
approché, appliquées dans cet ordre et arrêtées à la première qui aboutit. Le
rendement de chacune est reporté séparément, comme pour la segmentation, afin
que l'on sache ce que chaque règle apporte réellement.

Deux résultats de la quatrième passe sont sortis du total apparié, parce que les
y compter reviendrait à créditer la méthode d'un code inutilisable : la
sur-spécification, où le candidat désigne une entité plus fine que ce que le
texte autorise, et l'appariement sur une entité non codable, bloc ou chapitre,
qui porte un libellé mais pas de code.

Cette ligne de base est volontairement honnête plutôt que flatteuse : elle
n'utilise pas le lexique d'abréviations expansé par le clinicien, ressource
externe qui ne serait pas disponible dans un autre établissement. Une variante
l'utilisant est calculée à part, pour mesurer précisément ce que cette ressource
locale fait gagner.

Attention : un appariement produit ici n'est pas une vérité. Il est un candidat,
à confronter à l'annotation manuelle. Le taux d'appariement mesure la portée de
la méthode, pas sa justesse ; celle-ci ne se mesurera que contre le corpus
annoté.

Entrées : 01-donnees/cim11_mms.csv
          01-donnees/cim11_synonymes.csv (facultatif, non produit a ce jour)
          03-corpus/lexique_etiquettes.csv
          03-corpus/lexique_abreviations_a_expanser.csv (facultatif)
Sorties : 04-resultats/appariement_baseline.csv
          04-resultats/rendement_appariement.csv

Usage : python apparier_baseline.py
"""
import collections
import csv
import os
import re
import sys
import unicodedata

BASE = os.path.dirname(os.path.abspath(__file__))
DONNEES = os.path.join(BASE, "..", "01-donnees")
CORPUS = os.path.join(BASE, "..", "03-corpus")
RESULTATS = os.path.join(BASE, "..", "04-resultats")

# Seuil de l'appariement approché, sur le coefficient de Dice des trigrammes de
# caractères. 0,72 est le point où, sur un echantillon relu, les rapprochements
# cessent d'etre majoritairement justes. Il est expose ici pour etre discute,
# non enfoui dans le code.
SEUIL_DICE = 0.72
LONGUEUR_TOKEN_BLOCAGE = 4

# Modificateurs retires en passe 3. Repris de caracteriser_variation.py : ce
# sont ceux que le corpus emploie, pas une liste theorique.
MODIFICATEURS = [
    "d'echec therapeutique", "a forte parasitemie", "aspecifique",
    "recidivante", "compliquee", "complique", "chronique", "debutante",
    "probable", "suspecte", "moderee", "modere", "majeure", "majeur",
    "severe", "febrile", "associee", "legere", "leger", "grave", "simple",
    "aigue", "aigu",
]
MOTIFS_MODIFICATEUR = [
    re.compile(r"(?:^|\s)" + re.escape(m) + r"(?=\s|$)") for m in MODIFICATEURS
]


def replier(texte):
    """Minuscules, sans accents, ponctuation reduite a l'espace."""
    t = unicodedata.normalize("NFD", texte.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def trigrammes(texte):
    """Trigrammes de caracteres, bornes comprises."""
    t = "  %s  " % texte
    return {t[i:i + 3] for i in range(len(t) - 2)}


def dice(a, b):
    if not a or not b:
        return 0.0
    return 2.0 * len(a & b) / (len(a) + len(b))


def sans_modificateur(etiquette):
    """Retire les modificateurs cliniques ; retourne (base, modificateurs)."""
    base, trouves = etiquette, []
    for motif, mot in zip(MOTIFS_MODIFICATEUR, MODIFICATEURS):
        if motif.search(base):
            trouves.append(mot)
            base = motif.sub(" ", base)
    return re.sub(r"\s+", " ", base).strip(), trouves


def lire(chemin):
    with open(chemin, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ecrire(chemin, entetes, lignes):
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(entetes)
        w.writerows(lignes)


def construire_index():
    """Index des formes de surface de la CIM-11 vers leurs entites.

    Une meme forme peut designer plusieurs entites : l'index conserve toutes
    les cibles, et l'ambiguite est reportee plutot que tranchee au hasard.
    """
    entites = {e["uri"]: e for e in lire(os.path.join(DONNEES, "cim11_mms.csv"))}
    index = collections.defaultdict(list)

    for e in entites.values():
        if e["genre"] not in ("category", "chapter", "block"):
            continue
        for champ, source in (("titre_fr", "titre francais"),
                              ("titre_en", "titre anglais")):
            titre = (e[champ] or "").strip()
            if titre:
                index[replier(titre)].append((e["uri"], source))

    chemin_syn = os.path.join(DONNEES, "cim11_synonymes.csv")
    if os.path.exists(chemin_syn):
        for s in lire(chemin_syn):
            if s["uri"] in entites and s["terme"]:
                index[replier(s["terme"])].append(
                    (s["uri"], "%s %s" % (s["type"], s["langue"])))

    # Index inverse par token, pour restreindre l'appariement approche.
    par_token = collections.defaultdict(set)
    for forme in index:
        for token in forme.split():
            if len(token) >= LONGUEUR_TOKEN_BLOCAGE:
                par_token[token].add(forme)

    return entites, index, par_token


def approcher(forme, index, par_token):
    """Meilleur appariement approche, ou (None, 0.0, "").

    Deux corrections par rapport a un simple maximum de similarite.

    D'abord, a similarite quasi egale, le candidat retenu est celui dont
    l'ensemble de mots s'ecarte le moins de la requete. Sans cela, la mesure sur
    les trigrammes favorise les titres courts qui partagent un prefixe, et fait
    preferer un enfant a son parent.

    Ensuite, le sens de l'ecart est rapporte. Un candidat qui contient tous les
    mots de la requete et en ajoute d'autres ne designe pas la meme entite : il
    en designe une plus fine. << infection urinaire >> apparie sur
    << infection urinaire neonatale >> n'est pas un appariement correct assorti
    d'une nuance, c'est une erreur de niveau. La distinguer permet de mesurer un
    biais directionnel que le seul taux d'appariement dissimulerait.
    """
    candidats = set()
    for token in forme.split():
        if len(token) >= LONGUEUR_TOKEN_BLOCAGE:
            candidats |= par_token.get(token, set())
    if not candidats:
        return None, 0.0, ""

    reference, mots = trigrammes(forme), set(forme.split())
    notes = []
    for candidat in candidats:
        s = dice(reference, trigrammes(candidat))
        if s >= SEUIL_DICE:
            ecart = len(mots ^ set(candidat.split()))
            notes.append((ecart, -s, candidat))
    if not notes:
        meilleur = max((dice(reference, trigrammes(c)) for c in candidats),
                       default=0.0)
        return None, meilleur, ""

    ecart, score_negatif, candidat = min(notes)
    mots_candidat = set(candidat.split())
    if mots_candidat == mots:
        relation = "meme ensemble de mots"
    elif mots < mots_candidat:
        relation = "sur-specification"
    elif mots_candidat < mots:
        relation = "sous-specification"
    else:
        relation = "recouvrement partiel"
    return candidat, -score_negatif, relation


def expansions_abreviations():
    """Lit les expansions validees par le clinicien, si le fichier est rempli."""
    chemin = os.path.join(CORPUS, "lexique_abreviations_a_expanser.csv")
    if not os.path.exists(chemin):
        return {}
    return {replier(l["etiquette_repliee"]): replier(l["expansion_validee"])
            for l in lire(chemin) if l.get("expansion_validee", "").strip()}


def apparier(etiquette, index, par_token, expansions):
    """Applique les passes dans l'ordre ; retourne (methode, forme, score)."""
    forme = replier(etiquette)

    if forme in index:
        return "1. egalite stricte", forme, 1.0, ""

    if expansions:
        etendue = " ".join(expansions.get(m, m) for m in forme.split())
        if etendue != forme and etendue in index:
            return "2. abreviation expansee", etendue, 1.0, ""

    base, modificateurs = sans_modificateur(forme)
    if modificateurs and base and base in index:
        return "3. modificateur retire", base, 1.0, ""

    cible, score, relation = approcher(base or forme, index, par_token)
    if cible and relation == "sur-specification":
        return "5. sur-specification", cible, score, relation
    if cible:
        return "4. appariement approche", cible, score, relation

    return "non apparie", "", score, ""


def main():
    chemin_mms = os.path.join(DONNEES, "cim11_mms.csv")
    if not os.path.exists(chemin_mms):
        sys.exit("cim11_mms.csv absent : lancer d'abord recuperer_cim11.py.")

    entites, index, par_token = construire_index()
    expansions = expansions_abreviations()
    lexique = lire(os.path.join(CORPUS, "lexique_etiquettes.csv"))
    total_occurrences = sum(int(l["frequence"]) for l in lexique)

    print("CIM-11 : %d entites, %d formes de surface indexees"
          % (len(entites), len(index)))
    print("Abreviations expansees disponibles : %d" % len(expansions))
    print("Lexique : %d types, %d occurrences\n"
          % (len(lexique), total_occurrences))

    lignes = []
    par_methode = collections.Counter()
    occurrences_methode = collections.Counter()
    ambigus = 0
    # Un titre peut s'apparier exactement sans etre codable : les blocs et les
    # chapitres portent un libelle mais pas de code. L'appariement a reussi, il
    # ne produit pourtant aucun code utilisable.
    non_codables, occurrences_non_codables = 0, 0

    for l in lexique:
        etiquette, frequence = l["etiquette_repliee"], int(l["frequence"])
        methode, forme, score, relation = apparier(etiquette, index,
                                                   par_token, expansions)
        cibles = index.get(forme, [])
        if len(cibles) > 1:
            ambigus += 1
        uri, source = cibles[0] if cibles else ("", "")
        e = entites.get(uri, {})
        lignes.append([l["rang"], etiquette, frequence, methode, relation,
                       "non" if (methode != "non apparie" and not e.get("code"))
                       else "oui", round(score, 3), forme, e.get("code", ""),
                       e.get("titre_fr", ""), e.get("titre_en", ""), source,
                       len(cibles)])
        par_methode[methode] += 1
        occurrences_methode[methode] += frequence
        if methode != "non apparie" and not e.get("code"):
            non_codables += 1
            occurrences_non_codables += frequence

    ecrire(os.path.join(RESULTATS, "appariement_baseline.csv"),
           ["rang", "etiquette", "frequence", "methode", "relation",
            "codable", "score",
            "forme_appariee", "cim11_code", "cim11_titre_fr", "cim11_titre_en",
            "source_de_la_forme", "cibles_possibles"], lignes)

    ordre = ["1. egalite stricte", "2. abreviation expansee",
             "3. modificateur retire", "4. appariement approche",
             "5. sur-specification", "non apparie"]
    rendement = []
    for methode in ordre:
        if not par_methode[methode]:
            continue
        rendement.append([
            methode, par_methode[methode],
            round(100.0 * par_methode[methode] / len(lexique), 2),
            occurrences_methode[methode],
            round(100.0 * occurrences_methode[methode] / total_occurrences, 2)])
    # La sur-specification n'est pas comptee comme un appariement : elle
    # designe une entite plus fine que ce que le texte autorise.
    apparies = sum(o for m, o in occurrences_methode.items()
                   if m not in ("non apparie", "5. sur-specification"))
    types_apparies = sum(t for m, t in par_methode.items()
                         if m not in ("non apparie", "5. sur-specification"))
    rendement.append(["Total apparie, sur-specification exclue",
                      types_apparies,
                      round(100.0 * types_apparies / len(lexique), 2),
                      apparies,
                      round(100.0 * apparies / total_occurrences, 2)])
    rendement.append(["dont cible non codable, bloc ou chapitre",
                      non_codables,
                      round(100.0 * non_codables / len(lexique), 2),
                      occurrences_non_codables,
                      round(100.0 * occurrences_non_codables
                            / total_occurrences, 2)])
    codables = apparies - occurrences_non_codables
    rendement.append(["Total apparie a une categorie codable",
                      types_apparies - non_codables,
                      round(100.0 * (types_apparies - non_codables)
                            / len(lexique), 2),
                      codables,
                      round(100.0 * codables / total_occurrences, 2)])
    ecrire(os.path.join(RESULTATS, "rendement_appariement.csv"),
           ["methode", "types", "types_pct", "occurrences", "occurrences_pct"],
           rendement)

    print("%-26s %7s %8s %10s %9s" % ("methode", "types", "%", "occurr.", "%"))
    for ligne in rendement:
        print("%-26s %7d %7.1f%% %10d %8.1f%%" % tuple(ligne))
    print("\nFormes menant a plusieurs entites CIM-11 : %d" % ambigus)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
