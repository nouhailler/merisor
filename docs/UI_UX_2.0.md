# MERISOR UI/UX 2.0
## Cahier des charges et prompt d'implémentation pour Codex

**Projet :** MERISOR  
**Objectif :** Refonte complète UI/UX  
**Technologie :** Python / PySide6  
**Plateforme :** Linux Desktop  
**Version cible :** MERISOR UI/UX 2.0

---

# 1. MISSION DE CODEX

Tu travailles sur le projet **MERISOR**, une application desktop Linux de modélisation MERISE.

Ta mission est d'effectuer une **refonte complète de l'expérience utilisateur et de l'interface graphique de MERISOR**, appelée :

> **MERISOR UI/UX 2.0**

Cette évolution ne doit pas être une simple modification esthétique.

Il s'agit d'une **refonte UX, UI, navigation, hiérarchie visuelle, interactions et présentation des fonctionnalités**.

MERISOR possède déjà un moteur fonctionnel important.

L'objectif est de faire en sorte que sa puissance soit :

- visible ;
- compréhensible ;
- intuitive ;
- agréable ;
- moderne ;
- professionnelle ;
- pédagogique.

---

# 2. PROBLÈME À RÉSOUDRE

L'interface actuelle de MERISOR donne une impression :

- trop sobre ;
- trop technique ;
- trop uniforme ;
- peu engageante ;
- parfois difficile à comprendre ;
- de fonctionnalités parfois cachées ou insuffisamment mises en valeur.

Cela ne signifie pas que les fonctionnalités sont insuffisantes.

Au contraire, MERISOR dispose d'un ensemble fonctionnel riche.

Le problème principal est :

> **La richesse fonctionnelle n'est pas suffisamment communiquée par l'interface.**

La refonte doit donc améliorer principalement :

1. la hiérarchie visuelle ;
2. la navigation ;
3. la découverte des fonctionnalités ;
4. la lisibilité du MCD ;
5. la compréhension MCD → MLD → SQL ;
6. la visibilité des erreurs ;
7. la compréhension des transformations ;
8. la cohérence graphique ;
9. l'accessibilité ;
10. le plaisir d'utilisation.

---

# 3. RÈGLE ABSOLUE : NE PAS RÉÉCRIRE LE MOTEUR MERISE

Avant toute modification, inspecter le projet.

Analyser notamment :

```text
src/merisor/
tests/
docs/
examples/
pyproject.toml
README.md
CHANGELOG.md
CONTEXT.md
```

Identifier :

- modèles domaine ;
- contrôleurs ;
- commandes ;
- undo/redo ;
- validation ;
- transformation MCD → MLD ;
- génération SQL ;
- persistance ;
- IA ;
- imports ;
- exports ;
- documentation ;
- composants UI ;
- signaux Qt ;
- tests.

---

# 4. PRINCIPE ARCHITECTURAL

La nouvelle UI doit rester une couche de présentation.

Conserver autant que possible :

```text
┌──────────────────────┐
│      DOMAIN          │
├──────────────────────┤
│    APPLICATION       │
├──────────────────────┤
│     PERSISTENCE      │
├──────────────────────┤
│         UI           │
└──────────────────────┘
```

Le domaine ne doit pas dépendre de PySide6.

Ne pas déplacer la logique métier dans les widgets.

Ne pas dupliquer :

- validation ;
- transformation MLD ;
- génération SQL ;
- règles MERISE.

---

# 5. MÉTHODE DE TRAVAIL OBLIGATOIRE

Tu dois travailler par phases.

Ne pas réaliser une énorme modification monolithique.

À chaque phase :

```text
ANALYSER
↓
IMPLÉMENTER
↓
TESTER
↓
INSPECTER
↓
CORRIGER
↓
DOCUMENTER
```

Avant toute modification :

```bash
pytest
```

Conserver le résultat comme état de référence.

---

# 6. PHASE 0 — AUDIT DU PROJET

Avant de coder l'interface, réaliser un audit du projet.

Identifier :

## UI actuelle

- fenêtre principale ;
- menus ;
- toolbars ;
- canvas ;
- panneaux ;
- dialogues ;
- vues MLD ;
- vues SQL ;
- IA ;
- documentation ;
- paramètres.

## Architecture

Identifier les interfaces entre :

```text
MCDModel
McdToMldTransformer
MLDModel
SQLGenerator
Validation
AI
Persistence
UI
```

## Tests

Identifier :

- tests unitaires ;
- tests d'intégration ;
- tests UI ;
- tests de régression.

Créer éventuellement :

```text
docs/UI_AUDIT.md
```

Ce document doit résumer :

- architecture actuelle ;
- composants réutilisables ;
- composants à refondre ;
- risques ;
- dépendances ;
- stratégie de migration.

---

# 7. NOUVELLE PHILOSOPHIE UX

MERISOR doit être organisé autour du workflow utilisateur.

Le workflow principal devient :

```text
① CONCEVOIR
      ↓
② VÉRIFIER
      ↓
③ TRANSFORMER
      ↓
④ PRODUIRE
```

---

# 8. CONCEVOIR

Cette section correspond au modèle conceptuel.

Fonctions :

- MCD ;
- entités ;
- associations ;
- attributs ;
- identifiants ;
- cardinalités ;
- associations historisées ;
- héritage ;
- associations réflexives ;
- associations n-aires.

---

# 9. VÉRIFIER

Cette section regroupe :

- validation ;
- qualité ;
- normalisation ;
- cohérence ;
- analyse d'impact ;
- comparaison de versions.

---

# 10. TRANSFORMER

Cette section regroupe :

- MLD ;
- transformation ;
- provenance ;
- explications ;
- « Pourquoi ? ».

---

# 11. PRODUIRE

Cette section regroupe :

- SQL ;
- documentation ;
- exports ;
- diagrammes ;
- données de test ;
- requêtes.

---

# 12. IA

L'IA constitue une fonctionnalité transversale.

Elle doit permettre notamment :

```text
Créer un MCD
Analyser un modèle
Trouver des problèmes
Proposer des corrections
Expliquer un modèle
Expliquer une transformation
```

---

# 13. NOUVELLE IDENTITÉ VISUELLE

Créer une identité visuelle propre à MERISOR.

Direction :

> **Professionnel + moderne + visuel + pédagogique + rassurant**

Ne pas créer une interface de type :

- SaaS commercial ;
- dashboard marketing ;
- outil « startup » générique.

MERISOR doit rester un logiciel professionnel de bureau.

---

# 14. DESIGN SYSTEM

Créer un design system centralisé.

Proposer une structure similaire à :

```text
src/merisor/ui/theme/
    tokens.py
    theme_manager.py
    light_theme.py
    dark_theme.py
```

Adapter à l'architecture existante si nécessaire.

---

# 15. TOKENS

Centraliser :

- couleurs ;
- typographie ;
- espacements ;
- rayons ;
- bordures ;
- dimensions ;
- ombres ;
- états.

Ne jamais disperser les valeurs graphiques dans les widgets.

---

# 16. PALETTE

Créer une palette moderne.

Base possible :

```text
Primary
#3157D5

Primary Dark
#243FA3

Accent
#19B7A5

Accent Secondary
#7C6AE6
```

Prévoir des couleurs sémantiques :

```text
Success
Warning
Error
Info
AI
```

Les valeurs peuvent être ajustées après inspection de l'application.

---

# 17. THÈMES

Implémenter :

```text
Clair
Sombre
Système
```

Le thème doit être global.

Éviter de coder des couleurs spécifiques directement dans les widgets.

---

# 18. TYPOGRAPHIE

Créer une hiérarchie cohérente :

```text
Application Title
Page Title
Section Title
Card Title
Body
Secondary
Caption
Code
```

La police monospace doit être réservée :

- SQL ;
- JSON ;
- code ;
- informations techniques.

---

# 19. ICONOGRAPHIE

Utiliser une iconographie cohérente.

Actions principales :

```text
Nouveau
Ouvrir
Enregistrer
Annuler
Rétablir

Entité
Association
Attribut
Identifiant
Héritage

Valider
Analyser
MLD
SQL
Exporter

IA
Documentation
Recherche
Paramètres
```

Les icônes doivent être accompagnées de texte lorsque leur signification n'est pas évidente.

---

# 20. NOUVELLE APPLICATION SHELL

Refondre la fenêtre principale.

Structure cible :

```text
┌──────────────────────────────────────────────────────────────┐
│ MERISOR                                                     │
│ Projet   Édition   Modèle   Affichage   Outils   Aide      │
├──────────────────────────────────────────────────────────────┤
│ [Nouveau] [Ouvrir] [Enregistrer]                            │
│                                                              │
│ CONCEVOIR   VÉRIFIER   TRANSFORMER   PRODUIRE      ✨ IA   │
├──────────────┬───────────────────────────────────┬───────────┤
│              │                                   │           │
│ OUTILS       │                                   │ PROPRIÉTÉS│
│              │                                   │           │
│ Sélection    │              MCD                  │ Élément   │
│ Entité       │                                   │ sélectionné│
│ Association  │                                   │           │
│ Héritage     │                                   │ Attributs │
│              │                                   │ Relations │
├──────────────┴───────────────────────────────────┴───────────┤
│ ✓ Modèle valide     MCD à jour     MLD à jour              │
└──────────────────────────────────────────────────────────────┘
```

Adapter la structure à l'architecture actuelle.

---

# 21. START CENTER

Créer ou refondre l'écran d'accueil.

Il doit afficher :

```text
MERISOR

Concevez vos systèmes d'information
avec MERISE
```

Actions principales :

```text
＋ Nouveau modèle

Ouvrir un modèle

✨ Assistant IA
```

Puis :

```text
Modèles récents
```

Et éventuellement :

```text
Exemples
```

---

# 22. NOUVEAU MODÈLE

Créer un parcours simple.

Choix :

```text
Créer manuellement
Créer avec l'IA
Partir d'un exemple
Importer
```

Ne pas transformer cette étape en formulaire complexe.

---

# 23. CANVAS MCD

Le canvas est la **pièce maîtresse de MERISOR**.

Il doit devenir l'espace visuel dominant.

Améliorer :

- lisibilité ;
- sélection ;
- grille ;
- alignement ;
- guides ;
- zoom ;
- pan ;
- minimap ;
- recherche ;
- auto-layout ;
- multi-sélection ;
- copy/paste.

---

# 24. ENTITÉS

Moderniser les cartes d'entités.

Exemple conceptuel :

```text
┌─────────────────────────────┐
│ 👤 CLIENT                   │
├─────────────────────────────┤
│ 🔑 id_client     INTEGER    │
│    nom           VARCHAR    │
│    email         VARCHAR    │
│    téléphone     VARCHAR    │
└─────────────────────────────┘
```

Prévoir une hiérarchie claire entre :

- nom ;
- identifiant ;
- attributs ;
- types ;
- contraintes.

---

# 25. IDENTIFIANTS

Un identifiant doit être immédiatement identifiable.

Utiliser :

- icône ;
- badge ;
- style typographique ;
- séparation visuelle.

Ne pas dépendre uniquement de la couleur.

---

# 26. FOREIGN KEYS

Dans les vues MLD/SQL, différencier clairement :

```text
PK
FK
PK + FK
UNIQUE
```

---

# 27. ASSOCIATIONS

Améliorer fortement :

- lisibilité ;
- labels ;
- cardinalités ;
- sélection ;
- poignées ;
- survol.

Les cardinalités doivent être suffisamment visibles.

---

# 28. HÉRITAGE

Prévoir une représentation graphique claire :

```text
              PERSONNE
                 │
                ISA
             ┌───┴───┐
             │       │
          CLIENT   EMPLOYÉ
```

---

# 29. ASSOCIATIONS RÉFLEXIVES

Les associations réflexives doivent être clairement représentées.

Éviter toute ambiguïté visuelle.

---

# 30. ASSOCIATIONS N-AIRES

Prévoir une représentation distincte et compréhensible.

Ne pas essayer de masquer leur nature.

---

# 31. TOOLBAR DU CANVAS

Prévoir :

```text
[Sélection]
[Entité]
[Association]
[Héritage]
[Recherche]
[Auto-layout]
[Grille]
[−]
[100%]
[+]
```

La toolbar doit rester compacte.

---

# 32. PANNEAU PROPRIÉTÉS

Le panneau droit doit être contextuel.

### Aucun élément sélectionné

Afficher :

```text
MON MODÈLE

12 entités
9 associations
54 attributs

✓ Modèle valide
✓ MLD à jour
```

### Entité sélectionnée

Afficher :

```text
CLIENT

Général

Identifiants

Attributs

Relations

Options avancées
```

---

# 33. ATTRIBUTS

Créer un éditeur moderne.

Exemple :

```text
ATTRIBUTS

🔑 id_client     INTEGER       PK
   nom           VARCHAR(100)
   email         VARCHAR(255)  UNIQUE

[＋ Ajouter un attribut]
```

Permettre si possible :

- édition ;
- suppression ;
- duplication ;
- déplacement ;
- type ;
- nullable ;
- unique ;
- identifiant.

---

# 34. ACTIONS CONTEXTUELLES

Pour une entité :

```text
Modifier
Ajouter attribut
Créer association
Dupliquer
Aligner
Supprimer
```

Pour une association :

```text
Modifier
Modifier cardinalité
Historiser
Matérialiser
Supprimer
```

---

# 35. VALIDATION

Le statut du modèle doit être visible en permanence.

Exemple :

```text
✓ Modèle valide
```

ou :

```text
✕ 1 erreur
⚠ 3 avertissements
```

---

# 36. CENTRE DE VALIDATION

Créer une vue dédiée :

```text
QUALITÉ DU MODÈLE

✕ 1 erreur
⚠ 3 avertissements
✓ 18 contrôles réussis
```

Chaque erreur doit être exploitable.

Exemple :

```text
✕ CLIENT n'a pas d'identifiant

[Localiser]
[Corriger]
[Pourquoi ?]
```

---

# 37. FOCUS AUTOMATIQUE

Lorsqu'un utilisateur clique sur un problème :

1. localiser l'élément ;
2. centrer le canvas ;
3. sélectionner l'élément ;
4. ouvrir le panneau correspondant.

---

# 38. EXPLICATIONS « POURQUOI ? »

Ajouter une action :

```text
ⓘ Pourquoi ?
```

Aux endroits pertinents.

Exemples :

```text
Pourquoi cette FK ?

Pourquoi cette table ?

Pourquoi cette clé primaire ?

Pourquoi cette table intermédiaire ?

Pourquoi cette matérialisation ?
```

L'explication doit être basée sur les règles réelles de MERISOR.

Ne pas inventer de justification.

---

# 39. NORMALISATION

Présenter les résultats de manière pédagogique.

Exemple :

```text
NORMALISATION

1NF ✓
2NF ✓
3NF ⚠

Problème :

CLIENT.email dépend...
```

Permettre de revenir vers l'élément concerné.

---

# 40. ANALYSE D'IMPACT

Afficher les dépendances de manière visuelle.

Exemple :

```text
CLIENT
 │
 ├── COMMANDE
 │     └── LIGNE_COMMANDE
 │
 └── ADRESSE
```

Afficher éventuellement :

```text
3 tables MLD impactées
5 contraintes SQL
2 documents
```

---

# 41. MCD → MLD

Créer une navigation claire :

```text
MCD
 ↓
Transformation
 ↓
MLD
 ↓
SQL
```

Chaque niveau possède un état :

```text
✓ À jour
⚠ À régénérer
✕ Erreur
```

---

# 42. MLD

Créer une interface avec :

```text
[Graphique] [Texte] [Provenance]
```

Le graphique doit être cohérent avec le nouveau design system.

---

# 43. PROVENANCE

Lorsqu'une table MLD est sélectionnée :

```text
CLIENT

Origine MCD
→ CLIENT

Colonnes

id_client ← CLIENT.id_client
nom       ← CLIENT.nom
email     ← CLIENT.email
```

---

# 44. EXPLICATION MLD

Afficher :

```text
Pourquoi cette structure ?

Cette table provient de l'entité CLIENT.

La clé étrangère provient de
la relation CLIENT → COMMANDE.

[Voir dans le MCD]
```

---

# 45. SQL

Créer une interface moderne.

En-tête :

```text
SQL

[PostgreSQL]
[SQLite]
[MariaDB / MySQL]
```

Actions :

```text
Copier
Exporter
Rechercher
```

Afficher :

```text
✓ SQL généré

12 tables
18 contraintes
```

---

# 46. ÉDITEUR SQL

Améliorer :

- monospace ;
- numéros de lignes ;
- coloration syntaxique si raisonnablement possible ;
- recherche ;
- copie ;
- sélection.

Ne pas introduire une dépendance lourde uniquement pour la coloration syntaxique.

---

# 47. ASSISTANT IA

Créer un espace clairement identifiable :

```text
✨ Assistant MERISOR
```

Actions :

```text
Créer un MCD
Analyser mon modèle
Trouver les problèmes
Réparer mon modèle
Expliquer le MLD
```

---

# 48. IA — WORKFLOW

L'IA doit fonctionner selon :

```text
Demande
↓
Proposition
↓
Prévisualisation
↓
Validation locale
↓
Diff
↓
Confirmation
↓
Modification
```

Jamais :

```text
Demande IA
↓
Modification silencieuse
```

---

# 49. IA — DIFF

Présenter clairement :

```text
AJOUT

+ CLIENT.telephone

+ CLIENT — COMMANDE

MODIFICATION

~ CLIENT.email → UNIQUE

SUPPRESSION

- ancienne association
```

L'utilisateur doit savoir précisément ce qui va changer.

---

# 50. IA — SÉCURITÉ

Préserver les règles existantes :

- clé OpenRouter hors projet ;
- jamais dans le MCD ;
- jamais dans Git ;
- jamais dans SQL ;
- validation locale ;
- confirmation utilisateur.

---

# 51. IMPORT

Moderniser l'import.

Présenter :

```text
Importer

MCD MERISOR
DDL SQL
Schéma PWA / IndexedDB
```

Après import :

```text
Import terminé

12 entités
9 associations

⚠ 2 éléments nécessitent votre attention
```

---

# 52. EXPORT

Créer une interface cohérente :

```text
EXPORTER

Diagrammes
  PNG
  SVG
  PDF
  Mermaid
  Graphviz

Modèle
  JSON

Documentation
  Markdown
  HTML
  PDF

SQL
  PostgreSQL
  SQLite
  MySQL

Données
  Jeu de test
  Requêtes SQL
```

---

# 53. DOCUMENTATION CENTER

Créer une interface moderne :

```text
DOCUMENTATION MERISOR

Sommaire
──────────────
Démarrage
MCD
MLD
SQL
Validation
IA
Raccourcis
```

Accès :

```text
Documentation
F1
```

Prévoir recherche si possible.

---

# 54. RECHERCHE GLOBALE

Créer :

```text
⌕ Rechercher
```

Recherche dans :

- entités ;
- associations ;
- attributs ;
- tables ;
- documentation.

Un résultat sur le modèle doit permettre de centrer le canvas.

---

# 55. COMMAND PALETTE

Si raisonnablement faisable :

```text
Ctrl+K

Rechercher une commande...

Créer une entité
Créer une association
Valider
Afficher le MLD
Afficher le SQL
Exporter
Documentation
Assistant IA
```

---

# 56. UNDO / REDO

Rendre visibles :

```text
↶ Annuler
↷ Rétablir
```

Les tooltips doivent expliquer l'action.

Exemple :

```text
Annuler :
Ajouter l'entité CLIENT
Ctrl+Z
```

---

# 57. ÉTATS

Toutes les vues importantes doivent gérer :

```text
EMPTY
LOADING
SUCCESS
WARNING
ERROR
DISABLED
```

Exemple :

```text
Aucun modèle

Créez votre première entité.

[Créer une entité]
```

---

# 58. FEEDBACK

Les actions importantes doivent produire un feedback non intrusif :

```text
✓ Modèle enregistré
✓ MLD régénéré
✓ SQL généré
✓ Export terminé
```

Éviter les fenêtres modales inutiles.

---

# 59. MODIFICATIONS NON ENREGISTRÉES

Afficher clairement :

```text
● Modifications non enregistrées
```

Le titre de fenêtre peut également refléter cet état.

---

# 60. MLD OBSOLÈTE

Exploiter le système de fraîcheur existant.

Exemple :

```text
MCD ✓ À jour
MLD ⚠ À régénérer
SQL ⚠ À régénérer
```

Cliquer sur MLD doit proposer une régénération.

---

# 61. TABLEAU DE BORD DU MODÈLE

Lorsque rien n'est sélectionné :

```text
MON MODÈLE

12 Entités
9 Associations
54 Attributs

3 × 1:N
2 × N:N
1 × 1:1

2 historisées

✓ Validation
✓ MLD
⚠ SQL à régénérer
```

Ce panneau doit rester compact.

---

# 62. ACCESSIBILITÉ

Prévoir :

- contraste suffisant ;
- focus visible ;
- navigation clavier ;
- tooltips ;
- labels ;
- icônes compréhensibles ;
- pas de dépendance exclusive à la couleur.

---

# 63. RESPONSIVE DESKTOP

Tester au minimum :

```text
1280 × 720
1366 × 768
1920 × 1080
2560 × 1440
```

Le canvas doit rester prioritaire.

Les panneaux doivent être redimensionnables.

---

# 64. PETITE FENÊTRE

Lorsque l'espace devient limité :

- réduire les panneaux ;
- masquer certains textes secondaires ;
- utiliser des panneaux temporaires ;
- conserver le canvas fonctionnel.

---

# 65. MODE DÉBUTANT / EXPERT

Préparer l'architecture pour éventuellement supporter :

## Débutant

```text
MCD
Validation
MLD
SQL
IA
```

## Expert

Ajouter :

```text
matérialisation
options avancées
détails SQL
stratégies techniques
```

Ne pas nécessairement implémenter cette fonctionnalité lors de la première passe si cela complexifie inutilement la refonte.

---

# 66. MENUS

Réorganiser les menus autour du workflow.

## Fichier

```text
Nouveau
Ouvrir
Enregistrer
Enregistrer sous
Importer
Exporter
Quitter
```

## Édition

```text
Annuler
Rétablir
Couper
Copier
Coller
Supprimer
```

## Modèle

```text
Valider
Analyser
Normalisation
Impact
Comparer
```

## Affichage

```text
MCD
MLD
SQL
Documentation
Minimap
Grille
Panneaux
```

## Outils

```text
Auto-layout
Recherche
Palette de commandes
Paramètres
```

## IA

```text
Assistant
Créer
Analyser
Réparer
Paramètres IA
```

---

# 67. RÈGLE DES 3 CLICS

Une fonction fréquente doit être accessible en environ trois actions maximum.

Exemples :

```text
Créer une entité
→ Entité
→ Canvas
→ Nom
```

```text
Valider
→ Vérifier
→ Valider
```

```text
SQL
→ Produire
→ SQL
```

---

# 68. RÈGLE DU CONTEXTE

À tout moment l'utilisateur doit comprendre :

```text
Où suis-je ?
Que regarde-je ?
Que puis-je faire ?
Quel est l'état ?
Que va faire cette action ?
```

---

# 69. RÈGLE DU CANVAS

Lorsque l'utilisateur travaille sur le MCD :

> Le canvas doit rester l'espace dominant.

Les panneaux ne doivent pas écraser le modèle.

---

# 70. RÈGLE DE L'ÉTAT GLOBAL

L'état du modèle doit toujours être visible.

Exemple :

```text
✓ Modèle valide
✓ MLD à jour
✓ SQL à jour
```

ou :

```text
✕ 2 erreurs
⚠ 3 avertissements
MLD à régénérer
```

---

# 71. STRUCTURE UI RECOMMANDÉE

Adapter selon l'existant.

Structure indicative :

```text
src/merisor/ui/

theme/
    tokens.py
    theme_manager.py
    light.py
    dark.py

components/
    buttons.py
    cards.py
    badges.py
    notifications.py
    status.py

shell/
    app_shell.py
    top_bar.py
    navigation.py
    status_bar.py

home/
    start_center.py

mcd/
    canvas.py
    entity_item.py
    association_item.py
    inheritance_item.py
    canvas_toolbar.py
    minimap.py

properties/
    properties_panel.py
    entity_properties.py
    association_properties.py
    attribute_editor.py

validation/
    validation_center.py
    validation_item.py

mld/
    mld_view.py
    provenance_panel.py
    why_panel.py

sql/
    sql_view.py

ai/
    ai_assistant.py
    ai_preview.py
    ai_diff.py

documentation/
    documentation_center.py

dialogs/
    ...
```

Ne pas imposer cette arborescence si l'architecture existante possède une organisation meilleure.

---

# 72. DESIGN SYSTEM DOCUMENTATION

Créer :

```text
docs/DESIGN_SYSTEM.md
```

Documenter :

- couleurs ;
- typographie ;
- espacements ;
- composants ;
- états ;
- boutons ;
- badges ;
- panneaux ;
- notifications ;
- thèmes.

---

# 73. UX DOCUMENTATION

Créer :

```text
docs/UX_GUIDELINES.md
```

Documenter :

- navigation ;
- workflow ;
- feedback ;
- erreurs ;
- accessibilité ;
- interactions ;
- raccourcis ;
- principes UX.

---

# 74. UI ARCHITECTURE

Créer :

```text
docs/UI_ARCHITECTURE.md
```

Documenter :

- architecture UI ;
- responsabilités ;
- communication avec l'application ;
- signaux ;
- états ;
- modèles de présentation.

---

# 75. UI/UX 2.0

Copier également ce cahier des charges dans :

```text
docs/UI_UX_2.0.md
```

Le document doit devenir la référence permanente du projet.

---

# 76. TESTS

Avant modification :

```bash
pytest
```

Après chaque phase :

```bash
pytest
```

Ne jamais supprimer un test uniquement parce qu'il gêne la refonte.

---

# 77. TESTS UI

Ajouter lorsque possible :

- ouverture application ;
- Start Center ;
- nouveau modèle ;
- création entité ;
- sélection ;
- propriétés ;
- validation ;
- focus erreur ;
- MLD ;
- SQL ;
- IA ;
- documentation ;
- changement thème.

---

# 78. TESTS VISUELS

Si l'environnement le permet, créer des captures de référence pour :

```text
Start Center
MCD
Properties
Validation
MLD
SQL
IA
Documentation
```

L'objectif est de détecter les régressions visuelles.

---

# 79. PERFORMANCE

Ne pas dégrader les performances.

Tester notamment :

- gros modèles ;
- nombreuses entités ;
- nombreuses associations ;
- zoom ;
- pan ;
- sélection multiple ;
- minimap ;
- validation ;
- génération MLD.

Éviter les recalculs inutiles lors des mouvements du canvas.

---

# 80. COMPATIBILITÉ

Préserver :

- JSON V1 ;
- JSON V2 ;
- migrations ;
- modèles existants ;
- exemples ;
- imports ;
- exports.

---

# 81. INTERDIT : SIMPLE SKIN

Ne pas considérer la mission comme :

> « Changer les couleurs et arrondir les boutons. »

La mission est :

> **Transformer l'expérience d'utilisation de MERISOR.**

Il faut améliorer simultanément :

- navigation ;
- hiérarchie ;
- compréhension ;
- feedback ;
- interactions ;
- visualisation ;
- cohérence.

---

# 82. INTERDIT : SURDESIGN

Ne pas :

- mettre des gradients partout ;
- utiliser des ombres énormes ;
- arrondir tous les éléments ;
- mettre des cartes partout ;
- multiplier les animations ;
- créer un dashboard marketing ;
- utiliser des couleurs criardes.

---

# 83. INTERDIT : CACHER LES FONCTIONNALITÉS

La simplification ne doit jamais signifier :

> supprimer ou cacher arbitrairement les fonctionnalités existantes.

Les fonctionnalités avancées doivent être accessibles via :

```text
Options avancées
```

ou un mode expert lorsque pertinent.

---

# 84. IA : RÈGLE ABSOLUE

Aucune réponse IA ne doit modifier le modèle sans confirmation explicite.

Toujours :

```text
Proposition
→ Validation
→ Diff
→ Confirmation
→ Application
```

---

# 85. EXEMPLE D'EXPÉRIENCE CIBLE

Un utilisateur crée :

```text
CLIENT
```

MERISOR propose :

```text
Ajoutez votre premier attribut

[＋ Ajouter un attribut]
```

L'utilisateur ajoute :

```text
id_client
nom
email
```

MERISOR détecte :

```text
id_client
```

et propose :

```text
🔑 Définir comme identifiant
```

Il crée :

```text
COMMANDE
```

Puis :

```text
CLIENT ─── passe ─── COMMANDE
```

Les cardinalités sont clairement affichées.

La validation indique :

```text
✓ Relation cohérente
```

L'utilisateur clique :

```text
MLD
```

et voit immédiatement :

```text
CLIENT
────────
PK id_client
nom
email

COMMANDE
────────
PK id_commande
FK id_client
date_commande
```

Puis :

```text
ⓘ Pourquoi ?
```

L'utilisateur clique.

MERISOR explique la transformation.

Puis :

```text
SQL
```

et obtient :

```text
PostgreSQL
SQLite
MySQL
```

Le workflow doit être aussi naturel que possible.

---

# 86. ORDRE D'IMPLÉMENTATION

## PHASE 0

Audit.

## PHASE 1

Design system.

## PHASE 2

Application shell.

## PHASE 3

Start Center.

## PHASE 4

Canvas MCD.

**Priorité maximale.**

## PHASE 5

Properties Panel.

## PHASE 6

Validation Center.

## PHASE 7

Navigation MCD / MLD / SQL.

## PHASE 8

MLD.

## PHASE 9

SQL.

## PHASE 10

IA.

## PHASE 11

Documentation.

## PHASE 12

Finitions :

- thème sombre ;
- thème système ;
- accessibilité ;
- animations ;
- recherche ;
- command palette ;
- onboarding ;
- tests visuels.

---

# 87. PRIORITÉS SI LE TEMPS EST LIMITÉ

Respecter cet ordre :

```text
1. Canvas MCD
2. Application Shell
3. Properties Panel
4. Validation
5. Navigation MCD/MLD/SQL
6. Design System
7. Start Center
8. MLD
9. SQL
10. IA
11. Documentation
12. Finitions
```

---

# 88. CRITÈRES D'ACCEPTATION

La refonte est réussie si un nouvel utilisateur peut comprendre rapidement :

```text
Comment créer une entité ?
Comment ajouter un attribut ?
Comment créer une association ?
Comment définir une cardinalité ?
Comment valider ?
Comment afficher le MLD ?
Comment générer le SQL ?
```

---

# 89. CRITÈRES VISUELS

L'application doit donner une impression :

```text
Moderne
Professionnelle
Claire
Visuelle
Pédagogique
Cohérente
Engageante
```

et ne doit plus donner principalement l'impression :

```text
Technique
Austère
Grise
Complexe
Datée
```

---

# 90. CRITÈRES FONCTIONNELS

Aucune fonctionnalité existante importante ne doit être perdue.

Les tests existants doivent continuer à fonctionner.

Les formats de données doivent rester compatibles.

---

# 91. CRITÈRES UX

Un utilisateur doit pouvoir :

- trouver une fonction ;
- comprendre son état ;
- comprendre son résultat ;
- revenir en arrière ;
- identifier une erreur ;
- localiser l'élément concerné ;
- comprendre une transformation.

---

# 92. RAPPORT DE FIN DE PHASE

À la fin de chaque phase, produire un résumé :

```text
PHASE :
État :

Fichiers créés :

Fichiers modifiés :

Fonctionnalités implémentées :

Tests exécutés :

Résultat des tests :

Régressions détectées :

Problèmes restants :

Prochaine phase :
```

---

# 93. RAPPORT FINAL

À la fin de la refonte, produire :

```text
docs/UI_UX_2.0_IMPLEMENTATION_REPORT.md
```

Contenant :

- résumé ;
- architecture finale ;
- composants ajoutés ;
- composants modifiés ;
- fonctionnalités UX ;
- thèmes ;
- raccourcis ;
- tests ;
- éventuelles limitations ;
- recommandations futures.

---

# 94. RÈGLE DE QUALITÉ

Ne pas considérer une phase terminée simplement parce que le code compile.

Une phase est terminée uniquement lorsque :

```text
Code
+
Tests
+
UX
+
Cohérence visuelle
+
Documentation
```

sont satisfaisants.

---

# 95. RÈGLE DE PRUDENCE

Si une décision implique une modification importante du moteur métier :

1. ne pas la faire immédiatement ;
2. identifier le problème ;
3. proposer une solution compatible avec l'architecture ;
4. privilégier un adaptateur UI ;
5. conserver les comportements existants.

---

# 96. RÈGLE DE SIMPLICITÉ

Toujours préférer :

```text
simple + clair + cohérent
```

à :

```text
complexe + spectaculaire
```

---

# 97. RÈGLE DE COHÉRENCE

Un bouton « Valider » doit avoir la même apparence partout.

Un message d'erreur doit avoir le même langage visuel partout.

Un panneau doit suivre les mêmes règles partout.

Un élément sélectionné doit avoir le même comportement partout.

---

# 98. RÈGLE DE PÉDAGOGIE

MERISOR doit pouvoir être utilisé :

- par un débutant découvrant MERISE ;
- par un étudiant ;
- par un développeur ;
- par un concepteur de bases de données ;
- par un utilisateur expert.

L'interface doit expliquer sans infantiliser.

---

# 99. VISION FINALE

La nouvelle expérience MERISOR doit suivre ce principe :

```text
             MERISOR

       ┌───────────────┐
       │    CONCEVOIR  │
       │      MCD      │
       └───────┬───────┘
               ↓
       ┌───────────────┐
       │    VÉRIFIER   │
       │ Qualité/Impact│
       └───────┬───────┘
               ↓
       ┌───────────────┐
       │  TRANSFORMER  │
       │      MLD      │
       └───────┬───────┘
               ↓
       ┌───────────────┐
       │    PRODUIRE   │
       │ SQL / Docs    │
       └───────────────┘
```

L'utilisateur doit toujours comprendre où il se trouve dans ce parcours.

---

# 100. DIRECTIVE FINALE À CODEX

**Commence maintenant par la PHASE 0.**

Ne modifie pas immédiatement toute l'application.

Commence par :

```text
1. Inspecter le dépôt.
2. Lire l'architecture.
3. Lire les tests.
4. Identifier l'UI existante.
5. Exécuter pytest.
6. Établir un état de référence.
7. Identifier les composants réutilisables.
8. Identifier les risques.
9. Créer docs/UI_AUDIT.md.
```

Ensuite seulement, commencer la PHASE 1.

---

# 101. ORDRE D'EXÉCUTION OBLIGATOIRE

```text
PHASE 0
Audit
   ↓
PHASE 1
Design System
   ↓
PHASE 2
Application Shell
   ↓
PHASE 3
Start Center
   ↓
PHASE 4
MCD Canvas
   ↓
PHASE 5
Properties
   ↓
PHASE 6
Validation
   ↓
PHASE 7
MCD → MLD → SQL
   ↓
PHASE 8
MLD
   ↓
PHASE 9
SQL
   ↓
PHASE 10
IA
   ↓
PHASE 11
Documentation
   ↓
PHASE 12
Finitions + tests
```

---

# 102. OBJECTIF ULTIME

À la fin de cette mission, MERISOR doit être perçu comme :

> **un véritable atelier moderne de modélisation MERISE.**

La puissance technique doit rester présente.

Mais elle doit désormais être :

**visible → compréhensible → accessible → explicable → agréable.**

La phrase directrice de toute l'implémentation est :

> **MERISOR doit être puissant sous le capot, mais évident à utiliser.**

---

# 103. INSTRUCTION DE DÉMARRAGE POUR CODEX

Une fois ce fichier placé dans le dépôt MERISOR, lancer Codex dans le répertoire du projet puis lui demander :

```text
Lis intégralement PROMPT_UI_UX_2.0.md et applique son cahier des charges.

Commence obligatoirement par la PHASE 0.

Ne commence aucune refonte graphique avant d'avoir :
1. inspecté le dépôt ;
2. analysé l'architecture ;
3. analysé l'UI existante ;
4. exécuté la suite de tests ;
5. créé docs/UI_AUDIT.md.

Travaille ensuite phase par phase.

Après chaque phase :
- exécute les tests ;
- vérifie les régressions ;
- documente les modifications ;
- indique clairement la phase terminée ;
- passe à la phase suivante uniquement si la précédente est suffisamment stable.

Ne réécris pas le moteur MERISE pour résoudre un problème d'interface.
Ne supprime aucune fonctionnalité existante.
Ne modifie pas silencieusement le format des données.
Ne transforme pas MERISOR en application web ou en SaaS.

Objectif :
faire de MERISOR un atelier moderne, professionnel, visuel, pédagogique et intuitif de modélisation MERISE, tout en conservant la robustesse du moteur existant.
```

---

# FIN DU DOCUMENT
