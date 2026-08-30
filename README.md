# MERISOR — éditeur MCD, générateur MLD et SQL

MERISOR 0.4 est une application de bureau Python/PySide6 pour construire un
modèle conceptuel de données MERISE, le valider et générer automatiquement son
modèle logique de données puis un script SQL exportable.

Le MCD et le MLD sont de véritables modèles métier distincts. Le MCD reste la
source de vérité ; le MLD est un résultat déterministe et régénérable. Le SQL
est toujours produit depuis ce MLD, jamais directement depuis le MCD. Aucun
script n'est exécuté et aucune connexion à une base n'est ouverte.

## Prérequis et installation

- Debian ou une distribution Linux équivalente avec environnement graphique ;
- Python 3.10 ou ultérieur ;
- `python3-venv` si le module `venv` n'est pas déjà installé ;
- les bibliothèques système usuelles de Qt/X11 ou Wayland.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
```

Le fichier `requirements.txt` peut aussi être utilisé directement.

## Paramètres OpenRouter (phase 1 IA)

Le menu **Paramètres → Paramètres OpenRouter…** permet d'enregistrer une clé
API, de la tester et de récupérer la liste des modèles texte gratuits. Le modèle
choisi et l'activation de l'IA sont conservés dans les paramètres locaux ; ils
ne sont jamais écrits dans les fichiers de projet JSON. Lorsque le paquet
optionnel `keyring` est installé (`python -m pip install -e ".[ai]"`), la clé
est conservée dans le trousseau du système ; sinon MERISOR utilise un repli
local QSettings explicitement signalé comme non chiffré. La génération et
l'import du JSON MCD se lancent depuis **Modèle → Générer un MCD avec l'IA…**.

### Génération assistée d'un MCD

La fenêtre IA affiche le modèle OpenRouter sélectionné, une zone de description
et un rappel des éventuels quotas des modèles gratuits. MERISOR impose au modèle
le format JSON version 2 avec identifiants internes, attributs identifiants,
cardinalités, historisation et stratégie de matérialisation.

La réponse ne remplace jamais immédiatement le document courant. Elle est
d'abord chargée par `JsonDiagramRepository`, puis analysée par le validateur
MERISE. L'aperçu présente les entités, associations, relations, erreurs et
avertissements. Le JSON reste éditable et peut être revalidé ; le bouton
**Importer dans l'éditeur** demeure désactivé tant qu'une erreur bloque le MCD.
Après confirmation, les modifications courantes peuvent être sauvegardées avant
le remplacement et le MCD importé est marqué comme non enregistré.

## Lancement

```bash
source .venv/bin/activate
python -m merisor
```

Après une installation éditable, la commande `merisor` est également
disponible.

### Installation Debian

Les releases GitHub fournissent un paquet `merisor_<version>_amd64.deb`.
Installez-le avec :

```bash
sudo apt install ./merisor_0.4.0_amd64.deb
```

Le paquet installe le lanceur `/usr/bin/merisor` et une entrée dans le menu
des applications. Il dépend des modules Debian PySide6 (`python3-pyside6.qtcore`,
`python3-pyside6.qtgui` et `python3-pyside6.qtwidgets`). Pour reconstruire le
paquet depuis les sources :

```bash
./packaging/build_deb.sh
```

## Édition du MCD

La barre d'outils permet de créer, sélectionner, déplacer et supprimer des
entités, associations et relations.

Lorsqu'une entité est sélectionnée, le panneau **Propriétés** permet de :

- modifier son nom ;
- ajouter, renommer ou supprimer ses attributs ;
- cocher plusieurs attributs pour créer un identifiant composé.

Les identifiants sont marqués par `#` dans le diagramme. Une association peut
porter ses propres attributs. Une relation expose les cardinalités `(0,1)`,
`(0,N)`, `(1,1)` et `(1,N)`.
Les attributs d'une association peuvent également être cochés comme
identifiants lorsqu'une matérialisation doit utiliser une PK conceptuelle.

Lorsqu'une association est sélectionnée, la section **Transformation MLD**
expose aussi deux décisions conceptuelles :

- **Historisée** (`is_historized`) indique explicitement que plusieurs
  occurrences indépendantes doivent pouvoir être conservées dans le temps ;
- **Stratégie de matérialisation** (`materialization_strategy`) accepte
  `AUTO`, `FORCE_TABLE` ou `FORCE_FK`.

L'historisation n'est jamais déduite du nom des attributs : la présence de
`date`, `date_debut` ou `annee` ne modifie pas automatiquement l'association.
Par exemple, pour `PILOTE ── ENGAGER ── EQUIPE`, l'utilisateur peut choisir
**Historisée : Oui** et **Matérialisation : Automatique**.

Le transformateur applique la priorité suivante : `FORCE_TABLE`, puis
l'historisation en mode `AUTO`, puis les règles classiques. `FORCE_FK` demande
explicitement ces règles classiques et n'est accepté que lorsque les
cardinalités le permettent. La combinaison « historisée + `FORCE_FK` » est une
erreur plutôt qu'un choix implicite.

La pile **Annuler/Rétablir** couvre les créations, suppressions, déplacements,
renommages, attributs, identifiants et cardinalités.

## Validation

**Modèle → Valider le MCD** (`Ctrl+Shift+V`) vérifie notamment :

- les noms et identifiants des entités ;
- l'unicité des attributs d'un même propriétaire ;
- le nom et le degré minimal des associations ;
- l'incompatibilité de `FORCE_FK` avec une association binaire N:N ;
- la contradiction entre historisation et `FORCE_FK` ;
- les extrémités, cardinalités et doublons de relations ;
- les doublons de noms entre objets d'un même type.

Les erreurs sont bloquantes pour la génération du MLD. Les avertissements sont
signalés mais n'empêchent pas la transformation. Un MCD incomplet peut toujours
être sauvegardé après confirmation.

## Génération du MLD

Utiliser **Modèle → Générer le MLD** (`Ctrl+Shift+M`) ou le bouton de la barre
d'outils. L'application :

1. valide le MCD ;
2. refuse la génération si des erreurs sont présentes ;
3. applique les règles MCD→MLD ;
4. construit un `MLDModel` autonome ;
5. affiche les tables dans les vues graphique et textuelle.

La vue MLD permet de consulter les colonnes, PK, FK, nullabilités et contraintes
UNIQUE. Le bouton **Copier le texte** place la représentation dans le
presse-papiers ; **Exporter…** écrit un fichier texte qui n'est pas du SQL.
Dans la vue graphique, les boutons `+`, `−` et **Adapter** contrôlent le zoom ;
`Ctrl` + molette permet également d'agrandir ou de réduire le diagramme.

### État à jour ou obsolète

Une empreinte logique relie le MLD à l'état du MCD qui l'a produit :

- `✓ MLD à jour` : l'empreinte correspond ;
- `⚠ MLD obsolète` : noms, attributs, identifiants, associations,
  propriétés de matérialisation ou cardinalités ont changé ;
- `MLD non généré` : aucun résultat n'est disponible.

Un déplacement graphique ne change pas l'empreinte et ne rend donc pas le MLD
obsolète. Une annulation ramenant exactement le MCD à son état généré remet le
MLD à jour.

## V0.4 — Génération SQL

Le bouton **Générer SQL** est disponible après la génération d'un MLD valide et
à jour. Il ouvre un aperçu permettant de choisir :

- PostgreSQL ;
- SQLite ;
- MariaDB / MySQL.

L'utilisateur peut examiner le script, changer de cible, le copier dans le
presse-papiers ou l'enregistrer dans un fichier `.sql`. Si le MCD change, le
MLD devient obsolète et le bouton SQL est désactivé jusqu'à sa régénération.

Le workflow reste strictement :

```text
MCD → McdToMldTransformer → MLDModel → SQLGenerator → script SQL
```

Le générateur SQL reçoit uniquement un `MLDModel`. Il ne relit ni les entités,
ni les associations, ni les cardinalités du MCD.

### Différences entre dialectes

- PostgreSQL utilise `INTEGER`, `DOUBLE PRECISION`, `TIMESTAMP` et
  `GENERATED BY DEFAULT AS IDENTITY` ;
- SQLite utilise ses affinités `INTEGER`, `REAL`, `NUMERIC` et `TEXT`, active
  les FK avec `PRAGMA foreign_keys = ON` et rend une PK technique sous la forme
  `INTEGER PRIMARY KEY AUTOINCREMENT` ;
- MariaDB / MySQL utilise notamment `INT`, `DOUBLE`, `DATETIME`, les quotes
  inverses et `AUTO_INCREMENT`.

Les identifiants sont systématiquement cités afin de préserver exactement les
noms du MLD et de protéger les mots réservés comme `USER`, `ORDER` ou `GROUP`.
Un avertissement est affiché lorsqu'un tel mot est rencontré.

### Types logiques initiaux

Le MLD expose les types indépendants du SGBD suivants :

```text
INTEGER, BIGINT, DECIMAL, FLOAT, BOOLEAN, VARCHAR(n), TEXT,
DATE, TIME, DATETIME, TIMESTAMP
```

Comme la V0.2 ne stocke pas encore le type des attributs MCD, la politique de
compatibilité initiale est : identifiant conceptuel → `INTEGER`, attribut
ordinaire → `VARCHAR(100)`, FK → copie exacte du type référencé. Aucun type de
date n'est déduit du nom d'un attribut. Une PK technique générée par la V0.3 est
un `INTEGER` explicitement auto-incrémenté dans le MLD.

### Contraintes et dépendances

Le générateur traduit directement depuis le MLD :

- PK simples et composées ;
- FK simples et composées ;
- `NULL` / `NOT NULL` ;
- contraintes UNIQUE et CHECK ;
- index explicites uniquement ;
- actions `ON DELETE` et `ON UPDATE` lorsqu'elles sont définies.

Il n'invente aucun index de FK, aucune action CASCADE et aucune contrainte
UNIQUE. Les tables sont triées par dépendances. En cas de cycle, PostgreSQL et
MariaDB/MySQL reçoivent les FK cycliques par `ALTER TABLE` après création des
tables. SQLite conserve ces FK dans les `CREATE TABLE`, car son `ALTER TABLE`
ne permet pas d'ajouter ensuite une contrainte.

### Validation avant génération

La génération est bloquée notamment pour une table sans PK, une FK orpheline,
une colonne référencée absente, des types de FK incompatibles, un type inconnu
ou un auto-incrément non entier. Les mots réservés sont des avertissements et
n'empêchent pas la génération, puisque les identifiants sont échappés.

## Modèle interne MLD

```text
MLDModel
└── MLDTable[]
    ├── source_element_id
    ├── is_historized
    ├── MLDColumn[]
    │   ├── data_type
    │   ├── nullable
    │   └── auto_increment
    ├── primary_key: column_ids[]
    ├── MLDForeignKey[]
    │   ├── column_ids[]
    │   ├── referenced_table_id
    │   ├── referenced_column_ids[]
    │   ├── source_relation_id
    │   └── source_cardinality
    ├── MLDUniqueConstraint[]
    ├── MLDCheckConstraint[]
    └── MLDIndex[]
```

Les contraintes utilisent des identifiants de colonnes plutôt que de simples
noms. Une FK composée est ainsi représentée par une seule contrainte logique,
avec des listes de colonnes locales et référencées de même longueur.

Les tables d'association conservent l'identifiant de leur association MCD.
Les FK conservent aussi leur relation et cardinalité sources ; les colonnes
natives ou migrées référencent déjà leurs attributs et éléments MCD d'origine.

`MLDColumn.nullable` vaut `True` ou `False` lorsqu'une règle MERISE permet de le
déterminer. Il reste `None` pour un attribut ordinaire du MCD, car la V0.2 ne
stocke pas sa nullabilité et la V0.3 n'invente pas cette information.

## Règles MCD → MLD implémentées

### Entités

- chaque entité produit une table portant le même nom ;
- chaque attribut produit une colonne portant le même nom ;
- les attributs identifiants forment la PK simple ou composée.

### Associations N:N

- une table portant le nom de l'association est créée ;
- les PK des deux entités deviennent deux FK, simples ou composées ;
- toutes les colonnes de ces FK forment la PK composée de l'association ;
- les attributs de l'association restent dans cette table.

`FORCE_TABLE` et l'historisation ne changent pas inutilement cette structure.
Si l'association porte explicitement un ou plusieurs attributs identifiants,
ceux-ci forment toutefois sa PK à la place du couple de FK.

### Associations 1:N

Les exemples normatifs du cahier des charges placent la FK dans la table de
l'entité dont le maximum vaut `1`, en référence à l'entité dont le maximum vaut
`N`. C'est la règle appliquée.

- le minimum du côté `N` vaut `0` : la FK est nullable ;
- le minimum du côté `N` vaut `1` : la FK est NOT NULL ;
- les attributs de l'association migrent dans la même table que la FK.

Cette règle correspond à `AUTO` non historisé et à `FORCE_FK`. Une association
1:N historisée en `AUTO`, ou configurée avec `FORCE_TABLE`, devient au contraire
une table autonome.

### Associations matérialisées et historisées

Pour une association non-N:N matérialisée :

- ses attributs identifiants explicites forment sa PK ;
- à défaut, une PK technique stable `id_<nom_association_en_minuscules>` est
  créée, par exemple `id_engager` ;
- les identifiants des deux entités deviennent des FK dans cette table ;
- un minimum `0` produit une FK nullable et un minimum `1` une FK NOT NULL ;
- tous les attributs de l'association restent dans cette table ;
- aucune contrainte UNIQUE n'est ajoutée sur le couple de FK.

Ainsi plusieurs occurrences historisées peuvent relier le même couple
d'entités. Aucune colonne de date n'est inventée : `date_debut` ou `date_fin`
doivent être définies explicitement dans le MCD.

La vue graphique et la vue textuelle signalent ces tables avec la mention
**Association historisée**.

Résumé des décisions :

```text
1:N + AUTO                 → FK classique
1:N + AUTO + historisée    → table indépendante
N:N                        → table d'association
FORCE_TABLE                → table indépendante, sauf structure N:N conservée
FORCE_FK compatible        → transformation FK classique
N:N + FORCE_FK             → erreur
Historisée + FORCE_FK      → erreur
```

### Associations 1:1

- `(1,1)` face à `(0,1)` : le côté `(1,1)` porte la FK NOT NULL UNIQUE ;
- deux côtés de même minimum : la table porteuse est choisie par
  `(nom insensible à la casse, identifiant interne)` ;
- `(1,1)/(1,1)` produit une FK NOT NULL UNIQUE ;
- `(0,1)/(0,1)` produit une FK NULL UNIQUE ;
- la contrainte UNIQUE est un objet explicite, y compris pour une FK composée.

### Ordre et nommage

Les tables et associations sont traitées par `(nom insensible à la casse,
identifiant interne)`. Les positions du canvas n'interviennent jamais.

Les noms du MCD sont conservés sans normalisation SQL. Si deux migrations
créent une collision de colonnes, un suffixe stable provenant de l'entité ou de
l'association source est ajouté. Cette politique est isolée dans
`MLDNamePolicy` afin qu'une future version puisse gérer les règles d'un SGBD.

## Exemple MotoGP

```text
PILOTE (0,N) ── PARTICIPER ── (1,N) COURSE

PILOTE                       COURSE
# id_pilote                  # id_course
nom                          date

PARTICIPER
position
points
temps
```

produit logiquement :

```text
PILOTE
------
PK  id_pilote
    nom

COURSE
------
PK  id_course
    date

PARTICIPER
----------
PK/FK  id_course
PK/FK  id_pilote
       position
       points
       temps
FK (id_course) → COURSE(id_course)
FK (id_pilote) → PILOTE(id_pilote)
```

L'ordre des FK est alphabétique par entité source, donc indépendant de l'ordre
de création et de la disposition graphique.

### Engagement historisé

```text
PILOTE (0,N) ── ENGAGER ── (1,1) EQUIPE

ENGAGER
date_debut
date_fin
Historisée : Oui
Matérialisation : Automatique
```

produit une table `ENGAGER` contenant `id_engager` comme PK technique,
`id_pilote` et `id_equipe` comme FK, puis `date_debut` et `date_fin`. Le couple
de FK n'est ni PK ni UNIQUE, ce qui autorise plusieurs périodes pour le même
pilote et la même équipe.

Après génération du MLD, PostgreSQL produit notamment :

```sql
CREATE TABLE "ENGAGER" (
    "id_engager" INTEGER GENERATED BY DEFAULT AS IDENTITY NOT NULL,
    "id_equipe" INTEGER NOT NULL,
    "id_pilote" INTEGER,
    "date_debut" VARCHAR(100),
    "date_fin" VARCHAR(100),
    PRIMARY KEY ("id_engager"),
    CONSTRAINT "fk_ENGAGER_id_equipe"
        FOREIGN KEY ("id_equipe") REFERENCES "EQUIPE" ("id_equipe"),
    CONSTRAINT "fk_ENGAGER_id_pilote"
        FOREIGN KEY ("id_pilote") REFERENCES "PILOTE" ("id_pilote")
);
```

Il n'existe volontairement aucune contrainte UNIQUE sur
`(id_pilote, id_equipe)` : plusieurs engagements historiques restent possibles.

## Architecture du projet

```text
src/merisor/
├── domain/
│   ├── model.py              modèle MCD
│   ├── validation.py         validation MCD
│   └── mld.py                modèle MLD autonome
├── application/
│   ├── controller.py         état du document et obsolescence du MLD
│   ├── commands.py           opérations annulables
│   ├── mld_transformer.py    règles MCD → MLD et politique de nommage
│   ├── mld_text.py           rendu textuel indépendant de Qt
│   └── sql_generator.py      validation, dialectes et génération MLD → SQL
├── persistence/
│   └── json_repository.py    JSON MCD V2 et migration V1
├── ui/
│   ├── canvas.py             canvas MCD
│   ├── items.py              objets graphiques MCD
│   ├── properties_panel.py   édition contextuelle
│   ├── validation_dialog.py  rapport de validation
│   ├── mld_view.py           vues MLD graphique et textuelle
│   ├── sql_dialog.py         choix cible, aperçu, copie et export SQL
│   └── main_window.py        fenêtre et actions
└── __main__.py
```

Le flux de dépendances reste explicite :

```text
MCD → McdToMldTransformer → MLDModel → vues MLD
                                      ↓
                                  SQLGenerator
                              ┌───────┼────────┐
                              ↓       ↓        ↓
                         PostgreSQL SQLite  MySQL/MariaDB
```

Le transformateur et le rendu textuel n'importent jamais Qt.

## Persistance et compatibilité

Le format JSON reste en version 2. Les fichiers V0.1 et V0.2 restent lisibles.
Le MLD n'est pas sauvegardé : il est dérivé et recalculé après chargement, ce
qui évite qu'un résultat généré devienne une seconde source de vérité.

Chaque association sauvegardée contient désormais les champs suivants :

```json
{
  "name": "ENGAGER",
  "is_historized": true,
  "materialization_strategy": "FORCE_TABLE"
}
```

Lorsqu'ils sont absents d'un ancien fichier, ils prennent en mémoire les
valeurs `false` et `AUTO`. Le fichier d'origine n'est pas réécrit au chargement ;
les champs deviennent explicites uniquement lors d'une sauvegarde ultérieure.

Une relation migrée depuis la V0.1 conserve une cardinalité inconnue `?,?` et
doit être complétée avant génération du MLD.

## Limitations V0.4

- les associations ternaires ou de degré supérieur sont détectées et refusées ;
- les associations réflexives ne sont pas supportées par le modèle V0.2 ;
- une association 1:1 porteuse d'attributs reste refusée en mode classique ;
  `FORCE_TABLE` permet de la matérialiser sans perte ;
- les expressions CHECK et les valeurs DEFAULT sont conservées telles
  qu'elles figurent dans le MLD, sans langage d'expression abstrait avancé ;
- aucune connexion, exécution SQL, migration, introspection de base ou ORM
  n'est réalisé.

## Tests

```bash
source .venv/bin/activate
QT_QPA_PLATFORM=offscreen pytest
```

La suite couvre toutes les variantes demandées de N:N, 1:N et 1:1, les PK et
FK composées, les contraintes UNIQUE, les attributs d'association, le cas
MotoGP, le déterminisme, l'absence de mutation du MCD, l'obsolescence, la
régénération, la copie/export, l'historisation, les stratégies de
matérialisation, les PK techniques, la répétition des couples de FK et les
non-régressions V0.1/V0.2/V0.3. Elle couvre également les trois dialectes SQL,
les types, contraintes, index, actions référentielles, dépendances, cycles,
mots réservés, erreurs MLD, aperçu/export et la chaîne MCD → MLD → SQL.
