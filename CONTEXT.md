# Contexte de reprise du projet MERISOR

Ce document décrit l'état réel du dépôt au 2 septembre 2026 et les évolutions
déjà terminées. Il doit être lu avant toute nouvelle évolution afin de
ne pas réimplémenter les versions précédentes.

## État global

MERISOR couvre actuellement la chaîne complète :

```text
MCD graphique → validation → MLD structuré → SQL exportable
```

Fonctionnalités déjà intégrées :

- documentation structurée sous `docs/`, lecteur hors ligne intégré accessible
  par le menu **Documentation** et `F1`, avec recherche et navigation ;
- édition graphique des entités, associations, relations et cardinalités ;
- attributs d'entités et d'associations, identifiants simples ou composés ;
- associations historisées, stratégies `AUTO`, `FORCE_TABLE` et `FORCE_FK` ;
- associations réflexives et n-aires avec rôles de branche ;
- héritages ISA `PARENT_ONLY`, `CHILDREN_ONLY` et `JOINED` ;
- canvas productif avec disposition automatique, alignements, grille,
  aimantation, guides, multi-sélection, copier/coller, duplication, recherche,
  pliage, couleurs de domaines, thèmes, minimap et plein écran ;
- zoom, export PNG/SVG/PDF et fichiers récents ;
- exports documentaires Mermaid et Graphviz/DOT du MCD ou du MLD actif ;
- génération d'une documentation MCD/MLD en Markdown, HTML autonome ou PDF,
  avec diagrammes, dictionnaire des objets, contraintes et fiches YAML ;
- sauvegarde JSON V2 rétrocompatible avec les anciens fichiers V1/V2 ;
- transformation MCD → MLD, dont provenance, PK/FK composées et contraintes ;
- explication pédagogique **ⓘ Pourquoi ?** de chaque table MLD sélectionnée,
  couvrant table, PK, colonnes, FK, nullabilité, UNIQUE et CHECK sans IA ;
- génération SQL PostgreSQL, SQLite et MariaDB/MySQL ;
- génération de scripts INSERT de données de test depuis le MLD, avec
  quantités par table, respect des FK/PK/UNIQUE, aperçu et export sans
  exécution ;
- génération locale de requêtes SELECT depuis une intention métier, avec
  jointures exclusivement dérivées des FK et explication des tables utilisées ;
- import et reverse-engineering de DDL PostgreSQL/SQLite ;
- import statique d’un projet PWA depuis un dossier ou ZIP, avec détection
  Dexie/IndexedDB, enrichissement TypeScript, preuves source, validation,
  aperçu et import annulable ;
- projet PWA IndexedDB natif de référence sous
  `examples/indexeddb-demo-pwa/`, également fourni comme ZIP directement
  importable et couvert par les tests dossier/archive ;
- paquets Debian, AppImage et publication PyPI/pipx ;
- génération d'un MCD depuis une description via OpenRouter, avec aperçu et
  confirmation avant remplacement du document courant ;
- assistant MERISE conversationnel avec brouillon isolé, patchs stricts,
  révisions, questions structurantes et import confirmé/annulable ;
- analyse facultative d'un MCD existant par OpenRouter, avec propositions
  autonomes, validation locale, aperçu, sélection et application confirmée en
  une commande annulable ;
- normalisation défensive des écarts sûrs produits par certains modèles IA :
  types textuels usuels, ID recopié à l'identique dans `changes` et mises à
  jour aplaties ; les types inconnus et remplacements d'ID restent refusés ;
- exploration non destructive du MCD avec recherche, filtres, focus par
  profondeur, dépendances, zoom et masquage temporaire ;
- domaines et vues métier/technique persistants, composables et sélectionnables
  dans l'explorateur.
- comparaison non destructive du MCD courant avec une version JSON, incluant
  les différences détaillées et leurs impacts MCD/MLD/SQL.
- analyse d'impact ciblée sur les objets et attributs, séparant les dépendances
  formelles des correspondances sémantiques potentielles.
- identité MERISOR visible dans la barre d'outils et réutilisée par la fenêtre,
  le lanceur, le README et les paquets Linux.

Le README est volontairement une page courte de découverte. Les informations
de référence sont réparties entre les guides utilisateur, concepts MERISE,
références techniques, guides de contribution et ADR. Le catalogue
`DocumentationCatalog` localise ce manuel depuis les sources, un environnement
`pipx`, le paquet Debian ou une AppImage ; `DocumentationDialog` l'affiche sans
connexion réseau. Toute nouvelle fonction publique doit mettre à jour la
rubrique correspondante et, si elle résulte d'un choix structurant, ajouter un
ADR.

Les associations complexes sont déjà supportées de bout en bout. Une réflexive
répète la même entité avec des rôles obligatoires et distincts ; en 1:N elle
produit une FK vers sa propre table, en 1:1 une FK UNIQUE et en N:N une table à
deux FK différenciées par les rôles. Une association de degré trois ou plus est
matérialisée en table, avec une FK par branche et une PK composée de ces FK,
sauf si l'association possède son propre identifiant conceptuel. `FORCE_FK` est
refusé pour une n-aire. Les tests de référence `SUPERVISER` et `FOURNIR`
vérifient désormais toute la chaîne MCD → MLD → SQL.

Le panneau **Propriétés MLD** propose **ⓘ Pourquoi ?** pour la table
sélectionnée. `MldTransformationExplainer`, indépendant de Qt, utilise les
identifiants de provenance déjà produits par `McdToMldTransformer` et génère
une liste de décisions vérifiables : résultat, règle MERISE et objet MCD
source. La fenêtre couvre les tables d'entité/association, PK conceptuelles,
composées ou techniques, colonnes natives/migrées, FK et nullabilité,
contraintes UNIQUE/CHECK, historisation, n-aires et ISA. Aucune IA n'intervient
et le format JSON reste inchangé.

Le reverse-engineering de fichier est déjà disponible via **Fichier → Importer
SQL / DDL** et suit `SQL → MLD → MCD`. Il comprend les contraintes FK inline ou
ajoutées par `ALTER TABLE`, les PK composées, UNIQUE, CHECK et index. Les tables
sans PK sont conservées avec avertissement plutôt que rejetées. Les types non
représentables exactement utilisent un repli documenté (`UUID` vers
`VARCHAR(36)`, autres types propriétaires vers `TEXT`). La connexion et
l'introspection directe d'une base restent hors périmètre.

Le reverse-engineering PWA est disponible via **Fichier → Importer un projet
PWA / IndexedDB**. Il inspecte localement les appels `version().stores()` de
Dexie, `createObjectStore`/`createIndex` de l’API native et les types TypeScript
associés. Chaque proposition conserve un fichier, une ligne et un niveau de
confiance. Le candidat est validé et affiché avant confirmation, puis importé
avec disposition automatique comme une commande annulable. Le moteur ne lit
pas les enregistrements IndexedDB d’un téléphone : le dépôt ne contient en
général que la définition du schéma. Les schémas dynamiques et les relations
métier sans champ de référence explicite restent à modéliser manuellement.

Les exports **Fichier → Exporter le diagramme** comprennent PNG, SVG, PDF,
Mermaid et Graphviz/DOT. Les deux formats textuels sont déterministes et dérivés
du modèle, pas de la géométrie du canvas. Ils conservent les objets et
attributs MCD, cardinalités, rôles, ISA, ainsi que les colonnes et FK du MLD.
Le CSV reste volontairement hors périmètre tant qu'un assistant ne peut pas
faire confirmer les clés et la sémantique par l'utilisateur.

La commande **Fichier → Générer la documentation** (`Ctrl+Shift+D`) produit un
rapport Markdown, HTML ou PDF. Le moteur `ModelDocumentationGenerator` reste
indépendant de Qt et reconstruit au besoin un MLD temporaire depuis un MCD
valide. `DocumentationFileExporter` réalise l'écriture atomique et le PDF via
Qt. Les diagrammes du canvas sont embarqués en HTML/PDF ; Markdown utilise des
blocs Mermaid déterministes. Un MCD invalide produit tout de même sa partie
conceptuelle et un avertissement, sans mutation du modèle courant.

La commande **Outils → Générer des données de test** (`Ctrl+Alt+T`) n'est active
que si le MLD est présent et à jour. `TestDataGenerator`, indépendant de Qt,
produit des valeurs déterministes adaptées aux types et ordonne les INSERT
selon les FK. Il vérifie les PK et UNIQUE générées, construit des combinaisons
cartésiennes pour les tables N:N, bloque les cycles obligatoires et met à NULL
une branche facultative avec avertissement. `TestDataDialog` configure les
quantités et le dialecte, puis permet aperçu, copie et export `.sql`. Aucun code
de connexion ou d'exécution SQL n'a été ajouté.

La commande **Outils → Générer une requête SQL** (`Ctrl+Alt+R`) utilise
`SQLQueryGenerator`, sans Qt ni IA, pour reconnaître les tables citées, une
mesure numérique, un comptage, un classement et une limite. Le moteur construit
le plus court chemin de FK, prend en charge les clés composées et refuse les
tables déconnectées. `QueryGeneratorDialog` propose PostgreSQL, SQLite, MySQL et
MariaDB séparément, affiche les tables utilisées et les hypothèses, puis permet
copie et export. Cette première version couvre les SELECT/JOIN/agrégats simples,
pas les filtres complexes, sous-requêtes ou fonctions fenêtres.

## Exploration du modèle terminée

La commande **Affichage → Explorer le modèle** (`Ctrl+Alt+E`) construit une
copie projetée du MCD courant. Elle permet de rechercher des objets ou des
attributs, filtrer les types de nœuds et les liens, isoler un voisinage, afficher
les relations, cardinalités, rôles, héritages et dépendances fonctionnelles,
puis masquer temporairement certains éléments.

Le moteur `ModelExplorer` ne dépend pas de Qt. La fenêtre graphique utilise un
`DiagramController` transitoire : ses déplacements, son auto-layout et ses
masquages ne rendent jamais le document principal modifié.

## Sous-modèles et domaines terminés

La commande **Modèle → Gérer les domaines et vues** (`Ctrl+Alt+D`) édite une
copie de la configuration. Un domaine peut contenir des entités et des
associations, et un même objet peut appartenir à plusieurs domaines. Une vue
`BUSINESS` ou `TECHNICAL` combine des domaines et des objets explicites.

La confirmation applique toute la configuration par une unique
`ReplaceSubmodelsCommand`, donc annulable et sans invalider le MLD. Le JSON V2
contient les tableaux facultatifs `domains` et `submodel_views`. Leur absence
dans les anciens fichiers produit des collections vides sans migration
destructive.

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
- mypy : aucune erreur sur 104 fichiers ;
- pytest : 333 tests réussis ;
- démarrage Qt hors écran : application active jusqu'au timeout de contrôle.

## Comparateur de versions terminé

La commande **Modèle → Comparer avec une version** (`Ctrl+Alt+C`) charge un
fichier JSON comme référence et le compare au modèle en mémoire. Le moteur
`ModelVersionComparator` est indépendant de Qt et ne modifie aucun modèle.

Il compare les entités, associations, attributs et toutes leurs propriétés,
les relations/cardinalités/rôles ainsi que les héritages. Chaque changement
porte un impact explicable calculé depuis la provenance du MLD de la version
concernée : associations MCD, tables MLD, FK et index SQL touchés. Un MCD
incomplet reste comparable ; seul le chiffrage MLD/SQL indisponible est alors
signalé comme tel.

## Analyse d'impact terminée

La commande **Modèle → Analyser l'impact** (`Ctrl+Alt+I`) et le bouton présent
dans les propriétés d'un attribut utilisent `ModelImpactAnalyzer`, indépendant
de Qt. Le panneau affiche aussi un résumé immédiat pour l'attribut sélectionné.

Le moteur suit les relations MCD, dépendances fonctionnelles, colonnes MLD
migrées, PK/FK, UNIQUE, CHECK et index en utilisant les identifiants de
provenance. Les attributs portant le même nom dans d'autres objets sont affichés
séparément comme correspondances potentielles : ils ne sont jamais présentés
comme des dépendances certaines sans référence structurelle.

Si le MCD est incomplet, l'analyse MCD reste disponible et le rapport explique
que les impacts MLD/SQL n'ont pas pu être calculés.

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

## Analyse et réparation IA du MCD terminée

La commande **Modèle → ✨ Analyser avec l'IA…** envoie, après action explicite,
une copie JSON du MCD courant, son rapport de validation et les signaux de
qualité locaux au modèle OpenRouter configuré. `AiRepairService` impose une
réponse `{summary, proposals}` stricte et un maximum de douze propositions.

Chaque proposition transporte un `DraftPatch` autonome, une justification et
un niveau de confiance. Le patch est interprété par le même
`DraftPatchApplier` que l'assistant conversationnel, rechargé par le dépôt JSON
et validé sans mutation du modèle source. Les cibles absentes, patchs sans
effet et valeurs arbitraires sont refusés. Deux propositions touchant la même
propriété sont déclarées concurrentes afin d'éviter une fusion silencieuse.

`AiRepairDialog` exécute l'appel réseau dans un `QThread`, affiche les actions
**Voir**, **Ignorer** et **Appliquer la sélection**, puis réutilise l'aperçu
graphique/différentiel/JSON. Seule une confirmation explicite remplace le MCD,
via `ReplaceModelStateCommand`; toute la réparation est donc annulable en une
commande. Fermer la fenêtre ne modifie rien.

## Assistant MERISE conversationnel terminé

La commande **Modèle → Assistant MERISE conversationnel** (`Ctrl+Alt+M`)
transforme la génération ponctuelle en assistant de conception itératif.

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

### État de l'implémentation

Les étapes 1 à 9 sont terminées : modèle `DesignSession`, enveloppe JSON
stricte, premier tour, concepts/hypothèses/questions, réponses structurées,
patchs contrôlés, validation à chaque tour, aperçu graphique et différentiel,
puis import confirmé en une commande annulable.

La sauvegarde et la reprise locale d'une session conversationnelle (ancienne
étape 10) restent facultatives et ne sont pas encore implémentées. Fermer la
fenêtre abandonne le brouillon sans toucher au MCD.

### Interface livrée

- conversation et réponses à gauche ;
- brouillon MCD et état de validation à droite ;
- section « Hypothèses retenues » ;
- liste des questions en attente ;
- boutons **Aperçu et import**, **Révision précédente**, envoi libre et
  poursuite avec les réponses structurées ;
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
