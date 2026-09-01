# Journal des modifications

Toutes les évolutions importantes de MERISOR sont documentées dans ce fichier.

## [Non publié]

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
  modifie jamais le MCD courant.

### Modifié

- normalisation du formatage de tous les fichiers Python ;
- annotations renforcées pour que les 57 modules source et tests passent le
  contrôle `mypy --strict` sans erreur.

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
