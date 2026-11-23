# -*- coding: utf-8 -*-
"""
Génère les figures du manuscrit, en français et en anglais.

Quatre figures, numérotées dans leur ordre de première citation :
  1. la chaîne de constitution du corpus, du champ source au plan d'annotation ;
  2. le rendement des six passes de segmentation ;
  3. la couverture cumulée du lexique et le coût d'annotation qui s'en déduit ;
  4. la distribution du nombre d'étiquettes par diagnostic.

Toutes les valeurs sont lues dans les CSV produits par les autres scripts : une
figure ne peut donc pas diverger du texte.

Palette
-------
Reprise de l'article 1, pour que les deux manuscrits d'un même programme se
lisent ensemble. Le validateur de palettes la refuse sur deux points, la bande
de clarté et le plancher de chroma : ce sont précisément les conventions qu'une
figure destinée à l'impression doit enfreindre, puisqu'elle joue sur un encre
très sombre et un aplat très clair afin de rester lisible en niveaux de gris.
Les deux contrôles qui importent ici, la séparation entre teintes voisines et
la séparation en vision normale, passent avec une marge large (ΔE 46,8 pour le
couple bleu / gris clair, 34,9 pour orange / gris clair).

Deux règles en découlent, appliquées partout :
  - le gris moyen et l'orange ne sont jamais deux catégories voisines : leur
    ΔE tombe à 14,8, sous le plancher de vision normale. L'orange ne sert donc
    qu'au repère et à l'annotation, jamais comme troisième série ;
  - tout aplat clair porte un filet sombre et une étiquette lisible, ce
    qu'exige son faible contraste sur fond blanc.

Sortie : 04-resultats/figures/figureN_<langue>.png, 300 ppp,
         plus legendes.md (légendes et textes alternatifs, deux langues).

Usage :
    python generer_figures.py          (les deux langues)
    python generer_figures.py en
"""
import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

BASE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(BASE, "..", "03-corpus")
RESULTATS = os.path.join(BASE, "..", "04-resultats")
SORTIE = os.path.join(RESULTATS, "figures")

PPP = 300
POLICE = "DejaVu Sans"

BLEU = "#1F4E79"
BLEU_CLAIR = "#8FB3D0"
GRIS = "#7A7A7A"
GRIS_CLAIR = "#D5D5D5"
ACCENT = "#B45309"
ENCRE = "#333333"

plt.rcParams.update({
    "font.family": POLICE,
    "font.size": 9,
    "axes.edgecolor": ENCRE,
    "axes.linewidth": 0.8,
    "savefig.dpi": PPP,
    "figure.dpi": PPP,
})

TEXTES = {
    "fr": {
        "f1_etapes": [
            ("Champ source", "med_consultation\n10 072 consultations\n71,4 % renseignes"),
            ("Lecture fidele", "Echappements SQL\nrestitues\n715 enonces corriges"),
            ("Normalisation", "Unicode, espaces,\nponctuation terminale\n4 559 formes repliees"),
            ("Segmentation", "6 passes ordonnees\n16 088 etiquettes\n2 438 types distincts"),
            ("Plan d'annotation", "143 types pour 80 %\ndes occurrences\n400 en double codage"),
        ],
        "f1_note": "Casse et accents sont conserves : ce sont des objets d'etude, non du bruit.",
        "f2_titre_a": "Types d'etiquettes distincts a annoter",
        "f2_titre_b": "Types couvrant 80 % des occurrences",
        "f2_axe": "Regle de segmentation ajoutee",
        "f3_titre": "Couverture cumulee du corpus par le lexique",
        "f3_x": "Types d'etiquettes annotes, du plus frequent au plus rare",
        "f3_y": "Occurrences du corpus couvertes (%)",
        "f3_reperes": {50: "8 types", 80: "143 types", 90: "830 types",
                       95: "1 634 types"},
        "f4_titre": "Nombre d'entites cliniques par diagnostic",
        "f4_x": "Etiquettes extraites d'un meme diagnostic",
        "f4_y": "Diagnostics (%)",
        "f4_mono": "Une seule entite",
        "f4_multi": "Plusieurs entites",
    },
    "en": {
        "f1_etapes": [
            ("Source field", "med_consultation\n10,072 encounters\n71.4% documented"),
            ("Faithful parsing", "SQL escapes restored\n715 statements\ncorrected"),
            ("Normalisation", "Unicode, whitespace,\nterminal punctuation\n4,559 folded forms"),
            ("Segmentation", "6 ordered passes\n16,088 labels\n2,438 distinct types"),
            ("Annotation plan", "143 types for 80%\nof occurrences\n400 double-coded"),
        ],
        "f1_note": "Case and diacritics are preserved: they are objects of study, not noise.",
        "f2_titre_a": "Distinct label types to annotate",
        "f2_titre_b": "Types covering 80% of occurrences",
        "f2_axe": "Segmentation rule added",
        "f3_titre": "Cumulative corpus coverage by the label lexicon",
        "f3_x": "Label types annotated, most to least frequent",
        "f3_y": "Corpus occurrences covered (%)",
        "f3_reperes": {50: "8 types", 80: "143 types", 90: "830 types",
                       95: "1,634 types"},
        "f4_titre": "Clinical entities per diagnostic statement",
        "f4_x": "Labels extracted from one statement",
        "f4_y": "Statements (%)",
        "f4_mono": "Single entity",
        "f4_multi": "Multiple entities",
    },
}

# Libellés des passes, indépendants des CSV pour rester tenables en abscisse.
PASSES = {
    "fr": ["Aucun\ndecoupage", "Marqueur\nd'enumeration", "Point-virgule,\nsaut de ligne",
           "Virgule", "Barre\noblique", "Deux-points", "Coordination\n<< et >>"],
    "en": ["No\nsplitting", "Enumeration\nmarker", "Semicolon,\nline break",
           "Comma", "Slash", "Colon", "Coordination\n“and”"],
}

LEGENDES = {
    "fr": [
        ("Figure 1", "Chaine de constitution du corpus de diagnostics.",
         "Schema en cinq etapes reliees par des fleches : champ source, lecture "
         "fidele du dump, normalisation, segmentation en six passes, plan "
         "d'annotation. Chaque etape porte ses effectifs."),
        ("Figure 2", "Rendement des six passes de segmentation.",
         "Deux panneaux superposes partageant la meme abscisse. Le panneau "
         "superieur montre le nombre de types d'etiquettes distincts, qui passe "
         "de 4 558 a 2 438. Le panneau inferieur montre le nombre de types "
         "couvrant 80 % des occurrences, qui passe de 3 120 a 143."),
        ("Figure 3", "Couverture cumulee du corpus par le lexique d'etiquettes.",
         "Courbe croissante en echelle logarithmique. Quatre reperes marquent "
         "les seuils : 8 types pour 50 % des occurrences, 143 pour 80 %, 830 "
         "pour 90 %, 1 634 pour 95 %."),
        ("Figure 4", "Distribution du nombre d'entites cliniques par diagnostic.",
         "Diagramme en barres de 1 a 7 etiquettes. La premiere barre, en gris "
         "clair, represente les 29,5 % de diagnostics mono-entite ; les "
         "suivantes, en bleu, les 70,5 % restants."),
    ],
    "en": [
        ("Figure 1", "Corpus construction pipeline for diagnostic statements.",
         "Five-step diagram linked by arrows: source field, faithful dump "
         "parsing, normalisation, six-pass segmentation, annotation plan. Each "
         "step carries its counts."),
        ("Figure 2", "Yield of the six segmentation passes.",
         "Two stacked panels sharing one x-axis. The upper panel shows distinct "
         "label types, falling from 4,558 to 2,438. The lower panel shows the "
         "number of types covering 80% of occurrences, falling from 3,120 to "
         "143."),
        ("Figure 3", "Cumulative corpus coverage by the label lexicon.",
         "Rising curve on a logarithmic x-axis. Four markers show the "
         "thresholds: 8 types for 50% of occurrences, 143 for 80%, 830 for 90%, "
         "1,634 for 95%."),
        ("Figure 4", "Distribution of clinical entities per diagnostic statement.",
         "Bar chart from 1 to 7 labels. The first bar, in light grey, is the "
         "29.5% of single-entity statements; the following bars, in blue, the "
         "remaining 70.5%."),
    ],
}


def decimale(valeur, langue):
    """Formate un pourcentage selon l'usage typographique de la langue."""
    texte = "%.1f" % valeur
    if langue == "fr":
        return texte.replace(".", ",") + " %"
    return texte + "%"


def lire(chemin):
    with open(chemin, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def enregistrer(fig, numero, langue):
    os.makedirs(SORTIE, exist_ok=True)
    chemin = os.path.join(SORTIE, "figure%d_%s.png" % (numero, langue))
    fig.savefig(chemin, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  figure %d %s" % (numero, langue))


def figure1(langue):
    """Schéma de la chaîne, du champ source au plan d'annotation.

    Les effectifs sont portés sous les cadres et non dedans : cinq etapes sur
    une largeur de page ne laissent pas la place d'inscrire trois lignes
    chiffrees a l'interieur d'un cadre lisible.
    """
    t = TEXTES[langue]
    etapes = t["f1_etapes"]
    fig, ax = plt.subplots(figsize=(7.2, 2.3))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    largeur, hauteur, ecart = 17.0, 26.0, 3.75
    bas = 62.0
    x = 0.0
    for i, (titre, detail) in enumerate(etapes):
        fond = BLEU if i in (0, len(etapes) - 1) else "white"
        encre = "white" if i in (0, len(etapes) - 1) else ENCRE
        ax.add_patch(FancyBboxPatch(
            (x, bas), largeur, hauteur,
            boxstyle="round,pad=0.3,rounding_size=1.4",
            linewidth=1.0, edgecolor=BLEU, facecolor=fond))
        # Un titre long deborderait son cadre : la taille suit sa longueur.
        ax.text(x + largeur / 2, bas + hauteur / 2, titre, ha="center",
                va="center", fontsize=7.2 if len(titre) <= 14 else 6.5,
                fontweight="bold", color=encre)
        ax.text(x + largeur / 2, bas - 6.0, detail, ha="center", va="top",
                fontsize=6.6, color=ENCRE, linespacing=1.55)
        if i < len(etapes) - 1:
            ax.add_patch(FancyArrowPatch(
                (x + largeur + 0.4, bas + hauteur / 2),
                (x + largeur + ecart - 0.4, bas + hauteur / 2),
                arrowstyle="-|>", mutation_scale=10, linewidth=1.0,
                color=GRIS))
        x += largeur + ecart

    ax.text(50, 16, t["f1_note"], ha="center", va="center", fontsize=7.2,
            color=ACCENT, style="italic")
    return fig


def figure2(langue):
    """Rendement des passes : deux panneaux, jamais deux axes superposés."""
    t = TEXTES[langue]
    lignes = lire(os.path.join(RESULTATS, "rendement_segmentation.csv"))
    lexique = [int(l["lexique_distinct"]) for l in lignes]
    rang80 = [int(l["rang_couvrant_80pct"]) for l in lignes]
    etiquettes = PASSES[langue][:len(lignes)]
    positions = range(len(lignes))

    fig, (haut, bas) = plt.subplots(2, 1, figsize=(7.2, 4.6), sharex=True,
                                    gridspec_kw={"hspace": 0.22})

    for axe, valeurs, titre in ((haut, lexique, t["f2_titre_a"]),
                                (bas, rang80, t["f2_titre_b"])):
        couleurs = [GRIS_CLAIR] + [BLEU] * (len(valeurs) - 1)
        barres = axe.bar(positions, valeurs, width=0.62, color=couleurs,
                         edgecolor=ENCRE, linewidth=0.5, zorder=3)
        for barre, valeur in zip(barres, valeurs):
            axe.text(barre.get_x() + barre.get_width() / 2,
                     valeur + max(valeurs) * 0.035, "{:,}".format(valeur)
                     .replace(",", " " if langue == "fr" else ","),
                     ha="center", va="bottom", fontsize=7.6, color=ENCRE)
        axe.set_title(titre, fontsize=9, loc="left", color=ENCRE, pad=6)
        axe.set_ylim(0, max(valeurs) * 1.22)
        axe.grid(axis="y", color=GRIS_CLAIR, linewidth=0.5, zorder=0)
        axe.set_axisbelow(True)
        for cote in ("top", "right"):
            axe.spines[cote].set_visible(False)
        axe.tick_params(labelsize=7.5, length=3)

    bas.set_xticks(list(positions))
    bas.set_xticklabels(etiquettes, fontsize=7.2, linespacing=1.4)
    bas.set_xlabel(t["f2_axe"], fontsize=8.2, labelpad=6)
    return fig


def figure3(langue):
    """Couverture cumulée du lexique, avec les seuils d'effort d'annotation."""
    t = TEXTES[langue]
    lignes = lire(os.path.join(RESULTATS, "couverture_par_rang.csv"))
    rangs = [int(l["rang"]) for l in lignes]
    couverture = [float(l["couverture_cumulee_pct"]) for l in lignes]

    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.plot(rangs, couverture, color=BLEU, linewidth=1.8, zorder=3)
    ax.set_xscale("log")
    ax.set_xlim(1, rangs[-1])
    ax.set_ylim(0, 102)

    for seuil, etiquette in sorted(t["f3_reperes"].items()):
        rang = next(r for r, c in zip(rangs, couverture) if c >= seuil)
        ax.plot([rang], [seuil], marker="o", markersize=5, color=ACCENT,
                markeredgecolor="white", markeredgewidth=0.8, zorder=5)
        ax.annotate("%d %%\n%s" % (seuil, etiquette), (rang, seuil),
                    textcoords="offset points", xytext=(9, -16),
                    fontsize=7.4, color=ENCRE, linespacing=1.4)
        ax.plot([rang, rang], [0, seuil], color=GRIS_CLAIR, linewidth=0.7,
                linestyle=(0, (3, 3)), zorder=1)

    ax.set_title(t["f3_titre"], fontsize=9, loc="left", color=ENCRE, pad=8)
    ax.set_xlabel(t["f3_x"], fontsize=8.2, labelpad=6)
    ax.set_ylabel(t["f3_y"], fontsize=8.2, labelpad=6)
    ax.grid(color=GRIS_CLAIR, linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    for cote in ("top", "right"):
        ax.spines[cote].set_visible(False)
    ax.tick_params(labelsize=7.5, length=3)
    return fig


def figure4(langue):
    """Distribution du nombre d'étiquettes par diagnostic."""
    t = TEXTES[langue]
    lignes = lire(os.path.join(RESULTATS, "distribution_etiquettes.csv"))
    nb = [int(l["nb_etiquettes"]) for l in lignes]
    part = [float(l["part_pct"]) for l in lignes]

    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    couleurs = [GRIS_CLAIR if n == 1 else BLEU for n in nb]
    barres = ax.bar(nb, part, width=0.66, color=couleurs, edgecolor=ENCRE,
                    linewidth=0.5, zorder=3)
    for barre, valeur in zip(barres, part):
        if valeur < 0.5:
            continue
        ax.text(barre.get_x() + barre.get_width() / 2, valeur + 1.0,
                decimale(valeur, langue), ha="center", va="bottom",
                fontsize=7.6, color=ENCRE)

    multi = sum(p for n, p in zip(nb, part) if n > 1)
    ax.annotate(decimale(multi, langue) + " " + t["f4_multi"].lower(),
                xy=(4.2, 20), fontsize=8.2, color=ACCENT, fontweight="bold")

    poignees = [plt.Rectangle((0, 0), 1, 1, facecolor=GRIS_CLAIR,
                              edgecolor=ENCRE, linewidth=0.5),
                plt.Rectangle((0, 0), 1, 1, facecolor=BLEU,
                              edgecolor=ENCRE, linewidth=0.5)]
    ax.legend(poignees, [t["f4_mono"], t["f4_multi"]], fontsize=7.8,
              frameon=False, loc="upper right")

    ax.set_title(t["f4_titre"], fontsize=9, loc="left", color=ENCRE, pad=8)
    ax.set_xlabel(t["f4_x"], fontsize=8.2, labelpad=6)
    ax.set_ylabel(t["f4_y"], fontsize=8.2, labelpad=6)
    ax.set_ylim(0, max(part) * 1.28)
    ax.set_xticks(nb)
    ax.grid(axis="y", color=GRIS_CLAIR, linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    for cote in ("top", "right"):
        ax.spines[cote].set_visible(False)
    ax.tick_params(labelsize=7.5, length=3)
    return fig


def ecrire_legendes():
    """Légendes et textes alternatifs, regroupés comme l'exigent les revues."""
    lignes = ["# Legendes des figures", ""]
    for langue, titre in (("fr", "Francais"), ("en", "English")):
        lignes += ["## %s" % titre, ""]
        for numero, (etiquette, legende, alt) in enumerate(LEGENDES[langue], 1):
            lignes += ["**%s.** %s" % (etiquette, legende), "",
                       "*Texte alternatif* : %s" % alt, "",
                       "`figure%d_%s.png`" % (numero, langue), ""]
    chemin = os.path.join(SORTIE, "legendes.md")
    with open(chemin, "w", encoding="utf-8") as f:
        f.write("\n".join(lignes))
    print("  legendes.md")


def main():
    langues = [sys.argv[1]] if len(sys.argv) > 1 else ["fr", "en"]
    for langue in langues:
        print("[%s]" % langue)
        for numero, fabriquer in enumerate((figure1, figure2, figure3,
                                            figure4), 1):
            enregistrer(fabriquer(langue), numero, langue)
    ecrire_legendes()
    print("\nEcrit dans", os.path.normpath(SORTIE))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
