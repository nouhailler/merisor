# Questions fréquentes

[← Portail](../INDEX.md)

## MERISOR exécute-t-il le SQL ?

Non. Il affiche, copie ou enregistre les scripts sans connexion à une base.

## Pourquoi « Générer SQL » est-il désactivé ?

Le MLD est absent ou obsolète. Validez le MCD puis régénérez le MLD.

## Puis-je sauvegarder un MCD invalide ?

Oui. Une confirmation est demandée, mais le travail incomplet est conservé.

## Où est ma clé OpenRouter ?

Dans le trousseau système avec `keyring`, sinon dans QSettings avec un
avertissement. Jamais dans le projet JSON.

## L'IA peut-elle modifier mon modèle seule ?

Non. Les candidats et patchs passent par validation, aperçu et confirmation.

## Pourquoi une association historisée devient-elle une table ?

Pour autoriser plusieurs occurrences entre les mêmes participants. Consultez
[Historisation](../concepts/HISTORISATION.md).

## Pourquoi ma FK est-elle nullable ?

La cardinalité minimale source vaut `0`. **ⓘ Pourquoi ?** indique la relation
exacte ayant produit la colonne.

## Le déplacement d'une entité rend-il le MLD obsolète ?

Non. La position n'influence pas la structure logique.

## Puis-je importer une base existante ?

Vous pouvez importer un fichier DDL pris en charge. MERISOR ne se connecte pas
à une base active et ne peut pas déduire toutes les intentions conceptuelles.

## IndexedDB est-il présent dans le dépôt d'une PWA ?

Le dépôt contient généralement le code de définition du schéma, pas les
enregistrements stockés sur le téléphone. L'import PWA analyse Dexie,
IndexedDB natif et certains types TypeScript statiques.

Un projet minimal prêt à tester est fourni dans
[`examples/indexeddb-demo-pwa`](https://github.com/nouhailler/merisor/tree/main/examples/indexeddb-demo-pwa),
ainsi que sous forme d'archive ZIP directement importable.

## Où signaler un problème ?

Sur [GitHub Issues](https://github.com/nouhailler/merisor/issues), avec un JSON
minimal, la version et la distribution. Retirez toute donnée confidentielle.
