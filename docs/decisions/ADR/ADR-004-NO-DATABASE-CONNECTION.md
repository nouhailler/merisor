# ADR-004 — Aucune connexion ou exécution SQL automatique

## Statut

Accepté.

## Contexte

La création ou modification d'une base externe augmente fortement les risques,
la configuration et la responsabilité de l'éditeur.

## Décision

MERISOR génère, affiche et exporte du SQL, mais n'ouvre aucune connexion et
n'exécute aucune instruction.

## Conséquences

L'utilisateur garde le contrôle du déploiement. Le reverse engineering travaille
sur un fichier DDL local, pas sur un serveur actif.

## Alternatives rejetées

Des connecteurs intégrés ou migrations automatiques sont hors périmètre de
cette décision et exigeraient une conception de sécurité séparée.
