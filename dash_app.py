from dash import Dash, dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sqlite3
import time
from datetime import datetime, timedelta

# --------------------------------------------------------------------------------
# Global Config
# --------------------------------------------------------------------------------

DB_NAME = "database_name.db"  # One global var for the DB name

# --------------------------------------------------------------------------------
# Helper functions
# --------------------------------------------------------------------------------

def generate_stamp(time_str):
    """
    Converts 'YYYY-mm-dd HH:MM:SS' to a UNIX timestamp.
    Returns -1 if there's a parsing error.
    """
    try:
        time_strip = time.strptime(time_str.strip(), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        print(f"Bad format of given time: {time_str}")
        return -1
    return int(time.mktime(time_strip))


def get_data_range():
    """
    Retrieve the earliest and latest timestamps from the ACTUAL and TOTAL tables.
    Returns a dictionary with the range for each table:
      {
        "ACTUAL": {"min_time": "...", "max_time": "..."},
        "TOTAL":  {"min_time": "...", "max_time": "..."}
      }
    """
    with sqlite3.connect(DB_NAME) as cnx:
        range_query = """
        SELECT 
            MIN(UTC_TIME) as min_time, 
            MAX(UTC_TIME) as max_time 
        FROM {table_name}
        """

        tables = ['ACTUAL', 'TOTAL']
        data_ranges = {}
        for table in tables:
            result = cnx.execute(range_query.format(table_name=table)).fetchone()
            if result:
                min_time, max_time = result
                data_ranges[table] = {
                    "min_time": (datetime.utcfromtimestamp(min_time).strftime('%Y-%m-%d %H:%M:%S')
                                 if min_time else None),
                    "max_time": (datetime.utcfromtimestamp(max_time).strftime('%Y-%m-%d %H:%M:%S')
                                 if max_time else None)
                }
            else:
                data_ranges[table] = {"min_time": None, "max_time": None}
    return data_ranges


def map_display_var_to_db_cols(display_var):
    """
    For 'IN', return [U_IN, V_IN, W_IN].
    For 'OUT', return [U_OUT, V_OUT, W_OUT].
    etc.
    """
    if display_var == "IN":
        return ["U_IN", "V_IN", "W_IN"]
    elif display_var == "OUT":
        return ["U_OUT", "V_OUT", "W_OUT"]
    else:
        # For ATLAS, BUPI, RENDER it's just that column
        return [display_var]


def build_column_list(selected_display_vars):
    """
    Given a list of user-chosen "display variables" (like IN, OUT, BUPI, RENDER),
    return the actual DB columns needed.
    """
    needed_cols = set()
    for dv in selected_display_vars:
        needed_cols.update(map_display_var_to_db_cols(dv))
    return list(needed_cols)


def get_period_options(min_date, max_date):
    """
    Given min_date and max_date (YYYY-MM-DD strings),
    return a dictionary with possible selections for year/month/week/day.
    """
    if not min_date or not max_date:
        return {"year": [], "month": [], "week": [], "day": []}

    start = pd.to_datetime(min_date)
    end = pd.to_datetime(max_date)

    years = [{"label": str(y), "value": str(y)} for y in pd.period_range(start, end, freq="Y").year]
    months = [{"label": p.strftime("%Y-%m"), "value": p.strftime("%Y-%m")} for p in
              pd.period_range(start, end, freq="M")]
    weeks = [
        {"label": p.start_time.strftime("%Y-%m-%d"), "value": p.start_time.strftime("%Y-%m-%d")}
        for p in pd.period_range(start, end, freq="W-MON")
    ]
    days = [
        {"label": d.strftime("%Y-%m-%d"), "value": d.strftime("%Y-%m-%d")}
        for d in pd.date_range(start, end, freq="D")
    ]

    return {"year": years, "month": months, "week": weeks, "day": days}


def compute_start_end(unit, value):
    """
    For a given time unit ('year', 'month', 'week', 'day') and selected value,
    compute start_date and end_date strings (YYYY-MM-DD).
    """
    if not unit or not value:
        return None, None

    if unit == "year":
        start = f"{value}-01-01"
        end = f"{value}-12-31"
    elif unit == "month":
        start = f"{value}-01"
        end = (pd.to_datetime(start) + pd.offsets.MonthEnd(0)).strftime("%Y-%m-%d")
    elif unit == "week":
        start = value
        end = (pd.to_datetime(start) + pd.Timedelta(days=6)).strftime("%Y-%m-%d")
    else:  # 'day'
        start = value
        end = value

    return start, end

def query_data_actual_advanced(start_dt_str, end_dt_str, needed_db_cols, step):
    """
    Retrieves only step-sampled rows + daily maxima from the 'ACTUAL' table
    for the chosen columns (needed_db_cols) within [start_dt_str, end_dt_str].

    - start_dt_str/end_dt_str: 'YYYY-mm-dd HH:MM:SS'
    - needed_db_cols: list of actual columns, e.g. ["U_IN","V_IN","W_IN"]
    - step: integer (>=1), for every-nth row.

    Returns a DataFrame with columns:
       [UTC_TIME, variable, value, is_max]
    where:
       - variable is e.g. "U_IN" or "ATLAS"
       - is_max is 0 or 1 (1 means daily max row)
    """
    stamp_od = generate_stamp(start_dt_str)
    stamp_do = generate_stamp(end_dt_str)
    if stamp_od == -1 or stamp_do == -1:
        print(f"Invalid timestamps: {start_dt_str}, {end_dt_str}")
        return pd.DataFrame()

    # Safety check
    if not needed_db_cols:
        return pd.DataFrame()

    # Build a subquery that "unions" each selected column as (UTC_TIME, variable, value)
    # so we effectively "melt" it at the SQL level
    col_subqueries = []
    for c in needed_db_cols:
        col_subqueries.append(f"""
            SELECT UTC_TIME, '{c}' AS variable, {c} AS value
            FROM ACTUAL
            WHERE UTC_TIME BETWEEN {stamp_od} AND {stamp_do}
        """)
    base_sql = " UNION ALL ".join(col_subqueries)

    # We'll use window functions to:
    # 1) assign row_number "global_rn" within each variable (for stepping),
    # 2) assign row_number "daily_rn" within each variable/day (for daily maxima).
    # Then define two subqueries: "stepped" picks where (global_rn - 1) % step=0,
    # and "dailymax" picks the row with daily_rn=1 (the row of max value each day).
    # Finally we UNION them to produce the final set.
    sql = f"""
    WITH base AS (
        {base_sql}
    ),
    NumberedAll AS (
        SELECT
          b.UTC_TIME,
          b.variable,
          b.value,
          ROW_NUMBER() OVER (
            PARTITION BY b.variable
            ORDER BY b.UTC_TIME
          ) AS global_rn,
          ROW_NUMBER() OVER (
            PARTITION BY b.variable, date(b.UTC_TIME, 'unixepoch')
            ORDER BY b.value DESC
          ) AS daily_rn
        FROM base b
    ),
    stepped AS (
        SELECT
          UTC_TIME,
          variable,
          value
        FROM NumberedAll
        WHERE (global_rn - 1) % {step} = 0
    ),
    dailymax AS (
        SELECT
          UTC_TIME,
          variable,
          value
        FROM NumberedAll
        WHERE daily_rn = 1
    ),
    final AS (
        SELECT UTC_TIME, variable, value, 0 AS is_max
        FROM stepped
        UNION ALL
        SELECT UTC_TIME, variable, value, 1 AS is_max
        FROM dailymax
    )
    SELECT *
    FROM final
    ORDER BY variable, UTC_TIME
    """

    with sqlite3.connect(DB_NAME) as cnx:
        df = pd.read_sql_query(sql, cnx)
    return df


def query_data_total(start_dt, end_dt):
    """
    Query the 'TOTAL' table for data between start_dt and end_dt (inclusive).
    Returns columns: UTC_TIME, U_IN, V_IN, W_IN, ATLAS, BUPI, RENDER
    """
    stamp_od = generate_stamp(start_dt)
    stamp_do = generate_stamp(end_dt)
    if stamp_od == -1 or stamp_do == -1:
        print(f"Invalid timestamps: {start_dt}, {end_dt}")
        return pd.DataFrame()

    sql_query = f"""
    SELECT UTC_TIME, U_IN, V_IN, W_IN, ATLAS, BUPI, RENDER
    FROM TOTAL
    WHERE UTC_TIME BETWEEN {stamp_od} AND {stamp_do}
    ORDER BY UTC_TIME
    """
    with sqlite3.connect(DB_NAME) as cnx:
        df = pd.read_sql_query(sql_query, cnx)
    return df


# --------------------------------------------------------------------------------
# Dash App
# --------------------------------------------------------------------------------

app = Dash(__name__, suppress_callback_exceptions=True)

# 1) Get the min/max date info for the ACTUAL & TOTAL tables
data_ranges = get_data_range()

# For ACTUAL
actual_min_full = data_ranges['ACTUAL']['min_time']
actual_max_full = data_ranges['ACTUAL']['max_time']
if actual_min_full:
    actual_min_date = actual_min_full.split(" ")[0]  # e.g. "2024-04-02"
else:
    actual_min_date = None
if actual_max_full:
    actual_max_date = actual_max_full.split(" ")[0]
else:
    actual_max_date = None

# For TOTAl
total_min_full = data_ranges['TOTAL']['min_time']
total_max_full = data_ranges['TOTAL']['max_time']
if total_min_full:
    total_min_date = total_min_full.split(" ")[0]
else:
    total_min_date = None
if total_max_full:
    total_max_date = total_max_full.split(" ")[0]
else:
    total_max_date = None

period_options_act = get_period_options(actual_min_date, actual_max_date)
period_options_tot = get_period_options(total_min_date, total_max_date)

default_unit_act = "day" if actual_min_date else None
default_value_act = actual_min_date
default_unit_tot = "day" if total_min_date else None
default_value_tot = total_min_date

range_text_act = f"Databáze (ACTUAL) obsahuje data od {actual_min_date} do {actual_max_date}"
range_text_tot = f"Databáze (TOTAL) obsahuje data od {total_min_date} do {total_max_date}"

# 2) Build Layout
app.layout = html.Div([
    # Main title
    html.H1("NAME", style={"color": "green"}),

    # Memory Store for 'TOTAL' data
    dcc.Store(id="df-store-total", storage_type="memory"),

    html.Div([
        html.H3("Závislost příkonu na čase"),
        html.Div(style={"height": "10px"}),
        html.Div(range_text_act, style={"margin-bottom": "20px"}),
        html.Div([
            html.Div([
                html.Div([
                    dcc.RadioItems(
                        id="time-unit-actual",
                        options=[
                            {"label": "Rok", "value": "year"},
                            {"label": "Měsíc", "value": "month"},
                            {"label": "Týden", "value": "week"},
                            {"label": "Den", "value": "day"},
                        ],
                        value=default_unit_act,
                        inline=True,
                        labelStyle={"margin-right": "10px"}
                    ),
                    dcc.Dropdown(
                        id="time-value-actual",
                        options=period_options_act.get(default_unit_act, []),
                        value=default_value_act,
                        style={"width": "200px", "margin-left": "10px"}
                    ),
                ], style={"display": "flex", "align-items": "center", "margin-bottom": "10px"}),
                dcc.Loading(
                    id="loading-actual",
                    type="circle",
                    children=[dcc.Graph(id="consumption_vs_time")]
                ),
                html.Div(id="actual-data-info", style={"margin-top": "30px"})
            ], style={"flex": "1", "display": "flex", "flex-direction": "column"}),
            html.Div([
                html.Span("VYBER SI, KTERÁ DATA ZOBRAZÍŠ NA GRAFU (ACTUAL):"),
                dcc.Checklist(
                    id="variable-checklist",
                    options=[
                        {'label': 'IN', 'value': 'IN'},
                        {'label': 'OUT', 'value': 'OUT'},
                        {'label': 'ATLAS', 'value': 'ATLAS'},
                        {'label': 'BUPI', 'value': 'BUPI'},
                        {'label': 'RENDER', 'value': 'RENDER'},
                    ],
                    value=[],
                    style={
                        "display": "flex",
                        "flex-direction": "column",
                        "gap": "10px"
                    }
                ),
            ], style={"margin-left": "20px", "display": "flex", "flex-direction": "column"})
        ], style={"display": "flex"})
    ]),
    # ------------------- TOTAL LAYOUT ------------------- #
    html.Div([
        html.H3("Celková spotřeba podle času"),
        html.Div([
            dcc.RadioItems(
                id="time-unit-total",
                options=[
                    {"label": "Rok", "value": "year"},
                    {"label": "Měsíc", "value": "month"},
                    {"label": "Týden", "value": "week"},
                    {"label": "Den", "value": "day"},
                ],
                value=default_unit_tot,
                inline=True,
                labelStyle={"margin-right": "10px"}
            ),
            dcc.Dropdown(
                id="time-value-total",
                options=period_options_tot.get(default_unit_tot, []),
                value=default_value_tot,
                style={"width": "200px", "margin-left": "10px"}
            )
        ], style={"display": "flex", "align-items": "center", "margin-bottom": "20px"}),
        html.Div(range_text_tot, style={"margin-bottom": "20px"}),

        # Aggregation Dropdown & Label on top
        html.Div([
            html.Span("VYBER SI FORMÁT ZOBRAZENÍ (TOTAL)", style={"margin-bottom": "10px", "margin-top": "10px"}),
            dcc.Dropdown(
                id='aggregation-dropdown',
                options=[                    {'label': 'Dny', 'value': 'D'},
                    {'label': 'Týdny', 'value': 'T'},
                    {'label': 'Měsíce', 'value': 'M'},
                    {'label': 'Roky', 'value': 'R'},
                    {'label': 'Total', 'value': 'To'},
                ],
                value='T',
                style={"margin-right": "5px"}
            ),
        ], style={"display": "flex", "flex-direction": "column", "margin-bottom": "20px"}),

        # Bar Mode
        html.Div([
            html.Span(
                "FORMÁT SLOUPCŮ",
                style={
                    "font-weight": "bold",
                    "margin-right": "10px",
                    "align-self": "center"
                }
            ),
            dcc.RadioItems(
                id='bar-mode',
                options=[
                    {'label': 'Stacked', 'value': 'stack'},
                    {'label': 'Grouped', 'value': 'group'},
                ],
                value='stack',
                inline=True,
                style={
                    "margin-bottom": "20px",
                    "margin-top": "20px"
                }
            ),
        ], style={"display": "flex", "align-items": "center"}),

        # Info about what the TOTAL graph is displaying
        html.Div(id="total-data-info", style={"margin-bottom": "20px"}),

        # The TOTAL graph with a loading indicator
        dcc.Loading(
            id="loading-total",
            type="circle",
            children=[dcc.Graph(id="consumption_vs_time_total")]
        ),
    ]),
])


# --------------------------------------------------------------------------------
# Time selector option callbacks
# --------------------------------------------------------------------------------
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


# --------------------------------------------------------------------------------
# ACTUAL Graph Callback
# --------------------------------------------------------------------------------@app.callback(
    [
        Output("consumption_vs_time", "figure"),
        Output("actual-data-info", "children"),
    ],
    [
        Input("time-unit-actual", "value"),
        Input("time-value-actual", "value"),
        Input("variable-checklist", "value"),
    ]

def update_actual_graph(time_unit, time_value, selected_vars):
    start_date, end_date = compute_start_end(time_unit, time_value)
    if not start_date or not end_date:
        return go.Figure(), "Graf teď nezobrazuje žádná data (není vybráno datum)"

    start_dt_obj = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt_obj = datetime.strptime(end_date, "%Y-%m-%d")
    diff_days = (end_dt_obj - start_dt_obj).days
    if diff_days < 0:
        diff_days = 0

    step = 10 * (diff_days // 7)
    if step < 1:
        step = 1

    info_text = f"Data od {start_date} do {end_date}"

    if not selected_vars:
        fig = go.Figure()
        return fig, info_text + " - bez vybraných sloupců."

    start_dt_str = f"{start_date} 00:00:00"
    end_dt_str = f"{end_date} 23:59:59"

    needed_db_cols = build_column_list(selected_vars)

    df = query_data_actual_advanced(start_dt_str, end_dt_str, needed_db_cols, step)
    if df.empty:
        return go.Figure(), info_text + " - v databázi nejsou žádná data."

    df['UTC_STAMP'] = pd.to_datetime(df['UTC_TIME'], unit='s', errors='coerce')
    df.sort_values(["variable", "UTC_STAMP"], inplace=True)

    fig = go.Figure()
    unique_vars = df['variable'].unique()
    for col_name in unique_vars:
        sub = df[df['variable'] == col_name]
        normal_rows = sub[sub['is_max'] == 0]
        if not normal_rows.empty:
            fig.add_trace(
                go.Scattergl(
                    x=normal_rows["UTC_STAMP"],
                    y=normal_rows["value"],
                    mode="lines",
                    name=f"{col_name} (sampled)"
                )
            )
        max_rows = sub[sub['is_max'] == 1]
        if not max_rows.empty:
            fig.add_trace(
                go.Scattergl(
                    x=max_rows["UTC_STAMP"],
                    y=max_rows["value"],
                    mode="markers",
                    marker=dict(size=10, symbol="diamond-open"),
                    name=f"{col_name} (max)"
                )
            )

    fig.update_layout(
        title="Závislost příkonu na čase",
        yaxis_title="kW",
        xaxis_title="Datum",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    info_text += f" | Zobrazené sloupce: {', '.join(selected_vars)} | Hustota = 1/{step}."

    return fig, html.Div(info_text, style={"margin-top": "30px"})

# --------------------------------------------------------------------------------
# TOTAL Callbacks
# --------------------------------------------------------------------------------

@app.callback(
    Output("df-store-total", "data"),
    [
        Input("time-unit-total", "value"),
        Input("time-value-total", "value")
    ]
)
def update_total_data_store(time_unit, time_value):
    start_date, end_date = compute_start_end(time_unit, time_value)
    if not start_date or not end_date:
        print("No start or end date provided for TOTAL data")
        return None

    start_dt = f"{start_date} 00:00:00"
    end_dt = f"{end_date} 23:59:59"
    df_total = query_data_total(start_dt, end_dt)
    if df_total.empty:
        print("No data retrieved for TOTAL table")
        return None

    # Melt the TOTAL table
    df_total = pd.melt(
        df_total.rename(columns={"UTC_TIME": "UTC_STAMP"}),
        id_vars=["UTC_STAMP"],
        value_vars=["U_IN", "V_IN", "W_IN", "ATLAS", "BUPI", "RENDER"],
        var_name="variable",
        value_name="value"
    )

    # Add aggregated variables (SUM_IN, MACHINES) if needed
    df_sum_in = df_total[df_total['variable'].isin(["U_IN", "V_IN", "W_IN"])]
    df_sum_in = df_sum_in.groupby("UTC_STAMP", as_index=False)["value"].sum()
    df_sum_in["variable"] = "SUM_IN"

    df_sum_machines = df_total[df_total['variable'].isin(["ATLAS", "BUPI", "RENDER"])]
    df_sum_machines = df_sum_machines.groupby("UTC_STAMP", as_index=False)["value"].sum()
    df_sum_machines["variable"] = "MACHINES"

    df_total = pd.concat([df_total, df_sum_in, df_sum_machines], ignore_index=True)

    return df_total.to_dict("records")


@app.callback(
    [
        Output("consumption_vs_time_total", "figure"),
        Output("total-data-info", "children")
    ],
    [
        Input("df-store-total", "data"),
        Input("aggregation-dropdown", "value"),
        Input("bar-mode", "value"),
        Input("time-unit-total", "value"),
        Input("time-value-total", "value")
    ]
)
def update_total_graph(stored_data, aggregation_level, bar_mode, time_unit, time_value):
    start_date, end_date = compute_start_end(time_unit, time_value)
    if not stored_data or not start_date or not end_date:
        print("No data available in TOTAL store or missing date range.")
        return px.bar(title="No data"), "Graf teď nezobrazuje žádná data"

    df_total = pd.DataFrame(stored_data)
    # Convert UTC_STAMP to datetime
    df_total['time'] = pd.to_datetime(df_total['UTC_STAMP'], unit='s', errors='coerce')
    if df_total['time'].isna().any():
        print("Time conversion failed for some rows.")
        return px.bar(title="Time conversion error"), "Graf teď nezobrazuje žádná data"

    # Aggregation
    if aggregation_level == 'T':  # Weekly
        df_total['period'] = df_total['time'].dt.to_period('W').apply(lambda x: x.start_time)
    elif aggregation_level == 'M':  # Monthly
        df_total['period'] = df_total['time'].dt.to_period('M').apply(lambda x: x.start_time)
    elif aggregation_level == 'D':  # Daily
        df_total['period'] = df_total['time'].dt.to_period('D').apply(lambda x: x.start_time)
    elif aggregation_level == 'R':  # Yearly
        df_total['period'] = df_total['time'].dt.to_period('Y').apply(lambda x: x.start_time)
    else:
        df_total['period'] = "All Data"

    # Calculate difference between first and last for each period/variable
    df_agg = df_total.sort_values(['period', 'time']).groupby(['period', 'variable'], as_index=False).agg(
        first_value=('value', 'first'),
        last_value=('value', 'last')
    )
    df_agg['value'] = df_agg['last_value'] - df_agg['first_value']
    df_agg = df_agg[['period', 'variable', 'value']]

    if df_agg.empty:
        return px.bar(title="No data after aggregation"), "Graf teď nezobrazuje žádná data"

    fig = px.bar(
        df_agg,
        x="period",
        y="value",
        color="variable",
        barmode=bar_mode,
        title="Spotřebovaná energie",
        labels={"period": "DATUM", "value": "kWh"}
    )

    fig.update_layout(
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    info_text = f"Graf teď zobrazuje data od {start_date} do {end_date}"
    # Also place it more down for TOTAl
    return fig, html.Div(info_text, style={"margin-top": "30px"})


# --------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------

if __name__ == "__main__":
    # Optional: print out the range info
    print("Data ranges for tables:")
    for table_name, rng in data_ranges.items():
        print(f"{table_name}: From {rng['min_time']} to {rng['max_time']}")

    app.run(debug=True, port=8000, host='127.0.0.1')
