# SiteScan PRESTATERRE V1.1

Maquette exploitable de pre-analyse de site a partir d'une adresse.

## Objectif

Permettre a un utilisateur de saisir une adresse et de generer un rapport clair couvrant :

- identification du site et carte 500 m ;
- equipements, commerces, ecoles, sante, transports ;
- voies d'acces ;
- dechets / tri dans un rayon de 3 km ;
- risques naturels et technologiques via Georisques, avec normalisation informative ;
- bruit / nuisances par detection indirecte OSM ;
- pre-score de mobilite / ecomobilite ;
- paysage, eau, vegetation ;
- zones protegees / patrimoine detectables OSM ;
- rubriques preparees pour BRGM/InfoTerre, eaux souterraines, PLU/SUP, Natura 2000, TVB.

## Lancement GitHub Codespaces

```bash
bash start.sh
```

Si besoin :

```bash
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Ouvrir ensuite le port 8000 dans l'onglet Ports de Codespaces.

## Lancement local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload
```

Puis ouvrir : http://127.0.0.1:8000

## Exports

- HTML imprimable en PDF depuis le navigateur.
- XML structure.
- GeoJSON des points collectes.
- API JSON : `POST /api/analyse`.

## Statut des donnees

### Actif en V1.1

- API Adresse / BAN pour geocodage.
- Overpass / OpenStreetMap pour equipements, transports, commerces, sante, nuisances, voies, dechets, paysage, protections/patrimoine OSM.
- Georisques en best effort + normalisation informative.
- Score mobilite indicatif inspire de la logique Effinergie Ecomobilite.

### Prepare mais non opposable en V1.1

- Bruit dB : detection indirecte uniquement. A raccorder aux cartes strategiques du bruit, PEB et classement sonore officiel.
- BRGM / InfoTerre : rubrique preparee, connecteur WMS/WFS ou couches prechargees a integrer.
- Eaux souterraines : rubrique preparee, SANDRE/Eaufrance/BDLISA a raccorder.
- Urbanisme : rubrique preparee, Geoportail de l'Urbanisme a raccorder.
- Natura 2000 / ZNIEFF / TVB : detection OSM partielle, connecteurs officiels a integrer.
- Cadastre : champ reference disponible, geocodage parcelle complet a integrer via API Carto / Cadastre.

## Limite importante

Cette V1.1 est une maquette exploitable de pre-analyse. Elle ne remplace pas une etude reglementaire, acoustique, geotechnique, environnementale, ni une verification urbanistique opposable.
