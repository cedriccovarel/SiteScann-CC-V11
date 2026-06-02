# Specification fonctionnelle V1.1

## Parcours utilisateur

1. Saisie adresse, reference cadastrale optionnelle, type de batiment, surface.
2. Geocodage BAN.
3. Collecte OSM/Overpass : equipements 500 m, dechets 3 km, routes/rail/nuisances 700 m, paysage 500 m, protections 1200 m.
4. Collecte Georisques best effort.
5. Normalisation des risques en tableau : theme, presence, niveau, commentaire.
6. Calcul d'un indicateur mobilite 0-100.
7. Rapport HTML avec carte, tableaux, alertes, limites.
8. Export XML et GeoJSON.

## Rubriques du rapport

- Identification.
- Synthese operationnelle.
- Carte 500 m.
- Risques naturels et technologiques.
- Mobilite / ecomobilite.
- Voies d'acces et equipements.
- Bruit / nuisances.
- Orientation, paysage, eau, vegetal.
- Zones protegees, patrimoine, Natura 2000, TVB.
- Sols, geologie, eaux souterraines.
- Urbanisme, PLU, servitudes.
- Dechets, traitement, tri.
- Limites.

## V1.2 recommandee

- Cadastre automatique par parcelle.
- PDF serveur avec Playwright.
- Cache API et historique.
- Integration couches officielles bruit / BRGM / GPU / INPN / Atlas patrimoine.
- Normalisation fiable par schema de donnees officiel par endpoint.
