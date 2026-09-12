# Simuler un changement avec « Et si… ? »

Le mode **Et si… ?** permet d'examiner les conséquences d'une suppression avant
de modifier le MCD. Il est accessible par **Modèle → Et si… ? Analyser un
changement…** ou avec `Ctrl+Alt+I`. Depuis les propriétés d'un attribut, le même
outil s'ouvre directement sur cet attribut.

## Parcours

1. Choisissez une entité, une association ou un attribut.
2. MERISOR effectue la suppression sur une copie en mémoire.
3. Consultez le rapport et les éventuelles nouvelles erreurs de validation.
4. Choisissez **Annuler** ou **Continuer et supprimer**.
5. Après confirmation, **Édition → Annuler** restaure encore le changement.

Tant que vous n'avez pas choisi **Continuer et supprimer**, le modèle courant,
le fichier du projet et le canvas restent inchangés.

## Couches analysées

- **MCD** : élément supprimé, relations et dépendances fonctionnelles ;
- **MLD** : colonnes directes ou migrées, PK, FK, UNIQUE et CHECK ;
- **SQL** : colonnes, contraintes et index qui disparaîtront à la régénération ;
- **documentation** : vues et inventaires qu'il faudra régénérer ;
- **données de test** et **requêtes** : livrables générés à la demande.

Les impacts fondés sur une provenance structurelle sont marqués **Certains**.
Les correspondances de nom et livrables non enregistrés sont marqués **À
confirmer**. MERISOR ne prétend pas connaître le nombre de documents, jeux de
données ou requêtes externes qui utilisent un élément.

## Exemple

Pour la suppression de `CLIENT.email`, le rapport peut indiquer :

```text
Impact MCD
  CLIENT.email

Impact MLD
  CLIENT.email

Impact SQL
  Colonne CLIENT.email
  UNIQUE(email)

Impact documentation
  Documentation générée — à régénérer
```

Si `email` est utilisé dans une dépendance fonctionnelle ou un index explicite,
ces dépendances apparaissent également. Si la suppression crée une erreur (par
exemple la disparition du seul identifiant d'une entité), elle est affichée
avant la confirmation.

## Limites actuelles

Cette première version interactive simule les suppressions. L'ancien moteur
d'analyse reste utilisé comme fondation pour les dépendances. Les scénarios de
renommage, de changement de type et de cardinalité pourront utiliser la même
architecture lors d'une évolution ultérieure.
