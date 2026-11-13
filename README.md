# Projet d'Actuariat - IMAFA 2026-2027
## Logiciel d'Assurance de Risque Météorologique

Application de tarification, d'émission de devis et d'analyse rétrospective pour l'assurance indicielle de risque pluviométrique.

### Fonctionnalités Clés
- **Digitalisation & Responsive Web/Mobile** : interface Streamlit utilisable depuis un navigateur d'ordinateur ou de téléphone.
- **Données Météorologiques Temps Réel** : précipitations journalières téléchargées au moment du calcul depuis l'API Open-Meteo (réanalyses ERA5, point de grille le plus proche de la ville), sans clé d'API.
- **Modélisation Actuarielle** : prime pure, écart-type, VaR 95 %, chargement de sécurité β·σ (principe de l'écart-type) et prime commerciale, sur les 365 jours suivant la date de souscription.
- **Émission de Devis PDF** : devis avec bloc assureur, identité du client, garantie, détail de la prime et zone de signature.
- **Analyse Rétrospective** : backtesting sur une année passée $a$ (prime calculée a priori) et sur plusieurs années (ratio sinistres / primes, part des années favorables au client), avec graphiques Plotly.

### Démarrage Rapide

```bash
# 1. Installation des dépendances (Python 3.11)
pip install -r requirements.txt

# 2. Lancement de l'application
streamlit run app.py

# 3. Tests automatisés
python -m pytest tests/
```

### Organisation du code

| Fichier | Rôle |
|---|---|
| `app.py` | Interface Streamlit (barre latérale, onglets Tarification, Rétrospective, Guide) |
| `src/simulation.py` | Formules du sujet : CA, résultat et indemnité journaliers |
| `src/pricing.py` | Périodes de couverture de 365 jours et calcul de la prime |
| `src/backtesting.py` | Analyse rétrospective sur une ou plusieurs années |
| `src/weather_api.py` | Géocodage et téléchargement des précipitations (Open-Meteo) |
| `src/pdf_generator.py` | Devis PDF |
| `src/visualisations.py` | Graphiques Plotly |
| `src/formatting.py` | Affichage des montants au format français |

Pour la documentation complète, les formules et les limites de la source météo, consultez le [Manuel d'Utilisation](docs/USER_GUIDE.md).
