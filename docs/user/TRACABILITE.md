# Traçabilité MCD → MLD → SQL

[← Portail](../INDEX.md) · [Comprendre le MLD](MLD.md) · [Générer du SQL](SQL.md)

Le mode **Traçabilité** explique comment un élément conceptuel devient une
structure logique, puis une instruction SQL. Il est entièrement déterministe :
aucune IA n'intervient dans l'explication.

## Ouvrir la traçabilité

1. générez un MLD à jour ;
2. sélectionnez une table dans le graphe MLD ;
3. sélectionnez éventuellement une colonne dans **Propriétés MLD** ;
4. cliquez sur **ⓘ Pourquoi ? / Traçabilité**.

Sans colonne sélectionnée, MERISOR explique la table entière. Avec une colonne,
il retrace précisément son attribut source, sa relation et ses contraintes.

## Les trois niveaux

~~~text
MCD                         MLD                       SQL
CLIENT.id_client     →      COMMANDE.id_client  →    FOREIGN KEY (...)
       │                     │
       └─ PASSER             └─ FK vers CLIENT
          (0,N)/(1,1)
~~~

- **Origine** : entité ou association, attribut et identifiant interne source ;
- **Transformation** : association, rôles, cardinalités et règle appliquée ;
- **Conséquence** : PK, FK, UNIQUE, nullabilité ou colonne technique obtenue ;
- **SQL** : extrait correspondant en PostgreSQL, SQLite ou MariaDB/MySQL.

Le sélecteur de dialecte recalcule l'extrait avec les types et les identifiants
cités propres à la cible. MERISOR construit cet extrait depuis le MLD ; il ne
tente pas de retrouver la règle en analysant du texte SQL.

## Exemple

Pour **CLIENT (0,N) — PASSER — COMMANDE (1,1)**, la sélection de
**COMMANDE.id_client** affiche :

~~~text
Origine
MCD → CLIENT.id_client

Transformation
Association PASSER
Cardinalités : CLIENT (0,N) / COMMANDE (1,1)

Conséquence
Création d'une FK dans COMMANDE vers CLIENT.

SQL
FOREIGN KEY ("id_client") REFERENCES "CLIENT" ("id_client")
~~~

Si le MCD a changé depuis la génération, la traçabilité est désactivée jusqu'à
la régénération du MLD afin de ne jamais expliquer un résultat obsolète.
