# Contexte de reprise du projet MERISOR

## État de l'intégration OpenRouter

Les trois étapes prévues sont terminées :

1. récupération et sélection des modèles gratuits OpenRouter ;
2. génération d'un JSON MCD avec validation, sans modifier le modèle courant ;
3. aperçu éditable et import confirmé du MCD généré dans l'éditeur.

La génération OpenRouter s'exécute désormais dans un `QThread` dédié. Le worker
ne touche jamais aux widgets ; le résultat, les erreurs, la validation et
l'ouverture de l'aperçu reviennent sur le thread principal Qt. La prochaine
reprise peut se concentrer sur les retours d'usage ou l'amélioration des prompts.

## Typage des attributs MCD

Les attributs portent désormais un `MLDDataType` logique optionnel. Une valeur
`None` correspond au mode automatique historique (`INTEGER` pour un identifiant,
`VARCHAR(100)` sinon). Un type explicite, y compris les paramètres de `VARCHAR`
et `DECIMAL`, est sauvegardé dans le JSON V2, intégré à l'empreinte du MCD et
propagé sans perte vers le MLD puis le générateur SQL.

Les anciens fichiers sans champ `data_type` restent compatibles et ne changent
pas de résultat logique.

## Associations avancées et héritages ISA

Les relations portent un rôle optionnel. Deux branches reliant la même entité à
la même association doivent avoir des rôles non vides et distincts ; le
contrôleur les initialise automatiquement. Les associations n-aires deviennent
des tables MLD, tandis que les réflexives appliquent les règles N:N, 1:N ou 1:1
avec des FK nommées selon leur rôle.

Le MCD possède aussi des objets `Inheritance` avec les stratégies
`PARENT_ONLY`, `CHILDREN_ONLY` et `JOINED`. Le mode joint produit une PK/FK vers
la table mère. Les modes aplatis refusent actuellement les associations portées
par une table qui serait supprimée, afin de ne jamais produire un MLD ambigu.

## Reverse-engineering DDL

`SQLDDLImporter` lit les `CREATE TABLE`, `CREATE INDEX` et les FK ajoutées par
`ALTER TABLE` dans les dialectes courants PostgreSQL/SQLite. Le MLD importé est
la représentation fidèle ; le MCD est une reconstruction heuristique présentée
à l'utilisateur avant confirmation. Les tables de jointure deviennent des
associations et une PK également FK devient un ISA `JOINED`. L'import ne se
connecte à aucune base et ignore, avec avertissement, les instructions hors DDL
prises en charge.

## Contraintes à conserver

- ne jamais enregistrer la clé API dans un fichier de projet JSON ;
- ne jamais remplacer le MCD courant sans confirmation explicite ;
- valider tout JSON produit par l'IA avant de l'importer ;
- conserver la séparation entre interface, service OpenRouter et modèle métier ;
- exécuter les tests existants avant de poursuivre.
