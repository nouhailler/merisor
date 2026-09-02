# Règles MCD → MLD appliquées par MERISOR

[← Portail](../INDEX.md) · [Cardinalités](CARDINALITES.md) · [Historisation](HISTORISATION.md)

Ce document décrit le comportement du transformateur. Le bouton **ⓘ Pourquoi ?**
relie chaque résultat concret à l'une de ces règles grâce à sa provenance.

## Entité → table

- une entité conservée devient une table ;
- ses attributs deviennent des colonnes ;
- son identifiant devient la PK simple ou composée ;
- le type explicite est conservé ; le mode automatique utilise `INTEGER` pour
  un identifiant et `VARCHAR(100)` sinon.

## Association N:N

Une table portant le nom de l'association est créée. Les identifiants des
entités migrent comme FK et forment par défaut la PK composée. Les attributs de
l'association restent dans cette table.

```text
PILOTE (0,N) ── PARTICIPER ── (1,N) COURSE

PARTICIPER(
  id_pilote PK/FK,
  id_course  PK/FK,
  position
)
```

Un identifiant explicite de l'association remplace cette PK composée ; les FK
restent ordinaires.

## Association 1:N

En `AUTO` non historisé, la PK du côté référencé migre dans la table porteuse
du côté déterminé par les maxima. Les attributs de l'association migrent avec
la FK. Le minimum conservé détermine la nullabilité.

`FORCE_TABLE` ou `AUTO + is_historized` crée une table indépendante.

## Association 1:1

Aucune table d'association n'est créée par défaut :

- `(1,1)` face à `(0,1)` porte une FK `NOT NULL UNIQUE` du côté obligatoire ;
- `(1,1)/(1,1)` produit une FK `NOT NULL UNIQUE` ;
- `(0,1)/(0,1)` produit une FK `NULL UNIQUE` ;
- si les côtés sont symétriques, un tri stable par nom puis ID choisit le porteur.

Une 1:1 porteuse d'attributs doit utiliser `FORCE_TABLE`, ou être historisée en
`AUTO`, afin de ne perdre aucune information.

## Association n-aire

Une association de trois branches ou plus devient une table avec une FK par
branche. Sans identifiant explicite, ces FK forment la PK composée.
`FORCE_FK` est refusé.

## Association réflexive

Les règles ordinaires s'appliquent, mais les rôles distinguent les branches.
Une réflexive 1:N crée une auto-FK ; une 1:1 ajoute UNIQUE ; une N:N crée une
table avec deux FK vers la même table.

## Historisation et FORCE_TABLE

Une association non-N:N matérialisée :

1. utilise ses attributs identifiants comme PK ;
2. sinon reçoit une PK technique `id_<association>` ;
3. reçoit une FK par relation ;
4. conserve tous ses attributs ;
5. n'invente ni date ni unicité entre les FK.

Priorité conceptuelle : `FORCE_TABLE`, puis historisation en `AUTO`, puis règle
classique. `is_historized + FORCE_FK` est une erreur explicite.

## Héritage ISA

### JOINED

Mère et filles sont conservées. La PK de chaque fille est aussi une FK vers la
mère. Une PK mère composée reste une FK composée.

### PARENT_ONLY

Seule la mère reste ; les attributs non-clés des filles sont copiés dans sa
table et deviennent facultatifs. Une association directement portée par une
fille empêche cette stratégie.

### CHILDREN_ONLY

La mère disparaît ; ses attributs non-clés sont copiés dans chaque fille. Une
association portée par la mère empêche cette stratégie.

## Contraintes d'attribut

- `identifier` → PK et `NOT NULL` ;
- `unique` → contrainte UNIQUE hors PK ;
- `constraints` → CHECK ;
- `default` et `comment` sont propagés ;
- `auto_increment` reste une propriété logique traduite ensuite par le dialecte.

## Déterminisme

Tables, choix symétriques et noms générés utilisent des tris et politiques
stables. La position graphique n'influence jamais le résultat.

## Limites d'expression

Une FK, `NOT NULL` ou UNIQUE ne suffit pas toujours à exprimer toutes les
contraintes minimales MERISE. Les cardinalités originales restent attachées à
la provenance afin que l'application et la documentation puissent l'expliquer.
