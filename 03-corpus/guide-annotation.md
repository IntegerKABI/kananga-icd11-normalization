# Guide d'annotation — diagnostics de la polyclinique de Kananga vers la CIM-11

Version 1.0, 24 août 2026. Ce guide est un document de travail : toute règle
ajoutée en cours d'annotation doit y être inscrite, datée, et les étiquettes
déjà traitées sous l'ancienne règle reprises.

---

## 1. Ce qui est annoté

L'unité d'annotation est **l'étiquette**, pas le diagnostic. Un diagnostic est
un énoncé libre saisi par le médecin ; la segmentation automatique l'a découpé
en étiquettes, chacune censée désigner une entité clinique.

> `Paludisme grave, salmonellose probable et infection urinaire`
> → trois étiquettes : `paludisme grave`, `salmonellose probable`,
> `infection urinaire`

Ce choix vient d'une mesure : 70,5 % des diagnostics portent plusieurs entités,
et annoter le **type** d'étiquette plutôt que chaque occurrence divise le volume
par 6,6. Vous annotez donc une liste d'étiquettes distinctes, ordonnée par
fréquence décroissante, dans `lexique_a_annoter.csv`.

La cible est la **linéarisation MMS de la CIM-11**, version notée en tête du
fichier de travail. Le code retenu doit exister dans cette version.

---

## 2. Champs à remplir

| Champ | Contenu |
|---|---|
| `cim11_code` | Code MMS, par exemple `1F40.0`. Un seul code par étiquette |
| `cim11_uri` | URI de l'entité, recopiée depuis le navigateur CIM-11 |
| `cim11_titre` | Libellé officiel, pour contrôle visuel |
| `modificateur_clinique` | Sévérité, évolution, contexte : voir section 5 |
| `certitude` | `affirme`, `probable`, `exclu`, `disjonction` : voir section 6 |
| `hors_perimetre` | `oui` si l'étiquette ne désigne pas une entité clinique |
| `annotateur` | Vos initiales |
| `commentaire` | Obligatoire dès que vous hésitez |

**Le commentaire n'est pas facultatif quand vous hésitez.** C'est lui qui
alimentera la révision des règles, et c'est sur les étiquettes commentées que
se concentrera l'arbitrage.

---

## 3. Règle générale

Coder ce que le médecin a écrit, **pas ce qu'il a probablement voulu dire**.

L'annotation constitue une vérité terrain destinée à évaluer des modèles
automatiques. Si vous corrigez silencieusement le diagnostic à partir de vos
connaissances cliniques, vous produisez une cible qu'aucun système ne peut
atteindre depuis le seul texte, et vous rendez l'évaluation ininterprétable.

La seule exception concerne les fautes de frappe manifestes : voir section 7.

---

## 4. Abréviations

Le corpus contient une cinquantaine d'abréviations locales, dont six pèsent
plus de quarante occurrences chacune. Elles n'appartiennent à aucune ressource
publique.

**Procédure** : consulter d'abord `lexique_abreviations_a_expanser.csv`, qui
porte l'expansion validée par le clinicien de l'établissement. Si l'abréviation
y figure, coder l'expansion. Si elle n'y figure pas, ne pas deviner : inscrire
`hors_perimetre = non`, laisser `cim11_code` vide et écrire en commentaire
`abréviation non résolue`.

Le cas de `SP` fixe la limite : 90 occurrences, et **jamais accompagnée d'une
autre étiquette dans le même diagnostic**. Aucun contexte de cooccurrence ne
permet de la désambiguïser depuis le texte. Elle ne sera résolue que par le
clinicien, ou pas du tout.

À l'inverse, `IU` apparaît 162 fois, dont 127 aux côtés de `paludisme` : son
expansion en `infection urinaire` est étayée par le contexte et par la présence
massive de la forme développée ailleurs dans le corpus.

---

## 5. Modificateurs

14,8 % des occurrences portent un modificateur. Il ne fait **jamais** partie du
libellé codé : il va dans `modificateur_clinique`, séparé par un point-virgule
s'il y en a plusieurs.

| Famille | Formes rencontrées | Traitement |
|---|---|---|
| Sévérité | `grave` (639), `simple` (476), `majeure` (195), `sévère` | Modificateur. Coder l'entité de base, sauf si la CIM-11 distingue explicitement la forme grave |
| Évolution | `aiguë` (482), `chronique` (78), `récidivante` | Modificateur, sauf si la CIM-11 offre une catégorie distincte |
| Réponse au traitement | `d'échec thérapeutique` (106) | Modificateur. La CIM-11 ne code pas cet axe |
| Charge parasitaire | `à forte parasitémie` (73) | Modificateur |
| Spécificité | `aspécifique` (15) | Modificateur |
| Contexte gravidique | `sur grossesse`, `sur grossesse débutante` | **Cas particulier, voir ci-dessous** |

**Quand la CIM-11 distingue elle-même la forme, utilisez sa distinction.** Le
paludisme grave et le paludisme simple ne sont pas la même catégorie MMS :
codez-les différemment et laissez `modificateur_clinique` vide. La règle n'est
donc pas « toujours dépouiller le modificateur », mais : *dépouiller quand la
classification ne le porte pas*.

**Contexte gravidique.** `infection urinaire sur grossesse` n'est pas une
infection urinaire assortie d'une note : la CIM-11 place les affections
survenant pendant la grossesse dans un chapitre propre. Coder l'entité
gravidique lorsqu'elle existe, et signaler en commentaire. Ne jamais coder la
seule entité de base en reléguant la grossesse dans le modificateur.

---

## 6. Incertitude

Le rédacteur exprime son incertitude de trois façons, et les trois doivent
survivre à l'annotation.

| Marque | Exemple du corpus | `certitude` |
|---|---|---|
| Aucune | `paludisme` | `affirme` |
| `probable`, `?`, `suspecte` | `salmonellose probable` ; le marqueur `probable` pèse 295 occurrences | `probable` |
| `et/ou` | `amygdalites et/ou glossite` (29 diagnostics) | `disjonction` |
| `exclure` | `exclure salmonellose` | `exclu` |

L'étiquette est codée dans tous les cas : `salmonellose probable` reçoit le code
de la salmonellose, avec `certitude = probable`. **Ne pas laisser le code vide
sous prétexte que le diagnostic n'est pas certain.** C'est l'information de
certitude qui porte la nuance, pas l'absence de code.

La disjonction `et/ou` a été volontairement protégée par la segmentation :
`amygdalites et/ou glossite` reste une seule étiquette. Codez l'entité citée en
premier et mentionnez la seconde en commentaire.

---

## 7. Fautes de frappe et variantes

289 groupes de variantes ont été détectés automatiquement par distance
d'édition. `paludime`, `pludisme`, `paluidisme` sont des graphies de
`paludisme` : codez-les comme `paludisme`, sans commentaire.

**Mais la ressemblance graphique ne suffit jamais à décider.** Neuf groupes
rapprochent des entités cliniquement opposées, à une ou deux lettres près :

| Ne jamais confondre | |
|---|---|
| `hypertension` | `hypotension` |
| `salmonellose majeure` | `salmonellose mineure` |
| `dermatite` | `dermatose` |
| `gonarthrite` | `gonarthrose` |
| `coxarthrite` | `coxarthrose` |
| `vaginite` | `vaginose` |

Le suffixe `-ite` désigne une inflammation, `-ose` un processus dégénératif ou
une infestation. Devant l'une de ces formes, coder **exactement ce qui est
écrit** et le signaler en commentaire. Si le reste du diagnostic contredit
franchement la forme écrite, le mentionner en commentaire sans changer le code.

---

## 8. Étiquettes qui ne désignent pas une maladie

Certaines étiquettes décrivent un motif de recours, un suivi ou un état
physiologique. Elles relèvent du chapitre 24 de la CIM-11, consacré aux
facteurs influant sur l'état de santé, et **ne sont pas hors périmètre** :
codez-les dans ce chapitre.

| Exemple du corpus | Fréquence | Traitement |
|---|---:|---|
| `suivi post-partum normal` | 42 | Chapitre 24 |
| `contrôle`, `bilan contrôle` | 24 | Chapitre 24 |
| `CPN`, `rendez-vous consultation prénatale` | 13 | Chapitre 24, surveillance de grossesse |
| `grossesse 26SA` | 5 | Grossesse normale ; l'âge gestationnel va en commentaire |

Réservez `hors_perimetre = oui` aux étiquettes qui ne sont pas cliniques du
tout : fragment de phrase, mot isolé sans signification diagnostique, nom
d'examen sans résultat, reliquat de segmentation.

---

## 9. Segments mal découpés

Le point n'a pas été exploité comme séparateur : il est terminal dans la
majorité des cas et frontière dans une minorité. Conséquence mesurée :
**370 segments, soit 2,3 % des étiquettes, restent agglutinés**.

> `paludisme .iu` : deux entités dans une seule étiquette
> `gastroentérite aiguë fébrile: paludisme grave` : reste d'un énoncé plus long

Devant un segment manifestement composite : coder l'entité principale, la
première citée, et écrire en commentaire `segment composite` en listant les
entités restantes. Ne modifiez pas le texte de l'étiquette : la mesure de ce
que la segmentation a manqué fait partie des résultats de l'étude.

---

## 10. Double codage et accord

400 étiquettes de `echantillon_double_codage.csv` sont codées **indépendamment
par deux annotateurs**, sans consultation. Elles sont stratifiées par fréquence,
hapax compris : la strate difficile est représentée à parité, faute de quoi
l'accord serait mesuré sur la seule partie facile du lexique.

Accord calculé séparément sur trois décisions, parce qu'elles n'ont ni la même
difficulté ni la même portée :

1. le code CIM-11 exact ;
2. le code CIM-11 tronqué à la catégorie parente, qui mesure l'accord sur le
   concept indépendamment de la finesse du codage ;
3. le champ `certitude`.

Les désaccords sont arbitrés en séance, par un tiers, et **chaque arbitrage
donne lieu à une règle ajoutée à ce guide**. Le kappa publié est celui du
premier tour, avant arbitrage : c'est le seul qui mesure la reproductibilité
réelle.

---

## 11. Ordre de travail

1. Attendre l'expansion des abréviations par le clinicien de l'établissement.
2. Coder le socle **P1** : 143 étiquettes, 80 % des occurrences du corpus.
3. Double codage des 400 étiquettes, calcul de l'accord, arbitrage, mise à jour
   de ce guide.
4. Reprendre les étiquettes P1 codées avant les règles ajoutées à l'étape 3.
5. Coder **P2** : jusqu'à 830 étiquettes, 90 % des occurrences.
6. **P3** n'est engagé que si l'évaluation montre que la queue de distribution
   change les conclusions. Passer de 90 % à 95 % de couverture double le volume
   d'annotation, pour 1 634 étiquettes : cette dépense doit être justifiée par
   une mesure, pas par le souci d'exhaustivité.
