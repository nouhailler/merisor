# ADR-005 — OpenRouter avec validation et confirmation humaine

## Statut

Accepté.

## Contexte

L'IA peut accélérer la conception mais produit des erreurs et traite des données
chez un tiers.

## Décision

Utiliser OpenRouter de manière facultative, avec clé hors projet, sorties JSON
strictes, validation locale, aperçu et confirmation avant toute mutation.

## Conséquences

Les appels sont asynchrones. L'interface indique les données envoyées, les
quotas et les niveaux de confiance. Une réponse textuelle n'est jamais appliquée.

## Alternatives rejetées

Appliquer directement un modèle généré ou stocker la clé dans le JSON violerait
les exigences de sûreté et de confidentialité.
