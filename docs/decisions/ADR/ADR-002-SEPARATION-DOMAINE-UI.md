# ADR-002 — Séparation du domaine et de l'interface

## Statut

Accepté.

## Contexte

Les règles MERISE doivent être testables sans serveur graphique et réutilisables
par les imports, générateurs et futurs outils.

## Décision

`domain` ne dépend pas de Qt. `application` porte orchestration et transformations.
`ui` représente les objets et passe par le contrôleur pour les mutations.

## Conséquences

Les tests métier sont rapides. Les `QGraphicsItem` ne deviennent jamais la
source des données.

## Alternatives rejetées

Placer attributs, cardinalités ou suppression dans les objets graphiques aurait
couplé le modèle au canvas.
