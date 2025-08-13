"""Application bootstrap for the Dash project.

The original implementation executed all setup logic at module import time.  To
enable easier reuse (e.g. for testing) the setup has been refactored into
functions.  ``create_app`` builds the Dash application, registers callbacks and
returns both the app instance and information about data ranges.  A separate
``main`` function serves as the runnable entrypoint.
"""

from dash import Dash

from config import DB_NAME
from data_utils import DataFetcher
from app_layout import LayoutBuilder
from actual_callbacks import register_actual_callbacks
from total_callbacks import register_total_callbacks


def create_app():
    """Create and configure the Dash application.

    Returns
    -------
    tuple
        A tuple of (app, data_ranges) where ``app`` is the configured Dash
        instance and ``data_ranges`` contains min/max timestamp information for
        the ACTUAL and TOTAL tables.
    """

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

    range_text_act = (
        #f"Databáze (ACTUAL) obsahuje data od {actual_min_date} do {actual_max_date}"
        ""
    )
    range_text_tot = (
        #f"Databáze (TOTAL) obsahuje data od {total_min_date} do {total_max_date}"
    )

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

    # Register callbacks in separate modules
    register_actual_callbacks(app, data_fetcher, period_options_act)
    register_total_callbacks(app, data_fetcher, period_options_tot)

    return app, data_ranges


def main():
    """Run the Dash development server."""
    app, data_ranges = create_app()
    print("Data ranges for tables:")
    for table_name, rng in data_ranges.items():
        print(f"{table_name}: From {rng['min_time']} to {rng['max_time']}")
    app.run(debug=True, port=8000, host="127.0.0.1")


if __name__ == "__main__":
    main()