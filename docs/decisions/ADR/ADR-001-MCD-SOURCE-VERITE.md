# ADR-001 — Le MCD est la source de vérité

## Statut

Accepté.

## Contexte

Le MLD et le SQL peuvent être recalculés depuis les intentions conceptuelles.
L'inverse perd les cardinalités, l'historisation et des notions métier.

## Décision

Le document persistant autoritatif est le MCD. MLD, SQL et documentation sont
des artefacts dérivés et signalés obsolètes après une modification logique.

## Conséquences

Le générateur SQL ne lit jamais le MCD. Un reverse engineering crée un candidat
MCD explicite, jamais une synchronisation silencieuse.

## Alternatives rejetées

Sauvegarder et éditer simultanément MCD et MLD créerait deux vérités difficiles
à réconcilier.
