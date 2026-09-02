# Contribuer à MERISOR

[← Portail](../INDEX.md) · [Développement](DEVELOPMENT.md)

## Processus

1. créez un fork ;
2. ouvrez une branche dédiée ;
3. réalisez une modification ciblée ;
4. ajoutez ou adaptez les tests ;
5. lancez Ruff, mypy et pytest ;
6. mettez à jour la documentation ;
7. ouvrez une pull request expliquant le besoin et le comportement.

## Règles d'architecture

- aucune règle MERISE dans un `QGraphicsItem` ;
- le domaine reste indépendant de Qt ;
- une mutation passe par le contrôleur et reste annulable ;
- le MCD reste la source de vérité ;
- le SQL est généré depuis le MLD ;
- toute sortie IA est validée et confirmée ;
- aucune connexion ou exécution SQL implicite.

## Compatibilité

Ne cassez pas le JSON V1/V2. Un nouveau champ doit avoir une valeur par défaut
rétrocompatible et des tests de chargement ancien. Un changement de format
nécessite une stratégie explicite.

## Style

- annotations mypy strictes ;
- formatage Ruff ;
- messages utilisateur en français et compréhensibles ;
- commentaires pour les décisions, pas pour répéter le code ;
- petites fonctions et services testables.

## Pull request

Indiquez : problème, solution, décisions, captures si UI, tests exécutés et
limitations. Ne joignez aucun secret ni donnée métier confidentielle.
