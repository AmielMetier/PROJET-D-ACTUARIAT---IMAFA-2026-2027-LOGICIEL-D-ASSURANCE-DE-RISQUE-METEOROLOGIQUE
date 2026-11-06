"""Application Web / Mobile (Streamlit) — Logiciel d'Assurance Météorologique.
Projet d'Actuariat IMAFA 2026-2027 — Polytech Nice Sophia.
"""

import streamlit as st
import os
import sys

# Ajout du dossier src au chemin de recherche Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

st.set_page_config(
    page_title="Assurance Météo | IMAFA 2026-2027",
    page_icon="🌧️",
    layout="wide"
)

st.title("🌧️ Logiciel d'Assurance de Risque Météorologique")
st.caption("Projet d'Actuariat — Polytech Nice Sophia (MAM, parcours IMAFA 2026-2027) | Enseignant : Marius AKRE")

# --- BARRE LATÉRALE : PARAMÈTRES DU CLIENT ---
st.sidebar.header("📋 Saisie des informations client")
nom_client = st.sidebar.text_input("Nom / Raison sociale", value="Commerçant Niçois")
ville = st.sidebar.text_input("Ville de localisation", value="Nice")
date_souscription = st.sidebar.date_input("Date de souscription")
ca_max = st.sidebar.number_input("Chiffre d'affaires journalier max (CA)", min_value=1.0, value=500.0, step=50.0)
couts_fixes = st.sidebar.number_input("Coûts fixes journaliers (Cf)", min_value=0.0, value=200.0, step=20.0)
pluie_pivot = st.sidebar.number_input("Niveau de pluie journalier pivot (pl̄ en mm)", min_value=1.0, value=10.0, step=1.0)

# --- ONGLETS PRINCIPAUX ---
tab1, tab2, tab3 = st.tabs([
    "📊 I/ Tarification (Pricing)",
    "📑 II/ Devis commercial",
    "📈 III/ Analyse rétrospective (R&D)"
])

with tab1:
    st.subheader("Département Tarification — Calcul de la prime d'assurance")
    st.info("TODO: Connecter vos fonctions de pricing (src/assurance_meteo/pricing.py).")

with tab2:
    st.subheader("Département Commercial — Devis client")
    st.info("TODO: Connecter votre module d'édition de devis (src/assurance_meteo/devis.py).")

with tab3:
    st.subheader("Département R&D — Analyse rétrospective")
    annee_choisie = st.number_input("Saisir une année passée (a)", min_value=1950, max_value=2025, value=1998, step=1)
    st.info("TODO: Connecter vos fonctions d'analyse rétrospective et vos graphiques (src/assurance_meteo/retrospective.py).")
