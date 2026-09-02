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
