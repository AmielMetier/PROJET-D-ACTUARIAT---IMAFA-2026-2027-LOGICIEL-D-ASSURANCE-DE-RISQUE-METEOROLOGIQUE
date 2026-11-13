# Logiciel d'Assurance de Risque Météorologique

Projet d'actuariat — **Polytech Nice Sophia (MAM, parcours IMAFA 2026-2027)**.  
Enseignant : **Marius AKRE**

## Équipe
- Amiel Metier
- Tahitoa Senis
- Nicolas Muratore
- Lucas Diguet
- Gabriel Ferré

---

## Présentation du projet

Dans le cadre d'une création d'offre d'assurance paramétrique, ce projet a pour objectif de concevoir un logiciel complet de couverture contre les aléas météorologiques (notamment le risque de pluie) pour des commerçants dont l'activité dépend directement de la météo.

Le logiciel répond aux exigences des trois départements de la compagnie :
1. **Département Tarification (Pricing)** : calculer la prime d'assurance annuelle garantissant un résultat d'exploitation positif ($R \ge 0$) pour chacun des 365 jours de l'année.
2. **Département Commercial (Devis)** : générer et imprimer un devis contractuel officiel au format **PDF** avec les caractéristiques client et les garanties.
3. **Département R&D (Analyse Rétrospective)** : comparer sur n'importe quelle année passée $a$ le résultat non assuré ($R_{nass}$), le résultat garanti ($R_{ass}$) et la prime payée ($P_a$) à l'aide de représentations graphiques interactives.

Le projet met également l'accent sur les critères de valorisation du barème :
- **Digitalisation & Responsive Web/Mobile** : interface web moderne développée avec **Streamlit** et visualisations **Plotly**.
- **Données Météorologiques en Temps Réel** : interrogation en direct de l'API Open-Meteo (historiques et prévisions mondiales/françaises) avec cache local de résilience.

---

## Modélisation mathématique et actuarielle

### 1. Activité économique du commerçant
Pour une journée $t$, avec une pluviométrie $pl_t$ (en mm) et un seuil pivot $\overline{pl}$ fixé par le commerçant :
- **Chiffre d'affaires journalier ($CA_t^{pl}$)** :
  $$CA_t^{pl} = \begin{cases} 0 & \text{si } pl_t \ge \overline{pl} \\ f_t^{pl} \times CA & \text{si } 0 < pl_t < \overline{pl} \\ CA & \text{si } pl_t = 0 \end{cases} \quad \text{avec } f_t^{pl} = \frac{\overline{pl} - pl_t}{\overline{pl}}$$
- **Résultat journalier ($R_t^{pl}$)** avec coûts fixes journaliers incompressibles $Cf$ ($CA > Cf$) :
  $$R_t^{pl} = CA_t^{pl} - Cf$$

### 2. Seuil de rentabilité journalier
Le commerçant subit une perte d'exploitation ($R_t^{pl} < 0$) dès que la pluie franchit le seuil critique :
$$pl^* = \overline{pl} \left(1 - \frac{Cf}{CA}\right)$$

### 3. Couverture d'assurance et indemnisation
Le contrat garantit un résultat journalier positif ou nul ($R \ge 0$). L'indemnité journalière versée par l'assureur est donc :
$$I_t = \max(0, -R_t^{pl})$$

Sur l'ensemble des 365 jours, le résultat non assuré et le résultat garanti brut sont :
$$R_{nass} = \sum_{t=1}^{365} R_t^{pl}, \qquad R_{ass} = \sum_{t=1}^{365} (R_t^{pl} + I_t) = R_{nass} + \sum_{t=1}^{365} I_t$$

### 4. Tarification prospective (Pricing)
La **prime pure technique** $\mathbb{E}[I]$ correspond à l'espérance mathématique des indemnités annuelles estimée sur l'historique climatique :
$$P_{pure} = \mathbb{E}\left[\sum_{t=1}^{365} I_t\right]$$
La prime commerciale annuelle $P$ intègre un chargement de sécurité actuariel lié à la volatilité climatique et des frais de gestion/marge commerciale :
$$P = \frac{P_{pure} + \beta \cdot P_{pure}}{1 - \alpha}$$
*(où $\beta$ est le taux de chargement de sécurité et $\alpha$ le taux de frais de gestion).*

---

## Organisation du code

```
.
├── src/
│   ├── __init__.py
│   ├── simulation.py      # Modèle client, CA journalier, résultat et calcul des indemnités
│   ├── pricing.py         # Tarification actuarielle (prime pure, écart-type, chargements)
│   ├── weather_api.py     # API météo Open-Meteo temps réel & archives avec cache local
│   ├── pdf_generator.py   # Générateur de devis officiel au format PDF (ReportLab)
│   ├── backtesting.py     # Analyse rétrospective R_nass vs R_ass et P
│   └── visualisations.py  # Graphiques interactifs (Plotly)
├── app.py                 # Interface Web & Mobile complète (Streamlit)
├── notebooks/
│   └── 01_tarification_et_analyse_retrospective.ipynb  # Démonstration et validation pas-à-pas
├── tests/
│   ├── __init__.py
│   └── test_pricing.py    # Tests unitaires automatisés (Pytest)
├── data/
│   └── nice_1998_rain.csv # Données pluviométriques réelles de référence (Nice 1998)
├── docs/
│   └── USER_GUIDE.md      # Manuel d'utilisation complet du logiciel
├── PROJET-ACTUARIAT- LOGICIEL D ASSURANCE DE RISQUE METEOROLOGIQUE.pdf # Sujet officiel
├── requirements.txt       # Dépendances Python
└── README.md
```

---

## Installation et démarrage rapide

### Prérequis
Python 3.10 ou supérieur.

```bash
# 1. Cloner le dépôt
git clone https://github.com/AmielMetier/PROJET-D-ACTUARIAT---IMAFA-2026-2027-LOGICIEL-D-ASSURANCE-DE-RISQUE-METEOROLOGIQUE.git
cd PROJET-D-ACTUARIAT---IMAFA-2026-2027-LOGICIEL-D-ASSURANCE-DE-RISQUE-METEOROLOGIQUE

# 2. Créer et activer l'environnement virtuel
python -m venv .venv
source .venv/bin/activate       # Sous Windows : .venv\Scripts\activate

# 3. Installer les dépendances
pip install -r requirements.txt
```

### Lancement de l'Application Web (Streamlit)
```bash
streamlit run app.py
```
L'application s'ouvre à l'adresse `http://localhost:8501`. Elle propose :
- La configuration du commerçant (CA, Coûts fixes, Pluie pivot, Ville).
- La tarification prospective avec téléchargement du **Devis officiel en PDF**.
- L'analyse rétrospective interactive avec courbes temporelles et graphiques de comparaison.
- Le guide d'utilisation intégré.

### Lancement des Notebooks
```bash
jupyter lab notebooks/01_tarification_et_analyse_retrospective.ipynb
```

### Exécution des Tests Unitaires
```bash
pytest tests/
```

---

## Exemple d'analyse rétrospective (Nice, 1998)

Conformément à l'exemple chiffré du sujet :
- **Paramètres client** : Ville de Nice, $\overline{pl} = 10\text{ mm}$, $CA = 1\,000\text{ €/j}$, $Cf = 400\text{ €/j}$ (seuil de perte $pl^* = 6\text{ mm/j}$).
- **Résultat non assuré ($R_{nass}^{1998}$)** : $\approx 90\,000\text{ €}$.
- **Prime payée a priori ($P^{1998}$)** : $3\,000\text{ €}$.
- **Pertes réelles évitées grâce à l'assurance** : $\approx 5\,000\text{ €}$.
- **Résultat net assuré ($R_{ass} - P$)** : $\approx 92\,000\text{ €}$.

**Conclusion rétrospective** : S'assurer en 1998 a été nettement favorable au commerçant, la prime payée a priori ($3\,000\text{ €}$) étant inférieure aux pertes réelles générées par les intempéries ($5\,000\text{ €}$).

---

## Calendrier des livrables

- **6 novembre 2026** : Envoi de la composition des groupes.
- **17 novembre 2026** : Présentation de la version DRAFT (10 min).
- **15 décembre 2026** : Présentation finale (10 min) et remise du livrable (code/logiciel + user guide).

---

## Sources et références
- Données historiques & prévisions en temps réel : [Open-Meteo API](https://open-meteo.com)
- Climatologie France : [Infoclimat](https://www.infoclimat.fr)
- National Centers for Environmental Information : [NOAA / NCEI](https://www.ncei.noaa.gov)
