from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html

from config import DB_NAME
from data_utils import DataFetcher
from app_layout import LayoutBuilder

# ----------------------------------------------------------------------------
# App and data helpers
# ----------------------------------------------------------------------------
data_fetcher = DataFetcher(DB_NAME)
app = Dash(__name__, suppress_callback_exceptions=True)

# Retrieve range information for ACTUAL and TOTAL tables
data_ranges = data_fetcher.get_data_range()

# Extract min/max dates
actual_min_full = data_ranges["ACTUAL"]["min_time"]
actual_max_full = data_ranges["ACTUAL"]["max_time"]
actual_min_date = actual_min_full.split(" ")[0] if actual_min_full else None
actual_max_date = actual_max_full.split(" ")[0] if actual_max_full else None

total_min_full = data_ranges["TOTAL"]["min_time"]
total_max_full = data_ranges["TOTAL"]["max_time"]
total_min_date = total_min_full.split(" ")[0] if total_min_full else None
total_max_date = total_max_full.split(" ")[0] if total_max_full else None

# Build dropdown options and defaults
period_options_act = DataFetcher.get_period_options(actual_min_date, actual_max_date)
period_options_tot = DataFetcher.get_period_options(total_min_date, total_max_date)

default_unit_act = "day" if actual_min_date else None
default_value_act = actual_min_date
default_unit_tot = "day" if total_min_date else None
default_value_tot = total_min_date

range_text_act = f"Databáze (ACTUAL) obsahuje data od {actual_min_date} do {actual_max_date}"
range_text_tot = f"Databáze (TOTAL) obsahuje data od {total_min_date} do {total_max_date}"

# Build layout using a builder class
layout_builder = LayoutBuilder(
    period_options_act,
    period_options_tot,
    default_unit_act,
    default_value_act,
    default_unit_tot,
    default_value_tot,
    range_text_act,
    range_text_tot,
)
app.layout = layout_builder.build_layout()

# ----------------------------------------------------------------------------
# Time selector option callbacks
# ----------------------------------------------------------------------------
@app.callback(
    [Output("time-value-actual", "options"), Output("time-value-actual", "value")],
    Input("time-unit-actual", "value"),
)
def update_time_value_actual(unit):
    opts = period_options_act.get(unit, [])
    val = opts[0]["value"] if opts else None
    return opts, val


@app.callback(
    [Output("time-value-total", "options"), Output("time-value-total", "value")],
    Input("time-unit-total", "value"),
)
def update_time_value_total(unit):
    opts = period_options_tot.get(unit, [])
    val = opts[0]["value"] if opts else None
    return opts, val


# ----------------------------------------------------------------------------
# ACTUAL Graph Callback
# ----------------------------------------------------------------------------
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

    start_dt_obj = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt_obj = datetime.strptime(end_date, "%Y-%m-%d")
    diff_days = max((end_dt_obj - start_dt_obj).days, 0)
    step = max(1, 10 * (diff_days // 7))

    info_text = f"Data od {start_date} do {end_date}"
    if not selected_vars:
        return go.Figure(), info_text + " - bez vybraných sloupců."

    start_dt_str = f"{start_date} 00:00:00"
    end_dt_str = f"{end_date} 23:59:59"
    needed_db_cols = DataFetcher.build_column_list(selected_vars)
    df = data_fetcher.query_data_actual_advanced(start_dt_str, end_dt_str, needed_db_cols, step)
    if df.empty:
        return go.Figure(), info_text + " - v databázi nejsou žádná data."

    df["UTC_STAMP"] = pd.to_datetime(df["UTC_TIME"], unit="s", errors="coerce")
    df.sort_values(["variable", "UTC_STAMP"], inplace=True)

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
        title="Závislost příkonu na čase",
        yaxis_title="kW",
        xaxis_title="Datum",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    info_text += f" | Zobrazené sloupce: {', '.join(selected_vars)} | Hustota = 1/{step}."
    return fig, html.Div(info_text, style={"margin-top": "30px"})


# ----------------------------------------------------------------------------
# TOTAL Callbacks
# ----------------------------------------------------------------------------
@app.callback(
    Output("df-store-total", "data"),
    [Input("time-unit-total", "value"), Input("time-value-total", "value")],
)
def update_total_data_store(time_unit, time_value):
    start_date, end_date = DataFetcher.compute_start_end(time_unit, time_value)
    if not start_date or not end_date:
        return None

    start_dt = f"{start_date} 00:00:00"
    end_dt = f"{end_date} 23:59:59"
    df_total = data_fetcher.query_data_total(start_dt, end_dt)
    if df_total.empty:
        return None

    df_total = pd.melt(
        df_total.rename(columns={"UTC_TIME": "UTC_STAMP"}),
        id_vars=["UTC_STAMP"],
        value_vars=["U_IN", "V_IN", "W_IN", "ATLAS", "BUPI", "RENDER"],
        var_name="variable",
        value_name="value",
    )

    df_sum_in = df_total[df_total["variable"].isin(["U_IN", "V_IN", "W_IN"])]
    df_sum_in = df_sum_in.groupby("UTC_STAMP", as_index=False)["value"].sum()
    df_sum_in["variable"] = "SUM_IN"

    df_sum_machines = df_total[df_total["variable"].isin(["ATLAS", "BUPI", "RENDER"])]
    df_sum_machines = df_sum_machines.groupby("UTC_STAMP", as_index=False)["value"].sum()
    df_sum_machines["variable"] = "MACHINES"

    df_total = pd.concat([df_total, df_sum_in, df_sum_machines], ignore_index=True)
    return df_total.to_dict("records")


@app.callback(
    [Output("consumption_vs_time_total", "figure"), Output("total-data-info", "children")],
    [
        Input("df-store-total", "data"),
        Input("aggregation-dropdown", "value"),
        Input("bar-mode", "value"),
        Input("time-unit-total", "value"),
        Input("time-value-total", "value"),
    ],
)
def update_total_graph(stored_data, aggregation_level, bar_mode, time_unit, time_value):
    start_date, end_date = DataFetcher.compute_start_end(time_unit, time_value)
    if not stored_data or not start_date or not end_date:
        return px.bar(title="No data"), "Graf teď nezobrazuje žádná data"

    df_total = pd.DataFrame(stored_data)
    df_total["time"] = pd.to_datetime(df_total["UTC_STAMP"], unit="s", errors="coerce")
    if df_total["time"].isna().any():
        return px.bar(title="Time conversion error"), "Graf teď nezobrazuje žádná data"

    if aggregation_level == "T":
        df_total["period"] = df_total["time"].dt.to_period("W").apply(lambda x: x.start_time)
    elif aggregation_level == "M":
        df_total["period"] = df_total["time"].dt.to_period("M").apply(lambda x: x.start_time)
    elif aggregation_level == "D":
        df_total["period"] = df_total["time"].dt.to_period("D").apply(lambda x: x.start_time)
    elif aggregation_level == "R":
        df_total["period"] = df_total["time"].dt.to_period("Y").apply(lambda x: x.start_time)
    else:
        df_total["period"] = "All Data"

    df_agg = df_total.sort_values(["period", "time"]).groupby(["period", "variable"], as_index=False).agg(
        first_value=("value", "first"),
        last_value=("value", "last"),
    )
    df_agg["value"] = df_agg["last_value"] - df_agg["first_value"]
    df_agg = df_agg[["period", "variable", "value"]]
    if df_agg.empty:
        return px.bar(title="No data after aggregation"), "Graf teď nezobrazuje žádná data"

    fig = px.bar(
        df_agg,
        x="period",
        y="value",
        color="variable",
        barmode=bar_mode,
        title="Spotřebovaná energie",
        labels={"period": "DATUM", "value": "kWh"},
    )
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    info_text = f"Graf teď zobrazuje data od {start_date} do {end_date}"
    return fig, html.Div(info_text, style={"margin-top": "30px"})


# ----------------------------------------------------------------------------
# Main entry
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    print("Data ranges for tables:")
    for table_name, rng in data_ranges.items():
        print(f"{table_name}: From {rng['min_time']} to {rng['max_time']}")
    app.run(debug=True, port=8000, host="127.0.0.1")