# Contexte de reprise du projet MERISOR

## Prochaine reprise

La prochaine fois que le projet est démarré, poursuivre l'intégration de
l'assistance IA OpenRouter. L'étape 1 est terminée : le menu Paramètres permet
d'enregistrer une clé OpenRouter localement, avec `keyring` lorsque le trousseau
système est disponible.

Les trois étapes restantes sont à terminer dans cet ordre :

1. **Récupération et sélection des modèles gratuits** OpenRouter.
2. **Génération d'un JSON MCD avec validation**, sans modifier le modèle
   courant.
3. **Aperçu et import confirmé** du MCD généré dans l'éditeur.

## Contraintes à conserver

- ne jamais enregistrer la clé API dans un fichier de projet JSON ;
- ne jamais remplacer le MCD courant sans confirmation explicite ;
- valider tout JSON produit par l'IA avant de l'importer ;
- conserver la séparation entre interface, service OpenRouter et modèle métier ;
- exécuter les tests existants avant de poursuivre.
