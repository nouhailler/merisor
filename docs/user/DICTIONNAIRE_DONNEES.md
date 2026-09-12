# Dictionnaire de données

Le dictionnaire de données complète le diagramme avec le sens métier de ses
éléments. Ouvrez-le avec **Modèle → Dictionnaire de données…** ou `Ctrl+Alt+G`.

## Informations disponibles

Pour une entité ou une association, vous pouvez renseigner une description :

```yaml
CLIENT:
  description: Personne ou organisation possédant un compte.
```

Pour un attribut, la fiche rassemble les propriétés déjà présentes dans le
MCD :

```yaml
email:
  type: VARCHAR(255)
  rôle: donnée métier
  nullable: non
  unique: oui
  description: Adresse électronique de contact.
```

La description d'un attribut est son champ **Commentaire**. Une modification
effectuée dans le dictionnaire est donc immédiatement cohérente avec le panneau
de propriétés.

## Termes métier

Le glossaire conserve des termes indépendants des noms techniques :

```yaml
Client:
  synonymes: [acheteur, utilisateur]
  définition: Personne ou organisation utilisant le service.
```

Utilisez **Ajouter un terme**, saisissez sa définition et séparez les synonymes
par des virgules. Deux termes ne peuvent pas porter le même nom, sans tenir
compte des majuscules.

## Confirmation et historique

Le dialogue travaille sur une copie du modèle. **Annuler** abandonne toutes les
modifications. **Appliquer au MCD** les enregistre comme une seule commande ;
`Ctrl+Z` permet donc de restaurer le dictionnaire précédent.

## Réutilisation

Les descriptions et le glossaire sont déjà repris dans :

- la documentation Markdown et HTML générée ;
- le format JSON du projet ;
- le schéma proposé aux fonctions de génération IA.

Ils constituent également une base stable pour de futures règles explicites de
validation, de génération de données et d'assistance. MERISOR ne transforme
pas automatiquement une définition libre en contrainte SQL : une information
sémantique ne doit jamais devenir une règle technique sans décision visible.

## Compatibilité JSON

Le format reste `format_version: 2`. Les champs suivants sont optionnels lors
du chargement :

```json
{
  "entities": [
    {
      "description": "Personne possédant un compte"
    }
  ],
  "business_terms": [
    {
      "id": "term_client",
      "name": "Client",
      "definition": "Personne utilisant le service",
      "synonyms": ["acheteur", "utilisateur"]
    }
  ]
}
```

Un ancien projet dépourvu de ces propriétés est chargé avec des descriptions
vides et un glossaire vide.
