"""Application Web interactive - Logiciel d'Assurance de Risque Météorologique.
Projet d'Actuariat IMAFA 2026-2027 — Polytech Nice Sophia.
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import sys

# Ajout du dossier src au PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from assurance_meteo.model import ProfilClient, simulation_activite_journaliere
from assurance_meteo.weather import (
    recuperer_pluviometrie_annuelle,
    recuperer_historique_pluviometrie,
    recuperer_previsions_temps_reel
)
from assurance_meteo.pricing import calculer_prime_assurance, indemnites_annuelles_historiques
from assurance_meteo.devis import generer_devis
from assurance_meteo.retrospective import analyser_annee_retrospective, tracer_analyse_retrospective

st.set_page_config(
    page_title="Assurance Météo | IMAFA 2026-2027",
    page_icon="🌧️",
    layout="wide"
)

st.title("🌧️ Logiciel d'Assurance de Risque Météorologique")
st.caption("Projet d'Actuariat — Polytech Nice Sophia (MAM, parcours IMAFA 2026-2027) | Enseignant : Marius AKRE")

# --- BARRE LATÉRALE : PARAMÈTRES DU CLIENT ---
st.sidebar.header("📋 Profil du commerçant (Client)")
nom_client = st.sidebar.text_input("Nom / Raison sociale", value="Café de la Promenade")
ville = st.sidebar.text_input("Ville de localisation", value="Nice")
date_souscription = st.sidebar.date_input("Date de souscription", value=pd.to_datetime("today"))

ca_max = st.sidebar.number_input(
    "Chiffre d'affaires max / jour (CA en €)",
    min_value=50.0,
    max_value=100000.0,
    value=500.0,
    step=50.0,
    help="Chiffre d'affaires réalisé les jours sans pluie (pl_t = 0)"
)

couts_fixes = st.sidebar.number_input(
    "Coûts fixes journaliers (Cf en €)",
    min_value=10.0,
    max_value=float(ca_max) - 1.0,
    value=200.0,
    step=20.0,
    help="Coûts incompressibles par jour (électricité, abonnements, loyer...)"
)

pluie_pivot = st.sidebar.number_input(
    "Pluie journalière pivot (pl̄ en mm)",
    min_value=1.0,
    max_value=100.0,
    value=10.0,
    step=1.0,
    help="Niveau pluviométrique au-delà duquel l'activité s'arrête totalement (CA = 0)"
)

# Instanciation du modèle client
try:
    client = ProfilClient(
        nom=nom_client,
        ville=ville,
        date_souscription=str(date_souscription),
        ca_max=ca_max,
        couts_fixes=couts_fixes,
        pluie_pivot=pluie_pivot
    )
except ValueError as e:
    st.sidebar.error(str(e))
    st.stop()

# Indicateurs rapides en barre latérale
seuil_perte = client.seuil_perte
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Seuil de perte ($pl^*$) :** `{seuil_perte:.2f} mm/jour`")
st.sidebar.caption(
    f"Dès que $pl_t > {seuil_perte:.2f}$ mm, le résultat journalier devient négatif et l'assurance intervient."
)

# --- ONGLETS PRINCIPAUX ---
tab_pricing, tab_devis, tab_retro, tab_realtime = st.tabs([
    "📊 I/ Tarification (Pricing)",
    "📑 II/ Devis commercial",
    "📈 III/ Analyse rétrospective (R&D)",
    "🌤️ IV/ Temps réel & Prévisions"
])

# --- ONGLET 1 : TARIFICATION ---
with tab_pricing:
    st.subheader("Département Tarification — Calcul de la prime prospective")
    st.markdown(
        """
        Le produit d'assurance garantit au client un **résultat journalier positif ($R_t \ge 0$)**
        sur l'ensemble des 365 jours de l'année. La prime annuelle est calculée sur la base
        de l'historique météorologique de la ville.
        """
    )
    
    col1, col2 = st.columns(2)
    with col1:
        annee_fin_hist = 2025
        nb_annees = st.slider("Historique d'observation (années)", min_value=5, max_value=30, value=15)
        annee_debut_hist = annee_fin_hist - nb_annees + 1
    with col2:
        coeff_sec = st.slider("Chargement de sécurité ($\\beta \cdot \sigma$)", 0.0, 0.5, 0.15, step=0.05)
        taux_frais = st.slider("Chargement pour frais de gestion", 0.0, 0.30, 0.10, step=0.02)

    if st.button("Calculer la tarification", key="btn_pricing"):
        with st.spinner("Récupération de l'historique météorologique..."):
            hist_pluie = recuperer_historique_pluviometrie(
                client.ville, annee_debut_hist, annee_fin_hist, cache_dir="data"
            )
            tarif = calculer_prime_assurance(
                client, hist_pluie, coeff_securite=coeff_sec, taux_frais=taux_frais
            )
            st.session_state["tarif"] = tarif
            st.session_state["hist_pluie"] = hist_pluie

    if "tarif" in st.session_state:
        tarif = st.session_state["tarif"]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Prime pure $\mathbb{E}[L]$", f"{tarif['prime_pure']:,.2f} €")
        m2.metric("Marge de sécurité", f"{tarif['chargement_securite']:,.2f} €")
        m3.metric("Frais de gestion", f"{tarif['chargement_frais']:,.2f} €")
        m4.metric("PRIME TOTALE ANNUELLE", f"{tarif['prime_totale']:,.2f} €")

        st.markdown("---")
        st.subheader("Historique annuel des pertes indemnisables")
        df_hist = indemnites_annuelles_historiques(client, st.session_state["hist_pluie"])
        st.bar_chart(df_hist.set_index("annee")["perte_totale"])

# --- ONGLET 2 : DEVIS COMMERCIAL ---
with tab_devis:
    st.subheader("Département Commercial — Édition du devis")
    if "tarif" not in st.session_state:
        st.info("Veuillez d'abord calculer la tarification dans l'onglet 'Tarification'.")
    else:
        devis_texte = generer_devis(client, st.session_state["tarif"])
        st.text_area("Devis client (format prêt à imprimer)", devis_texte, height=450)
        st.download_button(
            "Télécharger le devis (.txt)",
            data=devis_texte,
            file_name=f"Devis_{client.nom.replace(' ', '_')}.txt",
            mime="text/plain"
        )

# --- ONGLET 3 : ANALYSE RÉTROSPECTIVE ---
with tab_retro:
    st.subheader("Département R&D — Analyse rétrospective de l'impact de l'assurance")
    st.markdown(
        """
        Compare pour une année passée $a$ saisie par l'utilisateur :
        - Le résultat du client **non assuré** : $R_{\\bar{pl}, nass, i}^a$
        - Le résultat du client **assuré** (brut) : $R_{\\bar{pl}, ass, i}^a$
        - La prime a priori qui aurait été payée : $P_{\\bar{pl}, i}^a$
        - Le résultat net de prime : $R_{\\bar{pl}, ass, i}^a - P_{\\bar{pl}, i}^a$
        """
    )

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        annee_retro = st.number_input("Année passée à analyser (a)", min_value=1950, max_value=2025, value=1998, step=1)
    with col_r2:
        forcer_prime = st.checkbox("Imposer une prime a priori spécifique (ex: 3 000 € du sujet)", value=(annee_retro == 1998 and client.ville.lower() == "nice"))
        prime_val = st.number_input("Montant de la prime imposée (€)", value=3000.0, step=100.0) if forcer_prime else None

    if st.button("Lancer l'analyse rétrospective", key="btn_retro"):
        with st.spinner("Chargement des données météo et calculs..."):
            bilan = analyser_annee_retrospective(
                client,
                int(annee_retro),
                prime_imposee=prime_val,
                cache_dir="data"
            )
            st.session_state["bilan_retro"] = bilan

    if "bilan_retro" in st.session_state:
        bilan = st.session_state["bilan_retro"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Résultat non assuré (R_nass)", f"{bilan['resultat_non_assure']:,.2f} €")
        c2.metric("Prime a priori payée (P)", f"{bilan['prime_a_priori']:,.2f} €")
        c3.metric("Pertes réelles évitées", f"{bilan['pertes_reelles']:,.2f} €")
        c4.metric(
            "Résultat net assuré (R_ass - P)",
            f"{bilan['resultat_assure_net']:,.2f} €",
            delta=f"{bilan['gain_net_assurance']:+,.2f} € vs non assuré"
        )

        if bilan["assurance_favorable"]:
            st.success(
                f"✅ **Conclusion rétrospective :** S'assurer en {bilan['annee']} a été très favorable au client "
                f"(gain net de +{bilan['gain_net_assurance']:,.2f} € car la prime de {bilan['prime_a_priori']:,.2f} € "
                f"était inférieure aux pertes réelles de {bilan['pertes_reelles']:,.2f} €)."
            )
        else:
            st.info(
                f"ℹ️ **Conclusion rétrospective :** En {bilan['annee']}, l'année a été relativement sèche. "
                f"Le coût de la prime ({bilan['prime_a_priori']:,.2f} €) a été supérieur aux pertes constatées ({bilan['pertes_reelles']:,.2f} €)."
            )

        fig, _ = tracer_analyse_retrospective(bilan)
        st.pyplot(fig)

# --- ONGLET 4 : TEMPS RÉEL ---
with tab_realtime:
    st.subheader("Prévisions Météorologiques en Temps Réel")
    st.markdown("Statistiques météorologiques récupérées juste avant les calculs via l'API Open-Meteo temps réel.")
    if st.button("Actualiser les données temps réel", key="btn_realtime"):
        with st.spinner("Interrogation des serveurs météo..."):
            try:
                df_prev = recuperer_previsions_temps_reel(client.ville)
                st.dataframe(df_prev)
            except Exception as e:
                st.error(f"Erreur lors de la récupération : {e}")
