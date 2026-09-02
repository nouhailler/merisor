# Journal des modifications

Toutes les évolutions importantes de MERISOR sont documentées dans ce fichier.

## [Non publié]

## [0.10.1] - 2026-09-02

### Corrigé

- l'analyse IA accepte désormais les notations de type sûres `DATE`,
  `VARCHAR(255)` et `DECIMAL(10,2)` lorsqu'un modèle OpenRouter les renvoie
  comme textes, puis les normalise vers les objets JSON V2 stricts ;
- le prompt de réparation précise explicitement le format des types afin de
  réduire les réponses incompatibles des modèles gratuits ;
- les mises à jour IA qui recopient sans changement l'identifiant dans
  `changes`, ou utilisent une forme aplatie non ambiguë, sont normalisées ; une
  tentative de remplacement d'identifiant reste strictement refusée.

### Ajouté

- logo MERISOR désormais visible dans la barre d'outils principale, en plus de
  son utilisation comme icône de fenêtre, de bureau et de paquet ;
- PWA IndexedDB native de démonstration, exécutable localement et fournie aussi
  sous forme de ZIP directement importable, avec test de référence du MCD
  `CUSTOMER → ORDER` reconstruit.

## [0.10.0] - 2026-09-02

### Ajouté

- centre de documentation hors ligne accessible par **Documentation** ou `F1`,
  avec sommaire par public, recherche et navigation entre les pages Markdown ;
- manuel restructuré en guides utilisateur, concepts MERISE, références
  techniques, guides de développement et décisions d'architecture (ADR) ;
- exemple complet `examples/motogp.json`, validé par la couche de persistance ;
- tests automatiques des pages, liens, paquets et lecteur Qt de documentation ;
- bouton **ⓘ Pourquoi ?** dans les propriétés d'une table MLD sélectionnée ;
- moteur pédagogique déterministe expliquant la création des tables, PK,
  colonnes, FK, nullabilité, UNIQUE et CHECK depuis leur provenance MCD ;
- explications spécifiques aux transformations 1:N, 1:1, N:N, n-aires,
  associations historisées/matérialisées et héritages ISA ;
- fenêtre navigable indiquant pour chaque décision le résultat, la règle
  appliquée et l'objet MCD source, avec copie du rapport complet ;
- commande **Modèle → ✨ Analyser avec l'IA…** transmettant explicitement une
  copie du MCD courant à OpenRouter pour proposer des améliorations
  sémantiques ;
- réponse IA sous schéma JSON strict, limitée à douze propositions autonomes
  avec justification et niveau de confiance ;
- validation locale de chaque patch et de ses références, aperçu graphique,
  différentiel et JSON sans mutation du document ;
- actions **Voir**, **Ignorer** et **Appliquer la sélection**, détection des
  modifications concurrentes et confirmation finale obligatoire ;
- application des réparations confirmées comme une seule commande annulable ;
- grille, aimantation et guides dynamiques sur le canvas MCD ;
- alignement sur six axes et distribution horizontale ou verticale, avec
  historique Annuler/Rétablir ;
- déplacement collectif fiable des sélections au lasso ou avec `Ctrl` ;
- copier/coller et duplication structurés des objets MCD et de leurs liens ;
- coloration déterministe des objets par domaine ;
- thèmes système, clair et sombre persistants ;
- minimap cliquable indiquant la zone visible du grand MCD ;
- recherche visuelle dans les noms et attributs ;
- pliage de la sélection, affichage global des attributs et plein écran `F11`.

### Modifié

- README recentré sur la découverte, l'installation et l'accès au manuel ;
- documentation embarquée dans les paquets PyPI, Debian et AppImage.

## [0.9.0] - 2026-09-01

### Ajouté

- reverse-engineering local de projets PWA depuis un dossier cloné ou une
  archive ZIP, sans IA ni transfert réseau ;
- analyse des schémas Dexie et IndexedDB natifs, enrichis par les interfaces et
  alias objet TypeScript ;
- déduction prudente des identifiants, index, unicités, types et références,
  avec identifiants techniques explicitement signalés lorsqu’aucun `keyPath`
  n’est disponible ;
- aperçu obligatoire du MCD proposé, preuves `fichier:ligne`, niveaux de
  confiance, avertissements et rapport de validation ;
- import confirmé, automatiquement disposé et annulable en une seule commande
  via **Fichier → Importer un projet PWA / IndexedDB…** (`Ctrl+Alt+P`).

### Sécurité

- limites sur le nombre et la taille des fichiers analysés ;
- exclusion de `node_modules`, répertoires de build et fichiers binaires ;
- lecture locale uniquement et extraction ZIP interdite, évitant toute écriture
  de contenu non fiable hors du projet.

## [0.8.0] - 2026-09-01

### Modifié

- documentation des associations réflexives et n-aires alignée sur leur prise
  en charge réelle de bout en bout, avec exemples `SUPERVISER` et `FOURNIR` ;
- tests d'intégration renforcés pour vérifier leurs transformations complètes
  `MCD → MLD → SQL` dans les trois dialectes SQL ;
- le reverse-engineering conserve désormais les tables sans clé primaire dans
  le MLD/MCD et signale l'identifiant manquant au lieu de bloquer tout l'import ;
- les types SQL non portables ou propriétaires reçoivent un type logique de
  repli accompagné d'un avertissement explicite (`UUID`, `JSONB`, `BLOB`, etc.) ;
- prise en charge des entiers MySQL `TINYINT`, `MEDIUMINT` et `UNSIGNED`, avec
  signalement lorsque la sémantique non signée ne peut pas être conservée.

### Ajouté

- générateur local et explicable de requêtes `SELECT` depuis une description
  métier et le MLD, sans IA ni exécution ;
- reconnaissance des tables, mesures numériques, classements, sommes,
  comptages, regroupements et limites simples ;
- résolution des chemins de jointure exclusivement depuis les FK, y compris
  les FK composées, avec refus des concepts déconnectés ;
- cibles distinctes PostgreSQL, SQLite, MySQL et MariaDB, liste visible des
  tables utilisées, explications, avertissements, copie et export `.sql` via
  **Outils → Générer une requête SQL…** (`Ctrl+Alt+R`) ;
- générateur déterministe de données synthétiques exclusivement fondé sur le
  MLD, produisant des scripts `INSERT` PostgreSQL, SQLite ou MariaDB/MySQL ;
- quantités configurables par table, aperçu, copie et export `.sql` depuis
  **Outils → Générer des données de test…** (`Ctrl+Alt+T`) ;
- ordonnancement selon les FK, conservation des références simples/composées,
  parcours cartésien des clés d'association et contrôle des PK/UNIQUE ;
- détection des cycles de FK obligatoires et résolution documentée des cycles
  facultatifs par `NULL`, sans aucune connexion ni exécution automatique ;
- générateur de documentation complet fondé sur le MCD et le MLD, avec
  entités, attributs, associations, cardinalités, héritages, tables, PK, FK et
  contraintes ;
- fiches techniques déterministes par entité dans une représentation YAML,
  sans invention de descriptions métier absentes du modèle ;
- export de la documentation en Markdown avec diagrammes Mermaid, en HTML
  autonome avec images embarquées et en PDF A4 ;
- commande **Fichier → Générer la documentation…** (`Ctrl+Shift+D`), capable de
  recalculer un MLD obsolète sans modifier le document courant et de documenter
  un MCD invalide avec avertissements ;
- export documentaire du MCD et du MLD en Mermaid (`.mmd`, `.mermaid`) ;
- export documentaire du MCD et du MLD en Graphviz/DOT (`.dot`, `.gv`) ;
- conservation des attributs, types, PK/FK, cardinalités, rôles et héritages
  dans les formats textuels, avec génération déterministe et écriture atomique ;
- matrice des formats d'import/export et clarification du périmètre CSV dans le
  README.

## [0.7.0] - 2026-09-01

### Ajouté

- workflow GitHub Actions de qualité exécutant Ruff, mypy en mode strict et la
  suite pytest à chaque push ou pull request vers `main` ;
- configuration partagée de formatage, lint et typage dans `pyproject.toml` ;
- analyse locale de qualité du MCD avec suggestions de typage et d'unicité,
  détection d'entités similaires, conventions de nommage et signaux de
  normalisation ;
- rapport graphique avec score global pondéré, six dimensions, niveaux de
  confiance et justification de chaque déduction ;
- assistant pédagogique de normalisation avec dépendances fonctionnelles,
  fermeture d'attributs, clés candidates et contrôles 1NF/2NF/3NF ;
- persistance JSON rétrocompatible des dépendances fonctionnelles ;
- aperçu non destructif des décompositions et application confirmée/annulable
  des extractions 3NF non ambiguës ;
- suggestions facultatives de dépendances via OpenRouter, exécutées hors du
  thread graphique et soumises à confirmation ;
- édition complète des attributs MCD : nullabilité, valeur par défaut,
  unicité, commentaire, auto-incrémentation et contraintes `CHECK` ;
- propagation de ces propriétés vers le MLD, les trois dialectes SQL et le
  reverse-engineering DDL, avec commentaires SQL adaptés au dialecte ;
- affichage du type et des principales contraintes directement dans les objets
  du graphe MCD ;
- assistant MERISE conversationnel accessible depuis le menu **Modèle**, avec
  détection de concepts, hypothèses visibles et questions structurantes ;
- brouillon MCD local isolé du document, réponses OpenRouter sous enveloppe JSON
  stricte et évolutions exprimées uniquement par patchs contrôlés ;
- révisions du brouillon, retour à la version précédente et validation MERISE
  après chaque échange ;
- aperçu graphique, comparaison avec le MCD courant et import final confirmé
  comme une seule commande annulable ;
- appel conversationnel asynchrone avec progression et messages lisibles en cas
  de quota, d'erreur réseau ou de réponse JSON invalide ;
- vue **Exploration du modèle** avec recherche par objet ou attribut, filtres,
  focus par profondeur, zoom et ajustement du graphe ;
- panneau de dépendances affichant relations, cardinalités, rôles, héritages ISA
  et dépendances fonctionnelles ;
- masquage temporaire et restauration d'éléments sur une projection qui ne
  modifie jamais le MCD courant ;
- domaines persistants regroupant entités et associations, avec appartenance
  multiple possible ;
- vues enregistrées de type métier (`BUSINESS`) ou technique (`TECHNICAL`),
  composées de domaines et d'objets explicites ;
- gestion graphique des domaines et vues, application globale annulable et
  sélection directe de chaque sous-modèle dans l'explorateur ;
- persistance JSON V2 rétrocompatible des champs `domains` et
  `submodel_views`.
- comparateur de versions JSON accessible depuis le menu **Modèle**, avec
  recherche et filtres sur les ajouts, modifications et suppressions ;
- comparaison détaillée des attributs, cardinalités, rôles, propriétés
  d'association et héritages ISA ;
- analyse d'impact fondée sur la provenance MCD → MLD, recensant associations,
  tables logiques, contraintes FK et index SQL touchés ;
- dialogue de comparaison non destructif avec rapport copiable et indication
  explicite lorsqu'un MLD ne peut pas être dérivé d'une version incomplète.
- analyse d'impact accessible depuis le menu **Modèle** et depuis l'attribut
  sélectionné dans le panneau de propriétés ;
- suivi des colonnes migrées, relations, dépendances fonctionnelles, PK, FK,
  contraintes UNIQUE/CHECK et index explicites ;
- séparation visible entre dépendances structurelles certaines et
  correspondances de noms à confirmer, avec niveau de risque et rapport
  copiable.

### Modifié

- normalisation du formatage de tous les fichiers Python ;
- annotations renforcées pour que les 75 modules source et tests passent le
  contrôle `mypy --strict` sans erreur.

### Corrigé

- déclaration de la dépendance Debian `python3-pyside6.qtsvg`, nécessaire au
  démarrage lorsque l'export SVG est disponible.

## [0.6.1] - 2026-08-31

### Corrigé

- installation de la bibliothèque EGL requise par PySide6 dans le job de
  packaging GitHub Actions ;
- clarification des limites ISA et de la matérialisation des associations 1:1
  porteuses d'attributs dans le README.

## [0.6.0] - 2026-08-31

### Ajouté

- disposition automatique déterministe du MCD ;
- réorganisation automatique après import d'un MCD généré par l'IA ;
- commande **Modèle → Réorganiser automatiquement le MCD** annulable ;
- résolution des chevauchements tenant compte de la taille des objets ;
- logo MERISOR et icône de bureau installée avec le paquet Debian ;
- captures d'écran de l'éditeur MCD, du MLD, du SQL et de l'import IA ;
- licence MIT ;
- types logiques configurables sur les attributs MCD : `INTEGER`, `BIGINT`,
  `DECIMAL`, `FLOAT`, `BOOLEAN`, `VARCHAR`, `TEXT`, `DATE`, `TIME`, `DATETIME`
  et `TIMESTAMP` ;
- réglage de la longueur `VARCHAR` et de la précision/échelle `DECIMAL` dans le
  panneau de propriétés ;
- propagation des types explicites du JSON au MLD puis aux trois dialectes SQL.
- associations réflexives avec rôles distincts, affichage parallèle et FK
  auto-référencées dans le MLD ;
- associations ternaires et de degré supérieur matérialisées en tables avec PK
  et FK composées ;
- héritages/spécialisations ISA, connecteur graphique et stratégies
  `PARENT_ONLY`, `CHILDREN_ONLY` et `JOINED` ;
- persistance JSON rétrocompatible des rôles de relation et des héritages.
- génération OpenRouter non bloquante dans un `QThread`, avec indicateur de
  progression et verrouillage temporaire des contrôles concernés.
- import et reverse-engineering de DDL PostgreSQL/SQLite vers un MLD fidèle puis
  un MCD heuristique, avec aperçu et confirmation avant remplacement ;
- reconnaissance des tables de jointure, relations 1:N, réflexives et
  spécialisations ISA jointes depuis les contraintes SQL ;
- import des PK/FK composées, contraintes UNIQUE/CHECK et index explicites.
- export visuel du canvas MCD ou MLD actif en PNG haute résolution, SVG
  vectoriel et PDF A4 paysage ;
- cadrage automatique du contenu exporté et masquage temporaire de la
  sélection, sans modifier le diagramme.
- packaging AppImage autonome pour les distributions Linux `x86_64` et
  `aarch64`, en complément du paquet Debian ;
- publication automatique des fichiers `.deb` et `.AppImage` dans les releases
  GitHub, avec test de démarrage de l'AppImage.
- métadonnées de distribution PyPI complètes et installation via
  `pipx install merisor` ;
- publication PyPI sans secret statique par GitHub Actions et OIDC, avec wheel,
  archive source, contrôle `twine` et attestation de provenance.

### Modifié

- README entièrement restructuré pour les utilisateurs débutants et les
  contributeurs, avec guide d'installation, prise en main, architecture,
  format JSON, sécurité, limites et documentation des transformations ;
- le mode de typage automatique préserve les anciens comportements
  `INTEGER` pour les identifiants et `VARCHAR(100)` pour les autres attributs.

## [0.5.0] - 2026-08-30

### Ajouté

- menu **Fichier → Ouvrir récent**, conservant les dix derniers modèles ;
- zoom de la vue graphique MLD avec boutons et `Ctrl` + molette ;
- panneau de propriétés pour les tables sélectionnées dans le MLD ;
- menu **Paramètres** et stockage local de la clé OpenRouter ;
- prise en charge du trousseau système via le paquet optionnel `keyring` ;
- test de la clé OpenRouter ;
- récupération et sélection des modèles texte gratuits ;
- activation ou désactivation de la génération assistée par IA ;
- fenêtre de description métier pour générer un MCD ;
- génération d'un JSON MERISOR version 2 par OpenRouter ;
- validation structurelle du JSON et validation métier MERISE ;
- aperçu des entités, associations, relations et cardinalités générées ;
- correction manuelle et revalidation du JSON avant import ;
- import explicite du MCD sans modification préalable du document courant ;
- gestion lisible des erreurs OpenRouter, des quotas et des réponses invalides.

### Modifié

- cadres MLD élargis pour éviter les chevauchements de texte ;
- affichage MLD enrichi avec types, nullabilité, PK, FK, UQ et AI ;
- documentation OpenRouter, génération IA et installation Debian complétée ;
- couverture de tests portée à 140 tests automatisés.

### Sécurité

- la clé OpenRouter n'est jamais enregistrée dans les fichiers JSON du projet ;
- le MCD courant n'est remplacé qu'après validation et confirmation explicite ;
- un JSON IA invalide ne peut pas être importé.

## [0.4.0] - 2026-08-29

### Ajouté

- génération MCD → MLD ;
- génération SQL PostgreSQL, SQLite et MariaDB/MySQL ;
- gestion des associations historisées et stratégies de matérialisation ;
- validation du MCD et du MLD ;
- paquet Debian initial.
