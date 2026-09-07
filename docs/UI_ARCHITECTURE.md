# Architecture de présentation MERISOR 2.0

## Principes

La nouvelle interface reste une projection du modèle métier. Aucun widget ne
porte une règle MERISE, une règle de transformation ou une règle SQL. Les écritures
passent par `DiagramController`, qui demeure la façade applicative et le point de
synchronisation avec la scène.

```text
Application shell
├── barre des commandes du projet
├── navigation Concevoir / Vérifier / Transformer / Produire / IA
├── palette d'outils contextuelle
├── espaces Accueil / MCD / Vérifier / MLD / SQL / IA / Documentation
├── inspecteur de propriétés
└── bandeau d'état MCD / MLD
              │
              ▼
      DiagramController
       │       │       │
       ▼       ▼       ▼
      MCD     MLD     services
```

## Composants du shell

`WorkflowNavigation` rend visible le parcours utilisateur sans dupliquer les cas
d'usage. Chaque étape redirige vers une vue ou appelle une action existante.

`ToolPalette` ne contient que les outils agissant sur le canvas. Elle réutilise les
`QAction` de la fenêtre, garantissant que menus, raccourcis et boutons déclenchent
exactement les mêmes commandes.

`ModelStatusStrip` présente en permanence :

- la validité du MCD ;
- l'état enregistré ou modifié du projet ;
- l'absence, la fraîcheur ou l'obsolescence du MLD.

Les composants n'importent aucune classe du domaine. Leur état leur est transmis
sous forme de valeurs de présentation.

## Compatibilité

La première étape de migration conserve :

- `workspace_tabs` comme widget central ;
- les attributs publics de `MainWindow` utilisés par les tests et extensions ;
- tous les menus, actions, raccourcis, dialogues et docks existants ;
- le format JSON et les services applicatifs.

Les futurs espaces Vérifier et Produire pourront remplacer progressivement les
dialogues modaux tout en gardant ces derniers comme adaptateurs de compatibilité.

Cette migration est désormais appliquée à Vérifier, SQL, IA et Documentation.
`SQLWorkspace` ne reçoit qu'un `MLDModel`; `ValidationCenter` reçoit un rapport
de validation; `AIHub` déclenche les cas d'usage existants; et
`DocumentationCenter` lit le catalogue Markdown sans dépendre du domaine.

## Rapport de PHASE 2

```text
PHASE : 2 — Application shell
État : terminé

Fichiers créés :
- src/merisor/ui/application_shell.py
- tests/test_application_shell.py
- docs/UI_ARCHITECTURE.md

Fichiers modifiés :
- src/merisor/ui/main_window.py
- src/merisor/ui/theme/tokens.py

Fonctionnalités implémentées :
- navigation explicite du workflow MERISE
- barre de commandes projet allégée
- palette d'outils MCD latérale
- statut permanent MCD/projet/MLD
- icônes système des commandes universelles

Tests exécutés :
- tests du shell
- suite complète de qualité et de non-régression

Régressions détectées :
- aucune

Prochaine phase :
- PHASE 3 — Start Center
```
