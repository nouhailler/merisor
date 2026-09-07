# Principes UX de MERISOR 2.0

## Le workflow avant les fonctions

L'interface suit quatre verbes : **Concevoir**, **Vérifier**, **Transformer** et
**Produire**. L'IA est transversale. Une fonction avancée doit être placée selon
l'intention de l'utilisateur et non selon son module Python.

## Entrée progressive

Le Start Center propose d'abord trois choix immédiatement compréhensibles : créer,
ouvrir ou solliciter l'assistant. Les imports et exemples restent visibles sans
transformer l'accueil en formulaire. Un exemple est toujours chargé comme un
nouveau modèle non enregistré afin de ne jamais écraser sa source.

## Préserver le contexte

- privilégier un panneau ou espace de travail aux boîtes modales successives ;
- conserver le canvas visible pendant l'édition et la vérification ;
- afficher les états MCD, projet et MLD en permanence ;
- permettre de revenir à Concevoir en une action ;
- ne jamais appliquer une proposition IA sans aperçu et confirmation.

## Hiérarchie des actions

- primaire : une seule action qui fait avancer l'utilisateur ;
- secondaire : alternatives sûres ;
- destructive : libellé explicite, rôle visuel danger et confirmation si la
  récupération par Annuler n'est pas possible ;
- indisponible : état désactivé accompagné d'une explication accessible.

## Messages

Les messages répondent à trois questions : que s'est-il passé, pourquoi, et que
faire ensuite. Une erreur technique brute n'est jamais présentée à l'utilisateur.
Les erreurs bloquantes, avertissements et succès utilisent à la fois un texte, un
symbole et une couleur sémantique.

## Accessibilité

- ordre de tabulation logique ;
- focus visible ;
- nom accessible pour toute commande iconique ;
- libellé associé à chaque champ ;
- texte non transmis uniquement par la couleur ;
- raccourcis existants préservés et documentés ;
- SQL, JSON et code seuls emploient une police monospace.

## Recherche et raccourcis transversaux

- `Ctrl+K` ouvre la palette de commandes ;
- `Ctrl+Shift+F` recherche dans MCD, MLD et documentation ;
- `F1` ouvre la documentation intégrée ;
- `Espace + glisser` déplace le canvas ;
- `Ctrl + molette` zoome sans changer d'outil.

Les états vide, prêt, avertissement, erreur et obsolète sont exprimés par un
symbole et un texte, jamais uniquement par une couleur.

## Rapport de PHASE 3

```text
PHASE : 3 — Start Center
État : terminé

Fichiers créés :
- src/merisor/ui/start_center.py
- tests/test_start_center.py
- docs/UX_GUIDELINES.md

Fichiers modifiés :
- src/merisor/ui/main_window.py
- src/merisor/ui/theme/tokens.py

Fonctionnalités implémentées :
- accueil MERISOR orienté découverte
- nouveau modèle, ouverture et assistant IA
- modèles récents et exemples
- accès direct aux imports SQL/DDL et PWA

Tests exécutés :
- tests du Start Center
- suite complète de qualité et de non-régression

Régressions détectées :
- aucune

Prochaine phase :
- PHASE 4 — Canvas MCD
```
