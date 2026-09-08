# Tester le MCD avec des scénarios métier

La commande **Modèle → Tester un scénario métier…** (`Ctrl+Shift+T`) confronte
le MCD à un usage fonctionnel avant la génération de la base.

## Écrire un scénario

Donnez un titre puis saisissez une attente métier par ligne :

```text
Scénario : Emprunter un livre

Un lecteur peut effectuer plusieurs emprunts
Un exemplaire peut être emprunté plusieurs fois dans le temps
Un emprunt possède une date de début
Un emprunt possède une date de retour
Déterminer si un exemplaire est disponible à une date donnée
```

Employez les noms présents dans le MCD. MERISOR reconnaît les variantes
simples, notamment singulier/pluriel et accents.

## Lire le résultat

Le rapport présente d'abord le chemin métier retrouvé dans le graphe :

```text
LECTEUR → EFFECTUER → EMPRUNT → CONCERNER → EXEMPLAIRE → LIVRE
```

Chaque attente reçoit ensuite un statut :

- **Satisfait** : la structure apporte une preuve directe, par exemple une
  cardinalité maximale `N` ou un attribut présent ;
- **Risque** : le chemin, la cardinalité ou l'attribut attendu manque ;
- **Non vérifiable** : la règle dépasse ce que la structure du MCD peut
  démontrer, par exemple la disponibilité à une date ou l'absence de
  chevauchement entre deux périodes.

Le rapport peut être copié. L'analyse est locale, déterministe et ne modifie
jamais le modèle.

## Limites volontaires

Cette première version n'interprète pas librement tout le langage naturel. Elle
s'appuie sur les concepts explicitement nommés, les chemins du graphe, les
cardinalités et les attributs. Une règle de calcul, une contrainte temporelle ou
une politique métier reste **non vérifiable** tant qu'elle n'est pas formalisée
ailleurs. Une future assistance IA pourra reformuler les attentes, mais ne
devra jamais transformer une hypothèse en preuve.

