# -*- coding: utf-8 -*-
"""
Article 2, étape 3 : plan d'annotation.

L'annotation est le poste de dépense de cet article. Le corpus compte 16 088
étiquettes ; les annoter toutes serait déraisonnable et inutile, la distribution
étant très concentrée. Ce script produit donc :

1. la liste de travail, ordonnée par fréquence décroissante et découpée en
   priorités selon la couverture visée : annoter le type d'étiquette, non
   l'occurrence, divise le volume par un facteur mesuré ici ;
2. l'échantillon de double codage, stratifié par tranche de fréquence, sur
   lequel se calcule l'accord inter-annotateurs ;
3. l'échantillon d'évaluation de bout en bout, stratifié par service et tiré
   au niveau du diagnostic entier : c'est lui qui sert à mesurer la chaîne
   complète, segmentation comprise, et non les seules étiquettes.

Les tirages sont reproductibles : la graine est fixe et inscrite dans les
sorties. Aucun échantillon ne recouvre l'autre en fonction, mais leur
recoupement est autorisé et documenté.

Sorties : 03-corpus/lexique_a_annoter.csv
          03-corpus/echantillon_double_codage.csv
          03-corpus/echantillon_evaluation.csv
          04-resultats/plan_annotation.csv
"""
import collections
import csv
import os
import random
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
CORPUS = os.path.join(BASE, "03-corpus")
RESULTATS = os.path.join(BASE, "04-resultats")

GRAINE = 20260824

# Tranches de fréquence pour la stratification du double codage. La strate des
# hapax est la plus difficile et la plus nombreuse : elle est échantillonnée
# aussi, sans quoi l'accord inter-annotateurs serait mesuré sur la seule partie
# facile du lexique et surestimerait la fiabilité.
STRATES = [
    ("frequente (>= 50)", lambda n: n >= 50),
    ("moyenne (10 a 49)", lambda n: 10 <= n < 50),
    ("rare (2 a 9)", lambda n: 2 <= n < 10),
    ("hapax (1)", lambda n: n == 1),
]
TAILLE_DOUBLE_CODAGE = 400
TAILLE_EVALUATION = 300

# Colonnes laissées vides, à remplir par l'annotateur. Le code et le libellé
# sont séparés du titre de la catégorie CIM-11 afin que la saisie reste
# vérifiable contre l'API de l'OMS.
COLONNES_ANNOTATION = [
    "cim11_code", "cim11_uri", "cim11_titre", "modificateur_clinique",
    "certitude", "hors_perimetre", "annotateur", "commentaire",
]


def lire(nom, dossier=CORPUS):
    with open(os.path.join(dossier, nom), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ecrire(chemin, entetes, lignes):
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(entetes)
        w.writerows(lignes)


def rang_couvrant(lexique, total, seuil):
    """Rang du type qui fait franchir le seuil de couverture cumulee."""
    cumul = 0
    for rang, (_, n) in enumerate(lexique.most_common(), 1):
        cumul += n
        if 100.0 * cumul / total >= seuil:
            return rang
    return len(lexique)


def priorite(rang, bornes):
    """Priorite d'annotation, deduite du rang et des bornes de couverture.

    Le type qui fait franchir le seuil appartient au palier qu'il complete :
    la borne est inclusive, faute de quoi la liste de travail comporterait une
    etiquette de moins que le volume annonce par le plan.
    """
    if rang <= bornes[80]:
        return "P1 - socle, couverture 80 %"
    if rang <= bornes[90]:
        return "P2 - extension, couverture 90 %"
    return "P3 - queue de distribution"


def main():
    alea = random.Random(GRAINE)
    etiquettes = lire("etiquettes_candidates.csv")
    corpus = lire("corpus_diagnostics.csv")

    lexique = collections.Counter(e["etiquette_repliee"] for e in etiquettes)
    total = sum(lexique.values())

    # Forme de surface la plus fréquente : c'est elle que verra l'annotateur,
    # la forme repliée ayant perdu la casse et les accents.
    surfaces = collections.defaultdict(collections.Counter)
    for e in etiquettes:
        surfaces[e["etiquette_repliee"]][e["etiquette"]] += 1

    # --- liste de travail --------------------------------------------------
    bornes = {s: rang_couvrant(lexique, total, s) for s in (50, 80, 90, 95)}
    cumul, travail = 0, []
    for rang, (etq, n) in enumerate(lexique.most_common(), 1):
        cumul += n
        couverture = 100.0 * cumul / total
        travail.append([rang, surfaces[etq].most_common(1)[0][0], etq, n,
                        round(couverture, 2), priorite(rang, bornes)]
                       + [""] * len(COLONNES_ANNOTATION))
    ecrire(os.path.join(CORPUS, "lexique_a_annoter.csv"),
           ["rang", "forme_a_annoter", "etiquette_repliee", "frequence",
            "couverture_cumulee_pct", "priorite"] + COLONNES_ANNOTATION,
           travail)

    # --- échantillon de double codage --------------------------------------
    par_strate = collections.OrderedDict((nom, []) for nom, _ in STRATES)
    for etq, n in lexique.items():
        for nom, test in STRATES:
            if test(n):
                par_strate[nom].append((etq, n))
                break

    # Allocation proportionnelle aux occurrences, plancher de 40 par strate :
    # une strate peu fréquente doit rester mesurable. La strate des étiquettes
    # fréquentes est vite saturée, faute de types disponibles ; le reliquat est
    # alors redistribué sur les strates qui ont encore de la capacité, jusqu'à
    # atteindre la taille visée.
    poids = {nom: sum(n for _, n in membres)
             for nom, membres in par_strate.items()}
    somme_poids = sum(poids.values())
    alloc = {}
    for nom, membres in par_strate.items():
        cible = max(40, int(round(TAILLE_DOUBLE_CODAGE * poids[nom] / somme_poids)))
        alloc[nom] = min(cible, len(membres))

    reliquat = TAILLE_DOUBLE_CODAGE - sum(alloc.values())
    while reliquat > 0:
        disponibles = [nom for nom, membres in par_strate.items()
                       if alloc[nom] < len(membres)]
        if not disponibles:
            break
        for nom in sorted(disponibles, key=lambda n: -poids[n]):
            if reliquat <= 0:
                break
            alloc[nom] += 1
            reliquat -= 1

    tirage = []
    for nom, membres in par_strate.items():
        for etq, n in alea.sample(sorted(membres), alloc[nom]):
            tirage.append([nom, surfaces[etq].most_common(1)[0][0], etq, n]
                          + [""] * len(COLONNES_ANNOTATION))
    ecrire(os.path.join(CORPUS, "echantillon_double_codage.csv"),
           ["strate", "forme_a_annoter", "etiquette_repliee", "frequence"]
           + COLONNES_ANNOTATION, tirage)

    # --- échantillon d'évaluation de bout en bout --------------------------
    # Stratification par service, proportionnelle au volume de diagnostics.
    par_service = collections.defaultdict(list)
    for d in corpus:
        par_service[d["service"] or "non renseigne"].append(d)

    evaluation = []
    for service, docs in sorted(par_service.items()):
        cible = max(5, int(round(TAILLE_EVALUATION * len(docs) / len(corpus))))
        cible = min(cible, len(docs))
        for d in alea.sample(sorted(docs, key=lambda x: x["id_consultation"]),
                             cible):
            evaluation.append([d["id_consultation"], d["service"], d["mois"],
                               d["sexe"], d["age"], d["nb_etiquettes"],
                               d["texte_normalise"]]
                              + [""] * (len(COLONNES_ANNOTATION) + 1))
    ecrire(os.path.join(CORPUS, "echantillon_evaluation.csv"),
           ["id_consultation", "service", "mois", "sexe", "age",
            "nb_etiquettes_automatiques", "texte_normalise",
            "etiquettes_de_reference"] + COLONNES_ANNOTATION, evaluation)

    # --- plan chiffré ------------------------------------------------------
    volume = bornes.__getitem__

    plan = [
        ["Occurrences a coder si l'annotation portait sur l'occurrence",
         total, "reference haute"],
        ["Types d'etiquettes distincts", len(lexique),
         "facteur de reduction %.1f" % (float(total) / len(lexique))],
        ["Annotations pour couvrir 50 % des occurrences", volume(50), "P1"],
        ["Annotations pour couvrir 80 % des occurrences", volume(80), "P1"],
        ["Annotations pour couvrir 90 % des occurrences", volume(90), "P2"],
        ["Annotations pour couvrir 95 % des occurrences", volume(95), "P3"],
        ["Echantillon de double codage", len(tirage),
         "; ".join("%s : %d" % (k, v) for k, v in alloc.items())],
        ["Echantillon d'evaluation de bout en bout", len(evaluation),
         "stratifie par service, %d services" % len(par_service)],
        ["Graine du tirage", GRAINE, "tirages reproductibles"],
    ]
    ecrire(os.path.join(RESULTATS, "plan_annotation.csv"),
           ["poste", "volume", "precision"], plan)

    for poste, vol, precision in plan:
        print("%-58s %7s  %s" % (poste, vol, precision))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
