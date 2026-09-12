# Documentation MERISOR

Bienvenue dans le manuel de MERISOR. Le **MCD est la source de vérité** : le
MLD, le SQL et la documentation technique sont toujours des résultats dérivés.

Pour une vue synthétique, ouvrez la
[documentation transversale du projet](PROJECT_DOCUMENTATION.md).

```text
Description métier → MCD → validation → MLD → SQL
                         └──────────────→ documentation
```

## 👤 Utilisateur

- [Prise en main en dix minutes](user/PRISE_EN_MAIN.md)
- [Guide utilisateur complet](user/GUIDE_UTILISATEUR.md)
- [Créer et éditer un MCD](user/MCD.md)
- [Documenter le modèle avec le dictionnaire de données](user/DICTIONNAIRE_DONNEES.md)
- [Générer et lire un MLD](user/MLD.md)
- [Analyser la qualité du modèle](user/QUALITE.md)
- [Tester le MCD avec des scénarios métier](user/SCENARIOS_METIER.md)
- [Apprendre avec le mode étudiant](user/MODE_ETUDIANT.md)
- [Suivre la traçabilité MCD → MLD → SQL](user/TRACABILITE.md)
- [Simuler un changement avec « Et si… ? »](user/ET_SI.md)
- [Générer et exporter du SQL](user/SQL.md)
- [Utiliser les assistants IA](user/IA.md)
- [Questions fréquentes](user/FAQ.md)

## 📐 Concepts MERISE

- [Comprendre la méthode MERISE](concepts/MERISE.md)
- [Règles exactes MCD → MLD](concepts/REGLES_MCD_MLD.md)
- [Cardinalités](concepts/CARDINALITES.md)
- [Historisation et matérialisation](concepts/HISTORISATION.md)
- [Normalisation, 1NF, 2NF et 3NF](concepts/NORMALISATION.md)

## 🔧 Documentation technique

- [Architecture logicielle](technical/ARCHITECTURE.md)
- [Modèle de données interne](technical/DATA_MODEL.md)
- [Format JSON V2](technical/JSON_FORMAT.md)
- [Dialectes SQL](technical/SQL_DIALECTS.md)
- [Architecture des fonctions IA](technical/AI_ARCHITECTURE.md)
- [Persistance et compatibilité](technical/PERSISTENCE.md)
- [Sécurité et confidentialité](technical/SECURITY.md)

## 🎨 Interface et expérience utilisateur

- [Cahier des charges UI/UX 2.0](UI_UX_2.0.md)
- [Rapport d’implémentation](UI_UX_2.0_IMPLEMENTATION_REPORT.md)
- [Audit initial](UI_AUDIT.md)
- [Design system](DESIGN_SYSTEM.md)
- [Architecture de présentation](UI_ARCHITECTURE.md)
- [Principes UX](UX_GUIDELINES.md)
- [Canvas MCD](CANVAS_UX.md)
- [Propriétés](PROPERTIES_PANEL_UX.md)
- [Validation](VALIDATION_CENTER_UX.md)
- [MLD](MLD_VIEW_UX.md)
- [SQL](SQL_WORKSPACE_UX.md)
- [Assistant IA](AI_HUB_UX.md)
- [Documentation intégrée](DOCUMENTATION_CENTER_UX.md)
- [Recherche et commandes](SEARCH_AND_COMMANDS_UX.md)

## 🧪 Développement

- [Installer un environnement développeur](development/DEVELOPMENT.md)
- [Lancer et écrire les tests](development/TESTS.md)
- [Contribuer](development/CONTRIBUTING.md)
- [Préparer une release](development/RELEASE.md)
- [Construire les paquets](development/PACKAGING.md)
- [Guide de reprise pour Codex](development/CODEX_GUIDE.md)

## 🧠 Projet et décisions

- [Contexte et principes permanents](decisions/CONTEXT.md)
- [ADR-001 — Le MCD est la source de vérité](decisions/ADR/ADR-001-MCD-SOURCE-VERITE.md)
- [ADR-002 — Séparation domaine et interface](decisions/ADR/ADR-002-SEPARATION-DOMAINE-UI.md)
- [ADR-003 — Format JSON V2](decisions/ADR/ADR-003-JSON-V2.md)
- [ADR-004 — Aucune connexion automatique](decisions/ADR/ADR-004-NO-DATABASE-CONNECTION.md)
- [ADR-005 — OpenRouter et confirmation humaine](decisions/ADR/ADR-005-OPENROUTER.md)
- [ADR-006 — Dialectes SQL](decisions/ADR/ADR-006-SQL-DIALECTS.md)

## Ressources

- [Exemple MotoGP](https://github.com/nouhailler/merisor/blob/main/examples/motogp.json)
- [PWA IndexedDB de démonstration](https://github.com/nouhailler/merisor/tree/main/examples/indexeddb-demo-pwa)
- [Archive PWA directement importable](https://github.com/nouhailler/merisor/raw/main/examples/indexeddb-demo-pwa.zip)
- [Journal des changements](https://github.com/nouhailler/merisor/blob/main/CHANGELOG.md)
- [Licence MIT](https://github.com/nouhailler/merisor/blob/main/LICENSE)
- [Dépôt GitHub](https://github.com/nouhailler/merisor)

Dans l'application, utilisez **Documentation → Centre de documentation…** ou
`F1` pour ouvrir ce manuel hors ligne.
