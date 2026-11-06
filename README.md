# Logiciel d'Assurance de Risque Météorologique

Projet d'actuariat — **Polytech Nice Sophia (MAM, parcours IMAFA 2026-2027)**.  
Enseignant : **Marius AKRE**

## Équipe
- Amiel Metier
- *(Membres du groupe)*

---

## Présentation du projet

Dans le cadre d'une création d'offre d'assurance paramétrique, ce projet consiste à réaliser un logiciel permettant à des commerçants de protéger leur résultat d'exploitation contre les aléas météorologiques (notamment la pluie).

Le logiciel s'articule autour de trois volets principaux :
1. **Département Tarification** : tarifer l'assurance demandée en fonction des paramètres client afin de lui garantir un résultat positif ($R \ge 0$) tout au long des 365 jours de l'année.
2. **Département Commercial** : imprimer un devis clair pour le client (approche prospective).
3. **Département R&D** : présenter une analyse rétrospective sur une année passée au choix avec représentation graphique (approche rétrospective).

---

## Modélisation [Section I & II]

### Notations
- $pl_t$ : niveau pluviométrique à la date $t$
- $\overline{pl}$ : niveau de pluie journalier pivot
- $CA$ : chiffre d'affaires journalier maximum possible (avec $CA > Cf$)
- $Cf$ : coûts fixes journaliers (électricité, abonnements, etc.)
- $CA_t^{pl}$ : chiffre d'affaires à la date $t$
- $R_t^{pl}$ : résultat à la date $t$

### Relations
- Facteur d'atténuation du chiffre d'affaires :
  $$f_t^{pl} = \frac{\overline{pl} - pl_t}{\overline{pl}} \quad (0 < pl_t < \overline{pl})$$

- Chiffre d'affaires journalier :
  $$CA_t^{pl} = \begin{cases} 0 & \text{si } pl_t \ge \overline{pl} \\ f_t^{pl} \times CA & \text{si } 0 < pl_t < \overline{pl} \\ CA & \text{si } pl_t = 0 \end{cases}$$

- Résultat journalier :
  $$R_t^{pl} = CA_t^{pl} - Cf$$

- **Seuil de rentabilité journalier** : le résultat est négatif ($R_t^{pl} < 0$) dès que :
  $$pl_t > pl^* = \overline{pl}\left(1 - \frac{Cf}{CA}\right)$$

- **Garantie d'assurance** : indemnité journalière versée pour assurer $R \ge 0$ :
  $$I_t = \max(0, -R_t^{pl})$$

---

## Organisation du code

```
.
├── src/assurance_meteo/
│   ├── __init__.py
│   ├── model.py           # Modélisation commerçant, CA, résultat et indemnités
│   ├── weather.py         # Récupération des données météo (archives et temps réel)
│   ├── pricing.py         # Tarification actuarielle (prime pure et chargements)
│   ├── devis.py           # Édition de devis (Département commercial)
│   └── retrospective.py   # Analyse rétrospective & graphiques (Département R&D)
├── app.py                 # Interface Web / Mobile (Streamlit)
├── notebooks/
│   └── 01_tarification_et_analyse_retrospective.ipynb  # Démonstration du projet
├── data/
│   └── nice_1998_rain.csv # Données pluviométriques de référence (Nice 1998)
├── report/
│   └── figures/           # Dossier pour les exports graphiques
├── requirements.txt       # Dépendances Python
└── README.md
```

---

## Installation et exécution

### Prérequis
Python 3.10 ou supérieur.

```bash
# Création et activation de l'environnement virtuel
python -m venv .venv
source .venv/bin/activate       # Sous Windows : .venv\Scripts\activate

# Installation des dépendances
pip install -r requirements.txt
```

### Lancement de l'application Web (Streamlit)
```bash
streamlit run app.py
```

### Lancement des notebooks
```bash
jupyter lab
```

---

## Calendrier des livrables

- **6 novembre** : Envoi de la composition des groupes.
- **17 novembre** : Présentation de la version DRAFT (10 min).
- **15 décembre** : Présentation finale (10 min) + remise du logiciel/script et du user guide.

---

## Références
- Données météorologiques : [Open-Meteo API](https://open-meteo.com)
- Climatologie France : [Infoclimat](https://www.infoclimat.fr)
- National Centers for Environmental Information : [NOAA / NCEI](https://www.ncei.noaa.gov)
