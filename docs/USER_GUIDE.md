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
- Python 3.11 (versions des bibliothèques figées dans `requirements.txt`)
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

#### Étape 1 : Profil client et paramètres (barre latérale)
Dans la barre latérale gauche, renseignez les paramètres du commerçant :
- **Ville du commerce** : choisissez-la dans le menu déroulant (44 grandes villes françaises, triées par ordre alphabétique ; tapez les premières lettres pour filtrer la liste). Si la ville n'y figure pas, tapez son nom en entier puis validez avec Entrée : n'importe quelle ville reconnue par le service météo est acceptée (ex. *Lorient*).
  - La recherche se fait d'abord **en France**, puis dans le monde entier si rien n'est trouvé ; en cas d'homonymes, la commune la plus peuplée est retenue.
  - La localité retenue et ses coordonnées s'affichent sous le champ (« Point de grille météo ») : vérifiez-la avant de tarifer.
- **Chiffre d'affaires journalier maximal ($CA$)** : réalisé par temps sec.
- **Coûts fixes journaliers ($Cf$)** : frais incompressibles quotidiens. Le champ est automatiquement limité à $CA - 1$ € ($CA > Cf$).
- **Niveau de pluie pivot ($\bar{pl}$)** : seuil journalier en millimètres au-delà duquel l'activité s'arrête ($CA = 0$).
- **Date de souscription** (aujourd'hui ou plus tard).

> Le logiciel calcule immédiatement le **seuil critique de perte journalière** :
> $$pl_{\text{seuil}} = \bar{pl} \times \left(1 - \frac{Cf}{CA}\right)$$

Plus bas, la rubrique **Paramètres actuariels** sert aux deux onglets de calcul :
- **Années d'historique** (5 à 30) utilisées pour estimer la prime ;
- **Chargement de sécurité β** : multiplicateur de l'écart-type des indemnités annuelles (0,30 par défaut) ;
- **Frais de gestion et marge** (en % de la prime commerciale).

#### Étape 2 : Tarification prospective et devis (onglet 1)
1. Cliquez sur **« Récupérer les données météo temps réel & Calculer la prime »**.
   - Le contrat couvre les **365 jours à partir de la date de souscription**.
   - La prime est estimée sur les périodes équivalentes des années passées : pour une souscription au 13/11, chaque année d'historique va du 13/11 au 12/11 suivant. Chaque période compte **365 jours**, comme le contrat, même si elle contient un 29 février. Seules les périodes complètes sont retenues.
   - Les jours sans donnée météo sont comptés comme secs et signalés par un avertissement ; une période où plus de 5 % des jours manquent est écartée.
2. Les indicateurs actuariels s'affichent :
   - prime pure $E[I]$ (moyenne des indemnités annuelles) et écart-type $\sigma(I)$ ;
   - **VaR 95 %** (indemnités annuelles dépassées une année sur vingt en moyenne) et pire année historique ;
   - chargement de sécurité $\beta \cdot \sigma(I)$ et prime commerciale :
   $$P = \frac{E[I] + \beta\,\sigma(I)}{1 - \text{frais}}$$
   Ce **principe de l'écart-type** fait payer davantage un risque irrégulier qu'un risque stable de même moyenne.
3. Saisissez le **nom du client** et la **raison sociale** du commerce, puis cliquez sur **« Télécharger le Devis »**. Le PDF contient : le bloc assureur, la référence unique (`DEV-AAAAMMJJ-XXXXXX`) et la date de validité, les données du souscripteur, la garantie, le détail de la prime et une **zone de signature** pour chaque partie.

> Si vous modifiez un paramètre (profil client ou paramètres actuariels) après le calcul, le devis est masqué jusqu'à ce que vous recalculiez la prime : un devis ne peut donc jamais associer un profil à la prime d'un autre. Le nom et la raison sociale, eux, peuvent être changés sans recalcul.
>
> Si le service météo est injoignable, le logiciel réessaie 3 fois puis affiche un message d'erreur au lieu de planter.

#### Étape 3 : Analyse rétrospective (onglet 2)
**A. Une année passée $a$**
1. Choisissez une année (ex. 1998 ; les archives commencent en 1940).
2. Cliquez sur **« Lancer l'analyse rétrospective »**. La prime $P_a$ n'est pas à saisir : le logiciel la calcule **a priori**, comme au 1er janvier de $a$, avec les seules années antérieures (et les paramètres actuariels de la barre latérale).
3. Le logiciel affiche $R_{nass}$, $R_{ass}$, $P_a$, $R_{ass} - P_a$, la conclusion (assurance favorable ou non) et deux graphiques : le bilan annuel en barres et la trajectoire cumulée jour par jour.

**B. Sur plusieurs années**
1. Choisissez une plage d'années (25 dernières années par défaut) et lancez l'analyse.
2. Chaque année est tarifée a priori puis comparée aux indemnités réellement versées. Le logiciel affiche :
   - le **ratio sinistres / primes (S/P)** : indemnités versées divisées par primes encaissées. Sous 100 %, le produit est rentable pour l'assureur ;
   - la **part des années favorables** au client (indemnités supérieures à la prime) ;
   - le gain cumulé du client, les totaux de primes et d'indemnités ;
   - un graphique prime contre indemnités année par année, et le tableau détaillé.

> Les résultats restent affichés tant que les paramètres qui les influencent ne changent pas (vous pouvez passer d'un onglet à l'autre ou remplir le devis sans les perdre). Si un paramètre change, un message invite à relancer l'analyse.

---

### 4. Source des données météo et limites

Les précipitations sont téléchargées au moment du calcul depuis **Open-Meteo** (API gratuite, sans clé), qui s'appuie sur les **réanalyses ERA5 et ERA5-Land** du centre européen ECMWF.

- Ce ne sont **pas les relevés d'une station au sol** : ce sont des valeurs calculées sur un **point de grille** d'environ 10 à 25 km de côté, le plus proche de la ville choisie. Le logiciel parle donc de « point de grille », pas de station.
- Les réanalyses ont tendance à **lisser les fortes pluies** (les orages locaux sont sous-estimés) et à compter **trop de jours de pluie faible** (bruine répartie sur toute la maille).
- Dans ce modèle, **toute pluie réduit le chiffre d'affaires** et seuls les jours au-delà du seuil critique déclenchent une indemnité : le nombre de jours pluvieux et l'intensité des épisodes pèsent donc directement sur la prime. Selon la ville, le premier biais tend à sous-estimer la prime, le second peut la surestimer.
- Pour un usage réel, il faudrait comparer ces séries avec des relevés de station (Météo-France, [Infoclimat](https://www.infoclimat.fr), [NCEI](https://www.ncei.noaa.gov), cités par le sujet) et, si besoin, les corriger.

---

### 5. Tests Unitaires & Validation

Pour lancer la suite de tests automatisés (ils fonctionnent sans connexion Internet) :
```bash
python -m pytest tests/ -v
```
