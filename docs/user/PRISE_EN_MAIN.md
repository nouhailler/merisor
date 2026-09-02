# Prise en main

[← Portail](../INDEX.md) · [Guide complet](GUIDE_UTILISATEUR.md)

Ce parcours construit un petit modèle `CLIENT — PASSER — COMMANDE`, génère son
MLD puis son SQL.

## 1. Créer un document

Lancez MERISOR puis choisissez **Fichier → Nouveau**. Enregistrez tôt avec
`Ctrl+S` : un projet MERISOR est un fichier JSON lisible.

## 2. Créer CLIENT

1. Activez l'outil **Entité**.
2. Cliquez dans le canvas et saisissez `CLIENT`.
3. Sélectionnez l'entité.
4. Dans **Propriétés**, ajoutez `id_client`, `nom` et `email`.
5. Cochez `id_client` comme identifiant.
6. Choisissez `INTEGER` pour `id_client` et `VARCHAR(255)` pour `email`.

## 3. Créer COMMANDE

Créez une seconde entité `COMMANDE` avec :

- `id_commande`, identifiant `INTEGER` ;
- `date_commande`, type `DATE` ;
- `montant`, type `DECIMAL(10,2)`.

## 4. Relier les entités

1. Créez l'association `PASSER`.
2. Activez **Relation** puis cliquez sur `CLIENT` et `PASSER`.
3. Reliez ensuite `COMMANDE` à `PASSER`.
4. Sélectionnez chaque relation et définissez :
   - `CLIENT (0,N)` ;
   - `COMMANDE (1,1)`.

Ce modèle signifie qu'un client peut passer zéro à plusieurs commandes et
qu'une commande appartient obligatoirement à un seul client.

## 5. Valider

Choisissez **Modèle → Valider le MCD…**. Une erreur empêche la génération du
MLD ; un avertissement demande seulement une vérification métier.

## 6. Générer le MLD

Cliquez sur **Générer le MLD**. `CLIENT` et `COMMANDE` deviennent des tables ;
`id_client` migre dans `COMMANDE` comme FK. Sélectionnez la table puis cliquez
sur **ⓘ Pourquoi ?** pour lire la règle appliquée et sa provenance.

## 7. Générer le SQL

Cliquez sur **Générer SQL**, choisissez PostgreSQL, SQLite ou MariaDB/MySQL,
vérifiez l'aperçu puis utilisez **Copier** ou **Enregistrer sous…**. MERISOR
n'exécute jamais le script.

## Pour aller plus loin

- [Édition détaillée du MCD](MCD.md)
- [Comprendre le MLD](MLD.md)
- [Cardinalités](../concepts/CARDINALITES.md)
- [Exemple MotoGP](https://github.com/nouhailler/merisor/blob/main/examples/motogp.json)
