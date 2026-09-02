# Normalisation

[← Portail](../INDEX.md) · [Guide utilisateur](../user/GUIDE_UTILISATEUR.md)

La normalisation réduit les redondances et les anomalies de mise à jour. Une
analyse formelle exige les **dépendances fonctionnelles** réellement connues du
métier.

## Dépendance fonctionnelle

`A → B` signifie que la valeur de `A` détermine une seule valeur de `B`. Exemple :

```text
code_postal → ville
```

MERISOR permet de saisir les déterminants et dépendants, calcule la fermeture
d'un ensemble d'attributs et recherche les clés candidates.

## Première forme normale — 1NF

Chaque valeur doit être atomique et aucun groupe répétitif ne doit être caché
dans un attribut. La sémantique étant nécessaire, MERISOR fournit des indices
pédagogiques plutôt qu'une certitude automatique.

Exemples à vérifier : `telephones`, `adresse_complete`, `produit_1/produit_2`.

## Deuxième forme normale — 2NF

Une relation en 1NF est en 2NF lorsque tout attribut non-clé dépend de la clé
entière, pas seulement d'une partie d'une clé composée.

## Troisième forme normale — 3NF

Une relation en 2NF est en 3NF lorsqu'un attribut non-clé ne dépend pas
transitivement d'un autre attribut non-clé.

## Assistant MERISOR

**Modèle → Assistant de normalisation…** affiche :

- dépendances déclarées ;
- fermetures et clés candidates ;
- violations 1NF/2NF/3NF ;
- explications pédagogiques ;
- aperçu d'une décomposition.

Le MCD courant n'est modifié qu'après confirmation et l'application est
annulable. Les suggestions IA facultatives ne remplacent pas les règles métier
déclarées par l'utilisateur.
