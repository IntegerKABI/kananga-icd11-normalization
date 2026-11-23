# -*- coding: utf-8 -*-
"""
Article 2 : apport du contexte biologique au codage du paludisme.

Le diagnostic libre porte tres souvent seulement « paludisme », alors que la
CIM-11 distingue l'espece et le statut de confirmation parasitologique. Ce
script relie chaque consultation portant une etiquette de paludisme a ses
demandes de goutte epaisse et a leurs resultats.

La detection du paludisme accepte une distance de Levenshtein <= 2 sur un mot,
afin d'inclure les fautes documentees dans le corpus (paludime, pludisme,
paluisme, etc.). Elle exclut ainsi « syndrome paludo-grippal », qui n'affirme
pas a lui seul un diagnostic de paludisme.

La polarite de la goutte epaisse est une aide analytique, pas une nouvelle
verite terrain : une negation explicite prime ; sinon une mention explicite de
positivite, de paludisme ou un comptage de trophozoites est classe positif. Les
cas non decidables restent « indetermines » et sont conserves pour relecture.

Sorties :
    04-resultats/contexte_paludisme.csv
    04-resultats/croisement_paludisme_goutte_epaisse.csv
"""
import collections
import csv
import os
import re
import unicodedata

import lire_dump
from caracteriser_variation import distance


BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
CORPUS = os.path.join(BASE, "03-corpus")
RESULTATS = os.path.join(BASE, "04-resultats")

TYPE_GOUTTE_EPAISSE = "15"
CIBLE = "paludisme"
VARIANTES_FORCEES = {"plusisme"}
CHAMPS_RESULTAT = ("resultat", "interpretation", "conclusion")

MOT = re.compile(r"[^\W\d_]+", re.UNICODE)
NEGATIF = re.compile(
    r"\bnegati\w*\b|\bneg\b|\bpas\s+de\s+(?:troph\w*|paras\w*)\b|"
    r"\babsence\s+de\s+(?:troph\w*|paras\w*)\b"
)
POSITIF = re.compile(r"\bpositi\w*\b|\bpos\b|\bpalu(?:disme)?\b|\bpalud\w*\b")
# Variantes réellement observées : TROPHO, THROPH, TR0PH0 et « trop ho ».
MOT_TROPHO = r"t[hr]*[o0]\s*p\s*h\w*"
COMPTAGE_TROPHO = re.compile(
    r"\d[^\n;]{0,30}" + MOT_TROPHO + r"|" + MOT_TROPHO + r"[^\n;]{0,30}\d"
)
ESPECE = re.compile(
    r"\b(?:plasmodium|falciparum|vivax|ovale|malariae|knowlesi)\b"
)
PF_CANDIDAT = re.compile(r"\bpf\b")


def replier(texte):
    """Minuscules, accents retires et espaces uniformises."""
    texte = unicodedata.normalize("NFD", (texte or "").lower())
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", texte).strip()


def est_paludisme(etiquette):
    """Vrai si un mot de l'etiquette designe le paludisme ou une faute proche."""
    for mot in MOT.findall(replier(etiquette)):
        if mot.startswith(CIBLE) or mot in VARIANTES_FORCEES:
            return True
        if 6 <= len(mot) <= 11 and distance(mot, CIBLE, 2) <= 2:
            return True
    return False


def classer_resultat(ligne):
    """Classe un resultat de goutte epaisse en positif, negatif ou indetermine."""
    champs = [replier(ligne.get(c) or "") for c in CHAMPS_RESULTAT]
    ensemble = " | ".join(champs)
    if NEGATIF.search(ensemble):
        return "negatif"
    tokens_resultat = MOT.findall(champs[0].replace("0", "o"))
    comptage_approche = any(
        mot.startswith(("tr", "th")) and
        (distance(mot, "troph", 2) <= 2 or distance(mot, "tropho", 2) <= 2)
        for mot in tokens_resultat
    ) and bool(re.search(r"\d", champs[0]))
    if (POSITIF.search(ensemble) or COMPTAGE_TROPHO.search(champs[0])
            or comptage_approche):
        return "positif"
    return "indetermine"


def lire_csv(nom):
    with open(os.path.join(CORPUS, nom), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ecrire(chemin, entetes, lignes):
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(entetes)
        w.writerows(lignes)


def pct(numerateur, denominateur):
    return round(100.0 * numerateur / denominateur, 1) if denominateur else 0.0


def main():
    etiquettes = lire_csv("etiquettes_candidates.csv")
    corpus = {r["id_consultation"]: r for r in lire_csv("corpus_diagnostics.csv")}

    etiquettes_paludisme = collections.defaultdict(list)
    for ligne in etiquettes:
        if est_paludisme(ligne["etiquette_repliee"]):
            etiquettes_paludisme[ligne["id_consultation"]].append(ligne["etiquette"])

    demandes = {r["id_demande_examen"]: r
                for r in lire_dump.charger("med_demande_examen")}
    lignes_ge = [r for r in lire_dump.charger("med_ligne_demande_examen")
                 if r["id_type_examen"] == TYPE_GOUTTE_EPAISSE]
    resultats_par_ligne = collections.defaultdict(list)
    for r in lire_dump.charger("med_resultat_examen"):
        resultats_par_ligne[r["id_ligne_demande"]].append(r)

    ge_par_consultation = collections.defaultdict(list)
    ge_sans_consultation = 0
    for ligne in lignes_ge:
        demande = demandes.get(ligne["id_demande_examen"], {})
        consultation = demande.get("id_consultation")
        if consultation:
            ge_par_consultation[consultation].append(ligne)
        else:
            ge_sans_consultation += 1

    details = []
    compte = collections.Counter()
    consultations_espece = 0
    consultations_pf_candidat = 0
    consultations_discordantes = 0

    for id_consultation in sorted(etiquettes_paludisme, key=lambda x: int(x)):
        lignes = ge_par_consultation.get(id_consultation, [])
        resultats = []
        for ligne in lignes:
            resultats.extend(resultats_par_ligne.get(ligne["id_ligne_demande"], []))

        classes = [classer_resultat(r) for r in resultats]
        classe_distincte = set(classes)
        discordant = "positif" in classe_distincte and "negatif" in classe_distincte
        if discordant:
            statut = "discordant"
            consultations_discordantes += 1
        elif "positif" in classe_distincte:
            statut = "positif"
        elif "negatif" in classe_distincte:
            statut = "negatif"
        elif resultats:
            statut = "indetermine"
        elif lignes:
            statut = "demande_sans_resultat"
        else:
            statut = "non_demandee"

        textes_resultats = [" | ".join((r.get(c) or "").strip()
                                       for c in CHAMPS_RESULTAT)
                            for r in resultats]
        espece_documentee = any(ESPECE.search(replier(t)) for t in textes_resultats)
        pf_candidat = any(PF_CANDIDAT.search(replier(t)) for t in textes_resultats)
        consultations_espece += int(espece_documentee)
        consultations_pf_candidat += int(pf_candidat)
        compte[statut] += 1

        c = corpus.get(id_consultation, {})
        details.append([
            id_consultation,
            c.get("date_consultation", ""),
            c.get("service", ""),
            c.get("texte_normalise", ""),
            " ; ".join(etiquettes_paludisme[id_consultation]),
            len(lignes),
            len(resultats),
            statut,
            "oui" if espece_documentee else "non",
            "oui" if pf_candidat else "non",
            " || ".join(textes_resultats),
        ])

    n_paludisme = len(etiquettes_paludisme)
    avec_demande = n_paludisme - compte["non_demandee"]
    avec_resultat = sum(compte[s] for s in
                        ("positif", "negatif", "indetermine", "discordant"))
    confirmation_decidable = compte["positif"] + compte["negatif"]

    tous_resultats_ge = []
    for ligne in lignes_ge:
        tous_resultats_ge.extend(resultats_par_ligne.get(ligne["id_ligne_demande"], []))
    classes_tous = collections.Counter(classer_resultat(r) for r in tous_resultats_ge)
    especes_tous = sum(
        any(ESPECE.search(replier(r.get(c) or "")) for c in CHAMPS_RESULTAT)
        for r in tous_resultats_ge
    )
    pf_tous = sum(
        any(PF_CANDIDAT.search(replier(r.get(c) or "")) for c in CHAMPS_RESULTAT)
        for r in tous_resultats_ge
    )

    synthese = [
        ["consultations_diagnostic_paludisme", n_paludisme, "",
         "Au moins une etiquette contenant paludisme ou une faute a distance <= 2"],
        ["avec_goutte_epaisse_demandee", avec_demande, pct(avec_demande, n_paludisme),
         "Liaison par id_consultation"],
        ["avec_resultat_goutte_epaisse", avec_resultat, pct(avec_resultat, n_paludisme),
         "Au moins un enregistrement med_resultat_examen"],
        ["resultat_positif", compte["positif"], pct(compte["positif"], n_paludisme),
         "Negation explicite prioritaire, sinon positivite/paludisme/comptage trophozoites"],
        ["resultat_negatif", compte["negatif"], pct(compte["negatif"], n_paludisme),
         "Mention explicite negative, absence ou pas de trophozoites/parasites"],
        ["resultat_indetermine", compte["indetermine"], pct(compte["indetermine"], n_paludisme),
         "Resultat present mais polarite non decidable par les regles"],
        ["resultat_discordant", compte["discordant"], pct(compte["discordant"], n_paludisme),
         "Au moins un resultat positif et un negatif dans la meme consultation"],
        ["demande_sans_resultat", compte["demande_sans_resultat"],
         pct(compte["demande_sans_resultat"], n_paludisme), ""],
        ["goutte_epaisse_non_demandee", compte["non_demandee"],
         pct(compte["non_demandee"], n_paludisme), ""],
        ["confirmation_parasitologique_decidable", confirmation_decidable,
         pct(confirmation_decidable, n_paludisme),
         "Consultations classees positives ou negatives; discordances exclues"],
        ["espece_plasmodiale_documentee", consultations_espece,
         pct(consultations_espece, n_paludisme),
         "Recherche falciparum, vivax, ovale, malariae, knowlesi ou Plasmodium"],
        ["abreviation_pf_candidate", consultations_pf_candidat,
         pct(consultations_pf_candidat, n_paludisme),
         "PF dans un resultat de goutte epaisse; interpretation falciparum a valider"],
        ["toutes_lignes_goutte_epaisse", len(lignes_ge), "",
         "Toutes consultations, avec ou sans diagnostic de paludisme"],
        ["tous_resultats_goutte_epaisse", len(tous_resultats_ge), "", ""],
        ["tous_resultats_ge_positifs", classes_tous["positif"],
         pct(classes_tous["positif"], len(tous_resultats_ge)), ""],
        ["tous_resultats_ge_negatifs", classes_tous["negatif"],
         pct(classes_tous["negatif"], len(tous_resultats_ge)), ""],
        ["tous_resultats_ge_indetermines", classes_tous["indetermine"],
         pct(classes_tous["indetermine"], len(tous_resultats_ge)), ""],
        ["tous_resultats_ge_avec_espece", especes_tous,
         pct(especes_tous, len(tous_resultats_ge)), ""],
        ["tous_resultats_ge_avec_pf_candidat", pf_tous,
         pct(pf_tous, len(tous_resultats_ge)), ""],
        ["lignes_ge_sans_consultation", ge_sans_consultation, "", ""],
        ["consultations_paludisme_discordantes", consultations_discordantes, "", ""],
    ]

    ecrire(os.path.join(RESULTATS, "contexte_paludisme.csv"),
           ["indicateur", "valeur", "pourcentage", "definition"], synthese)
    ecrire(os.path.join(RESULTATS, "croisement_paludisme_goutte_epaisse.csv"),
           ["id_consultation", "date_consultation", "service", "diagnostic",
            "etiquettes_paludisme", "nb_gouttes_epaisses", "nb_resultats",
            "statut_parasitologique", "espece_documentee", "pf_candidat",
            "resultats_ge"],
           details)

    print("Consultations avec diagnostic de paludisme :", n_paludisme)
    print("Avec goutte epaisse demandee : %d (%.1f %%)" %
          (avec_demande, pct(avec_demande, n_paludisme)))
    print("Avec resultat : %d (%.1f %%)" %
          (avec_resultat, pct(avec_resultat, n_paludisme)))
    print("Confirmation positive/negative decidable : %d (%.1f %%)" %
          (confirmation_decidable, pct(confirmation_decidable, n_paludisme)))
    print("Espece plasmodiale documentee :", consultations_espece)
    print("Gouttes epaisses, toutes consultations : %d demandes, %d resultats" %
          (len(lignes_ge), len(tous_resultats_ge)))


if __name__ == "__main__":
    main()
