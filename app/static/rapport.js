// Schéma de fonctionnement du site (500 m) et exports, à partir des données intégrées à la page.
(() => {
  const donnees = JSON.parse(document.getElementById("donnees").textContent);
  const legende = JSON.parse(document.getElementById("legende-categories").textContent);
  const { lat, lon, libelle } = donnees.lieu;

  const conteneur = document.getElementById("carte");
  if (conteneur && window.L) {
    const carte = L.map(conteneur, { scrollWheelZoom: false }).setView([lat, lon], 16);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19, attribution: "&copy; contributeurs OpenStreetMap",
    }).addTo(carte);
    L.control.scale({ imperial: false }).addTo(carte);

    const nord = L.control({ position: "topright" });
    nord.onAdd = () => Object.assign(L.DomUtil.create("div", "nord"), { textContent: "N ↑", title: "Nord" });
    nord.addTo(carte);

    const cercle = L.circle([lat, lon], { radius: 500, color: "#1b2631", weight: 1.5, dashArray: "6 6", fill: false }).addTo(carte);
    if (donnees.parcelle) L.geoJSON(donnees.parcelle, { style: { color: "#000", weight: 3, fillOpacity: 0.15 } }).addTo(carte);
    L.circleMarker([lat, lon], { radius: 7, color: "#000", fillColor: "#f1c40f", fillOpacity: 1 })
      .addTo(carte).bindTooltip("Site du projet");

    // Une couche par catégorie présente dans les 500 m (les objets plus lointains restent dans les tableaux).
    const couches = {};
    for (const e of donnees.elements) {
      if (e.distance_m > 500) continue;
      const style = legende[e.categorie];
      const couche = (couches[e.categorie] ??= L.layerGroup().addTo(carte));
      const texte = `${e.nom || style.libelle} – ${e.distance_m} m`;
      const forme = e.geometrie
        ? L.geoJSON(e.geometrie, {
            style: { color: style.couleur, weight: 3, fillOpacity: 0.2 },
            pointToLayer: (_, ll) => L.circleMarker(ll, { radius: 4 }),
          })
        : L.circleMarker([e.lat, e.lon], { radius: 5, color: style.couleur, fillOpacity: 0.8 });
      // Nœud texte et non chaîne : Leaflet insère les chaînes en HTML, les noms OSM ne doivent pas l'être.
      forme.bindTooltip(Object.assign(document.createElement("span"), { textContent: texte })).addTo(couche);
    }
    carte.fitBounds(cercle.getBounds());

    const ul = document.getElementById("legende");
    for (const [cle, couche] of Object.entries(couches)) {
      const li = document.createElement("li");
      const case_ = Object.assign(document.createElement("input"), { type: "checkbox", checked: true });
      case_.addEventListener("change", () => (case_.checked ? couche.addTo(carte) : couche.remove()));
      const pastille = Object.assign(document.createElement("span"), { className: "pastille" });
      pastille.style.background = legende[cle].couleur;
      const label = document.createElement("label");
      label.append(case_, pastille, legende[cle].libelle);
      li.append(label);
      ul.append(li);
    }
  }

  function telecharger(nom, contenu, type) {
    const url = URL.createObjectURL(new Blob([JSON.stringify(contenu, null, 2)], { type }));
    Object.assign(document.createElement("a"), { href: url, download: nom }).click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  const base = `analyse-site-${donnees.date.slice(0, 10)}`;
  const exports = {
    json: () => telecharger(`${base}.json`, donnees, "application/json"),
    geojson: () => telecharger(`${base}.geojson`, {
      type: "FeatureCollection",
      features: [
        { type: "Feature", geometry: { type: "Point", coordinates: [lon, lat] }, properties: { categorie: "site", nom: libelle } },
        ...(donnees.parcelle ? [{ ...donnees.parcelle, properties: { categorie: "parcelle", ...donnees.parcelle.properties } }] : []),
        ...donnees.elements.map((e) => ({
          type: "Feature",
          geometry: e.geometrie ?? { type: "Point", coordinates: [e.lon, e.lat] },
          properties: { categorie: e.categorie, libelle: legende[e.categorie].libelle, nom: e.nom, distance_m: e.distance_m, source: e.source },
        })),
      ],
    }, "application/geo+json"),
  };
  document.querySelectorAll("[data-export]").forEach((b) => b.addEventListener("click", exports[b.dataset.export]));
})();
