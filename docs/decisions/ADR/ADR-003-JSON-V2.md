# ADR-003 — Format JSON V2 versionné

## Statut

Accepté.

## Contexte

Les modèles doivent être lisibles, échangeables et enrichissables sans perdre
les fichiers historiques.

## Décision

Utiliser un JSON avec `format_version`, IDs stables et références explicites.
Charger V1/V2, migrer en mémoire et écrire V2 lors d'un enregistrement demandé.

## Conséquences

Chaque nouveau champ exige une valeur par défaut et un test de compatibilité.
Le MLD n'est pas inclus car il est dérivé.

## Alternatives rejetées

Un format binaire ou la sérialisation directe d'objets Python limiterait
l'interopérabilité et les migrations.
