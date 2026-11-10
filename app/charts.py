"""Small, Streamlit-independent Plotly figures for source observations."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from data_processing import MEASURES

PALETTE = ["#087f8c", "#3e58a8", "#ab5963", "#9565a4", "#d07a27", "#5a8375"]


def _format(measure_key: str) -> str:
    return ",.0f" if MEASURES[measure_key].decimals == 0 else ",.2f"


def make_trend_chart(rows: pd.DataFrame, measure_key: str) -> go.Figure:
    metric = MEASURES[measure_key]
    fig = px.line(
        rows, x="År", y="Värde", color="Region", markers=True,
        labels={"År": "Year", "Värde": metric.label, "Region": "Region"},
        color_discrete_sequence=PALETTE,
    )
    fmt = _format(measure_key)
    fig.update_traces(
        line=dict(width=2.5), marker=dict(size=8),
        hovertemplate=f"<b>%{{fullData.name}}</b><br>Year %{{x}}<br>%{{y:{fmt}}} {metric.unit}<extra></extra>",
    )
    fig.update_layout(
        template="plotly_white", height=390, margin=dict(l=10, r=10, t=20, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.03, x=0),
        hovermode="closest",
    )
    fig.update_xaxes(dtick=1, tickformat="d")
    fig.update_yaxes(rangemode="tozero", title=metric.label)
    return fig


def make_regional_chart(rows: pd.DataFrame, measure_key: str, national_reference: float | None) -> go.Figure:
    metric = MEASURES[measure_key]
    # Keep missing source measurements in the associated table and export, not
    # as empty bars that would imply a place in the regional ranking.
    plotted = rows.dropna(subset=["Värde"])
    fig = px.bar(
        plotted, x="Värde", y="Region", orientation="h",
        labels={"Värde": metric.label, "Region": "Region"},
        color_discrete_sequence=PALETTE[:1],
    )
    fmt = _format(measure_key)
    fig.update_traces(
        texttemplate=f"%{{x:{fmt}}}", textposition="outside", cliponaxis=False,
        hovertemplate=f"<b>%{{y}}</b><br>%{{x:{fmt}}} {metric.unit}<extra></extra>",
    )
    if national_reference is not None:
        fig.add_vline(
            x=national_reference, line_color="#a13e58", line_dash="dash", line_width=2,
            annotation_text="Riket (reference)", annotation_position="top left",
            annotation_font_color="#a13e58",
        )
    fig.update_layout(
        template="plotly_white", height=max(460, 27 * len(rows) + 110),
        margin=dict(l=10, r=90, t=35, b=15), showlegend=False,
    )
    fig.update_xaxes(title=metric.label, rangemode="tozero")
    fig.update_yaxes(title=None)
    return fig


def make_demographic_chart(rows: pd.DataFrame, measure_key: str, dimension: str) -> go.Figure:
    metric = MEASURES[measure_key]
    if dimension not in {"age", "sex"}:
        raise ValueError("dimension must be age or sex")
    plotted = rows.dropna(subset=["Värde"])
    fmt = _format(measure_key)
    if dimension == "age":
        # Eighteen labels on a horizontal axis are unreadable at common laptop
        # widths. Horizontal bars keep the original age ordering legible.
        fig = px.bar(
            plotted, x="Värde", y="Jämförelsegrupp", orientation="h",
            labels={"Jämförelsegrupp": "Age group", "Värde": metric.label},
            color_discrete_sequence=PALETTE[:1],
        )
        fig.update_traces(
            hovertemplate=f"<b>%{{y}}</b><br>%{{x:{fmt}}} {metric.unit}<extra></extra>"
        )
        fig.update_xaxes(title=metric.label, rangemode="tozero")
        fig.update_yaxes(
            title=None, categoryorder="array",
            categoryarray=list(reversed(plotted["Jämförelsegrupp"].tolist())),
        )
        height = max(460, 27 * len(plotted) + 110)
        bottom_margin = 15
    else:
        fig = px.bar(
            plotted, x="Jämförelsegrupp", y="Värde",
            labels={"Jämförelsegrupp": "Sex", "Värde": metric.label},
            color_discrete_sequence=PALETTE[:1],
        )
        fig.update_traces(
            hovertemplate=f"<b>%{{x}}</b><br>%{{y:{fmt}}} {metric.unit}<extra></extra>"
        )
        fig.update_xaxes(title=None)
        fig.update_yaxes(title=metric.label, rangemode="tozero")
        height = 330
        bottom_margin = 35
    fig.update_layout(
        template="plotly_white", height=height,
        margin=dict(l=8, r=8, t=15, b=bottom_margin), showlegend=False,
    )
    return fig
