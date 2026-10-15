FORM = {"adresse": "1 place Bellecour Lyon", "lat": "", "lon": "", "libelle": "", "code_insee": "",
        "reference_cadastrale": "", "type_projet": "neuf"}


def lignes(analyse):
    return {l["libelle"]: l for ex in analyse["exigences"] for r in ex["rubriques"] for l in r["lignes"]}


def test_rapport_html(web):
    r = web.post("/analyse", data=FORM)
    assert r.status_code == 200
    page = r.text
    for attendu in ("1.1.1", "Schéma de fonctionnement", "Bellecour", "Rives du Rhône", "Église Saint-Nizier",
                    "Zone UA", "Parcelle 69382 AB 0045", "Inondation, Séisme"):
        assert attendu in page, attendu
    assert "<script>alert(1)</script>" not in page.split('id="donnees"')[0]   # nom OSM échappé dans le HTML
    assert "&lt;script&gt;" in page


def test_analyse_json_neuf(web):
    a = web.post("/api/analyse", json={"adresse": "1 place Bellecour Lyon"}).json()
    assert [ex["cle"] for ex in a["exigences"]] == ["analyse_site", "eco_mobilite", "modes_doux",
                                                     "localisation_seniors", "dechets_menagers"]
    l = lignes(a)
    assert l["Transports en commun à moins de 500 m"]["statut"] == "indicatif"
    assert l["Aménagement cyclable à moins de 1 km"]["resultat"].endswith("à 700 m (vol d'oiseau)")
    assert l["Commerces de base (épicerie, boulangerie, pharmacie) à moins de 500 m"]["elements"][0]["distance_m"] == 300
    assert l["Services de soin à moins de 1 km"]["statut"] == "indicatif"
    assert l["Établissement scolaire / crèche"]["statut"] == "absent"
    casias = next(v for k, v in l.items() if k.startswith("Anciens sites industriels"))
    assert casias["statut"] == "indisponible"                                  # panne simulée : pas « rien trouvé »
    assert any("Certaines sources" in x for x in a["alertes"])
    assert {s["nom"] for s in a["sources"] if not s["ok"]} == {"Géorisques /ssp/casias"}


def test_renovation(web):
    a = web.post("/api/analyse", json={"adresse": "x", "lat": 45.76, "lon": 4.835, "type_projet": "renovation"}).json()
    cles = [ex["cle"] for ex in a["exigences"]]
    assert "acoustique_avant_travaux" in cles and "modes_doux" not in cles
    assert a["exigences"][0]["referentiel"] == "BEE Logement Rénovation"


def test_overpass_en_panne(web):
    web.pannes.add("/api/interpreter")
    a = web.post("/api/analyse", json={"adresse": "1 place Bellecour Lyon"}).json()
    assert lignes(a)["Transports en commun"]["statut"] == "indisponible"
    assert lignes(a)["Zonage sismique"]["statut"] == "donnee"


def test_adresse_introuvable(web):
    web.pannes.add("/geocodage/search")
    r = web.post("/analyse", data=FORM)
    assert r.status_code == 200 and "Adresse introuvable" in r.text


def test_reference_cadastrale_centre_l_analyse(web):
    a = web.post("/api/analyse", json={"reference_cadastrale": "69382 AB 45"}).json()
    assert a["parcelle"]["properties"]["numero"] == "0045"
    assert abs(a["lieu"]["lat"] - 45.76) < 1e-6


def test_propositions_adresses(web):
    r = web.get("/api/adresses", params={"q": "bellecour"})
    assert r.json()[0]["code_insee"] == "69382"
