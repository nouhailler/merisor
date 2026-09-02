# ADR-006 — Un MLD indépendant et des dialectes SQL

## Statut

Accepté.

## Contexte

PostgreSQL, SQLite et MariaDB/MySQL diffèrent sur les types, identités, citations
et cycles.

## Décision

Conserver un `MLDModel` dialecte-neutre puis déléguer le rendu à des sous-classes
`SQLDialect` partageant un générateur commun.

## Conséquences

Ajouter un SGBD ne réécrit pas MCD → MLD. Les différences restent centralisées
et testables.

## Alternatives rejetées

Des conditions `if database` dispersées ou des types SQL dans le MLD auraient
couplé toutes les couches.
