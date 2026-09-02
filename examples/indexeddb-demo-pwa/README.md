# Démonstration PWA IndexedDB pour MERISOR

Cette petite application gère des clients et leurs commandes avec l'API
IndexedDB native. Elle sert à tester **Fichier → Importer un projet PWA /
IndexedDB…** dans MERISOR.

## Tester l'import

Dans MERISOR :

1. ouvrez **Fichier → Importer un projet PWA / IndexedDB…** ;
2. choisissez **Dossier local cloné** et sélectionnez ce dossier ;
3. ou choisissez **Archive ZIP** et sélectionnez
   `examples/indexeddb-demo-pwa.zip` ;
4. vérifiez l'aperçu avant de confirmer.

Le MCD proposé doit contenir `CUSTOMER`, `ORDER` et une association construite
depuis `ORDER.customerId`.

## Lancer la PWA

Depuis ce dossier :

```bash
python3 -m http.server 8080
```

Ouvrez ensuite <http://localhost:8080>. Les données restent uniquement dans
le navigateur. Effacer les données du site supprime la base de démonstration.
