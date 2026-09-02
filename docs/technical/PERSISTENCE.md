# Persistance

[← Portail](../INDEX.md) · [Format JSON](JSON_FORMAT.md)

## Source persistée

Le fichier projet contient le MCD et sa présentation : positions, domaines et
vues. Le MLD et le SQL sont dérivés et ne sont pas sauvegardés comme vérité.

## Dépôt JSON

`JsonDiagramRepository` fournit `to_dict`, `from_dict`, `save` et `load`. Il
reconstruit de véritables objets métier et laisse au validateur les états
conceptuels incomplets autorisés pendant l'édition.

## Écriture atomique

L'enregistrement écrit un fichier temporaire dans le dossier cible, le vide sur
disque puis le remplace atomiquement. Une erreur ne doit pas tronquer le projet
existant.

## Migration

La version est lue avant les objets. V1 est migrée en mémoire vers les valeurs
V2 par défaut. Le fichier original n'est modifié que si l'utilisateur enregistre.

## Préférences locales

QSettings conserve thème, grille, guides, minimap, fichiers récents, activation
IA et modèle sélectionné. Ces préférences ne font pas partie du projet.

La clé OpenRouter utilise `keyring` si disponible ; QSettings n'est qu'un repli
signalé comme non chiffré.

## Documents importés

DDL, PWA et IA produisent d'abord un candidat en mémoire. L'import confirmé
remplace le modèle via une commande undo ; il ne réécrit pas le fichier source
importé.
