# -*- coding: utf-8 -*-
"""
Article 2, étape 2 : caractérisation de la variation d'écriture.

Trois phénomènes sont quantifiés séparément, parce qu'ils appellent des
traitements différents dans la chaîne de codage :

1. l'abréviation non conventionnelle, propre à l'établissement (SP, SM, IU) :
   elle échappe à toute ressource terminologique publique et exige un lexique
   local ;
2. la variante orthographique d'un même concept, mesurée par distance
   d'édition sur la forme repliée : elle relève d'un appariement approché ;
3. la modification du libellé (grave, simple, probable, aiguë, d'échec
   thérapeutique) : elle porte une information clinique que la CIM-11 code
   parfois, et qu'il faut donc isoler avant appariement.

Entrées  : 03-corpus/lexique_etiquettes.csv, etiquettes_candidates.csv
Sorties  : 04-resultats/inventaire_abreviations.csv
           04-resultats/variantes_orthographiques.csv
           04-resultats/modificateurs.csv
"""
import collections
import csv
import os
import re
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
CORPUS = os.path.join(BASE, "03-corpus")
RESULTATS = os.path.join(BASE, "04-resultats")

# Distance d'édition maximale pour rapprocher deux étiquettes d'un même concept.
# 2 sur une chaîne d'au moins 6 caractères : au-delà, le rapprochement devient
# spéculatif et relève de l'annotation, non de la mesure.
DISTANCE_MAX = 2
LONGUEUR_MIN_APPARIEMENT = 6

# Une étiquette est tenue pour une abréviation si elle est courte et dépourvue
# de voyelle suffisante, ou si elle est intégralement en capitales dans le
# corpus source. Le seuil est bas et volontairement inclusif : l'inventaire est
# destiné à une relecture clinicienne, pas à une décision automatique.
LONGUEUR_ABREVIATION = 5

# Oppositions sémantiques que la distance d'édition ne voit pas. Deux étiquettes
# séparées par une seule de ces substitutions sont à moins de deux éditions l'une
# de l'autre alors qu'elles désignent des entités distinctes. Les fusions
# correspondantes sont signalées, non supprimées : elles constituent la mesure
# de ce qu'un appariement purement formel ne peut pas trancher.
OPPOSITIONS = [
    ("majeur", "mineur"), ("ite", "ose"), ("hyper", "hypo"),
    ("gauche", "droite"), ("sus", "sous"), ("pre", "post"),
    ("avec", "sans"), ("aigue", "algie"),
]


def fusion_suspecte(a, b):
    """Vrai si a et b ne différent que par une opposition sémantique connue."""
    for gauche, droite in OPPOSITIONS:
        for x, y in ((gauche, droite), (droite, gauche)):
            if x in a and a.replace(x, y) == b:
                return "%s / %s" % (x, y)
    return ""


MODIFICATEURS = [
    "grave", "simple", "probable", "aigue", "aigu", "chronique", "majeure",
    "majeur", "severe", "compliquee", "complique", "recidivante", "febrile",
    "aspecifique", "d'echec therapeutique", "a forte parasitemie", "associee",
    "suspecte", "debutante", "modere", "moderee", "leger", "legere",
]


def distance(a, b, plafond):
    """Distance de Levenshtein, abandonnée dès que le plafond est dépassé."""
    if abs(len(a) - len(b)) > plafond:
        return plafond + 1
    precedente = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        courante = [i]
        for j, cb in enumerate(b, 1):
            courante.append(min(precedente[j] + 1,
                                courante[j - 1] + 1,
                                precedente[j - 1] + (ca != cb)))
        if min(courante) > plafond:
            return plafond + 1
        precedente = courante
    return precedente[-1]


def lire(nom, dossier=CORPUS):
    with open(os.path.join(dossier, nom), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ecrire(chemin, entetes, lignes):
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(entetes)
        w.writerows(lignes)


def inventorier_abreviations(lexique, brutes):
    """Repère les étiquettes candidates au statut d'abréviation.

    Pour chacune, on rapporte les étiquettes qui l'accompagnent le plus souvent
    dans le même diagnostic : le contexte de cooccurrence est ce qui permettra
    au clinicien de trancher l'expansion.
    """
    par_consultation = collections.defaultdict(list)
    for e in brutes:
        par_consultation[e["id_consultation"]].append(e["etiquette_repliee"])

    voisins = collections.defaultdict(collections.Counter)
    for etqs in par_consultation.values():
        for e in etqs:
            for autre in etqs:
                if autre != e:
                    voisins[e][autre] += 1

    formes_brutes = collections.defaultdict(collections.Counter)
    for e in brutes:
        formes_brutes[e["etiquette_repliee"]][e["etiquette"]] += 1

    lignes = []
    for etq, n in lexique.items():
        mots = etq.split()
        if len(etq) > LONGUEUR_ABREVIATION or len(mots) > 2:
            continue
        surface = formes_brutes[etq].most_common(1)[0][0]
        capitales = surface.isupper()
        sans_voyelle = not re.search(r"[aeiouy]", etq[1:])
        if not (capitales or sans_voyelle or len(etq) <= 3):
            continue
        contexte = "; ".join("%s (%d)" % (v, c)
                             for v, c in voisins[etq].most_common(3))
        lignes.append([etq, formes_brutes[etq].most_common(1)[0][0], n,
                       "capitales" if capitales else "forme courte",
                       contexte])
    lignes.sort(key=lambda l: -l[2])
    return lignes


def grouper_variantes(lexique):
    """Regroupe les étiquettes proches par distance d'édition.

    Chaque groupe est ancré sur son étiquette la plus fréquente. Le blocage se
    fait sur la première lettre et la longueur, faute de quoi la comparaison
    deux à deux serait inutilement coûteuse.
    """
    par_frequence = sorted(lexique.items(), key=lambda kv: (-kv[1], kv[0]))
    eligibles = [(e, n) for e, n in par_frequence
                 if len(e) >= LONGUEUR_MIN_APPARIEMENT]

    blocs = collections.defaultdict(list)
    for etq, n in eligibles:
        blocs[etq[0]].append((etq, n))

    ancre = {}
    groupes = collections.defaultdict(list)
    for _, membres in blocs.items():
        for etq, n in membres:
            if etq in ancre:
                continue
            ancre[etq] = etq
            groupes[etq].append((etq, n))
            for autre, m in membres:
                if autre in ancre or m > n:
                    continue
                if distance(etq, autre, DISTANCE_MAX) <= DISTANCE_MAX:
                    ancre[autre] = etq
                    groupes[etq].append((autre, m))

    lignes = []
    for tete, membres in groupes.items():
        if len(membres) < 2:
            continue
        total = sum(m for _, m in membres)
        variantes = sorted((m for m in membres if m[0] != tete),
                           key=lambda m: -m[1])
        alertes = [(v, fusion_suspecte(tete, v)) for v, _ in variantes]
        alertes = "; ".join("%s [%s]" % (v, a) for v, a in alertes if a)
        lignes.append([tete, lexique[tete], len(membres) - 1, total,
                       round(100.0 * (total - lexique[tete]) / total, 1),
                       "; ".join("%s (%d)" % v for v in variantes[:8]),
                       alertes])
    lignes.sort(key=lambda l: -l[3])
    return lignes


def inventorier_modificateurs(lexique):
    """Mesure la part des étiquettes portant un modificateur clinique."""
    lignes, couverts = [], set()
    for mod in MODIFICATEURS:
        motif = re.compile(r"(?:^|\s)" + re.escape(mod) + r"(?:\s|$)")
        concernees = [(e, n) for e, n in lexique.items() if motif.search(e)]
        if not concernees:
            continue
        couverts.update(e for e, _ in concernees)
        occurrences = sum(n for _, n in concernees)
        exemples = "; ".join(e for e, _ in sorted(concernees,
                                                  key=lambda kv: -kv[1])[:3])
        lignes.append([mod, len(concernees), occurrences, exemples])
    lignes.sort(key=lambda l: -l[2])
    return lignes, couverts


def main():
    brutes = lire("etiquettes_candidates.csv")
    lexique = collections.Counter()
    for e in brutes:
        lexique[e["etiquette_repliee"]] += 1
    total = sum(lexique.values())

    abrev = inventorier_abreviations(lexique, brutes)
    ecrire(os.path.join(RESULTATS, "inventaire_abreviations.csv"),
           ["etiquette_repliee", "forme_source_frequente", "frequence",
            "indice", "cooccurrences_frequentes"], abrev)

    # Feuille de travail destinée au clinicien de l'établissement. Elle porte
    # les mêmes lignes que l'inventaire, augmentées des colonnes qu'il seul peut
    # remplir. La colonne resolvable_par_contexte signale les abréviations qui
    # n'apparaissent jamais accompagnées : aucun indice textuel ne permettra de
    # les expanser, et l'annotation devra s'en passer si le clinicien ne tranche
    # pas.
    ecrire(os.path.join(CORPUS, "lexique_abreviations_a_expanser.csv"),
           ["forme_source_frequente", "etiquette_repliee", "frequence",
            "cooccurrences_frequentes", "resolvable_par_contexte",
            "expansion_validee", "code_cim11_suggere", "clinicien",
            "commentaire"],
           [[l[1], l[0], l[2], l[4], "non" if not l[4] else "oui", "", "", "", ""]
            for l in abrev])

    variantes = grouper_variantes(lexique)
    ecrire(os.path.join(RESULTATS, "variantes_orthographiques.csv"),
           ["forme_ancre", "frequence_ancre", "nb_variantes",
            "occurrences_groupe", "part_variantes_pct", "variantes",
            "fusions_suspectes"], variantes)

    mods, couverts = inventorier_modificateurs(lexique)
    ecrire(os.path.join(RESULTATS, "modificateurs.csv"),
           ["modificateur", "etiquettes_distinctes", "occurrences",
            "exemples"], mods)

    occ_abrev = sum(l[2] for l in abrev)
    occ_var = sum(l[3] - l[1] for l in variantes)
    occ_mod = sum(lexique[e] for e in couverts)

    print("Lexique                                %6d etiquettes distinctes, "
          "%d occurrences" % (len(lexique), total))
    print("Abreviations candidates                %6d etiquettes  %5.1f %% des "
          "occurrences" % (len(abrev), 100.0 * occ_abrev / total))
    print("Groupes de variantes orthographiques   %6d groupes    %5.1f %% des "
          "occurrences imputables aux variantes"
          % (len(variantes), 100.0 * occ_var / total))
    print("Etiquettes portant un modificateur     %6d etiquettes  %5.1f %% des "
          "occurrences" % (len(couverts), 100.0 * occ_mod / total))
    reductible = sum(l[2] for l in variantes)
    suspectes = sum(1 for l in variantes if l[6])
    print("Reduction possible du lexique par appariement approche : "
          "%d etiquettes, soit %.1f %%"
          % (reductible, 100.0 * reductible / len(lexique)))
    print("Groupes contenant une fusion semantiquement suspecte : %d"
          % suspectes)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
