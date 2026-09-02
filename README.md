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
  <a href="https://github.com/nouhailler/merisor/actions/workflows/quality.yml"><img alt="Qualité Python" src="https://github.com/nouhailler/merisor/actions/workflows/quality.yml/badge.svg"></a>
  <a href="https://pypi.org/project/merisor/"><img alt="PyPI" src="https://img.shields.io/pypi/v/merisor?logo=pypi&logoColor=white"></a>
  <a href="https://github.com/nouhailler/merisor/blob/main/LICENSE"><img alt="Licence MIT" src="https://img.shields.io/badge/Licence-MIT-blue.svg"></a>
</p>

MERISOR est un éditeur graphique MERISE pour Linux, destiné aux étudiants,
enseignants, analystes, développeurs et architectes de données. Il permet de
concevoir un MCD, contrôler sa cohérence, produire un MLD structuré et générer
du SQL PostgreSQL, SQLite ou MariaDB/MySQL.

Le modèle peut aussi être proposé ou analysé avec OpenRouter, mais **aucune
réponse IA ne modifie le document sans validation, aperçu et confirmation**.

> [!IMPORTANT]
> Le MCD reste la source de vérité. MERISOR génère des scripts SQL mais ne se
> connecte à aucune base et n'exécute jamais le SQL.

## 🗺️ Du besoin métier aux livrables

```mermaid
flowchart TB
    DESCRIPTION["📝 Description métier"]
    AI["🤖 Assistant IA<br/>facultatif"]
    PREVIEW["👁️ Aperçu et confirmation"]
    MCD["🧩 MCD<br/>SOURCE DE VÉRITÉ"]
    VALIDATION["✅ Validation MERISE"]
    IMPACT["🔎 Analyse d'impact"]
    DOCUMENTATION["📚 Documentation"]
    MLD["🗂️ MLD structuré<br/>tables · colonnes · PK · FK"]
    DOCS["📄 Markdown · HTML · PDF"]
    SQL["🛢️ Génération SQL<br/>aperçu et export uniquement"]
    POSTGRES[(PostgreSQL)]
    SQLITE[(SQLite)]
    MYSQL[(MariaDB / MySQL)]

    DESCRIPTION -->|Conception assistée| AI
    AI --> PREVIEW
    PREVIEW -->|Import confirmé| MCD
    DESCRIPTION -->|Modélisation manuelle| MCD
    MCD --> VALIDATION
    MCD --> IMPACT
    MCD --> DOCUMENTATION
    VALIDATION -->|MCD valide| MLD
    IMPACT -.->|Provenance MCD → MLD| MLD
    DOCUMENTATION --> DOCS
    MLD --> SQL
    SQL --> POSTGRES
    SQL --> SQLITE
    SQL --> MYSQL

    classDef truth fill:#fff4cc,stroke:#a56b00,stroke-width:3px,color:#302400;
    classDef conceptual fill:#e8f1fb,stroke:#315d8a,stroke-width:2px,color:#172b3a;
    classDef output fill:#e9f7ef,stroke:#287a50,stroke-width:2px,color:#173c2b;
    classDef optional fill:#f2eafa,stroke:#7651a8,stroke-width:2px,color:#312044;
    class MCD truth;
    class VALIDATION,IMPACT,MLD conceptual;
    class DOCUMENTATION,DOCS,SQL,POSTGRES,SQLITE,MYSQL output;
    class AI,PREVIEW optional;
```

## 📸 Aperçu

### Construire le MCD

![Fenêtre principale avec un MCD MotoGP](https://raw.githubusercontent.com/nouhailler/merisor/main/docs/images/mcd-editor.png)

### Décrire les attributs

![Édition d'un type DECIMAL](https://raw.githubusercontent.com/nouhailler/merisor/main/docs/images/attribute-types.png)

<table>
  <tr>
    <td width="50%"><strong>Examiner le MLD</strong></td>
    <td width="50%"><strong>Vérifier le SQL</strong></td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/nouhailler/merisor/main/docs/images/mld-view.png" alt="Vue graphique du MLD"></td>
    <td><img src="https://raw.githubusercontent.com/nouhailler/merisor/main/docs/images/sql-preview.png" alt="Aperçu SQL PostgreSQL"></td>
  </tr>
</table>

### Préparer un MCD avec l'IA

![Aperçu et validation avant import IA](https://raw.githubusercontent.com/nouhailler/merisor/main/docs/images/ai-preview.png)

## ✨ Fonctionnalités principales

- **MCD graphique** : entités, associations, attributs complets, identifiants
  composés, cardinalités, réflexives, n-aires et héritages ISA ;
- **canvas productif** : grille, guides, alignement, sélection multiple,
  copier/coller, domaines, minimap, recherche et disposition automatique ;
- **contrôles** : validation MERISE, qualité, normalisation 1NF/2NF/3NF,
  comparaison de versions et analyse d'impact ;
- **MLD explicable** : PK/FK composées, provenance, associations historisées et
  bouton **ⓘ Pourquoi ?** ;
- **SQL multi-dialecte** : PostgreSQL, SQLite, MariaDB/MySQL, aperçu et export ;
- **imports** : JSON V1/V2, DDL et schémas statiques PWA/IndexedDB, avec une
  [archive de démonstration prête à tester](examples/indexeddb-demo-pwa.zip) ;
- **exports** : PNG, SVG, PDF, Mermaid, Graphviz, documentation Markdown/HTML/PDF,
  données de test et requêtes SQL simples ;
- **IA facultative** : génération, conversation et réparation avec validation
  locale, normalisation prudente des réponses et confirmation humaine ;
- **historique** : opérations importantes annulables avec Annuler/Rétablir.

Le logo MERISOR est utilisé de manière cohérente dans la fenêtre principale,
le lanceur desktop, les paquets et cette page.

Le détail se trouve dans le [guide utilisateur](docs/user/GUIDE_UTILISATEUR.md).

## 🚀 Installation rapide

### AppImage

Téléchargez l'AppImage depuis la
[dernière release](https://github.com/nouhailler/merisor/releases/latest) :

```bash
chmod +x MERISOR-*.AppImage
./MERISOR-*.AppImage
```

### Debian / Ubuntu

```bash
sudo apt install ./merisor_*_amd64.deb
```

### PyPI avec pipx

```bash
pipx install merisor
merisor
```

Avec le trousseau sécurisé OpenRouter :

```bash
pipx install "merisor[ai]"
```

### Depuis les sources

```bash
git clone https://github.com/nouhailler/merisor.git
cd merisor
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test,ai]"
python -m merisor
```

Voir la [documentation d'installation développeur](docs/development/DEVELOPMENT.md).

## 🖱️ Premier modèle

1. Créez une entité et ses attributs.
2. Marquez au moins un attribut comme identifiant.
3. Créez une association et reliez-la aux entités.
4. Définissez `(0,1)`, `(0,N)`, `(1,1)` ou `(1,N)`.
5. Validez le MCD.
6. Générez le MLD et utilisez **ⓘ Pourquoi ?**.
7. Générez puis exportez le SQL du dialecte choisi.

Le tutoriel détaillé est disponible dans
[Prise en main](docs/user/PRISE_EN_MAIN.md). Vous pouvez également ouvrir
[l'exemple MotoGP](examples/motogp.json) ou tester le reverse-engineering avec
[la PWA IndexedDB de démonstration](examples/indexeddb-demo-pwa/README.md).

## 🧱 Architecture simplifiée

```text
MCDModel ──> McdToMldTransformer ──> MLDModel ──> SQLGenerator
   │                                      │             │
   └── JSON + validation                  └── vues       └── dialectes
```

Le domaine métier ne dépend pas de Qt. Les mutations passent par le contrôleur
et les commandes annulables. Consultez
[Architecture](docs/technical/ARCHITECTURE.md) et les
[ADR](docs/decisions/CONTEXT.md).

## 📚 Documentation

Dans l'application, ouvrez **Documentation → Centre de documentation…** ou
appuyez sur `F1`. Le manuel Markdown est inclus dans les paquets et reste
également consultable sur GitHub.

- [Portail documentaire](docs/INDEX.md)
- [Guide utilisateur](docs/user/GUIDE_UTILISATEUR.md)
- [Concepts MERISE](docs/concepts/MERISE.md)
- [Règles MCD → MLD](docs/concepts/REGLES_MCD_MLD.md)
- [Format JSON V2](docs/technical/JSON_FORMAT.md)
- [Architecture](docs/technical/ARCHITECTURE.md)
- [Sécurité](docs/technical/SECURITY.md)
- [Contribuer](docs/development/CONTRIBUTING.md)
- [Journal des changements](CHANGELOG.md)

## ⚠️ Limites principales

- pas de connexion, migration ou exécution automatique sur une base active ;
- le reverse engineering DDL ne retrouve pas toutes les intentions MERISE ;
- héritage multiple et cycles ISA refusés ;
- les stratégies ISA aplaties refusent une association portée par une table
  supprimée ; utilisez `JOINED` ;
- une association 1:1 porteuse d'attributs doit être matérialisée ;
- les contrôles de normalisation dépendent des règles métier déclarées ;
- les fonctions IA dépendent des quotas OpenRouter et peuvent se tromper.

La liste expliquée est maintenue dans la [FAQ](docs/user/FAQ.md) et les guides
conceptuels.

## 🤝 Contribuer

Les contributions sont bienvenues. Avant une pull request :

```bash
ruff format --check .
ruff check .
mypy
QT_QPA_PLATFORM=offscreen pytest
```

Lisez [CONTRIBUTING.md](docs/development/CONTRIBUTING.md) et ouvrez une
[issue](https://github.com/nouhailler/merisor/issues) pour discuter d'une
évolution importante.

## 📄 Licence

MERISOR est distribué sous [licence MIT](LICENSE).

---

<p align="center">
  Conçu pour rendre MERISE accessible sans sacrifier la structure du modèle.
</p>
