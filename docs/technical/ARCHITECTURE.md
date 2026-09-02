# Architecture logicielle

[← Portail](../INDEX.md) · [Modèle de données](DATA_MODEL.md)

## Principes

- le domaine ne dépend pas de Qt ;
- le MCD est la source de vérité ;
- MLD et SQL sont dérivés ;
- les mutations passent par le contrôleur et des commandes annulables ;
- la persistance JSON est indépendante de l'interface ;
- les appels réseau ne bloquent pas le thread graphique.

## Couches

```text
src/merisor/
├── domain/       objets MCD/MLD, validation, qualité, normalisation
├── application/  contrôleurs, commandes, transformateurs, générateurs
├── persistence/  dépôt JSON V1/V2
├── ui/           fenêtre, scènes, panneaux et dialogues PySide6
└── assets/       identité graphique
```

### Domaine

`MCDModel` agrège entités, associations, relations, ISA, dépendances
fonctionnelles, domaines et vues. `MLDModel` contient les objets logiques
indépendants de tout dialecte. Les règles structurelles et analyses n'importent
aucun module Qt.

### Application

`DiagramController` orchestre le document et la scène. Les commandes Qt Undo
encapsulent les changements. Les services indépendants couvrent notamment :

- `McdToMldTransformer` et `MldTransformationExplainer` ;
- `SQLGenerator` et ses dialectes ;
- reverse engineering DDL/PWA ;
- exploration, impact, comparaison et documentation ;
- brouillons, patchs et services OpenRouter.

### Persistance

`JsonDiagramRepository` convertit `MCDModel` en JSON V2, charge V1/V2 et réalise
une écriture atomique. Le MLD n'est pas sauvegardé.

### Interface

Les `QGraphicsItem` représentent le modèle mais ne portent pas les règles
MERISE. Les panneaux demandent leurs modifications au contrôleur. Les dialogues
d'aperçu manipulent des copies tant que l'utilisateur n'a pas confirmé.

## Flux principal

```text
MCDModel
  ├── JsonDiagramRepository ↔ fichier JSON
  ├── validate_mcd
  ├── McdToMldTransformer → MLDModel
  │                            ├── vues MLD
  │                            └── SQLGenerator → texte SQL
  └── ModelDocumentationGenerator → Markdown/HTML/PDF
```

Le générateur SQL ne reçoit aucun `MCDModel`. La position graphique est exclue
de l'empreinte logique.

## Événements d'état

Une mutation logique invalide le MLD ; un déplacement ne le fait pas. Le
contrôleur émet les signaux `model_changed`, `mld_changed`, `mld_stale_changed`
et `dirty_changed`. L'interface active ses actions à partir de cet état.

## Extension

- nouvelle règle métier : domaine/application + tests, puis représentation UI ;
- nouveau dialecte : sous-classe `SQLDialect` enregistrée dans la fabrique ;
- nouveau format d'import : produire un candidat MCD/MLD avec avertissements,
  aperçu et confirmation ;
- nouvelle IA : sortie structurée, validation locale et aucune mutation directe.
