# Comprendre MERISE

[← Portail](../INDEX.md) · [Prise en main](../user/PRISE_EN_MAIN.md)

MERISE sépare la compréhension du métier de sa traduction technique.

```text
MCD conceptuel → MLD logique → SQL physique
```

## MCD

Le Modèle Conceptuel de Données décrit les faits métier sans dépendre d'un
SGBD. Il utilise :

- **entités** : concepts identifiables (`CLIENT`, `PRODUIT`) ;
- **attributs** : informations portées par un concept (`email`, `prix`) ;
- **associations** : faits reliant les entités (`PASSER`, `CONTENIR`) ;
- **cardinalités** : nombre minimal et maximal de participations ;
- **identifiants** : attributs distinguant chaque occurrence.

## MLD

Le Modèle Logique de Données exprime tables, colonnes, PK, FK et contraintes,
mais reste indépendant de PostgreSQL, SQLite ou MySQL.

## SQL

Le SQL est la traduction physique du MLD dans un dialecte. Les types et
l'auto-incrémentation varient selon la cible.

## Exemple

```text
CLIENT (0,N) ── PASSER ── (1,1) COMMANDE
```

Chaque entité devient une table. La relation 1:N migre l'identifiant de CLIENT
dans COMMANDE comme clé étrangère. La cardinalité minimale `0` autorise ou non
la nullabilité selon le côté porteur déterminé par la règle.

## Pourquoi conserver les niveaux ?

- le métier peut évoluer sans dépendre d'un moteur SQL ;
- plusieurs dialectes sont générables depuis le même modèle ;
- une erreur conceptuelle est détectée avant le script ;
- le MCD reste lisible par un public non développeur.

MERISOR respecte cette séparation jusque dans son architecture. Consultez les
[règles MCD → MLD](REGLES_MCD_MLD.md).
