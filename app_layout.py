from dash import dcc, html

from config import (
    TITLE_MARGIN_LEFT,
    TITLE_MARGIN_TOP,
    SECTION_MARGIN_LEFT,
    SECTION_MARGIN_TOP,
)


class LayoutBuilder:
    """Constructs the Dash layout with movable offsets."""

    def __init__(
        self,
        period_options_act,
        period_options_tot,
        default_unit_act,
        default_value_act,
        default_unit_tot,
        default_value_tot,
        range_text_act,
        range_text_tot,
    ):
        self.period_options_act = period_options_act
        self.period_options_tot = period_options_tot
        self.default_unit_act = default_unit_act
        self.default_value_act = default_value_act
        self.default_unit_tot = default_unit_tot
        self.default_value_tot = default_value_tot
        self.range_text_act = range_text_act
        self.range_text_tot = range_text_tot

    def build_layout(self):
        """Return the root layout for the Dash application."""
        return html.Div([
            html.H1(
                "NAME",
                style={
                    "color": "green",
                    "margin-left": TITLE_MARGIN_LEFT,
                    "margin-top": TITLE_MARGIN_TOP,
                },
            ),
            dcc.Store(id="df-store-total", storage_type="memory"),
            html.Div([
                html.H3(
                    "Závislost příkonu na čase",
                    style={"margin-top": "10px"},
                ),
                html.Div(style={"height": "5px"}),
                html.Div(self.range_text_act, style={"margin-bottom": "20px"}),
                html.Div(
                    [
                        dcc.Dropdown(
                            id="time-unit-actual",
                            options=[
                                {"label": "Rok", "value": "year"},
                                {"label": "Měsíc", "value": "month"},
                                {"label": "Týden", "value": "week"},
                                {"label": "Den", "value": "day"},
                            ],
                            value=self.default_unit_act,
                            clearable=False,
                            style={
                                "width": "150px",
                                "border-radius": "20px",
                            },
                        ),
                        dcc.Dropdown(
                            id="time-value-actual",
                            options=self.period_options_act.get(self.default_unit_act, []),
                            value=self.default_value_act,
                            style={
                                "width": "200px",
                                "margin-left": "10px",
                                "border-radius": "20px",
                            },
                        ),
                    ],
                    style={
                        "display": "flex",
                        "align-items": "center",
                        "margin-bottom": "10px",
                    },
                ),
                html.Div(
                    [
                        dcc.Loading(
                            id="loading-actual",
                            type="circle",
                            children=[
                                dcc.Graph(
                                    id="consumption_vs_time",
                                    style={
                                        "margin-left": SECTION_MARGIN_LEFT,
                                        "margin-top": SECTION_MARGIN_TOP,
                                        "height": "600px",
                                    },
                                )
                            ],
                        ),
                        html.Div(
                            [
                                html.Span(
                                    "VYBER SI, KTERÁ DATA ZOBRAZÍŠ NA GRAFU (ACTUAL):"
                                ),
                                dcc.Checklist(
                                    id="variable-checklist",
                                    options=[
                                        {"label": "IN", "value": "IN"},
                                        {"label": "OUT", "value": "OUT"},
                                        {"label": "ATLAS", "value": "ATLAS"},
                                        {"label": "BUPI", "value": "BUPI"},
                                        {"label": "RENDER", "value": "RENDER"},
                                    ],
                                    value=[],
                                    style={
                                        "display": "flex",
                                        "flex-direction": "column",
                                        "gap": "10px",
                                    },
                                ),
                            ],
                            style={
                                "margin-left": "20px",
                                "display": "flex",
                                "flex-direction": "column",
                                "margin-top": SECTION_MARGIN_TOP,
                            },
                        ),
                    ],
                    style={"display": "flex", "align-items": "flex-start"},
                ),
                html.Div(id="actual-data-info", style={"margin-top": "30px"}),
            ],
                style={"display": "flex", "flex-direction": "column"}
            ),
            html.Div([
                html.H3("Celková spotřeba podle času"),
                html.Div([
                    dcc.Dropdown(
                        id="time-unit-total",
                        options=[
                            {"label": "Rok", "value": "year"},
                            {"label": "Měsíc", "value": "month"},
                            {"label": "Týden", "value": "week"},
                            {"label": "Den", "value": "day"},
                        ],
                        value=self.default_unit_tot,
                        clearable=False,
                        style={"width": "150px", "border-radius": "20px"},
                    ),
                    dcc.Dropdown(
                        id="time-value-total",
                        options=self.period_options_tot.get(self.default_unit_tot, []),
                        value=self.default_value_tot,
                        style={
                            "width": "200px",
                            "margin-left": "10px",
                            "border-radius": "20px",
                        },
                    ),
                ], style={"display": "flex", "align-items": "center", "margin-bottom": "20px"}),
                html.Div(self.range_text_tot, style={"margin-bottom": "20px"}),
                html.Div([
                    html.Span(
                        "VYBER SI FORMÁT ZOBRAZENÍ (TOTAL)",
                        style={"margin-bottom": "10px", "margin-top": "10px"},
                    ),
                    dcc.Dropdown(
                        id="aggregation-dropdown",
                        options=[
                            {"label": "Dny", "value": "D"},
                            {"label": "Týdny", "value": "T"},
                            {"label": "Měsíce", "value": "M"},
                            {"label": "Roky", "value": "R"},
                            {"label": "Total", "value": "To"},
                        ],
                        value="T",
                        style={
                            "margin-right": "5px",
                            "border-radius": "20px",
                        },
                    ),
                ], style={"display": "flex", "flex-direction": "column", "margin-bottom": "20px"}),
                html.Div([
                    html.Span(
                        "FORMÁT SLOUPCŮ",
                        style={
                            "font-weight": "bold",
                            "margin-right": "10px",
                            "align-self": "center",
                        },
                    ),
                    dcc.RadioItems(
                        id="bar-mode",
                        options=[
                            {"label": "Stacked", "value": "stack"},
                            {"label": "Grouped", "value": "group"},
                        ],
                        value="stack",
                        inline=True,
                        style={"margin-bottom": "20px", "margin-top": "20px"},
                    ),
                ], style={"display": "flex", "align-items": "center"}),
                html.Div(id="total-data-info", style={"margin-bottom": "20px"}),
                dcc.Loading(
                    id="loading-total",
                    type="circle",
                    children=[
                        dcc.Graph(
                            id="consumption_vs_time_total",
                            style={
                                "margin-left": SECTION_MARGIN_LEFT,
                                "margin-top": SECTION_MARGIN_TOP,
                            },
                        )
                    ],
                ),
            ]),
        ])
