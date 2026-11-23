# -*- coding: utf-8 -*-
"""
Article 2, étape 1 : constitution et caractérisation du corpus de diagnostics.

Extrait les diagnostics en texte libre de med_consultation, leur adjoint les
métadonnées nécessaires à un échantillonnage stratifié, applique une
normalisation documentée, puis segmente chaque énoncé en étiquettes candidates.

Le découpage en étiquettes est volontairement conservateur : seuls les
séparateurs non ambigus sont exploités. Le point, terminal dans la majorité des
cas mais séparateur dans une minorité, est laissé de côté et sa résidualité est
mesurée. Ce choix est un résultat en soi : il borne ce qu'une segmentation par
règles peut atteindre avant tout apprentissage.

Sorties :
    03-corpus/corpus_diagnostics.csv
    03-corpus/etiquettes_candidates.csv
    03-corpus/formes_distinctes.csv
    03-corpus/lexique_etiquettes.csv
    04-resultats/caracterisation_corpus.csv
    04-resultats/distribution_etiquettes.csv
    04-resultats/inventaire_separateurs.csv
"""
import collections
import csv
import datetime
import os
import re
import sys
import unicodedata

import lire_dump

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
CORPUS = os.path.join(BASE, "03-corpus")
RESULTATS = os.path.join(BASE, "04-resultats")

# Bornes de plausibilité, reprises de l'article 1 (décision D2).
NAISSANCE_MIN = datetime.date(1900, 1, 1)
OBSERVATION_MAX = datetime.date(2026, 8, 24)

# Passes de segmentation, ordonnées de la plus sûre à la moins sûre. Chaque
# passe est appliquée aux segments produits par la précédente, de sorte que son
# rendement propre soit mesurable (voir rendement_segmentation.csv).
#
# La coordination « et/ou » est protégée du découpage par la barre oblique :
# elle marque une disjonction diagnostique, pas une frontière d'étiquette.
ET_OU = "\x00ETOU\x00"

PASSES = [
    ("Marqueur d'enumeration",
     re.compile(r"(?:(?<=^)|(?<=[\s.;,)]))\d{1,2}\s*[.)]\s*(?=[^\W\d_])")),
    ("Point-virgule, retour a la ligne, signe plus",
     re.compile(r"[;\n\r]+|\s\+\s")),
    ("Virgule",
     re.compile(r",")),
    ("Barre oblique",
     re.compile(r"\s*/\s*")),
    ("Deux-points introducteur",
     re.compile(r"\s*:\s*")),
    ("Coordination et, et/ou",
     re.compile(r"\s+et\s+(?![\d])|" + re.escape(ET_OU), re.IGNORECASE)),
]

# Point suspect : un point suivi d'une lettre, ou précédé d'un espace. Séparateur
# dans une minorité de cas, terminal dans la majorité : laissé non exploité.
POINT_SEPARATEUR = re.compile(r"\.\s*(?=[^\W\d_])|\s+\.")

# Un segment sans aucune lettre n'est pas une étiquette (numéro orphelin).
CONTIENT_LETTRE = re.compile(r"[^\W\d_]")

# Numéro d'énumération résiduel. Il subsiste en bordure de segment lorsque le
# marqueur n'est pas ponctué (« 1 Paludisme ») ou lorsque le point de l'item
# suivant est remplacé par une virgule (« 1. paludisme 2, salmonellose »).
# Un chiffre terminal est en revanche significatif après un mot d'échelle :
# diabète de type 2, hypertension de grade 1, coma stade 3.
NUMERO_INITIAL = re.compile(r"^\d{1,2}\s+(?=[^\W\d_])")
NUMERO_TERMINAL = re.compile(r"\s+\d{1,2}$")
MOTS_ECHELLE = {"type", "grade", "stade", "coma", "degre", "classe", "niveau",
                "score", "sa", "phase", "jour", "jours", "an", "ans", "mois"}


def _date(valeur):
    """Convertit une date SQL en date Python, ou None si absente ou nulle."""
    if not valeur or valeur.startswith("0000"):
        return None
    try:
        return datetime.date(int(valeur[0:4]), int(valeur[5:7]), int(valeur[8:10]))
    except (ValueError, IndexError):
        return None


def normaliser(texte):
    """Normalisation de surface, sans toucher au contenu lexical.

    Unicode NFC, suppression des caractères de contrôle, uniformisation des
    espaces et des apostrophes, retrait de la ponctuation terminale. La casse
    et les accents sont conservés : ils font partie de l'objet d'étude.
    """
    t = unicodedata.normalize("NFC", texte)
    t = t.replace("’", "'").replace("‘", "'")
    t = "".join(" " if unicodedata.category(c) == "Cc" else c for c in t)
    t = re.sub(r"\s+", " ", t).strip()
    t = t.strip(" .,;:-")
    return t


def replier(texte):
    """Forme repliée : minuscules et accents retirés, pour le regroupement."""
    t = unicodedata.normalize("NFD", texte.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t).strip()


def segmenter(texte, jusqua=None):
    """Segmente un énoncé en étiquettes candidates.

    `jusqua` limite le traitement aux n premières passes ; None les applique
    toutes. Retourne la liste des segments non vides, dans l'ordre d'apparition.
    """
    morceaux = [texte.replace("et/ou", ET_OU).replace("et / ou", ET_OU)]
    for _, motif in PASSES[:jusqua]:
        suivant = []
        for m in morceaux:
            suivant.extend(motif.split(m))
        morceaux = suivant
    segments = []
    for m in morceaux:
        s = nettoyer_numerotation(normaliser(m.replace(ET_OU, "et/ou")))
        if s and CONTIENT_LETTRE.search(s):
            segments.append(s)
    return segments


def nettoyer_numerotation(segment):
    """Retire les numéros d'énumération restés en bordure de segment."""
    s = NUMERO_INITIAL.sub("", segment)
    m = NUMERO_TERMINAL.search(s)
    if m:
        avant = s[:m.start()].split()
        if avant and replier(avant[-1]) not in MOTS_ECHELLE:
            s = s[:m.start()]
    return s.strip(" .,;:-")


def charger_contexte():
    """Charge les tables de contexte et retourne les index utiles."""
    visites = {v["id_visite"]: v for v in lire_dump.charger("med_visite")}
    patients = {p["id_patient"]: p for p in lire_dump.charger("med_patient")}
    services = {s["id_service"]: s["nom_service"]
                for s in lire_dump.charger("med_service")}
    return visites, patients, services


def age_a(naissance, reference):
    """Âge en années révolues, ou None si l'un des deux jalons manque."""
    if not naissance or not reference or naissance < NAISSANCE_MIN:
        return None
    if naissance > reference or reference > OBSERVATION_MAX:
        return None
    return reference.year - naissance.year - (
        (reference.month, reference.day) < (naissance.month, naissance.day))


def ecrire(chemin, entetes, lignes):
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(entetes)
        w.writerows(lignes)


def main():
    consultations = lire_dump.charger("med_consultation")
    visites, patients, services = charger_contexte()

    corpus, etiquettes = [], []
    compteur_sep = collections.Counter()
    residuel_point = 0

    for c in consultations:
        brut = (c.get("diagnostic") or "").strip()
        if not brut:
            continue
        texte = normaliser(brut)
        if not texte:
            continue

        v = visites.get(c["id_visite"], {})
        p = patients.get(v.get("id_patient"), {})
        date_cs = _date(c.get("date_consultation"))
        naissance = _date(p.get("date_naissance"))
        service = (services.get(c.get("id_service"))
                   or services.get(v.get("id_service")) or "")

        segments = segmenter(texte)
        corpus.append({
            "id_consultation": c["id_consultation"],
            "id_visite": c["id_visite"],
            "id_patient": v.get("id_patient", ""),
            "date_consultation": date_cs.isoformat() if date_cs else "",
            "mois": date_cs.strftime("%Y-%m") if date_cs else "",
            "service": service,
            "type_visite": v.get("type_visite", ""),
            "sexe": p.get("sexe", ""),
            "age": age_a(naissance, date_cs),
            "longueur": len(texte),
            "nb_etiquettes": len(segments),
            "texte_brut": brut,
            "texte_normalise": texte,
        })

        for rang, seg in enumerate(segments, 1):
            etiquettes.append({
                "id_consultation": c["id_consultation"],
                "rang": rang,
                "etiquette": seg,
                "etiquette_repliee": replier(seg),
            })
            if POINT_SEPARATEUR.search(seg):
                residuel_point += 1

        if PASSES[0][1].search(texte):
            compteur_sep["Marqueur d'enumeration (1. 2) ...)"] += 1
        if ";" in texte:
            compteur_sep["Point-virgule"] += 1
        if "," in texte:
            compteur_sep["Virgule"] += 1
        if re.search(r"[\n\r]", texte):
            compteur_sep["Retour a la ligne"] += 1
        if re.search(r"\s\+\s", texte):
            compteur_sep["Signe plus"] += 1
        if re.search(r"et\s*/\s*ou", texte, re.I):
            compteur_sep["Coordination et/ou (disjonction, protegee)"] += 1
        elif "/" in texte:
            compteur_sep["Barre oblique"] += 1
        if ":" in texte:
            compteur_sep["Deux-points introducteur"] += 1
        if re.search(r"\s+et\s+(?![\d])", texte, re.I):
            compteur_sep["Coordination et"] += 1
        if POINT_SEPARATEUR.search(texte):
            compteur_sep["Point (ambigu, non exploite)"] += 1

    # --- sorties de corpus -------------------------------------------------
    champs = ["id_consultation", "id_visite", "id_patient", "date_consultation",
              "mois", "service", "type_visite", "sexe", "age", "longueur",
              "nb_etiquettes", "texte_brut", "texte_normalise"]
    ecrire(os.path.join(CORPUS, "corpus_diagnostics.csv"), champs,
           [[("" if d[k] is None else d[k]) for k in champs] for d in corpus])

    ecrire(os.path.join(CORPUS, "etiquettes_candidates.csv"),
           ["id_consultation", "rang", "etiquette", "etiquette_repliee"],
           [[e["id_consultation"], e["rang"], e["etiquette"],
             e["etiquette_repliee"]] for e in etiquettes])

    formes = collections.Counter(d["texte_normalise"] for d in corpus)
    formes_repliees = collections.Counter(replier(d["texte_normalise"])
                                          for d in corpus)
    ecrire(os.path.join(CORPUS, "formes_distinctes.csv"),
           ["forme_normalisee", "frequence"],
           [[f, n] for f, n in formes.most_common()])

    lexique = collections.Counter(e["etiquette_repliee"] for e in etiquettes)
    total_etq = sum(lexique.values())
    cumul, lignes_lex = 0, []
    for rang, (etq, n) in enumerate(lexique.most_common(), 1):
        cumul += n
        lignes_lex.append([rang, etq, n, round(100.0 * cumul / total_etq, 2)])
    ecrire(os.path.join(CORPUS, "lexique_etiquettes.csv"),
           ["rang", "etiquette_repliee", "frequence", "couverture_cumulee_pct"],
           lignes_lex)

    # --- caractérisation ---------------------------------------------------
    longueurs = sorted(d["longueur"] for d in corpus)
    nb_etq = collections.Counter(d["nb_etiquettes"] for d in corpus)
    hapax_formes = sum(1 for n in formes.values() if n == 1)
    hapax_etq = sum(1 for n in lexique.values() if n == 1)
    multi = sum(n for k, n in nb_etq.items() if k > 1)
    avec_age = sum(1 for d in corpus if d["age"] is not None)

    def quantile(serie, q):
        return serie[min(len(serie) - 1, int(len(serie) * q))]

    def seuil_couverture(pct):
        c = 0
        for rang, (_, n) in enumerate(lexique.most_common(), 1):
            c += n
            if 100.0 * c / total_etq >= pct:
                return rang
        return len(lexique)

    pct = lambda n, d: "%.1f %% " % (100.0 * n / d)
    mesures = [
        ("Consultations sur la periode", len(consultations), "med_consultation"),
        ("Consultations avec diagnostic renseigne", len(corpus),
         pct(len(corpus), len(consultations)) + "de completude"),
        ("Formes normalisees distinctes", len(formes),
         "apres normalisation de surface"),
        ("Formes repliees distinctes", len(formes_repliees),
         "casse et accents neutralises"),
        ("Formes n'apparaissant qu'une fois", hapax_formes,
         pct(hapax_formes, len(formes)) + "des formes"),
        ("Longueur mediane (caracteres)", quantile(longueurs, 0.50), ""),
        ("Longueur au 90e centile", quantile(longueurs, 0.90), ""),
        ("Longueur maximale", longueurs[-1], ""),
        ("Etiquettes candidates extraites", len(etiquettes),
         "%.2f par diagnostic" % (len(etiquettes) / float(len(corpus)))),
        ("Etiquettes repliees distinctes", len(lexique), ""),
        ("Etiquettes n'apparaissant qu'une fois", hapax_etq,
         pct(hapax_etq, len(lexique)) + "du lexique"),
        ("Diagnostics multi-etiquettes", multi, pct(multi, len(corpus)) + "du corpus"),
        ("Etiquettes couvrant 50 % des occurrences", seuil_couverture(50),
         "rang dans le lexique"),
        ("Etiquettes couvrant 80 % des occurrences", seuil_couverture(80),
         "rang dans le lexique"),
        ("Etiquettes couvrant 90 % des occurrences", seuil_couverture(90),
         "rang dans le lexique"),
        ("Segments portant un point residuel", residuel_point,
         pct(residuel_point, len(etiquettes))
         + "des etiquettes : borne de la segmentation par regles"),
        ("Age renseigne et plausible", avec_age, pct(avec_age, len(corpus)) + "du corpus"),
    ]
    ecrire(os.path.join(RESULTATS, "caracterisation_corpus.csv"),
           ["indicateur", "valeur", "precision"], mesures)

    ecrire(os.path.join(RESULTATS, "distribution_etiquettes.csv"),
           ["nb_etiquettes", "nb_diagnostics", "part_pct"],
           [[k, n, round(100.0 * n / len(corpus), 2)]
            for k, n in sorted(nb_etq.items())])

    ecrire(os.path.join(RESULTATS, "inventaire_separateurs.csv"),
           ["separateur", "diagnostics_concernes", "part_pct"],
           [[s, n, round(100.0 * n / len(corpus), 2)]
            for s, n in compteur_sep.most_common()])

    # --- rendement cumulé des passes de segmentation -----------------------
    # Mesure ce que chaque règle ajoutée retire au vocabulaire à annoter.
    textes = [d["texte_normalise"] for d in corpus]
    rendement, precedent = [], None
    for n_passes in range(0, len(PASSES) + 1):
        segments = [s for t in textes for s in segmenter(t, n_passes)]
        lex = collections.Counter(replier(s) for s in segments)
        tot = sum(lex.values())
        c, rang80 = 0, len(lex)
        for r, (_, f) in enumerate(lex.most_common(), 1):
            c += f
            if 100.0 * c / tot >= 80:
                rang80 = r
                break
        libelle = "Aucun decoupage" if n_passes == 0 else PASSES[n_passes - 1][0]
        gain = "" if precedent is None else "%+d" % (len(lex) - precedent)
        rendement.append([n_passes, libelle, len(segments), len(lex), gain,
                          rang80, sum(1 for f in lex.values() if f == 1),
                          round(100.0 * sum(1 for f in lex.values() if f == 1)
                                / len(lex), 1)])
        precedent = len(lex)
    ecrire(os.path.join(RESULTATS, "rendement_segmentation.csv"),
           ["passe", "regle_ajoutee", "segments", "lexique_distinct",
            "variation_lexique", "rang_couvrant_80pct", "hapax", "hapax_pct"],
           rendement)

    for libelle, valeur, precision in mesures:
        print("%-45s %8s  %s" % (libelle, valeur, precision))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
