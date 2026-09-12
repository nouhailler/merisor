# Mode étudiant

Le **Mode étudiant** transforme le MCD courant en réponse à un exercice MERISE.
Il est accessible par **Modèle → 🎓 Mode étudiant…** ou `Ctrl+Alt+U`.

## Déroulement

1. Lisez l'énoncé et les hypothèses du barème.
2. Fermez temporairement la fenêtre si nécessaire et construisez votre MCD.
3. Rouvrez le mode étudiant et cliquez sur **Évaluer mon MCD**.
4. Sélectionnez chaque critère pour lire son explication **Pourquoi ?**.
5. Corrigez le MCD puis relancez l'évaluation.

L'évaluation est locale, déterministe et ne modifie jamais le modèle. Elle ne
nécessite ni clé OpenRouter ni connexion réseau.

## Premier exercice

```text
Un client peut passer plusieurs commandes.
Une commande appartient à un seul client.
Une commande contient plusieurs produits.
```

Le barème contrôle :

- les entités `CLIENT`, `COMMANDE` et `PRODUIT` ;
- la présence d'au moins un attribut identifiant dans chaque entité ;
- une association reliant `CLIENT` et `COMMANDE` ;
- une association reliant `COMMANDE` et `PRODUIT` ;
- les cardinalités attendues sur chaque branche.

Les noms d'associations restent libres : `PASSER` et `CONTENIR` sont des noms
naturels, mais l'évaluateur reconnaît la structure par ses extrémités.

## Pourquoi afficher les hypothèses ?

Un court énoncé ne précise pas toujours tous les minima. Par exemple, il ne dit
pas explicitement si un produit peut exister avant sa première commande.
MERISOR affiche donc les choix du corrigé avant de noter : aucune hypothèse
cachée n'est transformée en vérité métier.

Dans l'exercice fourni, le corrigé attend notamment :

```text
CLIENT   (0,N) — PASSER   — (1,1) COMMANDE
COMMANDE (1,N) — CONTENIR — (0,N) PRODUIT
```

La réponse à **Pourquoi `(0,N)` côté CLIENT ?** est qu'un client peut être
enregistré sans avoir encore passé de commande, puis en passer plusieurs. La
cardinalité `(1,1)` côté COMMANDE exprime qu'une commande appartient exactement
à un client.

## Interpréter le résultat

- **Acquis** : le critère déclaré est satisfait par la structure du MCD ;
- **À revoir** : l'élément manque ou diffère du corrigé ;
- **score** : proportion de critères acquis dans cet exercice précis.

Le score n'est ni une certification MERISE ni une preuve que toutes les règles
métier sont justes. Il mesure uniquement le barème visible. Utilisez ensuite la
validation, l'analyse de qualité, la normalisation et les scénarios métier pour
examiner les autres dimensions du modèle.
