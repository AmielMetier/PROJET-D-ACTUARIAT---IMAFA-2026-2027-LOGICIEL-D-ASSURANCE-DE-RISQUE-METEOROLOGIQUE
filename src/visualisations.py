"""
Module de Visualisations Interactives (Plotly).
Fournit des graphiques pour l'analyse rétrospective et l'analyse de risque.
"""

from typing import Dict, Any
import plotly.graph_objects as go
import pandas as pd

from .formatting import fmt_eur


def plot_retrospective_comparison(analysis: Dict[str, Any], year: int) -> go.Figure:
    """
    Graphique en barres comparant R_nass, R_ass, Prime P et R_net.
    """
    categories = [
        "Résultat Non Assuré (R_nass)",
        "Résultat Garanti Brut (R_ass)",
        "Prime Payée (P)",
        "Résultat Net Assuré (R_net)"
    ]
    values = [
        analysis["r_nass"],
        analysis["r_ass"],
        analysis["premium"],
        analysis["r_net"]
    ]
    colors = ["#EF553B", "#00CC96", "#FFA15A", "#636EFA"]

    fig = go.Figure(data=[
        go.Bar(
            x=categories,
            y=values,
            marker_color=colors,
            text=[fmt_eur(v, 0) for v in values],
            textposition="auto"
        )
    ])
    fig.update_layout(
        title=f"Bilan Rétrospectif de l'Assurance Météorologique (Année {year})",
        yaxis_title="Montant en Euros (€)",
        template="plotly_white",
        separators=", ",  # virgule décimale, espace pour les milliers
        height=450
    )
    return fig


def plot_cumulative_results(df_details: pd.DataFrame, year: int) -> go.Figure:
    """
    Courbes d'évolution cumulée jour par jour sur l'année choisie.
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_details["date"] if "date" in df_details.columns else df_details.index,
        y=df_details["cum_r_nass"],
        mode="lines",
        name="Non Assuré (Cumul)",
        line=dict(color="#EF553B", width=2, dash="dash")
    ))

    fig.add_trace(go.Scatter(
        x=df_details["date"] if "date" in df_details.columns else df_details.index,
        y=df_details["cum_r_net"],
        mode="lines",
        name="Assuré Net de Prime (Cumul)",
        line=dict(color="#00CC96", width=2.5)
    ))

    fig.update_layout(
        title=f"Trajectoire Temporelle Cumulée du Résultat Journalier ({year})",
        xaxis_title="Date",
        yaxis_title="Résultat Cumulé (€)",
        template="plotly_white",
        separators=", ",  # virgule décimale, espace pour les milliers
        hovermode="x unified",
        height=450
    )
    return fig


def plot_multi_year_backtest(table: pd.DataFrame) -> go.Figure:
    """
    Primes calculées a priori contre indemnités réellement versées, année par année.
    Les barres vertes marquent les années où s'assurer aurait été favorable au client.
    """
    colors = ["#00CC96" if fav else "#B0BEC5" for fav in table["favorable"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=table["annee"],
        y=table["indemnites"],
        name="Indemnités versées (a posteriori)",
        marker_color=colors,
        customdata=[fmt_eur(v, 0) for v in table["indemnites"]],
        hovertemplate="%{customdata}<extra>Indemnités</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=table["annee"],
        y=table["prime"],
        name="Prime calculée a priori",
        mode="lines+markers",
        line=dict(color="#EF553B", width=2.5),
        customdata=[fmt_eur(v, 0) for v in table["prime"]],
        hovertemplate="%{customdata}<extra>Prime</extra>",
    ))
    fig.update_layout(
        title="Prime a priori et indemnités par année",
        xaxis_title="Année",
        yaxis_title="Montant (€)",
        template="plotly_white",
        separators=", ",  # virgule décimale, espace pour les milliers
        hovermode="x unified",
        height=450,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return fig
