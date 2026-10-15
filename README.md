# SiteScan Prestaterre

Pré-analyse de site urbain à partir d'une adresse ou d'une référence cadastrale. Le rapport suit, rubrique par
rubrique, l'exigence **« Analyse de site » du référentiel BEE Logement (Neuf ou Rénovation)** et les exigences qui
dépendent de la localisation :

| Exigence BEE | Neuf | Rénovation | Ce que fait SiteScan |
|---|---|---|---|
| Analyse de site | 1.1.1 | 1.1.1 | Les 5 rubriques du référentiel, avec schéma 500 m, contraintes, services à 1 km, déchets à 3 km, sols |
| Potentiel d'éco-mobilité | 1.1.5 | 1.1.5 | Rappelle le questionnaire officiel à renseigner (aucun score inventé) |
| Proximité des modes doux | 4.8.1 | – | Transports en commun et aménagements cyclables à moins de 1 km |
| Localisation du site (séniors) | 4.10.2 | – | Transports et commerces de base à moins de 500 m, soins à moins de 1 km |
| Traitement collectif des déchets ménagers | 4.2.1 | 4.2.1 | Compostage partagé et apport volontaire à proximité |
| Acoustique extérieure avant travaux | – | 1.1.6 | Rappelle la mesure à produire, renvoie aux sources de bruit |

Les textes, versions et pièces justificatives affichés viennent de `app/referentiel/bee.json`, extrait du catalogue
d'exigences de l'Observatoire Prestaterre. Les seuils de distance sont ceux de ces textes.

## Statut de chaque ligne

Chaque ligne du rapport indique d'où vient l'information :

- **Donnée officielle** : réponse d'une base publique (Géorisques, cadastre, Géoportail de l'Urbanisme, INPN via API Carto) ;
- **Indicatif (OpenStreetMap)** : données contributives, à confirmer ;
- **Rien trouvé – à vérifier** : la source a répondu sans résultat, ce qui n'est pas une preuve d'absence ;
- **À compléter** : ne peut pas être produit automatiquement aujourd'hui (orientation des façades, TVB, géologie…) ;
- **Source indisponible** : la source n'a pas répondu ou a renvoyé un format inattendu. Rien n'est deviné.

## Sources

| Source | Usage |
|---|---|
| Géocodage Géoplateforme IGN (BAN) | Adresse → point, avec propositions au fil de la saisie |
| API Carto IGN – cadastre | Parcelle sous le point ou depuis la référence saisie |
| API Carto IGN – nature | Natura 2000 (Habitats, Oiseaux), ZNIEFF I et II dans 500 m |
| API Carto IGN – Géoportail de l'Urbanisme | Zonage du PLU au point, servitudes (dont AC1 monuments historiques) |
| Géorisques API v1 | Zonage sismique, argiles, radon, risques communaux (GASPAR), ICPE, cavités, mouvements de terrain, SIS, CASIAS, ex-BASOL |
| OpenStreetMap (Overpass) | Une requête : voies, nuisances, paysage, commerces, transports, santé, écoles, cyclable, déchets |

Les distances sont mesurées à vol d'oiseau jusqu'au point le plus proche de chaque objet (une route qui passe à 20 m
est à 20 m, même si elle est longue). Toutes les sources sont interrogées en parallèle, et les réponses sont gardées
24 h en mémoire. **Rien n'est stocké sur le serveur** : les exports JSON et GeoJSON sont générés dans le navigateur.

## À raccorder ensuite

Classement sonore des voies et cartes de bruit, TVB régionale (SRCE/SRADDET), géologie (BRGM), eaux souterraines
(Hub'Eau, BDLISA), transports scolaires, orientation des façades à partir de l'emprise du bâtiment.
Les adresses et formats des endpoints Géorisques et API Carto sont à confirmer lors du premier essai réel :
une réponse inattendue s'affiche « Source indisponible », jamais comme une absence de risque.

## Lancer

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload        # http://127.0.0.1:8000
pytest                               # tests sur services simulés, sans réseau
```

API : `POST /api/analyse` avec `{"adresse": "…", "type_projet": "neuf" | "renovation"}` (ou `reference_cadastrale`,
ou `lat`/`lon`). Les URL des services se changent par variables d'environnement (voir `app/config.py`).

## Mettre à jour le référentiel

```bash
python scripts/extraire_referentiel.py ../observatoire-prestaterre-beta/requirements_catalog.json
```

## Organisation du code

```
app/
  main.py            routes (accueil, propositions d'adresses, analyse HTML et JSON)
  analyse.py         collecte en parallèle puis construction du rapport, exigence par exigence
  sources/           un module par fournisseur (geocodage, apicarto, georisques, osm)
  http.py            client HTTP unique : cache, gestion des erreurs, journal des sources
  geo.py             distances et géométries en mètres autour du site
  referentiel/       bee.json, extrait du catalogue de l'Observatoire
  templates/ static/ rapport imprimable, schéma Leaflet (servi localement)
tests/               services simulés et tests
```

Les catégories OpenStreetMap sont définies une seule fois (`app/sources/osm.py`, table `CATEGORIES`) :
la même table écrit la requête Overpass, classe les objets reçus et produit la légende du schéma.

Pré-analyse à partir de données publiques : elle ne remplace ni les études réglementaires, acoustiques,
géotechniques ou environnementales, ni la consultation des documents opposables.
