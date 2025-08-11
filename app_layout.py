from dash import dcc, html

from config import (
    TITLE_MARGIN_LEFT,
    TITLE_MARGIN_TOP,
    ACTUAL_GRAPH_RIGHT,
    ACTUAL_GRAPH_UP,
    TOTAL_GRAPH_RIGHT,
    TOTAL_GRAPH_UP,
    ACTUAL_VARIABLES_RIGHT,
    ACTUAL_VARIABLES_UP,
    ACTUAL_PERIOD_RIGHT,
    ACTUAL_PERIOD_UP,
    ACTUAL_DATEPICKER_RIGHT,
    ACTUAL_DATEPICKER_UP,
    TOTAL_PERIOD_RIGHT,
    TOTAL_PERIOD_UP,
    TOTAL_DATEPICKER_RIGHT,
    TOTAL_DATEPICKER_UP,
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
        return html.Div(
            [
                self._build_header(),
                dcc.Store(id="df-store-total", storage_type="memory"),
                self._build_actual_section(),
                self._build_total_section(),
            ]
        )

    def _build_header(self):
        return html.H1(
            "NAME",
            style={
                "color": "green",
                "margin-left": TITLE_MARGIN_LEFT,
                "margin-top": TITLE_MARGIN_TOP,
            },
        )

    # -------- ACTUAL section --------
    def _build_actual_section(self):
        return html.Div(
            [
                html.H3("Závislost příkonu na čase"),
                html.Div(style={"height": "10px"}),
                html.Div(self.range_text_act, style={"margin-bottom": "20px"}),
                self._build_actual_period_controls(),
                self._build_actual_graph_section(),
                html.Div(id="actual-data-info", style={"margin-top": "30px"}),
            ],
            style={"display": "flex", "flex-direction": "column"},
        )

    def _build_actual_period_controls(self):
        """Dropdowns for selecting period in the ACTUAL section."""
        return html.Div(
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
                        "margin-left": ACTUAL_PERIOD_RIGHT,
                        "margin-top": -ACTUAL_PERIOD_UP,
                    },
                ),
                dcc.Dropdown(
                    id="time-value-actual",
                    options=self.period_options_act.get(self.default_unit_act, []),
                    value=self.default_value_act,
                    style={
                        "width": "200px",
                        "margin-left": 10 + ACTUAL_DATEPICKER_RIGHT,
                        "border-radius": "20px",
                        "margin-top": -ACTUAL_DATEPICKER_UP,
                    },
                ),
            ],
            style={
                "display": "flex",
                "align-items": "center",
                "gap": "10px",
                "flex-wrap": "nowrap",
                "margin-bottom": "10px",
            },
        )

    def _build_actual_graph_section(self):
        """Graph with variable checklist for the ACTUAL section."""
        return html.Div(
            [
                dcc.Loading(
                    id="loading-actual",
                    type="circle",
                    children=[
                        dcc.Graph(
                            id="consumption_vs_time",
                            style={
                                "margin-left": ACTUAL_GRAPH_RIGHT,
                                "margin-top": -ACTUAL_GRAPH_UP,
                                "width": "1000px",
                            },
                        )
                    ],
                    style={"flex": "1"},
                ),
                html.Div(
                    [
                        html.Span(
                            ""  # "VYBER SI, KTERÁ DATA ZOBRAZÍŠ NA GRAFU (ACTUAL):",
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
                        "margin-left": 20 + ACTUAL_VARIABLES_RIGHT,
                        "display": "flex",
                        "flex-direction": "column",
                        "margin-top": -ACTUAL_VARIABLES_UP,
                        "flex": "0 0 260px",
                    },
                ),
            ],
            style={"display": "flex", "align-items": "stretch"},
        )

    # -------- TOTAL section --------
    def _build_total_section(self):
        return html.Div(
            [
                html.H3("Celková spotřeba podle času"),
                self._build_total_period_controls(),
                html.Div(self.range_text_tot, style={"margin-bottom": "20px"}),
                self._build_total_aggregation_controls(),
                self._build_total_bar_mode_controls(),
                html.Div(id="total-data-info", style={"margin-bottom": "20px"}),
                self._build_total_graph(),
            ]
        )

    def _build_total_period_controls(self):
        """Dropdowns for selecting period in the TOTAL section."""
        return html.Div(
            [
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
                    style={
                        "width": "150px",
                        "border-radius": "20px",
                        "margin-left": TOTAL_PERIOD_RIGHT,
                        "margin-top": -TOTAL_PERIOD_UP,
                    },
                ),
                dcc.Dropdown(
                    id="time-value-total",
                    options=self.period_options_tot.get(self.default_unit_tot, []),
                    value=self.default_value_tot,
                    style={
                        "width": "200px",
                        "margin-left": 10 + TOTAL_DATEPICKER_RIGHT,
                        "border-radius": "20px",
                        "margin-top": -TOTAL_DATEPICKER_UP,
                    },
                ),
            ],
            style={
                "display": "flex",
                "align-items": "center",
                "gap": "10px",
                "flex-wrap": "nowrap",
                "margin-bottom": "20px",
            },
        )

    def _build_total_aggregation_controls(self):
        """Dropdown for aggregation selection in the TOTAL section."""
        return html.Div(
            [
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
            ],
            style={
                "display": "flex",
                "flex-direction": "column",
                "margin-bottom": "20px",
            },
        )

    def _build_total_bar_mode_controls(self):
        """Radio buttons for bar mode selection in the TOTAL section."""
        return html.Div(
            [
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
            ],
            style={"display": "flex", "align-items": "center"},
        )

    def _build_total_graph(self):
        """Graph wrapped in a loading indicator for the TOTAL section."""
        return dcc.Loading(
            id="loading-total",
            type="circle",
            children=[
                dcc.Graph(
                    id="consumption_vs_time_total",
                    style={
                        "margin-left": TOTAL_GRAPH_RIGHT,
                        "margin-top": -TOTAL_GRAPH_UP,
                    },
                )
            ],
        )
