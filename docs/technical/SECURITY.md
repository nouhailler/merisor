# Sécurité et confidentialité

[← Portail](../INDEX.md) · [Architecture IA](AI_ARCHITECTURE.md)

## Clé OpenRouter

- jamais enregistrée dans le JSON, SQL, logs, documentation ou dépôt Git ;
- stockée dans le trousseau système avec `keyring` ;
- repli QSettings non chiffré avec avertissement visible ;
- champ masqué dans l'interface.

## Données envoyées

Aucun réseau n'est utilisé par les fonctions locales. Une action IA explicite
peut transmettre : description métier, MCD/brouillon, réponses, validation et
signaux locaux nécessaires. Les données passent par OpenRouter et le fournisseur
du modèle choisi.

Ne transmettez pas de secrets, données personnelles ou modèles confidentiels
sans base légale et autorisation.

## Validation des réponses

Le JSON IA est considéré non fiable : schéma strict, limites de taille/nombre,
rechargement par le dépôt, validation MCD, aperçu et confirmation. Les patchs
ne peuvent modifier les IDs ou viser des objets absents.

## Fichiers

- sauvegarde JSON atomique ;
- import DDL sans exécution ;
- import PWA local avec limites, exclusion de `node_modules`/build/binaires et
  aucune extraction ZIP sur le disque ;
- export SQL sans connexion ni exécution ;
- aucune suppression automatique du fichier importé.

## Logs et messages

Les erreurs destinées à l'utilisateur sont reformulées. Une clé ne doit jamais
être interpolée dans une exception. Les tests utilisent uniquement de fausses
valeurs clairement identifiées.

## Signalement

Avant de joindre un JSON, une capture ou un log à une issue, retirez les clés,
données personnelles et noms métier sensibles.

## Périmètre

MERISOR n'est pas un gestionnaire de secrets, n'audite pas un serveur SQL et ne
garantit pas qu'un script convient à une production. La revue et l'exécution
restent sous la responsabilité de l'utilisateur.
