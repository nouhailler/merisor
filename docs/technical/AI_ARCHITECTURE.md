# Architecture des fonctions IA

[← Portail](../INDEX.md) · [Guide IA](../user/IA.md) · [Sécurité](SECURITY.md)

## Invariant

Une réponse IA n'est jamais une commande. Elle produit un **candidat** ou un
**patch** soumis aux validateurs déterministes de MERISOR.

```text
Utilisateur → OpenRouter → JSON strict → dépôt JSON / patch applier
                                      → validation MCD
                                      → aperçu
                                      → confirmation
                                      → commande annulable
```

## Configuration

`OpenRouterKeyStore` stocke activation, modèle et clé. Les modèles récupérés
sont filtrés pour le texte et la gratuité (`:free` ou prix nul). Le client HTTP
centralise les erreurs réseau, authentification et quotas.

## Génération ponctuelle

`AiMcdService` impose le schéma V2 complet. Le JSON est éditable dans l'aperçu,
rechargé par `JsonDiagramRepository`, validé et importé seulement après
confirmation.

## Assistant de modélisation conversationnel

`DesignSession` conserve brouillon, tours, hypothèses, questions et révisions.
`ConversationalDesignService` n'accepte qu'une enveloppe structurée et un
`DraftPatch`. `DraftPatchApplier` contrôle collections, IDs, changements et
références avant de produire un nouveau brouillon.

`DesignStage` décrit les six étapes d'orchestration indépendamment de Qt.
L'enveloppe peut transporter des `DesignJustification` structurées contenant
l'identifiant cible, son libellé, la décision et son explication. La session
les associe uniquement aux éléments encore présents dans le brouillon. Elles
sont consultables pendant la conversation et dans l'aperçu final.

L'absence du champ `justifications` reste acceptée pour les réponses produites
avec l'ancien prompt. Le nouveau prompt demande toutefois une justification
pour chaque entité, association et relation créée ou modifiée avant d'annoncer
le brouillon prêt.

## Réparation

`AiRepairService` transmet le MCD courant et les signaux locaux, limite la
réponse à douze propositions autonomes et refuse patchs sans effet, cibles
absentes ou modifications concurrentes. L'utilisateur choisit Voir/Ignorer/
Appliquer avant l'aperçu final.

## Normalisation

`AiNormalizationService` suggère des dépendances fonctionnelles structurées.
Elles sont affichées comme suggestions et ne deviennent pas des faits sans
confirmation.

## Asynchronisme

Chaque dialogue utilise un worker `QObject` déplacé dans un `QThread`. Le
worker ne touche aucun widget ; il émet succès ou erreur. L'interface affiche
une progression et empêche la fermeture pendant la requête active.

## Données et confiance

Les prompts incluent seulement le contexte nécessaire à l'action. Les niveaux
de confiance et hypothèses restent visibles. Les validations locales restent
autoritaires pour la structure, mais l'utilisateur reste responsable de la
sémantique métier.
