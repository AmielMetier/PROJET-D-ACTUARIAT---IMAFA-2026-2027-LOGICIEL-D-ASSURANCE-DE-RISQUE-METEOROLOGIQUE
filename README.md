# Projet d'Actuariat - IMAFA 2026-2027
## Logiciel d'Assurance de Risque Météorologique

Application de tarification, d'émission de devis et d'analyse rétrospective pour l'assurance indicielle de risque pluviométrique.

### 🌟 Fonctionnalités Clés
- **Digitalisation & Responsive Web/Mobile** : Interface complète propulsée par Streamlit.
- **Données Météorologiques Temps Réel** : Connexion à l'API Open-Meteo pour interroger l'historique de précipitations de n'importe quelle ville sans clé d'API requise.
- **Modélisation Actuarielle** : Calcul de la prime pure, écart-type, chargement de sécurité et prime commerciale.
- **Émission de Devis PDF** : Devis imprimable conforme aux exigences du département commercial.
- **Analyse Rétrospective Interactive** : Backtesting sur n'importe quelle année passée $a$ avec visualisations graphiques (Plotly).

### 🚀 Démarrage Rapide

```bash
# 1. Installation des dépendances
pip install -r requirements.txt

# 2. Lancement de l'application
streamlit run app.py
```

Pour la documentation complète et les instructions pas à pas, consultez le [Manuel d'Utilisation](docs/USER_GUIDE.md).
