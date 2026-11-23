# Output schemas

Column names of every file the pipeline writes. Files marked *not released* stay with the authors;
see the README for the reason.

## Released

- `04-resultats/caracterisation_corpus.csv`: `indicateur`, `valeur`, `precision`
- `04-resultats/contexte_paludisme.csv`: `indicateur`, `valeur`, `pourcentage`, `definition`
- `04-resultats/couverture_cim11.csv`: `indicateur`, `valeur`, `precision`
- `04-resultats/couverture_par_rang.csv`: `rang`, `frequence`, `couverture_cumulee_pct`
- `04-resultats/distribution_etiquettes.csv`: `nb_etiquettes`, `nb_diagnostics`, `part_pct`
- `04-resultats/inventaire_abreviations.csv`: `etiquette_repliee`, `forme_source_frequente`, `frequence`, `indice`
- `04-resultats/inventaire_separateurs.csv`: `separateur`, `diagnostics_concernes`, `part_pct`
- `04-resultats/modificateurs.csv`: `modificateur`, `etiquettes_distinctes`, `occurrences`
- `04-resultats/plan_annotation.csv`: `poste`, `volume`, `precision`
- `04-resultats/rendement_appariement.csv`: `methode`, `types`, `types_pct`, `occurrences`, `occurrences_pct`
- `04-resultats/rendement_segmentation.csv`: `passe`, `regle_ajoutee`, `segments`, `lexique_distinct`, `variation_lexique`, `rang_couvrant_80pct`, `hapax`, `hapax_pct`
- `04-resultats/variantes_orthographiques_resume.csv`: `groupe`, `frequence_ancre`, `nb_variantes`, `occurrences_groupe`, `part_variantes_pct`, `fusion_suspecte`

## Not released

- `03-corpus/corpus_diagnostics.csv` (one row per consultation): `id_consultation`, `id_visite`, `id_patient`, `date_consultation`, `mois`, `service`, `type_visite`, `sexe`, `age`, `longueur`, `nb_etiquettes`, `texte_brut`, `texte_normalise`
- `03-corpus/etiquettes_candidates.csv` (one row per candidate label of a consultation): `id_consultation`, `rang`, `etiquette`, `etiquette_repliee`
- `03-corpus/echantillon_evaluation.csv` (330 whole statements set aside for end-to-end evaluation): `id_consultation`, `service`, `mois`, `sexe`, `age`, `nb_etiquettes_automatiques`, `texte_normalise`, `etiquettes_de_reference`, `(annotation columns)`
- `04-resultats/croisement_paludisme_goutte_epaisse.csv` (one row per consultation with a malaria label): `id_consultation`, `date_consultation`, `service`, `diagnostic`, `etiquettes_paludisme`, `nb_gouttes_epaisses`, `nb_resultats`, `statut_parasitologique`, `espece_documentee`, `pf_candidat`, `resultats_ge`
- `03-corpus/formes_distinctes.csv` (one row per distinct normalized statement): `forme_normalisee`, `frequence`
- `03-corpus/lexique_etiquettes.csv` (one row per label type): `rang`, `etiquette_repliee`, `frequence`, `couverture_cumulee_pct`
- `03-corpus/lexique_a_annoter.csv` (annotation worklist, one row per label type): `rang`, `forme_a_annoter`, `etiquette_repliee`, `frequence`, `couverture_cumulee_pct`, `priorite`, `cim11_code`, `cim11_uri`, `cim11_titre`, `modificateur_clinique`, `certitude`, `hors_perimetre`, `annotateur`, `commentaire`
- `03-corpus/echantillon_double_codage.csv` (400 labels drawn for double coding): `strate`, `forme_a_annoter`, `etiquette_repliee`, `frequence`, `cim11_code`, `cim11_uri`, `cim11_titre`, `modificateur_clinique`, `certitude`, `hors_perimetre`, `annotateur`, `commentaire`
- `03-corpus/lexique_abreviations_a_expanser.csv` (candidate abbreviations awaiting local validation): `forme_source_frequente`, `etiquette_repliee`, `frequence`, `cooccurrences_frequentes`, `resolvable_par_contexte`, `expansion_validee`, `code_cim11_suggere`, `clinicien`, `commentaire`
- `04-resultats/appariement_baseline.csv` (baseline match for each label type): `rang`, `etiquette`, `frequence`, `methode`, `relation`, `codable`, `score`, `forme_appariee`, `cim11_code`, `cim11_titre_fr`, `cim11_titre_en`, `source_de_la_forme`, `cibles_possibles`
- `04-resultats/variantes_orthographiques.csv` (spelling variant groups, with the variant strings): `forme_ancre`, `frequence_ancre`, `nb_variantes`, `occurrences_groupe`, `part_variantes_pct`, `variantes`, `fusions_suspectes`
