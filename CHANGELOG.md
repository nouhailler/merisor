# Journal des modifications

Toutes les évolutions importantes de MERISOR sont documentées dans ce fichier.

## [Non publié]

### Ajouté

- disposition automatique déterministe du MCD ;
- réorganisation automatique après import d'un MCD généré par l'IA ;
- commande **Modèle → Réorganiser automatiquement le MCD** annulable ;
- résolution des chevauchements tenant compte de la taille des objets ;
- logo MERISOR et icône de bureau installée avec le paquet Debian ;
- captures d'écran de l'éditeur MCD, du MLD, du SQL et de l'import IA ;
- licence MIT.

### Modifié

- README entièrement restructuré pour les utilisateurs débutants et les
  contributeurs, avec guide d'installation, prise en main, architecture,
  format JSON, sécurité, limites et documentation des transformations.

## [0.5.0] - 2026-08-30

### Ajouté

- menu **Fichier → Ouvrir récent**, conservant les dix derniers modèles ;
- zoom de la vue graphique MLD avec boutons et `Ctrl` + molette ;
- panneau de propriétés pour les tables sélectionnées dans le MLD ;
- menu **Paramètres** et stockage local de la clé OpenRouter ;
- prise en charge du trousseau système via le paquet optionnel `keyring` ;
- test de la clé OpenRouter ;
- récupération et sélection des modèles texte gratuits ;
- activation ou désactivation de la génération assistée par IA ;
- fenêtre de description métier pour générer un MCD ;
- génération d'un JSON MERISOR version 2 par OpenRouter ;
- validation structurelle du JSON et validation métier MERISE ;
- aperçu des entités, associations, relations et cardinalités générées ;
- correction manuelle et revalidation du JSON avant import ;
- import explicite du MCD sans modification préalable du document courant ;
- gestion lisible des erreurs OpenRouter, des quotas et des réponses invalides.

### Modifié

- cadres MLD élargis pour éviter les chevauchements de texte ;
- affichage MLD enrichi avec types, nullabilité, PK, FK, UQ et AI ;
- documentation OpenRouter, génération IA et installation Debian complétée ;
- couverture de tests portée à 140 tests automatisés.

### Sécurité

- la clé OpenRouter n'est jamais enregistrée dans les fichiers JSON du projet ;
- le MCD courant n'est remplacé qu'après validation et confirmation explicite ;
- un JSON IA invalide ne peut pas être importé.

## [0.4.0] - 2026-08-29

### Ajouté

- génération MCD → MLD ;
- génération SQL PostgreSQL, SQLite et MariaDB/MySQL ;
- gestion des associations historisées et stratégies de matérialisation ;
- validation du MCD et du MLD ;
- paquet Debian initial.
