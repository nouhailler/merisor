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

## Conversation

`DesignSession` conserve brouillon, tours, hypothèses, questions et révisions.
`ConversationalDesignService` n'accepte qu'une enveloppe structurée et un
`DraftPatch`. `DraftPatchApplier` contrôle collections, IDs, changements et
références avant de produire un nouveau brouillon.

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
