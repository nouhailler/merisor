# Rapport d’implémentation UI/UX 2.0

## Résumé

La refonte transforme MERISOR en atelier guidé autour du parcours **Concevoir →
Vérifier → Transformer → Produire**, avec l’IA comme assistance transversale.
Elle conserve les modèles MCD/MLD, la persistance JSON, les générateurs et les
commandes Annuler/Rétablir existants. Aucun format métier n’a été modifié.

Le travail a commencé par l’[audit de référence](UI_AUDIT.md), après inspection
de l’architecture et exécution de la suite existante. Le cahier des charges
intégral est conservé dans [UI_UX_2.0.md](UI_UX_2.0.md).

## Architecture finale

```text
MainWindow / application shell
├── navigation métier et état permanent
├── StartCenter
├── canvas MCD + palette + propriétés
├── ValidationCenter
├── MLDView (graphique / texte / provenance)
├── SQLWorkspace
├── AIHub
└── DocumentationCenter
             │
             ▼
      DiagramController
        │           │
        ▼           ▼
   modèle métier   services applicatifs
```

Les widgets restent des adaptateurs de présentation. Les règles MERISE,
MCD → MLD, SQL, IA et persistance demeurent dans leurs couches existantes.

## Composants ajoutés

- `theme/` : tokens sémantiques, thèmes clair/sombre/système et gestionnaire ;
- `application_shell.py` : navigation, palette et bandeau d’état ;
- `start_center.py` : accueil, récents, exemples et imports ;
- `validation_center.py` : filtres, détails, explications et localisation ;
- `sql_workspace.py` : production SQL intégrée ;
- `ai_hub.py` : point d’entrée des assistants ;
- `command_palette.py` : palette `Ctrl+K` et recherche globale ;
- `DocumentationCenter` : manuel hors ligne intégré.

## Évolutions des composants existants

- canvas : pan Espace, grille, outils regroupés et rendu thémable ;
- entités/associations : cartes lisibles, types alignés, badges PK, survol et
  sélection visibles ;
- propriétés : résumé du modèle, sélection multiple et hiérarchie d’actions ;
- MLD : tailles dynamiques, zoom, sélection, provenance et retour vers le MCD ;
- shell : état explicite du document, du MCD, du MLD et du SQL.

## Navigation, états et feedback

Les étapes affichent les états prêt, avertissement, erreur, en attente ou
obsolète. La production SQL est indisponible sans MLD à jour. Une validation
bloquante ouvre le centre correspondant au lieu d’un rapport technique isolé.

Raccourcis principaux :

- `Ctrl+K` : palette de commandes ;
- `Ctrl+Shift+F` : recherche globale ;
- `F1` : documentation ;
- `F11` : plein écran ;
- `Espace + glisser` : déplacement du canvas ;
- `Ctrl + molette` : zoom.

## Thèmes et accessibilité

Les couleurs, espacements, tailles, bordures et rôles viennent du design system.
Le thème choisi est persistant et les scènes MCD/MLD ainsi que la coloration SQL
s’adaptent aux modes clair, sombre et système. Les états utilisent texte,
symboles et couleur. Les commandes iconiques possèdent nom accessible et
info-bulle, et le focus clavier reste visible.

## IA et confiance

Le hub rappelle le parcours demande → proposition → prévisualisation →
validation locale → diff → confirmation → application. Les dialogues
OpenRouter restent non bloquants et aucune réponse ne modifie silencieusement
le modèle.

## Captures de référence

- [Accueil](images/ui2-start-center.png)
- [Canvas MCD](images/ui2-mcd.png)
- [Validation](images/ui2-validation.png)
- [MLD](images/ui2-mld.png)
- [SQL](images/ui2-sql.png)
- [Assistant IA](images/ui2-ai.png)
- [Thème sombre](images/ui2-dark.png)
- [Documentation](images/ui2-documentation.png)

Elles sont reproductibles avec `PYTHONPATH=src python scripts/capture_ui.py`.

## Phases

| Phase | Livrable | État |
|---:|---|---|
| 0 | Audit et référence de tests | Terminée |
| 1 | Design system | Terminée |
| 2 | Application shell | Terminée |
| 3 | Start Center | Terminée |
| 4 | Canvas MCD | Terminée |
| 5 | Panneau de propriétés | Terminée |
| 6 | Centre de validation | Terminée |
| 7 | Navigation et fraîcheur MCD/MLD/SQL | Terminée |
| 8 | Vue MLD | Terminée |
| 9 | Espace SQL | Terminée |
| 10 | Hub IA | Terminée |
| 11 | Documentation intégrée | Terminée |
| 12 | Recherche, commandes, thèmes et vérifications | Terminée |

## Tests et vérifications

- Ruff sur les sources et tests ;
- mypy sur la totalité des sources ;
- pytest en mode Qt hors écran ;
- captures à 1366 × 768 ;
- test de redimensionnement aux formats desktop demandés ;
- tests des espaces Accueil, MCD, Propriétés, Validation, MLD, SQL, IA,
  Documentation, recherche et thèmes.

Résultat final de cette implémentation : **377 tests réussis**, Ruff sans erreur
et mypy sans erreur sur 75 fichiers source.

## Limites et recommandations

- les dialogues métier très spécialisés restent modaux ; les convertir sans
  bénéfice de contexte n’est pas une priorité ;
- la coloration SQL est volontairement légère et sans dépendance externe ;
- les captures hors écran vérifient la composition, mais une revue humaine sur
  plusieurs environnements de bureau reste recommandée avant une release ;
- un futur mode débutant/expert peut s’appuyer sur les rôles et espaces actuels
  sans modifier le domaine.
