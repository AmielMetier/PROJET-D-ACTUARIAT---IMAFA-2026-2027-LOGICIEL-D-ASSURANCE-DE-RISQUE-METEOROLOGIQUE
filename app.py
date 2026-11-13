"""
Application Web de Tarification & d'Analyse d'Assurance Météorologique.
Projet d'Actuariat - IMAFA 2026-2027.
"""

from datetime import date
import streamlit as st
import pandas as pd
import numpy as np

from src.simulation import ClientProfile
from src.pricing import price_contract_historical
from src.backtesting import run_retrospective_analysis
from src.visualisations import plot_retrospective_comparison, plot_cumulative_results
from src.pdf_generator import generate_devis_pdf
from src.weather_api import get_coordinates, fetch_historical_precipitation

st.set_page_config(
    page_title="Assurance Risque Météorologique | IMAFA",
    page_icon="🌧️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Première année disponible dans les archives Open-Meteo
FIRST_ARCHIVE_YEAR = 1940

# En-tête principal
st.title("🌧️ Logiciel d'Assurance de Risque Météorologique")
st.caption("IMAFA 2026-2027 — Modélisation Actuarielle, Pricing & Analyse Rétrospective")

# Sidebar : Paramètres du client
st.sidebar.header("📋 Profil & Souscription")
city = st.sidebar.text_input("Ville du commerce", value="Nice")
ca_max = st.sidebar.number_input("Chiffre d'Affaires Max Journalier (€)", min_value=100.0, value=1000.0, step=50.0)
cf = st.sidebar.number_input("Coûts Fixes Journaliers (€)", min_value=10.0, max_value=ca_max - 1.0, value=400.0, step=20.0)
pl_pivot = st.sidebar.number_input("Niveau de Pluie Pivot (mm)", min_value=1.0, value=10.0, step=0.5)
sub_date = st.sidebar.date_input("Date de souscription", value=date.today())

profile = ClientProfile(
    ca_max=float(ca_max),
    cf=float(cf),
    pl_pivot=float(pl_pivot),
    city=city,
    subscription_date=str(sub_date)
)

# Seuil critique automatique
seuil_critique = profile.pl_pivot * (1 - profile.cf / profile.ca_max)
st.sidebar.info(
    f"💡 **Seuil de perte journalière** : à partir de **{seuil_critique:.2f} mm** de pluie, "
    f"le résultat d'exploitation devient négatif et l'assurance s'active."
)

tab_pricing, tab_retro, tab_guide = st.tabs([
    "📊 Tarification & Devis (Prospective)",
    "📈 Analyse Rétrospective (R&D)",
    "📖 Guide d'Utilisation"
])

# --- ONGLET 1 : PRICING & DEVIS ---
with tab_pricing:
    st.subheader("I. Tarification de l'Assurance (Approche Prospective)")
    st.write("Calcul de la prime annuelle pure et commerciale sur la base de l'historique météorologique réel.")

    col1, col2 = st.columns([2, 1])
    with col1:
        hist_years = st.slider("Nombre d'années d'historique météo pour l'estimation actuarielle", min_value=5, max_value=30, value=15)
        safety_rate = st.slider("Chargement de sécurité actuariel (%)", min_value=0, max_value=30, value=10) / 100.0
        expense_rate = st.slider("Frais de gestion & marge commerciale (%)", min_value=5, max_value=30, value=15) / 100.0

    if st.button("🚀 Récupérer les données météo temps réel & Calculer la prime", type="primary"):
        with st.spinner("Interrogation de l'API Météo et calcul actuariel en cours..."):
            coords = get_coordinates(profile.city)
            if not coords:
                st.error(f"Impossible de localiser la ville '{profile.city}'. Veuillez vérifier l'orthographe.")
            else:
                lat, lon, official_name = coords
                st.success(f"📍 Station localisée : **{official_name}** ({lat:.3f}°N, {lon:.3f}°E)")
                
                # Téléchargement historique
                current_year = date.today().year
                start_year = current_year - hist_years
                df_precip = fetch_historical_precipitation(lat, lon, f"{start_year}-01-01", f"{current_year - 1}-12-31")
                
                # Regroupement par année
                df_precip["year"] = df_precip["date"].dt.year
                hist_dict = {yr: grp["precipitation"] for yr, grp in df_precip.groupby("year")}
                
                # Pricing
                pricing_res = price_contract_historical(
                    hist_dict,
                    profile,
                    safety_margin_rate=safety_rate,
                    expense_rate=expense_rate
                )
                
                st.session_state["pricing_res"] = pricing_res
                st.session_state["hist_dict"] = hist_dict
                st.session_state["coords"] = coords

    if "pricing_res" in st.session_state:
        res = st.session_state["pricing_res"]
        st.divider()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Prime Pure E[I]", f"{res['pure_premium']:,.2f} €")
        m2.metric("Écart-type Sinistres", f"{res['std_indemnity']:,.2f} €")
        m3.metric("Pire Année Historique", f"{res['max_historical_claim']:,.2f} €")
        m4.metric("Prime Commerciale Annuelle", f"{res['commercial_premium']:,.2f} €", delta="Tarif final")

        st.subheader("II. Devis Commercial")
        pdf_bytes = generate_devis_pdf(profile, res)
        st.download_button(
            label="📄 Télécharger le Devis Officiel (PDF)",
            data=pdf_bytes,
            file_name=f"Devis_Assurance_Meteo_{profile.city}_{profile.subscription_date}.pdf",
            mime="application/pdf"
        )

# --- ONGLET 2 : ANALYSE RÉTROSPECTIVE ---
with tab_retro:
    st.subheader("III. Analyse Rétrospective de l'Impact de l'Assurance (Backtesting)")
    st.write(
        "Évaluez si l'assurance aurait été favorable à ce client pour une année passée quelconque *a*."
    )
    
    test_year = int(st.number_input(
        "Sélectionner une année passée (a)",
        min_value=FIRST_ARCHIVE_YEAR + 1,
        max_value=date.today().year - 1,
        value=1998
    ))
    # La prime P_a est calculée a priori : uniquement avec la météo antérieure à l'année a.
    prior_start_year = max(FIRST_ARCHIVE_YEAR, test_year - hist_years)
    st.info(
        f"La prime P_a est **calculée par le logiciel** comme elle l'aurait été début {test_year} : "
        f"à partir de la météo de {prior_start_year} à {test_year - 1} uniquement, avec les chargements "
        f"réglés dans l'onglet Tarification (sécurité {safety_rate:.0%}, frais {expense_rate:.0%})."
    )

    if st.button("🔍 Lancer l'analyse rétrospective sur l'année " + str(test_year)):
        with st.spinner(f"Récupération de la météo de {prior_start_year} à {test_year} pour {profile.city}..."):
            coords = get_coordinates(profile.city)
            if not coords:
                st.error(f"Impossible de localiser la ville '{profile.city}'. Veuillez vérifier l'orthographe.")
            else:
                lat, lon, _ = coords
                df_all = fetch_historical_precipitation(lat, lon, f"{prior_start_year}-01-01", f"{test_year}-12-31")
                df_all["year"] = df_all["date"].dt.year

                # Tarification a priori sur les années strictement antérieures à a
                df_prior = df_all[df_all["year"] < test_year]
                prior_dict = {yr: grp["precipitation"] for yr, grp in df_prior.groupby("year")}
                retro_pricing = price_contract_historical(
                    prior_dict,
                    profile,
                    safety_margin_rate=safety_rate,
                    expense_rate=expense_rate
                )
                custom_premium = retro_pricing["commercial_premium"]

                # Résultats a posteriori sur l'année a
                df_year = df_all[df_all["year"] == test_year].reset_index(drop=True)
                analysis = run_retrospective_analysis(df_year["precipitation"], profile, custom_premium)
                df_year_details = analysis["details_journaliers"]
                df_year_details["date"] = df_year["date"]

                st.metric(
                    f"Prime calculée a priori début {test_year} (P_a)",
                    f"{custom_premium:,.2f} €",
                    delta=f"Prime pure {retro_pricing['pure_premium']:,.2f} € sur {len(prior_dict)} années d'historique",
                    delta_color="off"
                )

                r1, r2, r3, r4 = st.columns(4)
                r1.metric("Résultat Non Assuré (R_nass)", f"{analysis['r_nass']:,.2f} €")
                r2.metric("Résultat Garanti Brut (R_ass)", f"{analysis['r_ass']:,.2f} €")
                r3.metric("Indemnités reçues (Pertes évitées)", f"{analysis['pertes_evitees']:,.2f} €")
                r4.metric("Résultat Net Assuré (R_net)", f"{analysis['r_net']:,.2f} €", delta=f"{analysis['gain_net_client']:+,.2f} € vs Non Assuré")

                if analysis["est_favorable"]:
                    st.success(
                        f"✅ **Conclusion Rétrospective : S'assurer aurait été favorable au client en {test_year} !** "
                        f"La prime payée a priori ({custom_premium:,.0f} €) a été inférieure aux pertes évitées "
                        f"({analysis['pertes_evitees']:,.0f} €), procurant un gain net de **{analysis['gain_net_client']:+,.0f} €**."
                    )
                else:
                    st.warning(
                        f"ℹ️ **Conclusion Rétrospective : L'assurance n'a pas été déclenchée de façon excédentaire en {test_year}.** "
                        f"Le client a payé {custom_premium:,.0f} € de prime pour {analysis['pertes_evitees']:,.0f} € de pertes évitées."
                    )

                st.plotly_chart(plot_retrospective_comparison(analysis, test_year), use_container_width=True)
                st.plotly_chart(plot_cumulative_results(df_year_details, test_year), use_container_width=True)

# --- ONGLET 3 : USER GUIDE ---
with tab_guide:
    st.subheader("📖 Guide Utilisateur & Documentation Modélisation")
    st.markdown("""
    ### Modèle Mathématique
    Pour chaque jour $t$ :
    - $CA_t^{pl} = f_t^{pl} \\times CA$
    - $R_t^{pl} = CA_t^{pl} - Cf$
    - Indemnité : $I_t = \\max(0, -R_t^{pl})$
    - Seuil critique de rentabilité : $pl_{seuil} = \\overline{pl} \\left(1 - \\frac{Cf}{CA}\\right)$

    ### Navigation dans l'application
    1. **Souscription** : Configurez votre commerce dans le panneau latéral gauche (CA max, Coûts fixes, Seuil de pluie pivot).
    2. **Pricing** : Cliquez sur le bouton de calcul pour interroger l'API météorologique en temps réel et générer votre devis officiel PDF.
    3. **Analyse Rétrospective** : Testez n'importe quelle année passée pour observer graphiquement l'efficacité de la couverture.
    """)
