# Normalizing abbreviated French clinical diagnoses to ICD-11: code and aggregated results

Companion material for the manuscript *Normalizing abbreviated French clinical diagnoses to ICD-11 in a
low-resource setting: corpus construction, difficulty analysis and a lexical baseline* (Grâce Murhula Kabi,
Evariste Ntaryamira), currently under review.

The study characterizes the free-text diagnoses of 10,072 consecutive consultations recorded over twelve
months in a general polyclinic in Kananga, Democratic Republic of the Congo, measures what stands in the way
of their normalization to the ICD-11 Mortality and Morbidity Statistics linearization (release 2026-01), and
reports an audited lexical baseline.

## What is here

| Path | Content |
|---|---|
| `02-scripts/` | The eight scripts of the analytical pipeline (Python, standard library; `matplotlib` for the figures) |
| `03-corpus/guide-annotation.md` | The annotation guideline (in French) |
| `04-resultats/*.csv` | The aggregated tables behind every table and figure of the manuscript |
| `04-resultats/figures/` | Figures 1 to 4, in English and French, with captions and alternative texts |
| `SCHEMAS.md` | Column names of every file the pipeline writes, including the files that are not released |

Scripts, comments and column names are in French, the working language of the project.

| Manuscript item | File |
|---|---|
| Table 1, corpus characteristics | `caracterisation_corpus.csv` |
| Table 2 and Fig. 2, yield of the segmentation passes | `rendement_segmentation.csv`, `inventaire_separateurs.csv` |
| Table 3, writing variation | `inventaire_abreviations.csv`, `variantes_orthographiques_resume.csv`, `modificateurs.csv` |
| Fig. 3, cumulative coverage | `couverture_par_rang.csv` |
| Fig. 4, labels per statement | `distribution_etiquettes.csv` |
| Annotation load | `plan_annotation.csv` |
| ICD-11 coverage | `couverture_cim11.csv` |
| Table 4, lexical baseline | `rendement_appariement.csv` |
| Table 5, thick blood smear context of malaria | `contexte_paludisme.csv` |

## What is not here, and why

No individual-level record is distributed. The source records are free-text clinical diagnoses collected
during routine care at a single facility; the authorization under which they were accessed prohibits their
redistribution, and the risk of re-identification cannot be excluded at that granularity.

For the same reason this repository does not contain the list of distinct diagnostic statements, the label
lexicons, the annotation samples or the per-label baseline output: they are made of the diagnoses' own
wording, and most statements occur only once. Three tables are released without their free-text columns
(`modificateurs.csv`, `inventaire_abreviations.csv`, and `variantes_orthographiques_resume.csv`, which keeps
the size of each spelling-variant group but not its strings). `SCHEMAS.md` documents the columns of all the
files that are withheld. Requests for access are handled as described in the data availability statement of
the article; contact the corresponding author.

The ICD-11 tabulation is not redistributed either: `recuperer_cim11.py` downloads it from the World Health
Organization, which distributes it under its own licence.

## Pipeline

Run from `02-scripts/`, in this order. Steps 1 to 3 and 6 need the source database dump, which is not
distributed; they are published so that the method can be audited and reused on another dump.

| Step | Script | Reads | Writes |
|---|---|---|---|
| 0 | `lire_dump.py` | MariaDB dump (module used by the others) | — |
| 1 | `extraire_corpus.py` | dump | corpus files, `caracterisation_corpus.csv`, `distribution_etiquettes.csv`, `inventaire_separateurs.csv`, `rendement_segmentation.csv` |
| 2 | `caracteriser_variation.py` | candidate labels | `inventaire_abreviations.csv`, `variantes_orthographiques.csv`, `modificateurs.csv` |
| 3 | `preparer_annotation.py` | corpus files | annotation worklist and samples, `plan_annotation.csv` |
| 4 | `recuperer_cim11.py` | WHO download | `01-donnees/cim11_mms.csv`, `couverture_cim11.csv` |
| 5 | `apparier_baseline.py` | label lexicon, ICD-11 tabulation | `appariement_baseline.csv`, `rendement_appariement.csv` |
| 6 | `analyser_contexte_paludisme.py` | dump, corpus files | `contexte_paludisme.csv` |
| 7 | `generer_figures.py` | aggregated tables | `04-resultats/figures/` |

The path of the dump is read from the environment variable `KANANGA_DUMP` (default: `01-donnees/dump.sql`).
The figures can be regenerated from this repository alone: `python generer_figures.py`.

## Differences from the authors' working copy

The scripts are those used for the manuscript, with two edits made for publication: `lire_dump.py` no longer
hard-codes the name of the production dump, and Fig. 3 in `generer_figures.py` reads `couverture_par_rang.csv`
(rank, frequency, cumulative coverage) instead of the label lexicon, from which that table is derived by
dropping the label strings. `variantes_orthographiques_resume.csv` is derived in the same way.

## Use of a large language model

A large language model (Claude, Anthropic) assisted the authors in writing these scripts. The scripts were
run locally on the data; no patient-level record and no diagnostic statement was submitted to the model.

## Licence and citation

Code and tables are released under the MIT licence (see `LICENSE`). To cite this material, see
`CITATION.cff`; please cite the article once it is published.
