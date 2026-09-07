# Documentation du projet MERISOR

Cette page est le point d’entrée transversal vers la documentation fonctionnelle,
conceptuelle et technique de MERISOR. Elle complète le [portail détaillé](INDEX.md)
et s’adresse aussi bien aux utilisateurs qu’aux contributeurs.

## Découvrir et utiliser MERISOR

- [Prise en main en dix minutes](user/PRISE_EN_MAIN.md)
- [Guide utilisateur complet](user/GUIDE_UTILISATEUR.md)
- [Créer et éditer un MCD](user/MCD.md)
- [Comprendre le MLD](user/MLD.md)
- [Générer et exporter du SQL](user/SQL.md)
- [Utiliser les assistants IA](user/IA.md)
- [Questions fréquentes](user/FAQ.md)

## Comprendre MERISE

- [Principes de la méthode](concepts/MERISE.md)
- [Cardinalités](concepts/CARDINALITES.md)
- [Règles MCD → MLD](concepts/REGLES_MCD_MLD.md)
- [Historisation et matérialisation](concepts/HISTORISATION.md)
- [Normalisation 1NF, 2NF et 3NF](concepts/NORMALISATION.md)

## Architecture et données

```text
MCDModel
   │ validation et transformations
   ▼
MLDModel
   │ génération par dialecte
   ▼
SQL PostgreSQL / SQLite / MariaDB-MySQL
```

- [Architecture logicielle](technical/ARCHITECTURE.md)
- [Modèle de données](technical/DATA_MODEL.md)
- [Format JSON V2 et rétrocompatibilité](technical/JSON_FORMAT.md)
- [Persistance](technical/PERSISTENCE.md)
- [Dialectes SQL](technical/SQL_DIALECTS.md)
- [Architecture IA](technical/AI_ARCHITECTURE.md)
- [Sécurité](technical/SECURITY.md)

Le MCD est la source de vérité. Le MLD, le SQL et la documentation produite
sont des résultats dérivés. MERISOR ne se connecte à aucune base et n’exécute
pas les scripts générés.

## Interface UI/UX 2.0

- [Rapport d’implémentation et captures](UI_UX_2.0_IMPLEMENTATION_REPORT.md)
- [Design system](DESIGN_SYSTEM.md)
- [Principes UX](UX_GUIDELINES.md)
- [Architecture de présentation](UI_ARCHITECTURE.md)
- [Cahier des charges de référence](UI_UX_2.0.md)

## Développer et contribuer

- [Installation de l’environnement](development/DEVELOPMENT.md)
- [Tests](development/TESTS.md)
- [Guide de contribution](development/CONTRIBUTING.md)
- [Packaging Linux](development/PACKAGING.md)
- [Publication d’une version](development/RELEASE.md)
- [Contexte et décisions](decisions/CONTEXT.md)

## Accès dans l’application

Dans MERISOR, utilisez **Documentation → Documentation du projet**. `F1` ouvre
le portail général. Le manuel est embarqué dans les distributions PyPI, Debian
et AppImage et reste donc disponible hors ligne.
