# Journal des modifications

Toutes les évolutions importantes de MERISOR sont documentées dans ce fichier.

## [Non publié]

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
