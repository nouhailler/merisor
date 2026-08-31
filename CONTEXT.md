# Contexte de reprise du projet MERISOR

Ce document décrit l'état réel du dépôt au 31 août 2026 et la prochaine
fonctionnalité retenue. Il doit être lu avant toute nouvelle évolution afin de
ne pas réimplémenter les versions précédentes.

## État global

MERISOR couvre actuellement la chaîne complète :

```text
MCD graphique → validation → MLD structuré → SQL exportable
```

Fonctionnalités déjà intégrées :

- édition graphique des entités, associations, relations et cardinalités ;
- attributs d'entités et d'associations, identifiants simples ou composés ;
- associations historisées, stratégies `AUTO`, `FORCE_TABLE` et `FORCE_FK` ;
- associations réflexives et n-aires avec rôles de branche ;
- héritages ISA `PARENT_ONLY`, `CHILDREN_ONLY` et `JOINED` ;
- disposition automatique, zoom, export PNG/SVG/PDF et fichiers récents ;
- sauvegarde JSON V2 rétrocompatible avec les anciens fichiers V1/V2 ;
- transformation MCD → MLD, dont provenance, PK/FK composées et contraintes ;
- génération SQL PostgreSQL, SQLite et MariaDB/MySQL ;
- import et reverse-engineering de DDL PostgreSQL/SQLite ;
- paquets Debian, AppImage et publication PyPI/pipx ;
- génération d'un MCD depuis une description via OpenRouter, avec aperçu et
  confirmation avant remplacement du document courant.

## Qualité logicielle

Le workflow `.github/workflows/quality.yml` exécute sur les push et pull
requests vers `main` :

```text
ruff format --check .
ruff check .
mypy
QT_QPA_PLATFORM=offscreen pytest
```

Mypy fonctionne en mode strict. À la dernière vérification locale :

- Ruff format et lint : conformes ;
- mypy : aucune erreur sur 57 fichiers ;
- pytest : 224 tests réussis ;
- démarrage Qt hors écran : application active jusqu'au timeout de contrôle.

## Analyse intelligente locale déjà terminée

La commande **Modèle → Analyser la qualité du modèle** fournit une seconde
couche non bloquante et explicable, sans appel IA :

- suggestion de type selon le nom de l'attribut ;
- suggestion d'unicité ;
- détection d'entités similaires ;
- cohérence des conventions de nommage ;
- mauvaises odeurs de normalisation ;
- score global et six scores détaillés, avec confiance et justification.

Une propriété déjà marquée `unique` n'est plus signalée comme suggestion.

## Assistant de normalisation déjà terminé

La commande **Modèle → Assistant de normalisation** (`Ctrl+Shift+N`) repose sur
un modèle métier de dépendances fonctionnelles :

- saisie, modification et suppression de dépendances composites `X → Y` ;
- origine `USER` ou `AI` conservée dans le JSON ;
- calcul de fermeture d'attributs et des clés candidates ;
- contrôle formel 2NF et 3NF à partir des dépendances déclarées ;
- détection heuristique 1NF, valeurs composées et groupes répétitifs ;
- rapport pédagogique avec explication de chaque problème ;
- aperçu d'une décomposition sans mutation du MCD ;
- application confirmée et annulable des extractions 3NF non ambiguës ;
- suggestions OpenRouter facultatives et asynchrones.

Limite volontaire : une décomposition 2NF nécessitant une identification
relative, ou une transformation ambiguë d'association, reste en aperçu. Elle
n'est jamais appliquée automatiquement.

Le JSON V2 possède désormais un tableau facultatif
`functional_dependencies`. Son absence produit une collection vide.

## Édition complète des attributs déjà terminée

`Attribute` porte maintenant les propriétés suivantes :

```text
name
data_type
nullable              # true, false ou null = automatique
default
unique
comment
identifier
auto_increment
constraints           # expressions CHECK
```

Le panneau de propriétés permet de modifier en une seule commande annulable :

- nom et type logique ;
- longueur `VARCHAR` ;
- précision et échelle `DECIMAL` ;
- obligatoire, facultatif ou automatique ;
- valeur par défaut ;
- unicité ;
- commentaire métier ;
- statut d'identifiant ;
- auto-incrémentation ;
- plusieurs expressions `CHECK`, une par ligne.

Les anciens fichiers reçoivent les valeurs rétrocompatibles suivantes :

```text
nullable       = null
default        = null
unique         = false
comment        = ""
auto_increment = false
constraints    = []
```

Ces propriétés sont propagées vers le MLD, la représentation textuelle et les
trois dialectes SQL. Les commentaires utilisent `COMMENT ON COLUMN` sous
PostgreSQL, `COMMENT` sous MySQL/MariaDB et un commentaire documentaire sous
SQLite. `UNIQUE` et `CHECK` deviennent de véritables contraintes MLD/SQL.

La validation refuse notamment :

- un identifiant facultatif ;
- une auto-incrémentation sur un attribut non identifiant ;
- une auto-incrémentation sur une clé composée ;
- une auto-incrémentation non entière ;
- une auto-incrémentation combinée à une valeur par défaut.

## Intégration OpenRouter existante

Les étapes historiques sont terminées :

1. stockage local de la clé hors des projets ;
2. récupération et sélection des modèles gratuits compatibles texte ;
3. génération d'un JSON MCD avec schéma imposé ;
4. validation JSON puis validation MERISE ;
5. aperçu éditable sans modifier le document ;
6. import confirmé et disposition automatique.

Les appels de génération et de suggestion de dépendances fonctionnelles
s'exécutent dans un `QThread`. Aucun worker réseau ne manipule directement un
widget Qt.

## Prochaine fonctionnalité : Assistant MERISE conversationnel

La prochaine évolution retenue doit transformer la génération ponctuelle en
assistant de conception. Elle n'est **pas encore implémentée**.

### Objectif utilisateur

À partir d'une description comme :

> Je veux gérer une bibliothèque avec des livres, des auteurs, des lecteurs et
> les emprunts.

MERISOR doit pouvoir :

1. détecter les concepts et associations probables ;
2. afficher ses hypothèses avec un niveau de confiance ;
3. poser uniquement les questions qui influencent réellement le modèle ;
4. faire évoluer un brouillon MCD structuré après chaque réponse ;
5. valider ce brouillon sans modifier le MCD courant ;
6. afficher les différences puis demander confirmation avant import.

Exemples de questions pertinentes :

- un livre peut-il avoir plusieurs auteurs ?
- faut-il distinguer `LIVRE` et `EXEMPLAIRE` ?
- un lecteur peut-il emprunter plusieurs exemplaires simultanément ?
- les emprunts rendus doivent-ils être historisés ?
- `EMPRUNT` est-il une association historisée ou une entité métier autonome ?

### Architecture obligatoire

Ne pas utiliser le texte de conversation comme source de vérité. Introduire un
agrégat local, par exemple `DesignSession`, contenant :

```text
DesignSession
├── turns
├── current_draft_mcd
├── assumptions
├── pending_questions
├── answered_questions
├── draft_revisions
└── validation_reports
```

Chaque réponse IA doit utiliser une enveloppe JSON stricte :

```json
{
  "assistant_message": "J'ai identifié quatre concepts principaux.",
  "detected_concepts": [],
  "questions": [],
  "assumptions": [],
  "draft_patch": {
    "entities_to_add": [],
    "entities_to_update": [],
    "associations_to_add": [],
    "relations_to_add": []
  },
  "ready_for_preview": false
}
```

Les évolutions successives doivent être exprimées sous forme de patchs
structurés et validés. Ne jamais régénérer silencieusement tout le document ni
appliquer directement une réponse textuelle de l'IA.

### Répartition des responsabilités

L'IA peut :

- détecter des concepts, attributs et associations ;
- identifier les ambiguïtés ;
- formuler des questions pédagogiques ;
- proposer types, cardinalités, historisation et dépendances fonctionnelles ;
- expliquer l'impact d'un choix.

MERISOR doit impérativement :

- contrôler les identifiants internes et les références ;
- valider toutes les cardinalités et règles MERISE ;
- valider chaque patch et chaque brouillon avec le dépôt JSON existant ;
- conserver l'historique des révisions du brouillon ;
- afficher les différences avec le MCD courant ;
- ne modifier le document qu'après confirmation explicite ;
- appliquer l'import final comme une opération annulable.

### Ordre d'implémentation recommandé pour la prochaine reprise

1. créer le modèle local `DesignSession` et ses révisions ;
2. définir et valider le schéma JSON des réponses conversationnelles ;
3. implémenter le premier tour d'analyse d'une description ;
4. afficher concepts, hypothèses et questions ;
5. enregistrer les réponses de l'utilisateur ;
6. appliquer les `draft_patch` au brouillon isolé ;
7. valider le brouillon après chaque tour ;
8. créer l'aperçu graphique et la comparaison MCD courant/brouillon ;
9. importer après confirmation comme une commande annulable ;
10. ajouter éventuellement la sauvegarde et la reprise locale d'une session.

### Interface envisagée

- conversation et réponses à gauche ;
- brouillon MCD et état de validation à droite ;
- section « Hypothèses retenues » ;
- liste des questions en attente ;
- boutons **Voir les changements**, **Version précédente**, **Régénérer la
  proposition** et **Importer dans le MCD** ;
- indicateur de progression pendant les appels OpenRouter ;
- gestion compréhensible des quotas, erreurs réseau et JSON invalides.

## Contraintes permanentes à conserver

- ne jamais enregistrer la clé API dans un fichier projet ou dans les logs ;
- ne jamais remplacer le MCD courant sans confirmation explicite ;
- valider toute sortie IA avant utilisation ;
- conserver la séparation domaine/application/interface ;
- maintenir la compatibilité JSON V1/V2 ;
- conserver MCD, MLD et SQL comme trois niveaux séparés ;
- maintenir les opérations importantes annulables ;
- ne jamais exécuter automatiquement le SQL généré ;
- lancer Ruff, mypy strict, pytest et le smoke test Qt avant toute livraison.
