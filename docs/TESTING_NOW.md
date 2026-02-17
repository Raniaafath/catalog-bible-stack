# Comment tester maintenant

Guide minimal pour lancer le backend, le frontend et vérifier les changements (product family, listing groups, axes résolus).

---

## 1. Prérequis

- Python 3.10+ avec venv
- Node 18+ (pour le frontend)
- PostgreSQL (ou Docker pour la DB)

---

## 2. Lancer le backend (Django)

### Variables d’environnement

À la racine du projet Django (`/srv/catalog-bible-stack/django`) :

```bash
# Copier l’exemple et adapter (au minimum la DB)
cp .env.example .env
# Éditer .env : DB_HOST=localhost si PostgreSQL est en local
```

### Base de données et migrations

```bash
# Créer la base PostgreSQL si besoin, puis :
python manage.py migrate
```

### Serveur de dev

```bash
python manage.py runserver 0.0.0.0:8000
```

L’API est disponible sur **http://localhost:8000/api/v1/**.

### (Optionnel) Données de test

```bash
# Crée des produits / variantes de test (voir docs/QUICK_START.md)
python manage.py test_parent_variant_import
```

---

## 3. Lancer le frontend (Vite)

Dans un **second terminal** :

```bash
cd frontend
npm install
npm run dev
```

Le front tourne sur **http://localhost:8080** (ou le port indiqué dans la console).

### Appeler l’API depuis le frontend

Si le front est sur **8080** et l’API sur **8000**, il faut que le front envoie les requêtes vers `http://localhost:8000/api/v1`.

Dans `frontend/.env` :

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Puis redémarrer `npm run dev`.

Côté Django, l’origine 8080 est déjà dans `DEFAULT_CORS_ORIGINS`. Si tu utilises l’auth par session/CSRF, ajoute dans `.env` :  
`DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://localhost:8080`.

---

## 4. Ce qu’on peut tester

### Produits (product families)

- **Menu Products** : liste des produits (colonnes « Product family », etc.).
- Créer un produit, ouvrir un produit : libellés « product family », « Back to Products », etc.
- Vérifier qu’un produit affiche bien ses variantes et attributs.

### Listing groups

- **Menu Listings** : liste des listing groups.
- **Créer un listing group** : choisir un product family (optionnel), un channel, un nom.
- Ouvrir un listing : onglets Variants, Variation Axes, Generate Titles.
- **Variation Axes** : les axes affichés sont **résolus** (listing → channel → product family). Si le listing a un product family et qu’aucun axe n’est défini sur le listing, les axes du canal ou du produit s’affichent.

### Axes résolus (API)

- `GET /api/v1/channel-listings/{id}/` : dans la réponse, `axes` doit lister les axes **résolus** (sans `id` ni `enabled` quand ils viennent du fallback channel/product).
- Sur un listing **sans** product family : `axes` reste la liste des axes configurés sur le listing (avec `id`, `enabled`).

### Génération de titres (backend)

En shell Django :

```python
from catalog.models import Product, Variant
from catalog.services import get_axes_for_context, generate_variant_title

# Avec axes par défaut (product family)
p = Product.objects.first()
axes = get_axes_for_context(p)
print([a.attribute_code for a in axes])

v = p.variants.first()
print(generate_variant_title(v))

# Avec canal / listing (si tu as des ChannelVariantAxis / ChannelListingAxis)
# print(generate_variant_title(v, channel=channel_id, listing=listing_id))
```

---

## 5. Résumé des commandes

| Où        | Commande |
|----------|----------|
| Backend  | `python manage.py migrate` puis `python manage.py runserver 0.0.0.0:8000` |
| Frontend | `cd frontend && npm install && npm run dev` |
| Données  | `python manage.py test_parent_variant_import` (optionnel) |

- **API** : http://localhost:8000/api/v1/
- **Front** : http://localhost:8080 (avec `VITE_API_BASE_URL=http://localhost:8000/api/v1` dans `frontend/.env`)

Pour l’auth (Token / Session), utiliser l’admin Django (`/admin/`) ou les endpoints d’auth du projet si configurés.
