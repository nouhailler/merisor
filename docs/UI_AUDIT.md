# Audit UI/UX de MERISOR — référence avant refonte 2.0

## Statut

- Phase : **0 — Audit du projet**
- État : **terminée**
- Révision auditée : `71a2bd6`
- Version applicative : `0.10.1`
- Environnement local : Python 3.13.5, PySide6 6.11.2, Qt 6.11.2
- Date de l'audit : 3 septembre 2026

Cet audit constitue l'état de référence avant toute refonte graphique. Aucun
comportement métier, format de données ni composant visuel n'a été modifié pour
l'établir.

## Architecture actuelle

MERISOR respecte déjà une séparation nette entre les données métier, les cas
d'usage, la persistance et Qt :

```text
UI PySide6
  MainWindow, canvas, panneaux, dialogues
                 │ signaux / actions
                 ▼
Couche application
  DiagramController, commandes undo/redo, services
        │                       │
        ▼                       ▼
Modèle métier              Transformations
  MCDModel, MLDModel         MCD → MLD → SQL
        │
        ▼
Persistance JSON V1/V2
```

### Interfaces structurantes

| Interface | Responsabilité actuelle | Observation UI/UX |
|---|---|---|
| `MCDModel` | Source de vérité conceptuelle : entités, associations, relations, ISA, domaines et dépendances fonctionnelles | Indépendant de Qt et directement testable ; à conserver tel quel |
| `DiagramController` | Façade applicative, synchronisation modèle/scène, sélection, commandes annulables, chargement et génération du MLD | Bonne frontière pour brancher une nouvelle présentation sans déplacer le métier dans l'UI |
| `McdToMldTransformer` | Transformation déterministe du MCD validé | Ne doit pas être réécrit par la refonte |
| `MLDModel` | Tables, colonnes, PK, FK, contraintes, provenance | Suffisamment riche pour plusieurs représentations visuelles |
| `SQLGenerator` | Validation du MLD et génération multi-dialecte | Le dialogue SQL ne reçoit déjà que le MLD, ce qui respecte le workflow cible |
| `validate_mcd` | Rapport métier structuré avec erreurs et avertissements | Le rapport peut alimenter un centre de validation non modal |
| Services IA | Génération, assistant conversationnel et réparation via OpenRouter | Les appels longs disposent déjà de workers Qt ; les écrans restent à harmoniser |
| `JsonDiagramRepository` | Lecture, migration V1/V2 et écriture atomique | Contrat rétrocompatible à préserver ; aucune donnée de présentation 2.0 ne doit le casser |

## Inventaire de l'interface actuelle

### Fenêtre principale

`MainWindow` est une fenêtre Qt de 1 212 lignes qui construit et connecte :

- une barre de menus complète (`Fichier`, `Paramètres`, `Édition`, `Modèle`,
  `Outils`, `Affichage`, `Documentation`) ;
- une barre d'outils unique mêlant marque, outils de dessin, validation,
  analyse, IA, génération et recherche ;
- un `QTabWidget` central contenant le MCD et le MLD ;
- un dock droit qui alterne entre propriétés MCD et propriétés MLD ;
- un dock de minimap ;
- une barre d'état utilisée surtout pour des messages éphémères et le zoom.

La fenêtre centralise aussi l'ouverture de la plupart des dialogues, les thèmes,
les fichiers récents, les imports/exports et le changement de contexte MCD/MLD.
Elle constitue le principal point de risque de la refonte.

### Canvas MCD

Le canvas repose correctement sur `QGraphicsScene` / `QGraphicsView` et offre
déjà :

- sélection simple et multiple ;
- création d'entités, d'associations et de relations ;
- déplacement avec mise à jour des liens ;
- zoom, déplacement panoramique et adaptation à la scène ;
- grille, aimantation et guides ;
- alignement et distribution ;
- copier, coller et dupliquer ;
- pliage et masquage des attributs ;
- recherche visuelle et minimap ;
- export visuel.

Les items graphiques connaissent leur identifiant métier, mais la synchronisation
reste assurée par le contrôleur. Cette séparation est saine. Les couleurs,
dimensions et styles sont en revanche codés directement dans `canvas.py`,
`items.py`, `mld_view.py` et plusieurs dialogues.

### Panneau de propriétés

Le panneau droit utilise un `QStackedWidget` pour les états vide, nœud et
relation. Il permet déjà l'édition complète des attributs (nom, type logique,
longueur, précision, échelle, présence, défaut, unicité, auto-incrémentation,
commentaire et contraintes), des identifiants, des cardinalités, des rôles et
des propriétés de matérialisation.

La couverture fonctionnelle est forte, mais la densité est importante : arbre
d'attributs, formulaires longs et actions secondaires cohabitent sans hiérarchie
visuelle uniforme. La sélection multiple n'offre pas encore de véritable résumé
contextuel.

### Validation et analyses

La validation, la qualité, l'impact, la normalisation, la comparaison de versions,
l'exploration et l'explication des transformations sont présentés dans des
dialogues modaux indépendants. Leurs structures sont adaptées à leurs données
(`QTreeWidget`, détails, onglets), mais elles fragmentent le parcours
« concevoir → vérifier » et limitent le focus direct sur l'objet concerné.

### MLD

La vue MLD propose une représentation graphique et une représentation textuelle,
le zoom, la copie, l'export et un panneau de propriétés. Les tables sont disposées
sur une grille fixe de trois colonnes. Les liens FK sont des lignes directes entre
centres ; la lisibilité baisse donc avec les modèles denses. Le statut « non
généré / à jour / obsolète » existe déjà et peut devenir l'indicateur d'étape du
workflow 2.0.

### SQL

Le SQL est présenté dans un dialogue modal avec choix PostgreSQL, SQLite ou
MySQL/MariaDB, validation, aperçu monospace, copie et export. La séparation MLD →
SQL est correcte. L'écran peut être intégré comme espace de travail sans modifier
le générateur.

### IA

MERISOR possède les paramètres OpenRouter, la génération de MCD, la réparation
assistée et un assistant conversationnel. Les candidats sont prévisualisés et
confirmés avant import. Les écrans emploient des workers `QThread` pour préserver
la réactivité. Les textes, états de chargement, erreurs et actions doivent être
unifiés par le futur design system.

### Documentation

Le centre de documentation hors ligne dispose d'une arborescence, d'une recherche,
d'un lecteur Markdown et de liens internes/externes. Il est fonctionnel et
réutilisable, mais exclusivement modal.

### Paramètres et apparence

Les réglages de canvas et le thème sont stockés avec `QSettings`. Trois modes sont
présents : système, clair et sombre. Le sombre repose actuellement sur une feuille
QSS assemblée dans `MainWindow`, tandis que le clair retombe sur le style Qt natif.
Il n'existe pas encore de tokens partagés, de gestionnaire de thème ni de catalogue
de composants.

## Composants réutilisables

- `DiagramController` et sa pile undo/redo ;
- `DiagramScene`, `DiagramView` et la minimap ;
- les items MCD et leurs signaux de déplacement/sélection ;
- `PropertiesPanel` et `MLDPropertiesPanel` comme sources fonctionnelles ;
- les modèles de rapports de validation, qualité, impact et normalisation ;
- `MLDView` et `SQLPreviewDialog`, à envelopper dans les futurs espaces de travail ;
- les services IA et leurs workers ;
- le catalogue et le navigateur de documentation ;
- toutes les actions existantes, raccourcis et réglages persistés ;
- les importeurs, exporteurs et générateurs indépendants de Qt.

## Composants à refondre ou à extraire

1. Extraire de `MainWindow` un shell applicatif, une navigation de workflow, une
   fabrique d'actions et des espaces de travail spécialisés.
2. Centraliser couleurs, typographie, espacements, rayons, états et QSS dans
   `merisor.ui.theme`.
3. Remplacer la barre d'outils unique surchargée par des commandes contextuelles
   liées à l'étape active.
4. Faire du panneau droit un inspecteur contextuel cohérent avec un état vide,
   une sélection simple, une sélection multiple et les objets MLD.
5. Transformer validation et analyses en centre de vérification navigable, tout
   en gardant les dialogues compatibles pendant la migration.
6. Intégrer MCD, vérification, MLD et SQL dans une navigation explicite sans
   toucher aux transformations.
7. Ajouter un Start Center au-dessus des opérations existantes de fichier/import.
8. Harmoniser les dialogues IA, SQL et documentation avec les composants partagés.

## Constats UX prioritaires

- Le workflow métier existe dans les fonctions mais n'est pas visible dans la
  structure principale de l'application.
- La barre d'outils présente trop d'actions de niveaux différents sans
  regroupement ni priorité claire.
- Les nombreux dialogues interrompent le contexte et masquent parfois le canvas.
- Les états MCD valide, MLD obsolète et SQL indisponible existent, mais ne sont pas
  rassemblés dans un même indicateur de progression.
- Les actions désactivées n'expliquent pas toujours la condition manquante.
- Le thème clair dépend du système, le thème sombre est partiel, et des couleurs
  sémantiques sont dupliquées dans le code.
- Plusieurs boutons n'ont qu'un symbole (`+`, `-`) ; leur nom accessible est
  parfois présent, mais l'effort n'est pas systématique.
- Les messages reposent largement sur des boîtes modales ; il manque des retours
  non bloquants et une zone persistante de problèmes.
- Les fonctions avancées sont nombreuses et difficiles à découvrir pour un
  nouvel utilisateur malgré une documentation riche.

## Tests et état de référence

La suite contient des tests unitaires métier, des tests de transformation et de
persistance, des tests d'intégration MCD → MLD → SQL, des tests UI Qt hors écran,
des tests d'import/export et des tests de distribution.

Commandes exécutées avant toute refonte :

```bash
.venv/bin/python -m ruff format --check .
.venv/bin/python -m ruff check .
.venv/bin/python -m mypy
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

Résultat de référence :

```text
146 fichiers déjà formatés
Ruff : aucun problème
mypy strict : aucun problème dans 107 fichiers source
pytest : 351 tests réussis en 1,31 s
```

## Risques et mesures de protection

| Risque | Mesure de migration |
|---|---|
| Régression due au volume de responsabilités de `MainWindow` | Extraire par petites façades, conserver les attributs/actions publics utilisés par les tests |
| Rupture des tests UI qui ciblent des widgets précis | Garder les noms d'objets et fournir des adaptateurs pendant la transition |
| Modification involontaire du modèle ou du JSON | Interdire aux nouveaux widgets d'écrire directement dans le domaine ; passer par le contrôleur |
| Perte de fonctions avancées dans une navigation simplifiée | Tenir un inventaire action → nouvel emplacement et tester chaque entrée |
| Incohérence clair/sombre | Utiliser des tokens sémantiques et générer un QSS complet pour chaque mode |
| Canvas moins performant | Conserver les items et algorithmes ; ne changer que le rendu et les contrôles autour |
| Dialogues trop nombreux migrés d'un coup | Maintenir les dialogues existants comme solution de repli, puis intégrer écran par écran |
| Accessibilité régressée par des contrôles iconiques | Associer texte, info-bulle, nom accessible, focus visible et raccourci |

## Stratégie de migration

La refonte sera incrémentale et compatible :

1. introduire le design system sans modifier le métier ;
2. construire le shell autour des vues existantes ;
3. ajouter le Start Center en réutilisant les actions de fichier ;
4. moderniser le canvas sans changer son contrat avec le contrôleur ;
5. restructurer l'inspecteur à fonctionnalités constantes ;
6. intégrer la validation et les analyses à partir des rapports existants ;
7. rendre explicite la chaîne MCD → MLD → SQL ;
8. habiller les vues MLD, SQL, IA et documentation ;
9. terminer par accessibilité, recherche globale, palette de commandes et tests
   visuels.

Après chaque phase, la suite complète sera relancée. Toute extraction conservera
temporairement les API publiques nécessaires aux tests et aux extensions
existantes. Le MCD restera la source de vérité ; aucune règle MERISE, règle SQL ni
version JSON ne sera modifiée par la présentation.

## Rapport de PHASE 0

```text
PHASE : 0 — Audit
État : terminé

Fichiers créés :
- docs/UI_AUDIT.md

Fichiers modifiés :
- aucun

Fonctionnalités implémentées :
- aucune (audit préalable uniquement)

Tests exécutés :
- ruff format --check
- ruff check
- mypy strict
- pytest Qt hors écran

Résultat des tests :
- 351 réussis, 0 échec

Régressions détectées :
- aucune

Problèmes restants :
- design system absent
- shell et workflow non structurés
- forte concentration des responsabilités dans MainWindow

Prochaine phase :
- PHASE 1 — Design system
```
