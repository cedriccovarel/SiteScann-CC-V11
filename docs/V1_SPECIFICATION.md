# Specification fonctionnelle V1

## Objectif

Permettre a un utilisateur PRESTATERRE de saisir une adresse et de generer une pre-analyse de site claire, exportable, autour d'un perimetre de 500 metres.

## Parcours utilisateur

1. L'utilisateur ouvre l'application.
2. Il saisit une adresse complete.
3. L'application geocode l'adresse.
4. L'application interroge les donnees disponibles.
5. Le rapport s'affiche.
6. L'utilisateur exporte en PDF via impression navigateur ou telecharge le XML.

## Donnees V1

| Domaine | Source V1 | Statut |
|---|---|---|
| Adresse | API Adresse | actif |
| Equipements | OpenStreetMap / Overpass | actif |
| Dechets | OpenStreetMap / Overpass | actif |
| Risques | Georisques best-effort | partiel |
| Bruit | Placeholder | V1.1 |
| Zones protegees | Placeholder | V2 |
| Geologie | Placeholder | V2 |
| PLU / SUP | Placeholder | V2 |

## Sorties

- Rapport HTML.
- Export PDF par impression navigateur.
- XML structure.
- API JSON.

## Definition du rapport clair

Le rapport doit contenir :

1. Fiche d'identification.
2. Carte 500 m.
3. Synthese vigilance.
4. Equipements proches.
5. Risques.
6. Bruit et nuisances.
7. Zones protegees.
8. Sols/geologie/eaux.
9. Dechets/tri dans 3 km.
10. Limites et points a verifier.
