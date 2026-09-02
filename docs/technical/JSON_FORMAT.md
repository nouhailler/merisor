# Format JSON MERISOR V2

[← Portail](../INDEX.md) · [Persistance](PERSISTENCE.md)

## Racine

```json
{
  "format_version": 2,
  "entities": [],
  "associations": [],
  "relations": [],
  "inheritances": [],
  "functional_dependencies": [],
  "domains": [],
  "submodel_views": []
}
```

`format_version` doit valoir `1` ou `2`. La version 1 est migrée en mémoire.

## Entité

```json
{
  "id": "entity_client",
  "name": "CLIENT",
  "position": {"x": 100, "y": 80},
  "attributes": []
}
```

`id`, `name`, `position` et `attributes` décrivent le nœud. Un nom vide reste
chargeable afin que le validateur puisse signaler un modèle en construction.

## Attribut

```json
{
  "id": "attribute_email",
  "name": "email",
  "identifier": false,
  "data_type": {"name": "VARCHAR", "length": 255},
  "nullable": false,
  "default": null,
  "unique": true,
  "comment": "Adresse de contact",
  "auto_increment": false,
  "constraints": []
}
```

`data_type` vaut `null` pour le mode automatique. `DECIMAL` accepte
`precision`/`scale`; `VARCHAR` exige `length`. Les anciens attributs sans
propriétés reçoivent des valeurs rétrocompatibles.

## Association

Elle reprend les champs d'un nœud et ajoute :

```json
{
  "is_historized": false,
  "materialization_strategy": "AUTO"
}
```

Les stratégies autorisées sont `AUTO`, `FORCE_TABLE`, `FORCE_FK`. Une valeur
absente devient `false` et `AUTO`.

## Relation et cardinalité

```json
{
  "id": "relation_client_passer",
  "entity_id": "entity_client",
  "association_id": "association_passer",
  "cardinality": {"minimum": "0", "maximum": "N"},
  "role": "client"
}
```

Une cardinalité peut être `null` dans un brouillon. Sinon, minimum vaut `0` ou
`1`, maximum `1` ou `N`. Les références doivent viser des objets existants.

## Héritage

```json
{
  "id": "isa_personne_client",
  "parent_entity_id": "entity_personne",
  "child_entity_ids": ["entity_client"],
  "strategy": "JOINED"
}
```

Stratégies : `JOINED`, `PARENT_ONLY`, `CHILDREN_ONLY`.

## Dépendance fonctionnelle

```json
{
  "id": "fd_client_email",
  "owner_id": "entity_client",
  "determinant_attribute_ids": ["attribute_id_client"],
  "dependent_attribute_ids": ["attribute_email"],
  "origin": "USER"
}
```

Tous les attributs doivent appartenir au propriétaire. Origine : `USER` ou `AI`.

## Domaines et vues

```json
{
  "domains": [{
    "id": "domain_sales",
    "name": "Commerce",
    "description": "Commandes et produits",
    "node_ids": ["entity_client", "entity_order"]
  }],
  "submodel_views": [{
    "id": "view_sales",
    "name": "Vue commerce",
    "kind": "BUSINESS",
    "domain_ids": ["domain_sales"],
    "node_ids": []
  }]
}
```

`kind` vaut `BUSINESS` ou `TECHNICAL`.

## Compatibilité

- V1 conserve noms, positions, entités, associations et relations ;
- champs V2 absents : valeurs par défaut documentées ci-dessus ;
- tableaux fonctionnels/domaines/vues absents : collections vides ;
- relation sans `role` : chaîne vide ;
- le chargement ne réécrit jamais le fichier ; l'enregistrement explicite
  produit un V2 complet.

## Validation et sécurité

Le dépôt refuse les versions inconnues, types JSON incohérents, IDs dupliqués,
références orphelines et valeurs d'énumération inconnues. Le JSON IA passe par
le même dépôt avant aperçu. Les clés API et le MLD généré ne font jamais partie
du fichier.

Voir [l'exemple MotoGP](https://github.com/nouhailler/merisor/blob/main/examples/motogp.json)
pour un modèle complet.
