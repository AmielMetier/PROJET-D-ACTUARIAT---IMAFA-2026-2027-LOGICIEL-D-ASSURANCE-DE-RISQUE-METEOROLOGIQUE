# Manuel d'Utilisation (User Guide)
## Logiciel d'Assurance de Risque Météorologique
**Master IMAFA 2026-2027 — Marius AKRE**

---

### 1. Présentation du Logiciel

Le logiciel permet à une compagnie ou un courtier d'assurance de tarifer et de simuler des contrats d'assurance indicielle (paramétrique) contre les aléas pluviométriques pour des commerçants dont l'activité dépend de la météo.

Il intègre 3 volets fondamentaux :
1. **Département Tarification (Pricing)** : Tarification prospective de la prime pure et commerciale grâce aux données météorologiques réelles interrogées en temps réel.
2. **Département Commercial (Devis)** : Génération automatisée et impression d'un devis contractuel au format PDF.
3. **Département R&D (Analyse Rétrospective / Backtesting)** : Évaluation a posteriori sur n'importe quelle année passée $a$ pour vérifier la rentabilité de l'assurance pour le client et visualiser les trajectoires de résultats.

---

### 2. Installation & Démarrage

#### Prérequis
- Python 3.10 ou supérieur
- Connexion Internet (pour la récupération temps réel des séries météo)

#### Installation des dépendances
Dans un terminal à la racine du projet :
```bash
pip install -r requirements.txt
```

#### Lancement de l'Application Web
```bash
streamlit run app.py
```
L'interface s'ouvre automatiquement dans votre navigateur par défaut à l'adresse `http://localhost:8501`. L'interface est conçue pour être "responsive" et utilisable sur ordinateur comme sur smartphone/tablette.

---

### 3. Guide Pas à Pas

#### Étape 1 : Saisie du Profil Client (Volet Latéral)
Dans la barre latérale gauche, renseignez les paramètres du commerçant :
- **Ville du commerce** (ex: *Nice*, *Marseille*, *Bordeaux*...)
- **Chiffre d'affaires journalier maximal ($CA$)** : réalisé par temps sec.
- **Coûts fixes journaliers ($Cf$)** : frais incompressibles quotidiens ($CA > Cf$).
- **Niveau de pluie pivot ($\bar{pl}$)** : seuil journalier en millimètres au-delà duquel l'activité s'arrête ($CA = 0$).
- **Date de souscription**.

> Le logiciel calcule immédiatement le **seuil critique de perte journalière** :
> $$pl_{\text{seuil}} = \bar{pl} \times \left(1 - \frac{Cf}{CA}\right)$$

#### Étape 2 : Tarification Prospective & Devis (Onglet 1)
1. Ajustez si souhaité le nombre d'années d'historique (5 à 30 ans), le chargement de sécurité et les frais de gestion.
2. Cliquez sur **"Récupérer les données météo temps réel & Calculer la prime"**.
3. Les métriques actuarielles s'affichent :
   - Prime pure technique $\mathbb{E}[I]$
   - Écart-type des sinistres annuels
   - Charge de sinistralité maximale historique
   - Prime commerciale finale
4. Cliquez sur **"Télécharger le Devis Officiel (PDF)"** pour obtenir le document prêt à être signé.

#### Étape 3 : Analyse Rétrospective / Backtesting (Onglet 2)
1. Choisissez une année passée $a$ (ex: 1998).
2. Indiquez la prime annuelle $P_a$ qui aurait été payée au début de l'année $a$.
3. Cliquez sur **"Lancer l'analyse rétrospective"**.
4. Le logiciel affiche la comparaison chiffrée ($R_{nass}$, $R_{ass}$, $P_a$, $R_{net}$) et deux graphiques interactifs :
   - Comparatif en barres des agrégats annuels.
   - Évolution temporelle cumulée jour par jour sur les 365 jours.

---

### 4. Tests Unitaires & Validation

Pour lancer la suite de tests automatisés :
```bash
pytest tests/
```
