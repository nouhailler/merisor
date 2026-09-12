# Tests

[← Portail](../INDEX.md) · [Développement](DEVELOPMENT.md)

## Lancer la suite

```bash
QT_QPA_PLATFORM=offscreen pytest
```

Pour une zone précise :

```bash
pytest tests/test_mld_transformer.py
pytest -k historized
```

## Catégories

- **domaine** : objets MCD/MLD, invariants, cardinalités, validation ;
- **persistance** : V1/V2, migrations, positions, propriétés ;
- **application** : transformation, SQL, impact, normalisation, imports ;
- **commandes** : annuler/rétablir et état obsolète ;
- **UI** : widgets et interactions avec `QT_QPA_PLATFORM=offscreen` ;
- **intégration** : chaînes MCD → MLD → SQL et MotoGP ;
- **distribution** : icônes, README, workflows et scripts de packaging ;
- **IA** : parsing strict et services simulés, sans appel réseau réel.

## Exécution réelle du SQL généré

Le marqueur `sql_runtime` couvre la chaîne **MCD → MLD → SQL → moteur réel**.
SQLite s'exécute toujours en mémoire :

```bash
pytest -q -m sql_runtime
```

Sans configuration supplémentaire, les essais PostgreSQL et MariaDB sont
ignorés localement. Le workflow GitHub Actions `sql-runtime.yml` démarre des
services éphémères PostgreSQL 16 et MariaDB 11, installe leurs clients, puis :

1. exécute intégralement chaque schéma généré ;
2. vérifie la présence des tables et des deux FK MotoGP ;
3. insère des données valides ;
4. confirme qu'une référence inexistante est réellement rejetée.

Pour reproduire ces tests avec des moteurs locaux, renseignez :

```bash
export MERISOR_POSTGRES_DSN='postgresql://merisor:merisor@127.0.0.1:5432/merisor'
export MERISOR_MARIADB_HOST='127.0.0.1'
export MERISOR_MARIADB_PORT='3306'
export MERISOR_MARIADB_DATABASE='merisor'
export MERISOR_MARIADB_USER='merisor'
export MERISOR_MARIADB_PASSWORD='merisor'
pytest -q -m sql_runtime
```

Utilisez exclusivement des bases temporaires et vides : ces tests créent les
tables `PILOTE`, `EQUIPE` et `ENGAGER`. La variable
`MERISOR_REQUIRE_EXTERNAL_SQL=1`, utilisée en CI, transforme toute absence de
client ou de configuration en échec au lieu d'un test ignoré.

## Écrire un test métier

Préférez un test sans Qt pour toute règle MERISE. Construisez un petit
`MCDModel`, exécutez le service puis vérifiez structure, provenance et absence
de mutation du source.

## Écrire un test UI

Utilisez le fixture `qapp`, évitez d'afficher une fenêtre sur le bureau et
testez les signaux/états visibles. Les dialogues réseau reçoivent des réponses
simulées.

## Non-régression obligatoire

Une nouvelle règle MCD → MLD doit tester : cas nominal, composés, nullabilité,
provenance, déterminisme et SQL des trois dialectes si concerné. Une évolution
JSON doit tester anciens fichiers et round-trip.

## Aucun secret

Les tests OpenRouter utilisent des clés factices (`sk-or-v1-test`) et ne doivent
jamais appeler Internet.
