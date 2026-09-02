# Contexte et principes de conception

[← Portail](../INDEX.md) · [ADR](ADR/ADR-001-MCD-SOURCE-VERITE.md)

## Vision

MERISOR est un éditeur MERISE pédagogique et professionnel. Il doit rendre les
transformations explicables sans réduire le diagramme à une image.

## Source de vérité

```text
MCD → MLD → SQL
```

Le MLD est régénérable ; le SQL est exportable. Aucun artefact dérivé ne modifie
automatiquement le MCD. Les imports inverses sont des workflows explicites avec
avertissements, aperçu et confirmation.

## Séparation

Le domaine contient les faits et règles. L'application orchestre et transforme.
La persistance sérialise. Qt affiche et collecte les intentions utilisateur.

## Sécurité

Pas de connexion SQL, pas d'exécution automatique, pas de clé dans les projets.
Une IA ou un import ne produit qu'un candidat non fiable validé localement.

## Compatibilité

Les projets V1/V2 restent lisibles. Tout ajout JSON possède un défaut. Le MLD
reste dialecte-neutre.

## Explicabilité

Validation, qualité, normalisation, impact et **ⓘ Pourquoi ?** produisent des
raisons déterministes. Les suggestions heuristiques ou IA affichent leur
incertitude et exigent une décision humaine.

## Évolution

Le projet préfère une extension modulaire accompagnée de tests à une réécriture
des versions précédentes. Les décisions structurantes sont enregistrées dans
les ADR de ce dossier.
