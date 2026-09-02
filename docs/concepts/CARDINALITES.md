# Cardinalités

[← Portail](../INDEX.md) · [Règles MCD → MLD](REGLES_MCD_MLD.md)

Une cardinalité décrit combien de fois une occurrence d'entité peut participer
à une association.

| Cardinalité | Sens |
|---|---|
| `(0,1)` | facultative, au maximum une fois |
| `(1,1)` | obligatoire, exactement une fois |
| `(0,N)` | facultative, plusieurs occurrences possibles |
| `(1,N)` | obligatoire, au moins une occurrence |

## Minimum

- `0` signifie que la participation est facultative ;
- `1` signifie qu'elle est obligatoire.

Lors d'une migration de FK, MERISOR traduit le minimum en nullabilité lorsque
la contrainte est représentable : `0 → NULL`, `1 → NOT NULL`.

## Maximum

- `1` limite la participation à une occurrence ;
- `N` autorise plusieurs occurrences.

Les maxima des deux branches permettent de reconnaître une association 1:1,
1:N ou N:N.

## Limite relationnelle

Une table et des FK n'expriment pas toujours toute une cardinalité MERISE. Par
exemple, une contrainte « au moins une occurrence » peut demander une règle
applicative ou différée. MERISOR conserve la cardinalité source dans la
provenance au lieu de prétendre qu'un simple `NOT NULL` suffit toujours.

## Associations réflexives

Deux branches peuvent viser la même entité. Le rôle (`superviseur`, `supervisé`)
les distingue et produit des noms de FK non ambigus.
