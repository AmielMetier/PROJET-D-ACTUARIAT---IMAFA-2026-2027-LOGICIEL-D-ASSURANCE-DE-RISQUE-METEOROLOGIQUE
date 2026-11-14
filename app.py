"""
Application Web de Tarification & d'Analyse d'Assurance Météorologique.
Projet d'Actuariat - IMAFA 2026-2027.
"""

from datetime import date, timedelta
import streamlit as st
import pandas as pd

from src.simulation import ClientProfile
from src.pricing import price_contract_historical, split_into_coverage_periods, coverage_end
from src.backtesting import run_retrospective_analysis, run_multi_year_backtest
from src.visualisations import plot_retrospective_comparison, plot_cumulative_results, plot_multi_year_backtest
from src.pdf_generator import generate_devis_pdf, make_quote_ref
from src.weather_api import get_coordinates, fetch_historical_precipitation, WeatherAPIError
from src.formatting import fmt_eur, fmt_num, fmt_pct

st.set_page_config(
    page_title="Assurance Risque Météorologique | IMAFA",
    layout="wide",
    initial_sidebar_state="auto",  # ouverte sur ordinateur, repliée sur téléphone
)

# Première année disponible dans les archives Open-Meteo
FIRST_ARCHIVE_YEAR = 1940
# Les archives Open-Meteo sont publiées avec quelques jours de retard
ARCHIVE_DELAY_DAYS = 7
LAST_FULL_YEAR = date.today().year - 1

# Villes proposées dans le menu déroulant (toute autre ville peut être tapée directement)
CITY_CHOICES = sorted([
    "Ajaccio", "Amiens", "Angers", "Annecy", "Avignon", "Bastia", "Bayonne", "Besançon",
    "Biarritz", "Bordeaux", "Brest", "Caen", "Cannes", "Clermont-Ferrand", "Dijon",
    "Grenoble", "La Rochelle", "Le Havre", "Le Mans", "Lille", "Limoges", "Lyon",
    "Marseille", "Metz", "Montpellier", "Mulhouse", "Nancy", "Nantes", "Nice", "Nîmes",
    "Orléans", "Paris", "Pau", "Perpignan", "Poitiers", "Reims", "Rennes", "Rouen",
    "Saint-Étienne", "Saint-Malo", "Strasbourg", "Toulon", "Toulouse", "Tours",
])


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def locate(city_name: str):
    """Géocodage mis en cache : la localité ne change pas d'un calcul à l'autre."""
    return get_coordinates(city_name)


def missing_days_warning(n_missing: int) -> None:
    """Avertit l'utilisateur quand des jours sans donnée ont été comptés comme secs."""
    if n_missing > 0:
        st.warning(
            f"{n_missing} jour(s) sans donnée météo dans l'historique utilisé : ils sont comptés comme "
            f"des jours sans pluie, ce qui peut sous-estimer légèrement la prime."
        )


def require_location(coords, city_name: str):
    """Renvoie les coordonnées ou lève une erreur lisible si la ville est introuvable."""
    if not coords:
        raise ValueError(f"Impossible de localiser la ville « {city_name} ». Veuillez vérifier l'orthographe.")
    return coords


# En-tête principal
st.title("Logiciel d'Assurance de Risque Météorologique")
st.caption("IMAFA 2026-2027 — Modélisation Actuarielle, Pricing & Analyse Rétrospective | Enseignant : Marius AKRE")

# ---------------------------------------------------------------------------
# Barre latérale : profil du client et paramètres actuariels (communs aux deux onglets)
# ---------------------------------------------------------------------------
st.sidebar.header("Profil & Souscription")
city = st.sidebar.selectbox(
    "Ville du commerce",
    options=CITY_CHOICES,
    index=CITY_CHOICES.index("Nice"),
    accept_new_options=True,
    placeholder="Choisir ou taper une ville",
    help="Choisissez une ville dans la liste, ou tapez le nom de n'importe quelle autre ville puis validez avec Entrée.",
) or "Nice"

# Localité réellement retenue pour la météo : affichée pour lever toute ambiguïté (villes homonymes)
location, location_error = None, None
try:
    location = locate(city)
except WeatherAPIError as e:
    location_error = str(e)
if location:
    st.sidebar.caption(
        f"Point de grille météo : **{location[2]}** ({fmt_num(location[0], 3)}° ; {fmt_num(location[1], 3)}°)"
    )
elif location_error:
    st.sidebar.caption("Localité non vérifiée : service météo injoignable pour le moment.")
else:
    st.sidebar.error(f"Ville « {city} » introuvable.")

ca_max = st.sidebar.number_input("Chiffre d'Affaires Max Journalier (€)", min_value=100.0, value=1000.0, step=50.0)
cf = st.sidebar.number_input(
    "Coûts Fixes Journaliers (€)",
    min_value=10.0,
    max_value=ca_max - 1.0,
    value=min(400.0, ca_max - 1.0),
    step=20.0,
    help="Doivent rester inférieurs au chiffre d'affaires maximum (CA > Cf).",
)
pl_pivot = st.sidebar.number_input("Niveau de Pluie Pivot (mm)", min_value=1.0, value=10.0, step=0.5)
sub_date = st.sidebar.date_input("Date de souscription", value=date.today(), min_value=date.today())

profile = ClientProfile(
    ca_max=float(ca_max),
    cf=float(cf),
    pl_pivot=float(pl_pivot),
    city=city,
    subscription_date=str(sub_date)
)

seuil_critique = profile.pl_pivot * (1 - profile.cf / profile.ca_max)
st.sidebar.info(
    f"**Seuil de perte journalière** : à partir de **{fmt_num(seuil_critique)} mm** de pluie, "
    f"le résultat d'exploitation devient négatif et l'assurance s'active."
)

st.sidebar.header("Paramètres actuariels")
hist_years = st.sidebar.slider("Années d'historique météo utilisées pour tarifer", min_value=5, max_value=30, value=15)
safety_beta = st.sidebar.slider(
    "Chargement de sécurité β (× écart-type)",
    min_value=0.0, max_value=1.0, value=0.30, step=0.05,
    help="Prime chargée = E[I] + β × σ(I) : plus les indemnités annuelles sont irrégulières, plus le chargement est élevé.",
)
expense_rate = st.sidebar.slider("Frais de gestion & marge commerciale (%)", min_value=5, max_value=30, value=15) / 100.0

# Empreinte des paramètres qui influencent les calculs : sert à détecter des résultats périmés
params_key = (
    profile.city.strip().lower(), profile.ca_max, profile.cf, profile.pl_pivot,
    hist_years, safety_beta, expense_rate
)

tab_pricing, tab_retro, tab_guide = st.tabs([
    "Tarification & Devis (Prospective)",
    "Analyse Rétrospective (R&D)",
    "Guide d'Utilisation"
])

# ---------------------------------------------------------------------------
# ONGLET 1 : PRICING & DEVIS
# ---------------------------------------------------------------------------
with tab_pricing:
    st.subheader("I. Tarification de l'Assurance (Approche Prospective)")
    st.write(
        "Calcul de la prime annuelle pure et commerciale à partir de l'historique météorologique réel, "
        "récupéré au moment du calcul. Les paramètres se règlent dans la barre latérale."
    )
    pricing_key = params_key + (profile.subscription_date,)

    if st.button("Récupérer les données météo temps réel & Calculer la prime", type="primary"):
        with st.spinner("Interrogation de l'API Météo et calcul actuariel en cours..."):
            try:
                lat, lon, official_name = require_location(locate(profile.city), profile.city)

                # Historique : périodes de 365 jours commençant au jour/mois de la souscription
                latest_available = date.today() - timedelta(days=ARCHIVE_DELAY_DAYS)
                first_year = latest_available.year - hist_years - 1
                df_precip = fetch_historical_precipitation(
                    lat, lon, f"{first_year}-01-01", latest_available.isoformat()
                )
                periods = split_into_coverage_periods(
                    df_precip, sub_date.month, sub_date.day, first_year, latest_available.year
                )
                kept_years = sorted(periods)[-hist_years:]
                periods = {yr: periods[yr] for yr in kept_years}
                if not periods:
                    raise ValueError("Aucune période historique complète disponible pour cette localisation.")

                pricing_res = price_contract_historical(
                    {yr: p["precipitation"] for yr, p in periods.items()},
                    profile,
                    safety_beta=safety_beta,
                    expense_rate=expense_rate
                )
                first_p, last_p = periods[kept_years[0]], periods[kept_years[-1]]
                st.session_state["pricing"] = {
                    "key": pricing_key,
                    "profile": profile,
                    "res": pricing_res,
                    "station": official_name,
                    "coords": (lat, lon),
                    "history_label": f"{first_p['start']:%d/%m/%Y} au {last_p['end']:%d/%m/%Y} ({len(periods)} années)",
                    "missing_days": sum(p["missing_days"] for p in periods.values()),
                }
            except (WeatherAPIError, ValueError) as e:
                st.error(str(e))

    pricing = st.session_state.get("pricing")
    if pricing and pricing["key"] != pricing_key:
        st.warning(
            "Les paramètres ont changé depuis le dernier calcul : cliquez à nouveau sur le bouton "
            "pour recalculer la prime avant d'éditer le devis."
        )
    elif pricing:
        res = pricing["res"]
        st.divider()
        st.caption(
            f"Couverture du **{sub_date:%d/%m/%Y}** au **{coverage_end(sub_date):%d/%m/%Y}** — "
            f"tarif établi sur les périodes équivalentes du {pricing['history_label']}, "
            f"au point de grille de {pricing['station']}."
        )
        if res["n_years"] < hist_years:
            st.info(f"Seules {res['n_years']} années complètes étaient disponibles (sur {hist_years} demandées).")
        missing_days_warning(pricing["missing_days"])

        m1, m2, m3 = st.columns(3)
        m1.metric("Prime pure E[I]", fmt_eur(res["pure_premium"]))
        m2.metric("Écart-type des indemnités σ", fmt_eur(res["std_indemnity"]))
        m3.metric("Prime commerciale annuelle", fmt_eur(res["commercial_premium"]))
        m4, m5, m6 = st.columns(3)
        m4.metric("VaR 95 % des indemnités", fmt_eur(res["var_95"]),
                  help="Montant d'indemnités annuelles dépassé en moyenne une année sur vingt (95e centile historique).")
        m5.metric("Pire année historique", fmt_eur(res["max_historical_claim"]))
        m6.metric("Chargement de sécurité β·σ", fmt_eur(res["safety_loading"]))
        st.caption(
            f"Prime commerciale = (E[I] + β·σ) / (1 − frais) = ({fmt_eur(res['pure_premium'])} + "
            f"{fmt_num(safety_beta)} × {fmt_eur(res['std_indemnity'])}) / (1 − {fmt_pct(expense_rate)})."
        )

        st.subheader("II. Devis Commercial")
        c1, c2 = st.columns(2)
        client_name = c1.text_input("Nom et prénom du client", placeholder="ex. Marie Dupont")
        company_name = c2.text_input("Raison sociale du commerce", placeholder="ex. SARL Les Glaces du Port")
        quote_ref = make_quote_ref(pricing["profile"])
        pdf_bytes = generate_devis_pdf(
            pricing["profile"], res,
            quote_ref=quote_ref,
            station_label=pricing["station"],
            history_label=pricing["history_label"],
            client_name=client_name.strip(),
            company_name=company_name.strip(),
        )
        st.download_button(
            label=f"Télécharger le Devis {quote_ref} (PDF)",
            data=pdf_bytes,
            file_name=f"Devis_Assurance_Meteo_{quote_ref}.pdf",
            mime="application/pdf"
        )

# ---------------------------------------------------------------------------
# ONGLET 2 : ANALYSE RÉTROSPECTIVE
# ---------------------------------------------------------------------------
with tab_retro:
    st.subheader("III. Analyse Rétrospective de l'Impact de l'Assurance (Backtesting)")
    st.write(
        "Pour une année passée *a*, le logiciel calcule la prime qu'il aurait proposée au 1er janvier de *a* "
        f"(avec les {hist_years} années précédentes uniquement, β = {fmt_num(safety_beta)}, frais {fmt_pct(expense_rate)}), "
        "puis la compare à ce qui s'est réellement passé pendant l'année."
    )

    # --- A. Une année ---
    st.markdown("#### A. Une année passée")
    test_year = int(st.number_input(
        "Sélectionner une année passée (a)",
        min_value=FIRST_ARCHIVE_YEAR + 2,
        max_value=LAST_FULL_YEAR,
        value=1998
    ))
    prior_start_year = max(FIRST_ARCHIVE_YEAR, test_year - hist_years)
    single_key = params_key + (test_year,)

    if st.button(f"Lancer l'analyse rétrospective sur l'année {test_year}"):
        with st.spinner(f"Récupération de la météo de {prior_start_year} à {test_year} pour {profile.city}..."):
            try:
                lat, lon, official_name = require_location(locate(profile.city), profile.city)
                df_all = fetch_historical_precipitation(lat, lon, f"{prior_start_year}-01-01", f"{test_year}-12-31")
                # Années civiles : le contrat rétrospectif est souscrit au 1er janvier de l'année a
                periods = split_into_coverage_periods(df_all, 1, 1, prior_start_year, test_year)
                if test_year not in periods:
                    raise ValueError(f"Données météo incomplètes pour l'année {test_year} : analyse impossible.")

                # Tarification a priori sur les années strictement antérieures à a
                prior = {yr: p for yr, p in periods.items() if yr < test_year}
                retro_pricing = price_contract_historical(
                    {yr: p["precipitation"] for yr, p in prior.items()},
                    profile,
                    safety_beta=safety_beta,
                    expense_rate=expense_rate
                )
                premium = retro_pricing["commercial_premium"]

                # Résultats a posteriori sur l'année a
                year_period = periods[test_year]
                analysis = run_retrospective_analysis(year_period["precipitation"], profile, premium)
                analysis["details_journaliers"]["date"] = pd.date_range(
                    year_period["start"], year_period["end"], freq="D"
                )
                st.session_state["retro_single"] = {
                    "key": single_key,
                    "year": test_year,
                    "station": official_name,
                    "pricing": retro_pricing,
                    "n_prior": len(prior),
                    "analysis": analysis,
                    "missing_days": sum(p["missing_days"] for p in periods.values()),
                }
            except (WeatherAPIError, ValueError) as e:
                st.error(str(e))

    retro = st.session_state.get("retro_single")
    if retro and retro["key"] != single_key:
        st.info("Les paramètres ont changé depuis la dernière analyse : relancez-la pour mettre à jour les résultats.")
    elif retro:
        a = retro["year"]
        analysis = retro["analysis"]
        premium = analysis["premium"]
        st.caption(f"Point de grille météo : {retro['station']}.")
        missing_days_warning(retro["missing_days"])
        st.metric(f"Prime calculée a priori début {a} (P_a)", fmt_eur(premium))
        st.caption(
            f"Prime pure {fmt_eur(retro['pricing']['pure_premium'])} sur {retro['n_prior']} années d'historique."
        )

        r1, r2 = st.columns(2)
        r1.metric("Résultat non assuré (R_nass)", fmt_eur(analysis["r_nass"]))
        r2.metric("Résultat garanti brut (R_ass)", fmt_eur(analysis["r_ass"]))
        r3, r4 = st.columns(2)
        r3.metric("Indemnités reçues (pertes évitées)", fmt_eur(analysis["pertes_evitees"]))
        r4.metric("Résultat net assuré (R_ass − P_a)", fmt_eur(analysis["r_net"]),
                  delta=f"{fmt_eur(analysis['gain_net_client'], signed=True)} vs non assuré")

        if analysis["est_favorable"]:
            st.success(
                f"**Conclusion : s'assurer aurait été favorable au client en {a}.** "
                f"La prime payée a priori ({fmt_eur(premium, 0)}) a été inférieure aux pertes évitées "
                f"({fmt_eur(analysis['pertes_evitees'], 0)}), soit un gain net de **{fmt_eur(analysis['gain_net_client'], 0, signed=True)}**."
            )
        else:
            st.warning(
                f"**Conclusion : s'assurer n'aurait pas été favorable au client en {a}.** "
                f"La prime payée a priori ({fmt_eur(premium, 0)}) a dépassé les pertes évitées "
                f"({fmt_eur(analysis['pertes_evitees'], 0)}) : écart de **{fmt_eur(analysis['gain_net_client'], 0)}** pour le client."
            )

        st.plotly_chart(plot_retrospective_comparison(analysis, a), width="stretch")
        st.plotly_chart(plot_cumulative_results(analysis["details_journaliers"], a), width="stretch")

    # --- B. Plusieurs années ---
    st.divider()
    st.markdown("#### B. Sur plusieurs années")
    st.write(
        "Chaque année de la plage est tarifée a priori, puis comparée aux indemnités réellement versées. "
        "On obtient ainsi le ratio sinistres / primes du produit et la part des années où s'assurer aurait été favorable."
    )
    min_multi = FIRST_ARCHIVE_YEAR + 2
    year_range = st.slider(
        "Plage d'années à rejouer",
        min_value=min_multi, max_value=LAST_FULL_YEAR,
        value=(max(min_multi, LAST_FULL_YEAR - 24), LAST_FULL_YEAR),
    )
    multi_key = params_key + (year_range,)

    if st.button(f"Lancer l'analyse sur {year_range[0]}–{year_range[1]}"):
        first_needed = max(FIRST_ARCHIVE_YEAR, year_range[0] - hist_years)
        with st.spinner(f"Récupération de la météo de {first_needed} à {year_range[1]} pour {profile.city}..."):
            try:
                lat, lon, official_name = require_location(locate(profile.city), profile.city)
                df_all = fetch_historical_precipitation(lat, lon, f"{first_needed}-01-01", f"{year_range[1]}-12-31")
                periods = split_into_coverage_periods(df_all, 1, 1, first_needed, year_range[1])
                backtest = run_multi_year_backtest(
                    periods, profile, list(range(year_range[0], year_range[1] + 1)),
                    hist_years=hist_years, safety_beta=safety_beta, expense_rate=expense_rate,
                )
                if backtest["summary"] is None:
                    raise ValueError("Pas assez de données météo complètes sur cette plage d'années.")
                st.session_state["retro_multi"] = {
                    "key": multi_key,
                    "station": official_name,
                    "range": year_range,
                    "backtest": backtest,
                }
            except (WeatherAPIError, ValueError) as e:
                st.error(str(e))

    multi = st.session_state.get("retro_multi")
    if multi and multi["key"] != multi_key:
        st.info("Les paramètres ont changé depuis la dernière analyse : relancez-la pour mettre à jour les résultats.")
    elif multi:
        summary, table = multi["backtest"]["summary"], multi["backtest"]["table"]
        st.caption(f"Point de grille météo : {multi['station']} — {summary['n_years']} années rejouées.")
        k1, k2, k3 = st.columns(3)
        k1.metric("Ratio sinistres / primes (S/P)", fmt_pct(summary["loss_ratio"]),
                  help="Indemnités versées / primes encaissées sur la période. Sous 100 %, le produit est rentable pour l'assureur.")
        k2.metric("Années favorables au client", fmt_pct(summary["share_favorable"]),
                  help="Part des années où les indemnités ont dépassé la prime payée.")
        k3.metric("Gain cumulé du client", fmt_eur(summary["cumulative_client_gain"], 0),
                  help="Somme des (indemnités − prime) : négatif si, au total, l'assurance a coûté plus qu'elle n'a rapporté.")
        k4, k5 = st.columns(2)
        k4.metric("Total des primes", fmt_eur(summary["total_premiums"], 0))
        k5.metric("Total des indemnités", fmt_eur(summary["total_indemnities"], 0))

        st.plotly_chart(plot_multi_year_backtest(table), width="stretch")
        st.caption("Barres vertes : années où les indemnités ont dépassé la prime (assurance favorable au client).")
        with st.expander("Détail année par année"):
            shown = pd.DataFrame({
                "Année": table["annee"].astype(str),
                "Prime a priori": table["prime"].map(lambda v: fmt_eur(v, 0)),
                "Indemnités": table["indemnites"].map(lambda v: fmt_eur(v, 0)),
                "R non assuré": table["r_nass"].map(lambda v: fmt_eur(v, 0)),
                "R net assuré": table["r_net"].map(lambda v: fmt_eur(v, 0)),
                "Favorable": table["favorable"].map({True: "oui", False: "non"}),
            })
            st.dataframe(shown, hide_index=True, width="stretch")

# ---------------------------------------------------------------------------
# ONGLET 3 : GUIDE
# ---------------------------------------------------------------------------
with tab_guide:
    st.subheader("Guide Utilisateur & Documentation Modélisation")
    st.markdown("""
    ### Modèle mathématique
    Pour chaque jour $t$ :
    - $CA_t^{pl} = f_t^{pl} \\times CA$, avec $f_t^{pl} = \\frac{\\overline{pl} - pl_t}{\\overline{pl}}$ (0 au-delà du pivot, 1 sans pluie)
    - $R_t^{pl} = CA_t^{pl} - Cf$
    - Indemnité : $I_t = \\max(0, -R_t^{pl})$, ce qui garantit un résultat journalier $\\geq 0$
    - Seuil critique : $pl_{seuil} = \\overline{pl} \\left(1 - \\frac{Cf}{CA}\\right)$

    ### Tarification
    - Indemnité annuelle $I = \\sum_t I_t$, rejouée sur les N années d'historique.
    - Prime commerciale $= \\dfrac{E[I] + \\beta \\, \\sigma(I)}{1 - \\text{frais}}$ (principe de l'écart-type).

    ### Navigation
    1. **Barre latérale** : profil du commerce (ville, CA max, coûts fixes, pluie pivot, date de souscription)
       et paramètres actuariels (historique, β, frais). La localité météo retenue s'affiche sous la ville.
    2. **Tarification** : la prime couvre les 365 jours à partir de la date de souscription ; elle est estimée sur les
       mêmes périodes des années passées. Renseignez le nom et la raison sociale, puis téléchargez le devis PDF.
    3. **Analyse rétrospective** : une année passée *a* (prime calculée au 1er janvier de *a* avec les seules années
       antérieures), ou une plage d'années (ratio sinistres / primes, part des années favorables).

    ### Source météo et limites
    Les précipitations viennent d'Open-Meteo, qui s'appuie sur les **réanalyses ERA5 / ERA5-Land** : des valeurs
    calculées sur un **point de grille** d'environ 10 à 25 km, et non les relevés d'une station au sol. Les réanalyses
    ont tendance à **lisser les fortes pluies** et à compter **trop de jours de pluie faible**. Dans ce modèle, toute
    pluie réduit le chiffre d'affaires : le nombre de jours pluvieux et l'intensité des épisodes pèsent donc
    directement sur la prime.
    """)
