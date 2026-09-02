<p align="center">
  <img src="https://raw.githubusercontent.com/nouhailler/merisor/main/src/merisor/assets/merisor.png" alt="Logo MERISOR" width="190">
</p>

<h1 align="center">MERISOR</h1>

<p align="center">
  <strong>Du modèle métier au script SQL, dans une application de bureau libre.</strong>
</p>

<p align="center">
  <a href="https://github.com/nouhailler/merisor/releases/latest"><img alt="Dernière release" src="https://img.shields.io/github/v/release/nouhailler/merisor?display_name=tag&sort=semver"></a>
  <img alt="Python 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white">
  <img alt="PySide6" src="https://img.shields.io/badge/Interface-PySide6-41CD52?logo=qt&logoColor=white">
  <img alt="Tests pytest" src="https://img.shields.io/badge/Tests-pytest-0A9EDC?logo=pytest&logoColor=white">
  <a href="https://github.com/nouhailler/merisor/actions/workflows/quality.yml"><img alt="Qualité Python" src="https://github.com/nouhailler/merisor/actions/workflows/quality.yml/badge.svg"></a>
  <a href="https://github.com/nouhailler/merisor/blob/main/LICENSE"><img alt="Licence MIT" src="https://img.shields.io/badge/Licence-MIT-blue.svg"></a>
  <a href="https://pypi.org/project/merisor/"><img alt="PyPI" src="https://img.shields.io/pypi/v/merisor?logo=pypi&logoColor=white"></a>
</p>

MERISOR est un éditeur graphique MERISE pour Linux. Il permet de dessiner un
MCD, de contrôler sa cohérence, de produire un MLD structuré puis de générer un
script SQL pour PostgreSQL, SQLite ou MariaDB/MySQL. Le modèle peut aussi être
préparé par une IA via OpenRouter, avec validation et confirmation avant import.

> [!IMPORTANT]
> MERISOR génère du SQL, mais ne se connecte à aucune base de données et
> n’exécute jamais le script. Le MCD reste toujours la source de vérité.

## 📸 Aperçu

### Édition d’un MCD

![Fenêtre principale de MERISOR avec un MCD MotoGP et le panneau de propriétés](https://raw.githubusercontent.com/nouhailler/merisor/main/docs/images/mcd-editor.png)

### Typage des attributs MCD

![Sélection d’un type DECIMAL avec précision et échelle dans le panneau de propriétés](https://raw.githubusercontent.com/nouhailler/merisor/main/docs/images/attribute-types.png)

<table>
  <tr>
    <td width="50%"><strong>MLD graphique et propriétés</strong></td>
    <td width="50%"><strong>Aperçu SQL avant export</strong></td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/nouhailler/merisor/main/docs/images/mld-view.png" alt="Vue graphique du MLD dans MERISOR"></td>
    <td><img src="https://raw.githubusercontent.com/nouhailler/merisor/main/docs/images/sql-preview.png" alt="Aperçu d’un script PostgreSQL généré par MERISOR"></td>
  </tr>
</table>

### Import d’un MCD proposé par l’IA

![Aperçu et validation d’un MCD généré par IA avant import](https://raw.githubusercontent.com/nouhailler/merisor/main/docs/images/ai-preview.png)

## 🧭 MERISE en trente secondes

Vous découvrez MERISE ? Voici les trois niveaux manipulés par l’application :

| Niveau | Rôle | Exemple |
|---|---|---|
| **MCD** — Modèle Conceptuel de Données | Décrit les objets métier et leurs liens, sans dépendre d’une base | `PILOTE participe à COURSE` |
| **MLD** — Modèle Logique de Données | Transforme le MCD en tables, colonnes, PK et FK | `PARTICIPER(id_pilote, id_course)` |
| **SQL** | Traduit le MLD dans le dialecte d’un SGBD | `CREATE TABLE ...` |

Le flux est volontairement unidirectionnel :

```mermaid
flowchart LR
    A[🧩 MCD] -->|Valider| B[✅ MCD cohérent]
    B -->|Générer le MLD| C[🗂️ MLD]
    C -->|Générer SQL| D[(PostgreSQL)]
    C -->|Générer SQL| E[(SQLite)]
    C -->|Générer SQL| F[(MariaDB / MySQL)]
```

## ✨ Fonctionnalités

### 🧩 Modélisation MCD

- création, sélection, déplacement et suppression d’entités et d’associations ;
- relations attachées aux objets : les lignes et cardinalités suivent les
  déplacements ;
- attributs d’entités et d’associations ;
- types logiques explicites ou automatiques, avec longueur de `VARCHAR` et
  précision/échelle de `DECIMAL` ;
- propriétés complètes des attributs : présence obligatoire/facultative,
  valeur par défaut, unicité, commentaire, auto-incrémentation et expressions
  `CHECK` ;
- identifiants simples ou composés, repérés par `#` ;
- cardinalités `(0,1)`, `(0,N)`, `(1,1)` et `(1,N)` ;
- associations historisées ;
- stratégies `AUTO`, `FORCE_TABLE` et `FORCE_FK` ;
- associations réflexives avec rôles de branche, et associations n-aires ;
- spécialisations ISA avec stratégies mère seule, filles seules ou jointes ;
- annuler/rétablir pour les principales opérations ;
- zoom, déplacement du canvas et disposition automatique du graphe ;
- export du MCD ou du MLD actif en PNG haute résolution, SVG, PDF, Mermaid ou
  Graphviz/DOT ;
- génération d'une documentation complète en Markdown, HTML ou PDF ;
- sauvegarde JSON versionnée, chargement V1/V2 et fichiers récents.

### 🎨 Canvas productif

Le canvas principal propose désormais les outils attendus sur les grands
diagrammes :

- grille optionnelle, aimantation au pas de la grille et guides dynamiques sur
  les axes des objets voisins ;
- alignement à gauche, à droite, en haut ou en bas, centrage et distribution
  régulière de la sélection ;
- sélection multiple au lasso ou avec `Ctrl`, déplacement collectif conservé
  comme une seule opération annulable ;
- copier/coller et duplication structurés : attributs, relations internes,
  cardinalités, rôles, héritages et dépendances fonctionnelles sont conservés ;
- couleur pastel déterministe selon le premier domaine de l’objet ;
- thèmes système, clair et sombre mémorisés dans les préférences locales ;
- recherche visuelle intégrée à la barre d’outils, qui met les correspondances
  en évidence et atténue le reste du graphe ;
- pliage individuel d’entités ou d’associations et masquage global temporaire
  des attributs ;
- minimap cliquable avec représentation de la zone actuellement visible ;
- mode plein écran avec `F11`.

Les préférences de grille, guides, aimantation, minimap et thème utilisent les
réglages locaux de l’application. Elles n’ajoutent aucune donnée de présentation
au JSON métier et ne modifient donc ni le MCD, ni le MLD.

### 🧭 Exploration des grands modèles

La commande **Affichage → Explorer le modèle…** (`Ctrl+Alt+E`) ouvre une vue
de navigation indépendante du canvas d'édition :

- recherche par nom d'entité, d'association ou d'attribut ;
- filtres séparés pour les entités, associations, relations et héritages ;
- focus sur un objet avec voisinage direct, deux niveaux, objet seul ou modèle
  complet ;
- zoom, recentrage automatique et ajustement à la fenêtre ;
- affichage des cardinalités, rôles, héritages ISA et dépendances
  fonctionnelles de l'objet sélectionné ;
- masquage temporaire d'éléments et restauration individuelle ou globale ;
- filtrage du graphe par les résultats de recherche et leur contexte direct.

Cette exploration travaille sur une projection en mémoire : déplacer, filtrer
ou masquer un objet dans cette fenêtre ne modifie jamais le MCD enregistré.

### 🗃️ Sous-modèles et domaines

La commande **Modèle → Gérer les domaines et vues…** (`Ctrl+Alt+D`) permet de
structurer un grand MCD sans le découper en plusieurs fichiers :

- un domaine regroupe librement des entités et des associations ;
- un objet peut appartenir à plusieurs domaines ;
- une vue métier compose un ou plusieurs domaines et des objets additionnels ;
- une vue technique utilise le même mécanisme pour présenter l'implémentation ;
- la vue globale reste toujours disponible ;
- les domaines et vues sont enregistrés dans le JSON du projet ;
- toute la configuration est appliquée comme une seule opération annulable.

Les vues enregistrées apparaissent automatiquement dans la liste **Vue** de
l'explorateur. Choisir un domaine, une vue métier ou une vue technique limite
immédiatement le graphe tout en conservant la recherche, le focus et les filtres.

### 🔀 Comparateur de versions

La commande **Modèle → Comparer avec une version…** (`Ctrl+Alt+C`) compare le
MCD actuellement ouvert à un ancien fichier JSON MERISOR. Le fichier choisi
sert de référence : le rapport décrit donc son évolution vers l'état courant.

- ajouts, modifications et suppressions d'entités, associations et attributs ;
- différences de type, identifiant, nullabilité, valeur par défaut, unicité,
  commentaire, auto-incrémentation et contraintes ;
- changements de cardinalité, de rôle, d'historisation, de matérialisation et
  d'héritage ISA ;
- recherche et filtre par nature du changement ;
- rapport copiable, sans modification d'aucune des deux versions ;
- impact détaillé sur les associations MCD, les tables MLD, les contraintes FK
  et les index SQL grâce à la provenance MCD → MLD.

Exemple de rapport :

```text
+ CLIENT.telephone [attribut]
+ CLIENT.date_naissance [attribut]
~ CLIENT.email [type] : VARCHAR(100) → VARCHAR(255)
- CLIENT.adresse [attribut]
```

Si une version est structurellement incomplète, ses changements MCD restent
consultables. Le dialogue indique alors clairement que ses impacts MLD/SQL ne
peuvent pas être calculés, plutôt que de produire une estimation trompeuse.

### 🧬 Analyse d'impact

La commande **Modèle → Analyser l'impact…** (`Ctrl+Alt+I`) suit les dépendances
d'une entité, d'une association ou d'un attribut avant sa modification. Le même
rapport est accessible directement par **Analyser l'impact…** sous les
propriétés de l'attribut sélectionné, où un résumé est affiché en permanence.

L'analyse recense notamment :

- les relations et cardinalités MCD concernées ;
- les colonnes migrées dans d'autres tables grâce à la provenance MCD → MLD ;
- les PK, FK, contraintes UNIQUE et CHECK ;
- les index explicites ;
- les dépendances fonctionnelles déclarées ;
- les attributs homonymes présents dans d'autres objets.

Les résultats distinguent toujours les **impacts certains**, issus des
références structurelles du modèle, des **correspondances à confirmer** fondées
sur un nom identique. Par exemple, `FACTURE.prix` peut être signalé comme une
correspondance potentielle de `PRODUIT.prix`, mais ne devient une dépendance
certaine que si le modèle contient effectivement une référence ou une
contrainte qui les relie.

```text
ANALYSE D'IMPACT — CLIENT.id_client
├── COMMANDE.id_client       colonne migrée
├── ADRESSE.id_client        colonne migrée
├── FACTURE.id_client        colonne migrée
├── 3 contraintes FK
└── 3 relations MCD
```

### ✅ Validation MERISE

- noms manquants ou dupliqués ;
- entités sans identifiant ;
- attributs dupliqués ;
- associations reliées à moins de deux entités ;
- relations incomplètes, cardinalités invalides et rôles réflexifs dupliqués ;
- incompatibilités entre historisation, `FORCE_FK` et N:N ;
- rapport distinguant erreurs bloquantes et avertissements.

### 🧠 Analyse intelligente de la qualité

La commande **Modèle → Analyser la qualité du modèle** ajoute une seconde
couche non bloquante, entièrement locale et sans IA :

- types suggérés à partir du nom (`date_naissance` → `DATE`, `prix` →
  `DECIMAL(10,2)`, `est_actif` → `BOOLEAN`, etc.) ;
- suggestions d'unicité pour les courriels, identifiants de connexion,
  références et identifiants métier courants ;
- détection d'entités aux noms proches, synonymes ou partageant de nombreux
  attributs, en ignorant les couples mère/fille ISA ;
- contrôle des conventions de nommage majoritaires pour les entités,
  associations et attributs ;
- signaux de normalisation : attributs numérotés, listes encodées dans un
  champ, attributs composés, clés étrangères techniques présentes dans le MCD
  et objets anormalement larges ;
- score global pondéré et six scores détaillés, avec chaque déduction affichée
  et expliquée.

Les résultats sont des recommandations avec un niveau de confiance. Ils ne
modifient jamais automatiquement le MCD et ne remplacent pas la validation
structurelle MERISE.

### 🎓 Assistant de normalisation

La commande **Modèle → Assistant de normalisation** accompagne l'utilisateur
sans masquer les hypothèses métier :

- saisie et modification de dépendances fonctionnelles composites `X → Y` ;
- calcul de fermeture d'attributs et recherche déterministe des clés candidates ;
- vérification formelle de la 2NF et de la 3NF à partir des dépendances saisies ;
- détection heuristique des listes, attributs composés et groupes répétitifs
  susceptibles d'enfreindre la 1NF ;
- rapport pédagogique expliquant chaque constat et son « Pourquoi ? » ;
- aperçu d'une décomposition dans un MCD projeté, sans toucher au document ;
- application confirmée des extractions 3NF non ambiguës en une opération
  entièrement annulable ;
- suggestions OpenRouter facultatives, asynchrones et toujours soumises à
  confirmation humaine.

> [!NOTE]
> La 1NF dépend de la signification des données : MERISOR signale donc des
> indices, pas des certitudes. Les conclusions 2NF/3NF ne sont complètes que si
> toutes les dépendances métier pertinentes ont été déclarées.

### 🗂️ Génération du MLD

- tables et colonnes issues du MCD ;
- PK et FK simples ou composées ;
- nullabilité et contraintes UNIQUE nécessaires aux relations 1:1 ;
- matérialisation des associations N:N et des associations historisées ;
- PK technique déterministe pour une association historisée sans identifiant ;
- conservation de la provenance MCD → MLD ;
- vues graphique et textuelle, zoom, copie et export ;
- indicateur **à jour / obsolète** après modification du MCD.

### 🛢️ Génération SQL

- PostgreSQL, SQLite et MariaDB/MySQL ;
- PK, FK, UNIQUE, CHECK et index explicites ;
- `NULL` / `NOT NULL` et identifiants auto-incrémentés ;
- ordre de création selon les dépendances et prise en charge des cycles ;
- échappement des identifiants et avertissement pour les mots réservés ;
- aperçu, copie et export en `.sql` ;
- aucune connexion et aucune exécution automatique.

### 🧪 Génération de données de test

La commande **Outils → Générer des données de test…** (`Ctrl+Alt+T`) travaille
exclusivement depuis le MLD valide et à jour :

- nombre de lignes configurable séparément pour chaque table, de zéro à
  10 000 depuis l'interface ;
- scripts `INSERT` pour PostgreSQL, SQLite et MariaDB/MySQL ;
- valeurs synthétiques adaptées aux types logiques : nombres, décimaux,
  booléens, textes, courriels, dates, heures et horodatages ;
- ordre d'insertion calculé depuis les dépendances FK ;
- reprise réelle des valeurs de clés référencées, y compris pour les FK
  composées ;
- parcours cartésien déterministe des FK des tables d'association afin de
  préserver leurs PK composées ;
- contrôle des PK et contraintes UNIQUE avant production du script ;
- aperçu, copie et export en `.sql` ;
- **aucune connexion et aucune exécution automatique**.

Un cycle composé uniquement de FK facultatives est résolu avec des valeurs
`NULL` et un avertissement. Un cycle de FK obligatoires bloque la génération,
car une suite de simples `INSERT` ne pourrait pas le satisfaire de façon
portable. Les expressions `CHECK` libres étant du SQL arbitraire, MERISOR les
signale lorsqu'il ne peut pas démontrer que les valeurs synthétiques les
respectent : le script doit alors être relu avant utilisation.

### 🔎 Générateur de requêtes SQL

La commande **Outils → Générer une requête SQL…** (`Ctrl+Alt+R`) transforme une
intention de consultation en `SELECT`, toujours depuis le MLD valide et à jour.
Elle prend en charge séparément PostgreSQL, SQLite, MySQL et MariaDB.

Exemple :

```text
Afficher les 10 meilleurs clients selon le montant total de leurs commandes.
```

MERISOR reconnaît la table principale, recherche une mesure numérique métier,
calcule le plus court chemin dans le graphe des FK, puis produit les `JOIN`,
`SUM`, `COUNT`, `GROUP BY`, `ORDER BY` et `LIMIT` simples correspondants. Le
dialogue affiche explicitement :

```text
Cette requête utilise les tables : CLIENT, COMMANDE, LIGNE_COMMANDE.
```

Chaque résultat fournit aussi les hypothèses et avertissements ayant conduit au
SQL. Deux tables déconnectées sont refusées : MERISOR ne fabrique jamais une
condition de jointure absente du MLD. Si aucun agrégat n'est reconnu, il génère
une sélection simple des tables citées et le signale.

Cette première version locale ne cherche pas encore à interpréter tout le
langage SQL : filtres métier complexes, sous-requêtes, fonctions fenêtres et
expressions libres devront être exprimés plus précisément ou complétés après
génération. Aucune IA, connexion ou exécution de requête n'intervient.

### 🔄 Reverse-engineering SQL / DDL

- import de fichiers `.sql` et `.ddl` PostgreSQL ou SQLite ;
- reconstruction structurée du MLD : tables, colonnes, types, PK simples ou
  composées, FK, UNIQUE, CHECK et index ;
- reconnaissance des tables de jointure comme associations MCD ;
- reconstruction des relations 1:N et des FK réflexives ;
- détection d'une spécialisation ISA `JOINED` lorsqu'une PK est également une
  FK vers une table mère ;
- import conservé même lorsqu'une table n'a pas de PK : l'entité est alors
  signalée sans identifiant et doit être corrigée avant une nouvelle génération ;
- adaptation documentée des types non portables (`UUID` → `VARCHAR(36)`,
  `JSONB` ou type propriétaire → `TEXT`) avec avertissement de perte ;
- aperçu du MLD, du MCD heuristique et du DDL source avant confirmation ;
- aucun changement du document courant sans validation explicite.

### 📱 Reverse-engineering d’une PWA / IndexedDB

MERISOR peut proposer un MCD à partir des sources locales d’une PWA, sans IA,
sans envoyer le dépôt sur Internet et sans lire les données personnelles d’un
navigateur :

- import d’un dossier cloné ou d’une archive `.zip` ;
- détection des schémas **Dexie** (`version().stores()`) ;
- détection d’IndexedDB natif (`createObjectStore`, `createIndex`, `keyPath`) ;
- enrichissement des attributs et types depuis les interfaces et alias objet
  TypeScript associés ;
- proposition des relations à partir des champs de référence tels que
  `clientId`, `id_client` ou `managerId` ;
- preuve `fichier:ligne` et niveau de confiance pour chaque déduction ;
- validation MERISE, aperçu obligatoire, disposition automatique et import en
  une seule commande annulable.

> [!IMPORTANT]
> Le dépôt contient généralement le **code qui définit le schéma** IndexedDB,
> pas les enregistrements créés sur le téléphone. Ceux-ci restent dans le
> stockage du navigateur de l’appareil, sauf si l’application les synchronise
> explicitement avec un serveur ou les exporte. Les cardinalités et relations
> proposées par analyse statique doivent donc être vérifiées par un humain.

### 📦 Formats d'import et d'export

| Format | Import | Export | Remarques |
|---|:---:|:---:|---|
| JSON MERISOR V1/V2 | ✓ | ✓ | Format natif, rétrocompatible |
| Projet PWA / IndexedDB | ✓ | — | Dossier ou ZIP ; Dexie, API native et types TypeScript |
| PostgreSQL DDL | ✓ | ✓ | `CREATE TABLE`, FK, `ALTER TABLE`, contraintes et index |
| SQLite DDL | ✓ | ✓ | Syntaxe inline et `AUTOINCREMENT` |
| MariaDB/MySQL | Partiel | ✓ | Constructions portables, `AUTO_INCREMENT`, entiers courants |
| PNG | — | ✓ | Image haute résolution |
| SVG | — | ✓ | Vectoriel, recommandé pour la documentation |
| PDF | — | ✓ | A4 paysage |
| Mermaid | — | ✓ | Texte `.mmd`, intégrable dans Markdown et Git |
| Graphviz/DOT | — | ✓ | Texte `.dot`, automatisable avec Graphviz |
| Documentation Markdown | — | ✓ | MCD, MLD, tables et blocs techniques YAML |
| Documentation HTML | — | ✓ | Document autonome avec diagrammes embarqués |
| Documentation PDF | — | ✓ | Rapport A4 prêt à transmettre ou imprimer |

L'import CSV n'est pas activé : un tableau de données ne décrit ni les clés,
ni les cardinalités, ni la distinction entité/association. Une future version
pourra proposer un assistant pédagogique demandant explicitement ces choix,
sans prétendre reconstruire automatiquement un MCD depuis quelques lignes.

### 📚 Générateur de documentation

La commande **Fichier → Générer la documentation…** (`Ctrl+Shift+D`) construit
un dossier de modèle lisible aussi bien par une équipe métier que technique :

- diagramme conceptuel, entités, attributs, associations, rôles et
  cardinalités ;
- héritages ISA, historisation et stratégie de matérialisation ;
- MLD dérivé avec tables, colonnes, PK, FK, UNIQUE, CHECK et index ;
- fiches techniques par entité dans une représentation YAML lisible ;
- formats **Markdown**, **HTML autonome** et **PDF A4**.

Le Markdown contient des diagrammes Mermaid afin de rester versionnable et
facile à intégrer à Git. Le HTML et le PDF embarquent les rendus du canvas
lorsqu'ils sont disponibles. Si le MLD affiché est absent ou obsolète,
MERISOR tente de le recalculer sans modifier le document courant. Un MCD
invalide reste documentable, mais la section logique est alors marquée comme
indisponible avec un avertissement explicite.

Les descriptions métier ne sont pas devinées : tant qu'aucun champ de
description n'existe dans le modèle, le rapport affiche **non renseignée**.
Les commentaires réellement saisis sur les attributs sont, eux, conservés.

### ✨ Génération assistée par IA

- clé OpenRouter stockée hors des projets ;
- test de la clé et récupération des modèles texte gratuits ;
- choix du modèle et activation explicite de l’IA ;
- génération d’un JSON MERISOR V2 depuis une description métier ;
- aperçu, JSON éditable et double validation avant import ;
- aucune modification du document courant sans confirmation ;
- appel de génération exécuté dans un thread Qt avec progression indéterminée,
  afin de conserver une interface réactive ;
- organisation automatique du graphe après import.

### 🗣️ Assistant MERISE conversationnel

En complément de la génération ponctuelle, MERISOR propose un véritable
assistant de conception. À partir d'une description métier, il détecte les
concepts, rend ses hypothèses visibles puis pose les questions qui modifient
réellement le modèle : cardinalités, historisation, distinction entre concept
et occurrence physique, ou choix entre entité et association.

Le principe de sécurité restera le même :

```text
Conversation
    ↓
Brouillon MCD isolé et versionné
    ↓
Validation déterministe MERISOR
    ↓
Aperçu des différences
    ↓
Import confirmé et annulable
```

Les réponses OpenRouter respectent une enveloppe JSON stricte contenant
le message, les concepts détectés, les hypothèses, les questions et un patch du
brouillon. Le texte de conversation ne deviendra jamais directement la source
de vérité et aucun changement n'est appliqué silencieusement. Le brouillon est
validé à chaque tour, peut revenir à sa révision précédente, puis s'affiche sous
forme de graphe et de différences avant un import confirmé et annulable.

## 🚀 Installation

### Option A — AppImage universelle

Cette option convient à Fedora, Arch Linux, openSUSE, Debian, Ubuntu et à la
plupart des distributions Linux 64 bits récentes :

1. Téléchargez `MERISOR-<version>-x86_64.AppImage` depuis la page
   [Releases](https://github.com/nouhailler/merisor/releases/latest).
2. Rendez le fichier exécutable et lancez-le :

```bash
chmod +x MERISOR-*.AppImage
./MERISOR-*.AppImage
```

L’AppImage embarque Python, PySide6 et les dépendances de l’application. Elle
ne demande pas d’installation administrateur et ne modifie pas le système.

> [!NOTE]
> Le runtime AppImage embarqué est autonome et ne requiert pas `libfuse2`.
> Si le montage des AppImage est interdit sur votre système, utilisez
> `APPIMAGE_EXTRACT_AND_RUN=1 ./MERISOR-*.AppImage`.

### Option B — paquet Debian / Ubuntu

1. Téléchargez le fichier `.deb` depuis la page
   [Releases](https://github.com/nouhailler/merisor/releases/latest).
2. Ouvrez un terminal dans le dossier de téléchargement.
3. Installez le paquet :

```bash
sudo apt install ./merisor_0.9.0_amd64.deb
```

Adaptez le nom au fichier téléchargé. MERISOR apparaît ensuite dans le menu des
applications et peut aussi être lancé avec :

```bash
merisor
```

### Option C — installation depuis les sources

Prérequis : Debian ou Linux équivalent, Python 3.10 ou plus récent, Git et le
module `venv`.

```bash
sudo apt install git python3 python3-venv python3-pip
git clone https://github.com/nouhailler/merisor.git
cd merisor
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools
python -m pip install -e ".[test,ai]"
python -m merisor
```

L’extra `ai` installe `keyring`, recommandé pour protéger la clé OpenRouter.
Sans fonctionnalité IA, `python -m pip install -e ".[test]"` suffit.

### Option D — installation avec pipx

MERISOR est publié sur [PyPI](https://pypi.org/project/merisor/) depuis la
version `0.6.1`. `pipx` crée un environnement isolé et installe le raccourci
`merisor` sans modifier les paquets Python du système :

```bash
pipx install merisor
merisor
```

Pour utiliser le trousseau système avec la clé OpenRouter, installez l'extra
optionnel sécurisé dès le départ : `pipx install "merisor[ai]"`.

Pour mettre l’application à jour ultérieurement :

```bash
pipx upgrade merisor
```

Pour vérifier la version disponible sur PyPI puis celle installée par `pipx` :

```bash
python3 -m pip index versions merisor
pipx runpip merisor show merisor
```

La commande `pipx list` permet également de retrouver MERISOR et le chemin de
son environnement isolé.

<details>
<summary><strong>Résoudre les problèmes d’affichage Qt sous Linux</strong></summary>

Sur une machine sans écran, les tests doivent utiliser le greffon Qt
hors-écran :

```bash
QT_QPA_PLATFORM=offscreen pytest
```

Dans une session graphique classique, vérifiez que `DISPLAY` ou
`WAYLAND_DISPLAY` est défini. Avec une installation par `pip`, PySide6 fournit
Qt. Le paquet Debian dépend pour sa part des modules PySide6 de Debian.

</details>

## 🖱️ Prise en main

### 1. Construire le MCD

1. Cliquez sur **Entité**, puis dans le canvas.
2. Sélectionnez l’entité pour ajouter ses attributs dans **Propriétés**.
3. Cochez au moins un attribut comme identifiant.
4. Sélectionnez un attribut pour choisir son type, ou conservez
   **Automatique**.
5. Créez une **Association**.
6. Choisissez **Relation**, puis cliquez sur une entité et une association.
7. Sélectionnez la relation pour régler sa cardinalité.
8. Déplacez les objets librement ou utilisez
   **Modèle → Réorganiser automatiquement le MCD**.

Pour une réflexive, reliez deux fois la même entité à l'association : MERISOR
crée des rôles distincts, modifiables dans les propriétés. Pour une
spécialisation, utilisez **Modèle → Ajouter une spécialisation ISA…**, puis
choisissez la mère, les filles et la stratégie MLD.

La touche `Suppr` enlève la sélection. Supprimer une entité ou une association
supprime aussi ses relations afin d’éviter les références orphelines.

#### Éditer complètement un attribut

Sélectionnez une entité ou une association, puis un attribut dans le panneau
**Propriétés**. La section dédiée permet de modifier en une seule opération
annulable :

- le nom et le type logique ;
- la longueur de `VARCHAR` ou la précision/échelle de `DECIMAL` ;
- la présence **Obligatoire**, **Facultative** ou **Automatique** pour préserver
  le comportement d'un ancien fichier ;
- la valeur par défaut, l'unicité et l'auto-incrémentation ;
- un commentaire métier ;
- une ou plusieurs expressions `CHECK`, une par ligne.

Les identifiants restent sélectionnables directement dans la première colonne
de la liste. Une auto-incrémentation exige un identifiant simple de type
`INTEGER` ou `BIGINT`, sans valeur par défaut explicite.

### 2. Valider et enregistrer

Utilisez **Modèle → Valider le MCD**. Un modèle incomplet peut être sauvegardé
pour reprendre le travail plus tard ; MERISOR demande simplement confirmation
si des erreurs sont présentes.

Les commandes **Fichier → Ouvrir récent**, **Enregistrer** et **Enregistrer
sous…** manipulent des fichiers JSON lisibles et versionnés.

### 3. Générer le MLD

Cliquez sur **Générer le MLD**. Si le MCD contient une erreur bloquante, le
rapport indique précisément ce qui doit être corrigé. Sinon, l’onglet **MLD**
présente :

- une vue graphique avec tables et FK ;
- une vue textuelle copiable ou exportable ;
- le panneau de propriétés de la table sélectionnée.

Après une modification logique du MCD, le MLD passe à l’état **obsolète** et
doit être régénéré. Déplacer seulement un objet ne le rend pas obsolète.

### 3 bis. Vérifier la normalisation

1. Ouvrez **Modèle → Assistant de normalisation…** (`Ctrl+Shift+N`).
2. Choisissez une entité ou une association.
3. Déclarez les dépendances fonctionnelles, par exemple
   `code_service → nom_service`.
4. Consultez les clés candidates et les contrôles 1NF, 2NF et 3NF.
5. Prévisualisez une décomposition proposée : le MCD courant reste inchangé.
6. Appliquez-la seulement après confirmation ; **Annuler** restaure alors le
   modèle complet.

Le bouton **Suggérer avec l'IA** n'est actif que si OpenRouter a été configuré.
Une proposition IA n'est jamais ajoutée silencieusement.

### 4. Générer le SQL

Lorsque le MLD est valide et à jour, cliquez sur **Générer SQL**, choisissez le
SGBD, vérifiez l’aperçu puis utilisez **Copier** ou **Enregistrer sous…**.

### 4 bis. Générer des données de test

1. Générez ou régénérez d'abord le MLD.
2. Ouvrez **Outils → Générer des données de test…** (`Ctrl+Alt+T`).
3. Choisissez PostgreSQL, SQLite ou MariaDB/MySQL.
4. Saisissez le nombre de lignes souhaité pour chaque table ; zéro exclut la
   table lorsque ses lignes ne sont requises par aucune FK obligatoire.
5. Cliquez sur **Générer**, vérifiez l'aperçu, puis copiez ou enregistrez le
   script `.sql`.

MERISOR ne contacte aucune base et n'exécute jamais les `INSERT` produits.

### 4 ter. Générer une requête SQL

1. Ouvrez **Outils → Générer une requête SQL…** (`Ctrl+Alt+R`).
2. Décrivez le résultat en citant les concepts présents dans le modèle.
3. Choisissez PostgreSQL, SQLite, MySQL ou MariaDB.
4. Cliquez sur **Générer la requête**.
5. Vérifiez la liste des tables utilisées, les explications et le SQL.
6. Copiez la requête ou exportez-la en `.sql`.

La requête n'est jamais envoyée à une base de données.

### 5. Exporter un diagramme

Activez l’onglet **MCD** ou **MLD**, puis choisissez **Fichier → Exporter le
diagramme…** (`Ctrl+Shift+E`). MERISOR cadre automatiquement tout le graphe,
indépendamment du zoom affiché, et propose :

- **PNG** haute résolution pour une insertion immédiate dans un document ;
- **SVG** vectoriel pour conserver une netteté parfaite à toute taille ;
- **PDF** vectoriel en page A4 paysage pour les rapports et l’impression.
- **Mermaid** (`.mmd` ou `.mermaid`) pour les dépôts Markdown et les outils de
  documentation compatibles ;
- **Graphviz/DOT** (`.dot` ou `.gv`) pour les chaînes documentaires automatisées.

Les marques de sélection ne figurent pas dans le fichier exporté et le modèle
courant n’est pas modifié. Les exports Mermaid et DOT sont générés depuis le
modèle métier et ne dépendent donc ni du zoom ni de la disposition du canvas.

### 5 bis. Générer la documentation du projet

1. Choisissez **Fichier → Générer la documentation…** (`Ctrl+Shift+D`).
2. Sélectionnez Markdown, HTML ou PDF.
3. Choisissez le fichier de destination.
4. Consultez les éventuels avertissements dans la barre d'état.

Cette opération ne modifie ni le MCD ni le MLD. Le document obtenu rassemble
le diagramme, le dictionnaire des entités, les associations et cardinalités,
les tables logiques et une synthèse technique par entité.

### 6. Explorer un modèle volumineux

1. Facultatif : ouvrez **Modèle → Gérer les domaines et vues…** (`Ctrl+Alt+D`)
   pour créer les regroupements du projet.
2. Ouvrez **Affichage → Explorer le modèle…** (`Ctrl+Alt+E`).
3. Choisissez la vue globale, un domaine, une vue métier ou une vue technique.
4. Recherchez un objet ou un attribut dans la barre supérieure.
5. Double-cliquez sur un résultat ou utilisez **Centrer et isoler**.
6. Choisissez la profondeur du voisinage et les types d'objets visibles.
7. Sélectionnez un objet dans le graphe pour consulter ses relations,
   cardinalités, héritages et dépendances fonctionnelles.
8. Utilisez **Masquer la sélection** pour simplifier temporairement la vue ; un
   double-clic dans la liste des éléments masqués les restaure individuellement.

### 7. Générer un MCD avec OpenRouter

1. Ouvrez **Paramètres → Paramètres OpenRouter…**.
2. Saisissez votre clé, testez-la puis actualisez les modèles gratuits.
3. Choisissez un modèle et activez la génération IA.
4. Ouvrez **Modèle → Générer un MCD avec l’IA…**.
5. Décrivez les objets métier, leurs identifiants et leurs relations.
6. Vérifiez l’aperçu et les messages de validation.
7. Corrigez ou régénérez si nécessaire, puis confirmez l’import.

> [!TIP]
> Une bonne description cite les objets métier, les informations attendues,
> les identifiants, les cardinalités et les besoins d’historisation. Les
> modèles gratuits OpenRouter peuvent être soumis à des quotas.

### 8. Concevoir un MCD avec l'assistant conversationnel

1. Configurez OpenRouter comme pour la génération ponctuelle.
2. Ouvrez **Modèle → Assistant MERISE conversationnel…** (`Ctrl+Alt+M`).
3. Décrivez le besoin métier dans vos propres mots.
4. Examinez les concepts détectés et les hypothèses retenues.
5. Répondez aux questions structurantes, puis cliquez sur **Continuer avec les
   réponses**.
6. Consultez la validation et, si nécessaire, envoyez une correction ou
   revenez à la révision précédente.
7. Lorsque le brouillon est prêt, ouvrez **Aperçu et import…** pour contrôler le
   graphe, les différences et le JSON.
8. Confirmez l'import. Une seule commande est ajoutée à l'historique :
   **Édition → Annuler** restaure le MCD précédent.

> [!IMPORTANT]
> La conversation et les réponses de l'IA ne modifient jamais directement le
> document ouvert. Seul le patch JSON strict, rechargé par le dépôt MERISOR et
> validé par les règles MCD, peut faire évoluer le brouillon isolé.

### 9. Importer un schéma SQL existant

1. Ouvrez **Fichier → Importer SQL / DDL…** (`Ctrl+Shift+O`).
2. Choisissez un fichier PostgreSQL ou SQLite.
3. Contrôlez le **MLD détecté**, puis le **MCD reconstruit** dans l'aperçu.
4. Confirmez avec **Importer le MCD et le MLD**.
5. Vérifiez les cardinalités conceptuelles, puis enregistrez le projet JSON.

> [!WARNING]
> Un DDL ne contient pas toutes les intentions d'un MCD : les cardinalités
> minimales, l'historisation et certaines associations métier ne peuvent pas
> toujours être déduites. MERISOR signale chaque approximation connue. Un type
> SQL non représentable est adapté à un type logique révisable ; une table sans
> PK reste importable, mais son entité est volontairement signalée invalide.

### 10. Proposer un MCD depuis une PWA

1. Clonez le dépôt GitHub localement ou téléchargez son archive ZIP.
2. Ouvrez **Fichier → Importer un projet PWA / IndexedDB…** (`Ctrl+Alt+P`).
3. Choisissez **Dossier local cloné** ou **Archive ZIP**.
4. Contrôlez les onglets **MCD proposé**, **Preuves**, **Validation** et
   **Portée de l’analyse**.
5. Confirmez avec **Importer le MCD proposé**. Le MCD précédent peut être
   restauré immédiatement avec **Édition → Annuler**.

Les répertoires générés ou volumineux (`node_modules`, `dist`, `build`, etc.)
sont ignorés. Si aucun schéma Dexie ou IndexedDB natif n’est déclaré dans les
sources, MERISOR n’invente pas de modèle et explique pourquoi l’analyse échoue.

## ⌨️ Raccourcis utiles

| Action | Raccourci |
|---|---|
| Nouveau / Ouvrir / Enregistrer | `Ctrl+N` / `Ctrl+O` / `Ctrl+S` |
| Annuler / Rétablir | `Ctrl+Z` / `Ctrl+Shift+Z` |
| Copier / Coller / Dupliquer | `Ctrl+C` / `Ctrl+V` / `Ctrl+D` |
| Tout sélectionner | `Ctrl+A` |
| Supprimer la sélection | `Suppr` |
| Zoom avant / arrière / initial | `Ctrl++` / `Ctrl+-` / `Ctrl+0` |
| Explorer le modèle | `Ctrl+Alt+E` |
| Gérer les domaines et vues | `Ctrl+Alt+D` |
| Valider le MCD | `Ctrl+Shift+V` |
| Assistant de normalisation | `Ctrl+Shift+N` |
| Assistant MERISE conversationnel | `Ctrl+Alt+M` |
| Réorganiser le MCD | `Ctrl+Shift+L` |
| Générer le MLD | `Ctrl+Shift+M` |
| Générer SQL | `Ctrl+Alt+S` |
| Générer des données de test | `Ctrl+Alt+T` |
| Générer une requête SQL | `Ctrl+Alt+R` |
| Exporter le MCD ou MLD actif | `Ctrl+Shift+E` |
| Générer la documentation | `Ctrl+Shift+D` |
| Importer SQL / DDL | `Ctrl+Shift+O` |
| Importer une PWA / IndexedDB | `Ctrl+Alt+P` |
| Plier/déplier la sélection | `Ctrl+Alt+F` |
| Mode plein écran | `F11` |
| Zoom MLD | `Ctrl` + molette ou boutons `+` / `−` |

## 🧪 Exemple MotoGP

```text
PILOTE (0,N) ── PARTICIPER ── (1,N) COURSE

PILOTE                       COURSE
# id_pilote                  # id_course
nom                          date_course

PARTICIPER
position
points
```

Le MLD produit une table d’association :

```text
PARTICIPER
-----------
PK/FK id_course  → COURSE(id_course)
PK/FK id_pilote  → PILOTE(id_pilote)
      position
      points
```

Une association `ENGAGER` marquée **Historisée : Oui** devient une table
indépendante avec une PK technique `id_engager`. Aucune contrainte
`UNIQUE(id_pilote, id_equipe)` n’est inventée : plusieurs périodes entre le
même pilote et la même équipe restent donc possibles.

Le fichier d’exemple [motogp.json](motogp.json) peut être ouvert directement
avec **Fichier → Ouvrir…**.

## 💾 Format JSON

Le format courant est la version `2`. Les identifiants internes relient les
objets sans dépendre de leurs noms ni de leur position graphique.

```json
{
  "format_version": 2,
  "entities": [
    {
      "id": "entity_pilote",
      "name": "PILOTE",
      "position": {"x": 100, "y": 100},
      "attributes": [
        {
          "id": "attr_pilote_id",
          "name": "id_pilote",
          "identifier": true,
          "data_type": {"name": "BIGINT"},
          "nullable": false,
          "default": null,
          "unique": false,
          "comment": "Identifiant technique du pilote",
          "auto_increment": true,
          "constraints": []
        },
        {
          "id": "attr_pilote_nom",
          "name": "nom",
          "identifier": false,
          "data_type": {"name": "VARCHAR", "length": 100},
          "nullable": false,
          "default": null,
          "unique": false,
          "comment": "Nom usuel",
          "auto_increment": false,
          "constraints": ["length(nom) >= 2"]
        }
      ]
    }
  ],
  "associations": [
    {
      "id": "association_participer",
      "name": "PARTICIPER",
      "position": {"x": 350, "y": 250},
      "attributes": [],
      "is_historized": false,
      "materialization_strategy": "AUTO"
    }
  ],
  "relations": [
    {
      "id": "relation_pilote_participer",
      "entity_id": "entity_pilote",
      "association_id": "association_participer",
      "role": "",
      "cardinality": {"minimum": "0", "maximum": "N"}
    }
  ],
  "inheritances": [],
  "functional_dependencies": [
    {
      "id": "fd_pilote_nom",
      "owner_id": "entity_pilote",
      "determinant_attribute_ids": ["attr_pilote_id"],
      "dependent_attribute_ids": ["attr_pilote_nom"],
      "origin": "USER"
    }
  ],
  "domains": [
    {
      "id": "domain_course",
      "name": "Gestion des courses",
      "description": "Pilotes, courses et participations",
      "node_ids": ["entity_pilote", "association_participer"]
    }
  ],
  "submodel_views": [
    {
      "id": "view_metier_course",
      "name": "Parcours course",
      "kind": "BUSINESS",
      "domain_ids": ["domain_course"],
      "node_ids": []
    }
  ]
}
```

Compatibilité :

- les fichiers V1 sont migrés en mémoire sans perdre noms, positions ou liens ;
- une cardinalité absente reste inconnue et doit être complétée ;
- les propriétés absentes d’une ancienne association valent
  `is_historized = false` et `materialization_strategy = AUTO` ;
- un attribut sans `data_type`, ou avec `data_type: null`, reste en mode
  automatique ;
- les anciennes propriétés d'attribut absentes reçoivent les valeurs
  rétrocompatibles `nullable = null`, `default = null`, `unique = false`,
  `comment = ""`, `auto_increment = false` et `constraints = []` ;
- une relation ancienne sans `role` reçoit une chaîne vide et un fichier sans
  `inheritances` reste parfaitement lisible ;
- un fichier sans `functional_dependencies` reçoit une collection vide ; les
  origines possibles sont `USER` et `AI` ;
- un fichier sans `domains` ou `submodel_views` reste une vue globale ordinaire ;
  les types de vue enregistrés sont `BUSINESS` et `TECHNICAL` ;
- le fichier source n’est réécrit que lors d’un enregistrement explicite ;
- le MLD n’est pas sauvegardé : il est toujours recalculé depuis le MCD.

## 🧠 Règles MCD → MLD

<details>
<summary><strong>Afficher les règles de transformation</strong></summary>

### Entités

- une entité devient une table ;
- ses attributs deviennent des colonnes ;
- ses attributs identifiants forment la PK simple ou composée.

### Associations N:N

- une table portant le nom de l’association est créée ;
- les PK des entités deviennent des FK ;
- ces FK forment par défaut la PK composée ;
- les attributs de l’association restent dans cette table.

### Associations 1:N

- en `AUTO` non historisé, la règle classique migre une FK ;
- les attributs de l’association migrent avec la FK ;
- le minimum détermine la nullabilité ;
- `FORCE_TABLE` ou `AUTO` historisé crée une table indépendante.

### Associations 1:1

- `(1,1)` face à `(0,1)` place une FK `NOT NULL UNIQUE` du côté `(1,1)` ;
- `(1,1)/(1,1)` produit une FK `NOT NULL UNIQUE` ;
- `(0,1)/(0,1)` produit une FK `NULL UNIQUE` ;
- lorsque les deux côtés sont équivalents, un tri stable par nom puis par
  identifiant choisit la table porteuse.

### Associations n-aires et réflexives

- elles sont prises en charge de bout en bout : édition MCD, validation,
  sauvegarde JSON, transformation MLD et génération SQL ;
- une association de degré trois ou plus devient une table indépendante ;
- ses FK forment la PK composée, sauf identifiant explicite d'association ;
- `FORCE_FK` est refusé pour une association n-aire ;
- dans une réflexive, les rôles produisent des noms de FK distincts
  (`id_employe_superviseur`, `id_employe_supervise`) ;
- les règles N:N, 1:N et 1:1 restent ensuite identiques aux associations
  binaires ordinaires.

Exemple réflexif :

```text
EMPLOYE (0,N, rôle superviseur)
    └── SUPERVISER
          └── EMPLOYE (0,1, rôle supervisé)

EMPLOYE(
    id_employe PK,
    id_employe_superviseur FK NULL → EMPLOYE.id_employe
)
```

Chaque branche répétée doit posséder un rôle non vide et distinct. MERISOR
propose automatiquement des rôles temporaires lors de la création graphique ;
ils restent modifiables dans le panneau de propriétés.

Exemple ternaire :

```text
FOURNISSEUR ─┐
PRODUIT ─────┼── FOURNIR ── quantite, prix_achat
ENTREPOT ────┘

FOURNIR(
    id_fournisseur PK/FK,
    id_produit PK/FK,
    id_entrepot PK/FK,
    quantite,
    prix_achat
)
```

Si l'association n-aire définit son propre attribut identifiant, celui-ci
devient sa PK et les clés migrées restent des FK ordinaires. Les cardinalités
originales sont conservées dans la provenance MCD → MLD, même si une table
d'association ne peut pas exprimer à elle seule toutes les contraintes MERISE.

### Héritages ISA

- `JOINED` conserve mère et filles ; la PK de chaque fille est également une FK
  vers la mère ;
- `PARENT_ONLY` conserve uniquement la mère et y aplatit les attributs propres
  des filles ;
- `CHILDREN_ONLY` supprime la table mère et copie ses attributs propres dans
  chaque table fille.

### Historisation et matérialisation

```text
1:N + AUTO                 → FK classique
1:N + AUTO + historisée    → table indépendante
N:N                        → table d’association
FORCE_TABLE                → table indépendante
FORCE_FK compatible        → transformation FK classique
N:N + FORCE_FK             → erreur
Historisée + FORCE_FK      → erreur
```

Une association matérialisée utilise ses attributs identifiants comme PK. À
défaut, une association non-N:N reçoit une PK technique stable
`id_<nom_association>`. Aucune date n’est ajoutée automatiquement et aucune
unicité du couple de FK n’est supposée.

</details>

## 🧱 Architecture

La logique métier ne dépend pas de Qt. L’interface représente et modifie les
modèles par l’intermédiaire du contrôleur.

```text
src/merisor/
├── domain/
│   ├── model.py                 objets MCD
│   ├── validation.py            validation métier
│   ├── quality.py               analyse locale et score explicable
│   ├── normalization.py         fermeture, clés candidates, 1NF/2NF/3NF
│   └── mld.py                   objets MLD indépendants
├── application/
│   ├── controller.py            orchestration document/scène
│   ├── commands.py              annuler/rétablir
│   ├── diagram_clipboard.py     copie structurée des sélections MCD
│   ├── mcd_layout.py            disposition automatique
│   ├── model_explorer.py        recherche et projections de navigation
│   ├── submodels.py             résolution des domaines et vues enregistrées
│   ├── mld_transformer.py       transformation MCD → MLD
│   ├── ddl_importer.py           reverse-engineering DDL → MLD → MCD
│   ├── sql_generator.py         validation et dialectes SQL
│   ├── ai_mcd_service.py        schéma/prompt/validation IA
│   ├── design_session.py        brouillon et révisions conversationnelles
│   ├── conversational_design_service.py patchs stricts OpenRouter
│   ├── ai_normalization_service.py suggestions facultatives de DF
│   ├── openrouter_client.py     appels HTTP OpenRouter
│   └── openrouter_settings.py   préférences et clé locale
├── persistence/
│   └── json_repository.py       JSON V2 et migration V1
├── ui/
│   ├── canvas.py, items.py      scène et objets graphiques MCD
│   ├── properties_panel.py      édition contextuelle
│   ├── mld_view.py              MLD graphique et textuel
│   ├── model_explorer_dialog.py exploration non destructive du MCD
│   ├── submodel_dialog.py       gestion des domaines et sous-modèles
│   ├── sql_dialog.py            aperçu et export SQL
│   ├── ai_mcd_dialog.py         génération/aperçu/import IA
│   ├── conversational_design_dialog.py conversation/aperçu/import
│   ├── quality_dialog.py        rapport de qualité détaillé
│   ├── normalization_dialog.py  saisie, rapport et aperçu non destructif
│   └── main_window.py           fenêtre principale
└── assets/
    └── merisor.png              icône de l’application
```

Le découplage principal est le suivant :

```text
MCDModel ──> McdToMldTransformer ──> MLDModel ──> SQLGenerator
   │                                      │             │
   └── JSON + validation                  └── vues       └── dialectes
```

Le générateur SQL ne consulte jamais le MCD. Les positions du canvas
n’influencent ni le MLD ni le SQL.

## 🗄️ Dialectes et types SQL

| Concept MLD | PostgreSQL | SQLite | MariaDB/MySQL |
|---|---|---|---|
| Entier | `INTEGER` | `INTEGER` | `INT` |
| Flottant | `DOUBLE PRECISION` | `REAL` | `DOUBLE` |
| Date/heure | `TIMESTAMP` | `TEXT` | `DATETIME` |
| PK technique | `GENERATED BY DEFAULT AS IDENTITY` | `INTEGER PRIMARY KEY AUTOINCREMENT` | `AUTO_INCREMENT` |
| Identifiants | `"nom"` | `"nom"` | `` `nom` `` |

Types logiques disponibles : `INTEGER`, `BIGINT`, `DECIMAL`, `FLOAT`,
`BOOLEAN`, `VARCHAR(n)`, `TEXT`, `DATE`, `TIME`, `DATETIME` et `TIMESTAMP`.

Dans le panneau **Propriétés**, sélectionnez un attribut puis son type. Les
champs de longueur apparaissent pour `VARCHAR(n)` et ceux de précision/échelle
pour `DECIMAL(p,s)`. Le type est enregistré dans le JSON, propagé au MLD puis
traduit par le dialecte SQL choisi. Une FK reprend exactement le type de la
colonne référencée.

Le mode **Automatique** conserve la compatibilité historique : `INTEGER` pour
un attribut identifiant et `VARCHAR(100)` pour un attribut ordinaire. Ainsi, les
anciens fichiers produisent le même MLD et le même SQL qu’avant cette évolution.

## 🔐 Confidentialité et sécurité

- la clé OpenRouter n’est jamais écrite dans un fichier MCD, le dépôt Git ou
  le SQL généré ;
- avec `keyring`, elle est stockée dans le trousseau du système ;
- sans `keyring`, QSettings est utilisé avec un avertissement : ce repli n’est
  pas chiffré ;
- la génération ponctuelle transmet la description ; l'assistant
  conversationnel transmet aussi le brouillon MCD courant, les derniers tours,
  les hypothèses et les réponses nécessaires pour poursuivre la conception ;
- ces données ne sont envoyées qu'après une action explicite de l'utilisateur,
  à OpenRouter et au fournisseur du modèle sélectionné ;
- le JSON reçu est validé avant de pouvoir remplacer le document courant ;
- le SQL est seulement affiché ou enregistré localement.

Ne placez jamais une clé API dans un fichier JSON, une capture d’écran, un
ticket GitHub ou un commit.

## 🧪 Développement et tests

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test,ai,quality]"
ruff format --check .
ruff check .
mypy
QT_QPA_PLATFORM=offscreen pytest
```

`ruff format .` applique automatiquement le formatage. La CI refuse une
contribution si le formatage, le lint, le typage strict ou les tests échouent.
La configuration commune de Ruff et mypy se trouve dans `pyproject.toml` afin
que les contrôles locaux et GitHub Actions restent identiques.

La suite couvre le domaine MCD, la validation, la persistance et migration JSON,
les commandes annulables, l’interface Qt, la disposition automatique, la
normalisation formelle, la génération IA ponctuelle et conversationnelle,
toutes les règles MCD → MLD, les trois dialectes SQL, les cycles de dépendances,
les exports et la chaîne MotoGP complète.

Pour vérifier que l’application démarre sans ouvrir de fenêtre visible :

```bash
QT_QPA_PLATFORM=offscreen timeout 5s python -m merisor
```

Le code suit une architecture modulaire et utilise des annotations de types.
Une contribution doit conserver la compatibilité JSON et ajouter des tests pour
toute nouvelle règle métier.

## 📦 Construire les paquets Linux

### Paquet Debian

```bash
./packaging/build_deb.sh
dpkg-deb --info dist/merisor_*.deb
```

Le paquet contient l’application Python, le lanceur, l’entrée de menu desktop
et l’icône.

### AppImage

Installez d’abord les dépendances de construction dans l’environnement Python,
puis lancez le script :

```bash
python -m pip install -e ".[ai]" pyinstaller
./packaging/build_appimage.sh
./dist/MERISOR-*-x86_64.AppImage
```

Le script prend en charge `x86_64` et `aarch64`. Il construit une application
autonome avec PyInstaller, prépare l’`AppDir`, puis utilise la version épinglée
d’`appimagetool`. La variable `APPIMAGETOOL` permet d’indiquer un binaire déjà
installé et d’effectuer une construction hors ligne.

Le workflow GitHub Actions exécute les tests, construit le `.deb` et
l’`.AppImage`, teste le démarrage de cette dernière puis publie les deux
artefacts lors de l’envoi d’un tag `v*`.

## ⚠️ Limites connues

- une même entité fille ne peut pas avoir plusieurs entités mères et les cycles
  ISA sont refusés ; une spécialisation comportant plusieurs entités filles est
  bien prise en charge ;
- pour éviter une transformation ambiguë, les stratégies ISA aplaties refusent
  encore une association directement portée par l'entité dont la table serait
  supprimée ; utilisez `JOINED` dans ce cas ;
- une association 1:1 porteuse d’attributs doit être matérialisée en table :
  utilisez `FORCE_TABLE`, ou `AUTO` si l'association est historisée. Les modes
  `AUTO` non historisé et `FORCE_FK` sont refusés pour éviter une perte
  d’information ;
- la génération IA dépend de la disponibilité et des quotas d’OpenRouter ;
- les sessions conversationnelles sont conservées en mémoire pendant
  l'ouverture de la fenêtre ; leur sauvegarde et reprise entre deux lancements
  restent une évolution future ;
- MERISOR ne gère ni connexion, ni migration automatique, ni introspection
  directe d'une base en fonctionnement ;
- le reverse-engineering importe un fichier DDL, mais ne se connecte pas à une
  base existante et n'analyse pas les vues, triggers, procédures ou extensions
  propriétaires ;
- le reverse-engineering PWA analyse les déclarations Dexie/IndexedDB et les
  types TypeScript statiques ; il ne lit ni les données présentes sur un
  téléphone, ni les schémas construits dynamiquement à l’exécution, et les
  relations proposées restent des inférences à confirmer ;
- les types SQL non portables ou inconnus sont adaptés à un type logique proche
  avec un avertissement explicite ; cette approximation doit être vérifiée ;
- les contrôles 2NF/3NF reflètent les dépendances déclarées : ils ne peuvent pas
  deviner une règle métier absente ;
- les décompositions 2NF nécessitant une identification relative, ainsi que les
  transformations ambiguës d'associations, sont proposées en aperçu mais ne
  sont pas appliquées automatiquement.

## 🤝 Contribuer et signaler un problème

Les contributions, propositions et rapports de bogues sont bienvenus.

1. Consultez les [issues](https://github.com/nouhailler/merisor/issues).
2. Créez une branche dédiée.
3. Ajoutez ou adaptez les tests.
4. Vérifiez `ruff format --check .`, `ruff check .`, `mypy` et
   `QT_QPA_PLATFORM=offscreen pytest`.
5. Ouvrez une pull request en expliquant le comportement attendu.

Pour un problème d’affichage ou de transformation, joignez si possible un petit
fichier JSON reproductible, la version de MERISOR et votre distribution Linux.
Retirez toute clé API ou donnée confidentielle avant publication.

## 🗺️ Documentation du projet

- [Journal des modifications](CHANGELOG.md)
- [Contexte et décisions techniques](CONTEXT.md)
- [Exemple MotoGP](motogp.json)
- [Licence MIT](LICENSE)
- [Releases et paquets Debian](https://github.com/nouhailler/merisor/releases)

## 📄 Licence

MERISOR est distribué sous la [licence MIT](LICENSE). Vous pouvez l’utiliser,
le modifier et le redistribuer dans les conditions de cette licence.

---

<p align="center">
  Conçu pour rendre MERISE accessible sans sacrifier la structure du modèle.
</p>
