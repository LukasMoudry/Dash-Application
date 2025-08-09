import pandas as pd
import plotly.express as px
from dash import Input, Output, html

from data_utils import DataFetcher


def register_total_callbacks(app, data_fetcher, period_options):
    """Register callbacks for TOTAL data interactions."""

    @app.callback(
        [Output("time-value-total", "options"), Output("time-value-total", "value")],
        Input("time-unit-total", "value"),
    )
    def update_time_value_total(unit):
        opts = period_options.get(unit, [])
        val = opts[0]["value"] if opts else None
        return opts, val

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
        df_sum_machines = df_sum_machines.groupby("UTC_STAMP", as_index=False)[
            "value"
        ].sum()
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

        df_agg = (
            df_total.sort_values(["period", "time"])
            .groupby(["period", "variable"], as_index=False)
            .agg(first_value=("value", "first"), last_value=("value", "last"))
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
        fig.update_layout(
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        info_text = f"Graf teď zobrazuje data od {start_date} do {end_date}"
        return fig, html.Div(info_text, style={"margin-top": "30px"})