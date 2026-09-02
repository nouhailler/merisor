# Historisation et matérialisation

[← Portail](../INDEX.md) · [Règles MCD → MLD](REGLES_MCD_MLD.md)

## Historisation

`is_historized = true` signifie que l'association représente des occurrences
indépendantes qui doivent pouvoir être conservées dans le temps.

```text
PILOTE ── ENGAGER ── EQUIPE
             │
        date_debut, date_fin
```

Deux engagements entre le même pilote et la même équipe doivent pouvoir
coexister. MERISOR matérialise donc `ENGAGER` en table indépendante et ne crée
pas `UNIQUE(id_pilote, id_equipe)` sans demande explicite.

L'historisation n'ajoute aucune date automatiquement. Les attributs nécessaires
doivent exister dans le MCD. Elle n'est jamais déduite du nom `date_debut`.

## Stratégies

| Stratégie | Effet |
|---|---|
| `AUTO` | applique les règles normales ; une historisée devient une table |
| `FORCE_TABLE` | matérialise toujours l'association |
| `FORCE_FK` | privilégie une FK si les cardinalités le permettent |

`FORCE_FK` est incompatible avec N:N, les n-aires et une association
historisée. Le validateur bloque ces contradictions.

## Identifiant de la table

- un identifiant conceptuel d'association devient la PK ;
- une N:N sans identifiant utilise normalement ses FK comme PK composée ;
- une association non-N:N matérialisée sans identifiant reçoit une PK technique
  déterministe `id_<association>` et auto-incrémentée.
