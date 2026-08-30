# Contexte de reprise du projet MERISOR

## État de l'intégration OpenRouter

Les trois étapes prévues sont terminées :

1. récupération et sélection des modèles gratuits OpenRouter ;
2. génération d'un JSON MCD avec validation, sans modifier le modèle courant ;
3. aperçu éditable et import confirmé du MCD généré dans l'éditeur.

La prochaine reprise peut se concentrer sur les retours d'usage, l'amélioration
des prompts ou le passage des appels réseau dans un traitement asynchrone.

## Contraintes à conserver

- ne jamais enregistrer la clé API dans un fichier de projet JSON ;
- ne jamais remplacer le MCD courant sans confirmation explicite ;
- valider tout JSON produit par l'IA avant de l'importer ;
- conserver la séparation entre interface, service OpenRouter et modèle métier ;
- exécuter les tests existants avant de poursuivre.
