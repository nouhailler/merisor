# Modèle de données interne

[← Portail](../INDEX.md) · [Format JSON](JSON_FORMAT.md)

## MCDModel

```text
MCDModel
├── entities: Entity[]
├── associations: Association[]
├── relations: Relation[]
├── inheritances: Inheritance[]
├── functional_dependencies: FunctionalDependency[]
├── domains: ModelDomain[]
└── submodel_views: SubmodelView[]
```

Tous les objets et attributs possèdent un ID interne unique, indépendant du
nom affiché.

## Nœuds

`Entity` : nom, position, attributs et identifiants calculés.

`Association` ajoute `is_historized` et `materialization_strategy`.

`Attribute` contient le type logique facultatif, nullabilité, défaut, UNIQUE,
commentaire, auto-incrémentation et CHECK.

## Liens

`Relation` référence exactement une entité et une association. Elle porte une
cardinalité et un rôle. Plusieurs relations vers la même entité permettent une
réflexive si leurs rôles sont distincts.

`Inheritance` référence une mère, une ou plusieurs filles et une stratégie ISA.

`FunctionalDependency` appartient à un nœud et relie des IDs d'attributs
déterminants/dépendants, avec origine `USER` ou `AI`.

## Organisation

`ModelDomain` regroupe des IDs de nœuds avec appartenance multiple possible.
`SubmodelView` compose domaines et nœuds explicites dans une vue `BUSINESS` ou
`TECHNICAL`.

## MLDModel

```text
MLDModel
└── tables: MLDTable[]
    ├── columns: MLDColumn[]
    ├── primary_key: column_ids[]
    ├── foreign_keys: MLDForeignKey[]
    ├── unique_constraints[]
    ├── check_constraints[]
    └── indexes[]
```

Une FK composée est un seul objet contenant plusieurs colonnes locales et
référencées. Les colonnes conservent les IDs de leurs attributs, éléments et
relations sources. Les FK conservent association, relation, cardinalité ou ISA.

## Types logiques

`MLDDataType` comprend `name`, `length`, `precision` et `scale`. Il reste
indépendant du SQL. `MLDTableSource` vaut `ENTITY` ou `ASSOCIATION`.

## Invariants

- unicité globale des IDs MCD ;
- aucune relation orpheline ;
- une FK référence autant de colonnes locales que distantes ;
- les IDs de PK/contraintes appartiennent à la table ;
- un MLD généré porte l'empreinte logique de son MCD source.
