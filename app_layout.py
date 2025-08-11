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
    TOTAL_VARIABLES_RIGHT,
    TOTAL_VARIABLES_UP,
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
            className="header-title",
            style={
                "margin-left": TITLE_MARGIN_LEFT,
                "margin-top": TITLE_MARGIN_TOP,
            },
        )

    # -------- ACTUAL section --------
    def _build_actual_section(self):
        return html.Div(
            [
                html.Div(self.range_text_act, style={"margin-bottom": "20px"}),
                self._build_actual_period_controls(),
                self._build_actual_graph_section(),
                self._build_actual_graph_name(),
                html.Div(id="actual-data-info", style={"margin-top": "30px"}),
            ],
            className="actual-section card",
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
                    className="select-dropdown",
                    style={
                        "width": "150px",
                        "margin-left": ACTUAL_PERIOD_RIGHT,
                        "margin-top": -ACTUAL_PERIOD_UP,
                    },
                ),
                dcc.Dropdown(
                    id="time-value-actual",
                    options=self.period_options_act.get(self.default_unit_act, []),
                    value=self.default_value_act,
                    className="select-dropdown",
                    style={
                        "width": "200px",
                        "margin-left": 10 + ACTUAL_DATEPICKER_RIGHT,
                        "margin-top": -ACTUAL_DATEPICKER_UP,
                    },
                ),
            ],
            className="control-row",
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
                            ""
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
                            className="variable-checklist",
                        ),
                    ],
                    className="variable-container",
                    style={
                        "margin-left": 20 + ACTUAL_VARIABLES_RIGHT,
                        "margin-top": -ACTUAL_VARIABLES_UP,
                    },
                ),
            ],
            className="actual-graph-wrapper",
        )

    def _build_actual_graph_name(self):
        return html.Div(
            html.Span("Závislost příkonu na čase", className="graph-title"),
            className="graph-title-wrapper",
        )

    # -------- TOTAL section --------
    def _build_total_section(self):
        return html.Div(
            [
                html.Div(self.range_text_tot, style={"margin-bottom": "20px"}),
                self._build_total_period_controls(),
                self._build_total_graph_section(),
                self._build_total_graph_name(),
                html.Div(id="total-data-info", style={"margin-top": "30px"}),
            ],
            className="total-section card",
            style={"display": "flex", "flex-direction": "column"},
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
                    className="select-dropdown",
                    style={
                        "width": "150px",
                        "margin-left": TOTAL_PERIOD_RIGHT,
                        "margin-top": -TOTAL_PERIOD_UP,
                    },
                ),
                dcc.Dropdown(
                    id="time-value-total",
                    options=self.period_options_tot.get(self.default_unit_tot, []),
                    value=self.default_value_tot,
                    className="select-dropdown",
                    style={
                        "width": "200px",
                        "margin-left": 10 + TOTAL_DATEPICKER_RIGHT,
                        "margin-top": -TOTAL_DATEPICKER_UP,
                    },
                ),
            ],
            className="control-row",
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
                    className="select-dropdown",
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

    def _build_total_graph_section(self):
        """Graph with controls for the TOTAL section."""
        return html.Div(
            [
                dcc.Loading(
                    id="loading-total",
                    type="circle",
                    children=[
                        dcc.Graph(
                            id="consumption_vs_time_total",
                            style={
                                "margin-left": TOTAL_GRAPH_RIGHT,
                                "margin-top": -TOTAL_GRAPH_UP,
                                "width": "1000px",
                            },
                        )
                    ],
                    style={"flex": "1"},
                ),
                html.Div(
                    [
                        html.Span(""),
                        self._build_total_aggregation_controls(),
                        self._build_total_bar_mode_controls(),
                    ],
                    className="variable-container",
                    style={
                        "margin-left": 20 + TOTAL_VARIABLES_RIGHT,
                        "margin-top": -TOTAL_VARIABLES_UP,
                    },
                ),
            ],
            className="actual-graph-wrapper",
        )

    def _build_total_graph_name(self):
        return html.Div(
            html.Span("Celková spotřeba podle času", className="graph-title"),
            className="graph-title-wrapper",
        )

