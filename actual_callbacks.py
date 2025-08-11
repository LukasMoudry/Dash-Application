from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dash import Input, Output, html

from data_utils import DataFetcher

def compute_sampling_step(start_date: str, end_date: str) -> int:
    """Return a sampling step based on the span between two dates."""
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    diff_days = max((end_dt - start_dt).days, 0)
    return max(1, 10 * (diff_days // 7))


def fetch_actual_dataframe(
    data_fetcher: DataFetcher,
    start_dt: str,
    end_dt: str,
    selected_vars,
    step: int,
):
    """Query and prepare ACTUAL data for plotting."""
    needed_db_cols = DataFetcher.build_column_list(selected_vars)
    df = data_fetcher.query_data_actual_advanced(start_dt, end_dt, needed_db_cols, step)
    if df.empty:
        return df
    df["UTC_STAMP"] = pd.to_datetime(df["UTC_TIME"], unit="s", errors="coerce")
    df.sort_values(["variable", "UTC_STAMP"], inplace=True)
    return df


def build_actual_figure(df: pd.DataFrame) -> go.Figure:
    """Create a plotly figure for ACTUAL data."""
    fig = go.Figure()
    for col_name in df["variable"].unique():
        sub = df[df["variable"] == col_name]
        normal_rows = sub[sub["is_max"] == 0]
        if not normal_rows.empty:
            fig.add_trace(
                go.Scattergl(
                    x=normal_rows["UTC_STAMP"],
                    y=normal_rows["value"],
                    mode="lines",
                    name=f"{col_name} (sampled)",
                )
            )
        max_rows = sub[sub["is_max"] == 1]
        if not max_rows.empty:
            fig.add_trace(
                go.Scattergl(
                    x=max_rows["UTC_STAMP"],
                    y=max_rows["value"],
                    mode="markers",
                    marker=dict(size=10, symbol="diamond-open"),
                    name=f"{col_name} (max)",
                )
            )
    fig.update_layout(
        template="plotly_white",
        colorway=px.colors.qualitative.Set2,
        title="",
        yaxis_title="kW",
        xaxis_title="",
        hovermode="x unified",
        legend=dict(
            title="Variables",
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        margin=dict(l=40, r=20, t=40, b=40),
    )
    return fig


def register_actual_callbacks(app, data_fetcher, period_options):
    """Register callbacks for ACTUAL data interactions."""

    @app.callback(
        [Output("time-value-actual", "options"), Output("time-value-actual", "value")],
        Input("time-unit-actual", "value"),
    )
    def update_time_value_actual(unit):
        opts = period_options.get(unit, [])
        val = opts[0]["value"] if opts else None
        return opts, val

    @app.callback(
        [Output("consumption_vs_time", "figure"), Output("actual-data-info", "children")],
        [
            Input("time-unit-actual", "value"),
            Input("time-value-actual", "value"),
            Input("variable-checklist", "value"),
        ],
    )
    def update_actual_graph(time_unit, time_value, selected_vars):
        start_date, end_date = DataFetcher.compute_start_end(time_unit, time_value)
        if not start_date or not end_date:
            return go.Figure(), "Graf teď nezobrazuje žádná data (není vybráno datum)"

        step = compute_sampling_step(start_date, end_date)

        info_text = f"Data od {start_date} do {end_date}"
        if not selected_vars:
            return go.Figure(), info_text + " - bez vybraných sloupců."

        start_dt_str = f"{start_date} 00:00:00"
        end_dt_str = f"{end_date} 23:59:59"
        df = fetch_actual_dataframe(data_fetcher, start_dt_str, end_dt_str, selected_vars, step)

        if df.empty:
            return go.Figure(), info_text + " - v databázi nejsou žádná data."

        fig = build_actual_figure(df)

        info_text += f" | Zobrazené sloupce: {', '.join(selected_vars)} | Hustota = 1/{step}."
        return fig, html.Div(info_text, style={"margin-top": "30px"})
