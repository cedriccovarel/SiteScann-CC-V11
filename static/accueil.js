// Propositions d'adresses : la proposition choisie fixe le point (lat/lon) envoyé à l'analyse.
(() => {
  const form = document.getElementById("formulaire");
  const champ = document.getElementById("adresse");
  const liste = document.getElementById("propositions");
  const cache = ["lat", "lon", "libelle", "code_insee"].map((n) => form.elements[n]);
  let minuterie, propositions = [], actif = -1;

  const effacerPoint = () => cache.forEach((c) => (c.value = ""));
  const fermer = () => { liste.hidden = true; actif = -1; champ.removeAttribute("aria-activedescendant"); };

  function afficher() {
    liste.replaceChildren(...propositions.map((p, i) => {
      const li = document.createElement("li");
      li.id = `prop-${i}`;
      li.setAttribute("role", "option");
      li.setAttribute("aria-selected", String(i === actif));
      li.textContent = p.libelle;
      li.addEventListener("mousedown", (e) => { e.preventDefault(); choisir(i); });
      return li;
    }));
    liste.hidden = propositions.length === 0;
    if (actif >= 0) champ.setAttribute("aria-activedescendant", `prop-${actif}`);
  }

  function choisir(i) {
    const p = propositions[i];
    champ.value = p.libelle;
    [p.lat, p.lon, p.libelle, p.code_insee].forEach((v, k) => (cache[k].value = v ?? ""));
    fermer();
  }

  champ.addEventListener("input", () => {
    effacerPoint();
    clearTimeout(minuterie);
    const q = champ.value.trim();
    if (q.length < 3) { propositions = []; return fermer(); }
    minuterie = setTimeout(async () => {
      try {
        const r = await fetch(`/api/adresses?q=${encodeURIComponent(q)}`);
        propositions = r.ok ? await r.json() : [];
      } catch { propositions = []; }
      actif = -1;
      afficher();
    }, 250);
  });

  champ.addEventListener("keydown", (e) => {
    if (liste.hidden) return;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      actif = (actif + (e.key === "ArrowDown" ? 1 : -1) + propositions.length) % propositions.length;
      afficher();
    } else if (e.key === "Enter" && actif >= 0) {
      e.preventDefault();
      choisir(actif);
    } else if (e.key === "Escape") fermer();
  });
  champ.addEventListener("blur", fermer);
  form.addEventListener("submit", () => {
    form.querySelector("button[type=submit]").disabled = true;
    document.getElementById("attente").hidden = false;
  });
})();
