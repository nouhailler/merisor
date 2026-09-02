# Créer et éditer un MCD

[← Portail](../INDEX.md) · [Concepts MERISE](../concepts/MERISE.md)

## Entités

Une entité représente un concept métier identifiable : `CLIENT`, `PRODUIT`,
`COURSE`. Elle possède un identifiant interne stable, un nom, une position et
des attributs. Au moins un attribut doit former l'identifiant conceptuel.

## Attributs

Sélectionnez une entité ou une association, puis utilisez le panneau
**Propriétés**. Les types disponibles sont `INTEGER`, `BIGINT`, `DECIMAL`,
`FLOAT`, `BOOLEAN`, `VARCHAR(n)`, `TEXT`, `DATE`, `TIME`, `DATETIME` et
`TIMESTAMP`.

Le mode **Automatique** conserve le comportement historique : identifiant en
`INTEGER`, autre attribut en `VARCHAR(100)`. Une propriété explicite est
propagée au MLD puis au SQL.

Règles importantes :

- un identifiant est obligatoire et `NOT NULL` ;
- une auto-incrémentation exige une PK simple entière ;
- plusieurs attributs cochés forment un identifiant composé ;
- `UNIQUE`, la valeur par défaut, le commentaire et les `CHECK` sont conservés.

## Associations et relations

Une association relie au moins deux branches. Chaque relation référence une
entité, l'association, une cardinalité et éventuellement un rôle. Les rôles
sont obligatoires et distincts lorsqu'une association est réflexive.

Une association peut porter ses propres attributs. Elle peut aussi être
**historisée** ou demander une stratégie `AUTO`, `FORCE_TABLE` ou `FORCE_FK`.

## Associations réflexives et n-aires

Pour `EMPLOYE — SUPERVISER — EMPLOYE`, reliez deux fois la même entité et
nommez les rôles `superviseur` et `supervisé`. Pour une association ternaire,
reliez trois entités à la même association. Le transformateur conserve une FK
par branche.

## Héritages ISA

**Modèle → Ajouter une spécialisation ISA…** relie une mère à une ou plusieurs
filles. Trois stratégies sont disponibles :

- `JOINED` : une table par niveau, PK/FK entre fille et mère ;
- `PARENT_ONLY` : table mère seule, attributs des filles aplatis ;
- `CHILDREN_ONLY` : tables filles seules, attributs de la mère copiés.

Les cycles et l'héritage multiple sont refusés. Une stratégie aplatie refuse
une association directement portée par une table supprimée ; utilisez `JOINED`.

## Validation

Le validateur vérifie notamment les noms, identifiants, doublons d'attributs,
branches d'association, cardinalités, rôles réflexifs et stratégies
contradictoires. Une erreur bloque le MLD ; un avertissement attire l'attention
sans empêcher la sauvegarde.

## Productivité du canvas

La grille, les guides, l'aimantation, l'alignement, la sélection multiple, le
copier/coller, le pliage, les domaines et la disposition automatique n'altèrent
pas la structure logique. Seules les positions sont sauvegardées avec le MCD.

## Suite

- [Cardinalités](../concepts/CARDINALITES.md)
- [Historisation](../concepts/HISTORISATION.md)
- [Normalisation](../concepts/NORMALISATION.md)
- [Générer le MLD](MLD.md)
