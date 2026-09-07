# Design system MERISOR 2.0

## Objectif

Le design system donne à toutes les surfaces Qt un langage visuel commun : sobre,
professionnel, pédagogique et adapté à une application de bureau. Les widgets ne
doivent plus introduire de couleurs ou de dimensions arbitraires.

## Architecture

```text
src/merisor/ui/theme/
├── tokens.py          couleurs, espacements, rayons, dimensions, typographie
├── light_theme.py     feuille QSS claire
├── dark_theme.py      feuille QSS sombre
└── theme_manager.py   choix clair/sombre/système et persistance QSettings
```

`ThemeManager` est l'unique point d'application du thème global. Il résout le mode
`system`, applique le QSS et expose la palette active aux vues graphiques qui ne
peuvent pas être stylées uniquement avec QSS.

## Couleurs

La marque s'appuie sur un bleu principal (`#3157D5` en thème clair), un accent
turquoise et un accent secondaire violet. Les couleurs `success`, `warning`,
`error`, `info` et `ai` sont sémantiques : leur usage ne doit pas être remplacé
par une valeur hexadécimale locale.

Les surfaces sont organisées en quatre niveaux : fond d'application, surface,
surface surélevée et surface atténuée. Texte principal, texte secondaire, texte
désactivé, bordures et sélection possèdent leurs propres tokens.

## Typographie

- titre de page : 18 pt, gras ;
- titre de section : 13 pt, semi-gras ;
- titre de carte : 11 pt, semi-gras ;
- corps : 10 pt ;
- légende : 9 pt ;
- monospace : uniquement SQL, JSON, code et valeurs techniques.

La famille demandée est `Inter`, avec repli sur `Noto Sans` puis les polices sans
serif du système. Aucun téléchargement de police n'est nécessaire.

## Espacement et dimensions

Les espacements suivent une échelle de 2, 4, 8, 12, 16, 24 et 32 px. Les contrôles
standards mesurent au minimum 32 px de haut. Les rayons disponibles sont 4, 7 et
10 px. Toute nouvelle valeur doit être ajoutée aux tokens avant d'être utilisée.

## Rôles dynamiques

Les propriétés Qt permettent d'exprimer une intention sans QSS local :

```python
button.setProperty("role", "primary")
label.setProperty("role", "warning")
```

Rôles disponibles :

- boutons : `primary`, `danger` ;
- libellés : `pageTitle`, `sectionTitle`, `secondary`, `success`, `warning`,
  `error`, `info`.

## États et accessibilité

Le QSS définit les états normal, survolé, pressé, désactivé, sélectionné et focus.
Un contrôle uniquement iconique doit toujours recevoir un nom accessible et une
info-bulle. Une couleur sémantique ne doit jamais être le seul vecteur
d'information : elle accompagne un texte, un symbole ou un libellé.

## Règle d'intégration

Les futurs écrans doivent :

1. utiliser les tokens pour tout dessin `QPainter` ;
2. privilégier les propriétés de rôle pour les widgets ;
3. ne pas appeler `setStyleSheet()` localement ;
4. conserver un texte explicite lorsque l'icône n'est pas universelle ;
5. vérifier les trois modes clair, sombre et système.

Les anciens styles locaux seront migrés progressivement dans les phases dédiées à
leurs écrans afin de limiter les régressions.

## Rapport de PHASE 1

```text
PHASE : 1 — Design system
État : terminé

Fichiers créés :
- src/merisor/ui/theme/__init__.py
- src/merisor/ui/theme/tokens.py
- src/merisor/ui/theme/light_theme.py
- src/merisor/ui/theme/dark_theme.py
- src/merisor/ui/theme/theme_manager.py
- tests/test_theme.py
- docs/DESIGN_SYSTEM.md

Fichiers modifiés :
- src/merisor/ui/main_window.py

Fonctionnalités implémentées :
- tokens visuels centralisés
- thèmes globaux clair, sombre et système
- états cohérents des widgets et focus visible
- persistance du thème via QSettings

Tests exécutés :
- tests du design system
- suite complète de qualité et de non-régression

Régressions détectées :
- aucune

Prochaine phase :
- PHASE 2 — Application shell
```
