import sqlite3
import time
from datetime import datetime
from typing import List, Dict, Tuple

import pandas as pd


class DataFetcher:
    """Encapsulates all database access and time helper utilities."""

    def __init__(self, db_name: str):
        self.db_name = db_name

    @staticmethod
    def generate_stamp(time_str: str) -> int:
        """Convert 'YYYY-mm-dd HH:MM:SS' to a UNIX timestamp."""
        try:
            time_strip = time.strptime(time_str.strip(), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            print(f"Bad format of given time: {time_str}")
            return -1
        return int(time.mktime(time_strip))

    def get_data_range(self) -> Dict[str, Dict[str, str]]:
        """Retrieve earliest and latest timestamps for ACTUAL and TOTAL tables."""
        with sqlite3.connect(self.db_name) as cnx:
            range_query = (
                "SELECT MIN(UTC_TIME) as min_time, MAX(UTC_TIME) as max_time FROM {table_name}"
            )
            tables = ["ACTUAL", "TOTAL"]
            data_ranges: Dict[str, Dict[str, str]] = {}
            for table in tables:
                result = cnx.execute(range_query.format(table_name=table)).fetchone()
                if result:
                    min_time, max_time = result
                    data_ranges[table] = {
                        "min_time": (
                            datetime.utcfromtimestamp(min_time).strftime("%Y-%m-%d %H:%M:%S")
                            if min_time
                            else None
                        ),
                        "max_time": (
                            datetime.utcfromtimestamp(max_time).strftime("%Y-%m-%d %H:%M:%S")
                            if max_time
                            else None
                        ),
                    }
                else:
                    data_ranges[table] = {"min_time": None, "max_time": None}
        return data_ranges

    @staticmethod
    def map_display_var_to_db_cols(display_var: str) -> List[str]:
        """Map display variable names to database column names."""
        if display_var == "IN":
            return ["U_IN", "V_IN", "W_IN"]
        if display_var == "OUT":
            return ["U_OUT", "V_OUT", "W_OUT"]
        return [display_var]

    @classmethod
    def build_column_list(cls, selected_display_vars: List[str]) -> List[str]:
        """Return required DB columns for chosen display variables."""
        needed_cols = set()
        for dv in selected_display_vars:
            needed_cols.update(cls.map_display_var_to_db_cols(dv))
        return list(needed_cols)

    @staticmethod
    def get_period_options(min_date: str, max_date: str) -> Dict[str, List[Dict[str, str]]]:
        """Generate selectable ranges for year/month/week/day."""
        if not min_date or not max_date:
            return {"year": [], "month": [], "week": [], "day": []}

        start = pd.to_datetime(min_date)
        end = pd.to_datetime(max_date)
        years = [{"label": str(y), "value": str(y)} for y in pd.period_range(start, end, freq="Y").year]
        months = [
            {"label": p.strftime("%Y-%m"), "value": p.strftime("%Y-%m")}
            for p in pd.period_range(start, end, freq="M")
        ]
        weeks = [
            {"label": p.start_time.strftime("%Y-%m-%d"), "value": p.start_time.strftime("%Y-%m-%d")}
            for p in pd.period_range(start, end, freq="W-MON")
        ]
        days = [
            {"label": d.strftime("%Y-%m-%d"), "value": d.strftime("%Y-%m-%d")}
            for d in pd.date_range(start, end, freq="D")
        ]
        return {"year": years, "month": months, "week": weeks, "day": days}

    @staticmethod
    def compute_start_end(unit: str, value: str) -> Tuple[str, str]:
        """Compute start and end date strings for selected unit and value."""
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
        else:
            start = value
            end = value
        return start, end

    def query_data_actual_advanced(
        self, start_dt_str: str, end_dt_str: str, needed_db_cols: List[str], step: int
    ) -> pd.DataFrame:
        """Retrieve sampled rows and daily maxima from ACTUAL table."""
        stamp_od = self.generate_stamp(start_dt_str)
        stamp_do = self.generate_stamp(end_dt_str)
        if stamp_od == -1 or stamp_do == -1 or not needed_db_cols:
            return pd.DataFrame()

        col_subqueries = []
        for c in needed_db_cols:
            col_subqueries.append(
                f"""
            SELECT UTC_TIME, '{c}' AS variable, {c} AS value
            FROM ACTUAL
            WHERE UTC_TIME BETWEEN {stamp_od} AND {stamp_do}
        """
            )
        base_sql = " UNION ALL ".join(col_subqueries)
        sql = f"""
        WITH base AS ({base_sql}),
        NumberedAll AS (
            SELECT b.UTC_TIME, b.variable, b.value,
                   ROW_NUMBER() OVER (PARTITION BY b.variable ORDER BY b.UTC_TIME) AS global_rn,
                   ROW_NUMBER() OVER (
                       PARTITION BY b.variable, date(b.UTC_TIME, 'unixepoch')
                       ORDER BY b.value DESC
                   ) AS daily_rn
            FROM base b
        ),
        stepped AS (
            SELECT UTC_TIME, variable, value
            FROM NumberedAll
            WHERE (global_rn - 1) % {step} = 0
        ),
        dailymax AS (
            SELECT UTC_TIME, variable, value
            FROM NumberedAll
            WHERE daily_rn = 1
        ),
        final AS (
            SELECT UTC_TIME, variable, value, 0 AS is_max FROM stepped
            UNION ALL
            SELECT UTC_TIME, variable, value, 1 AS is_max FROM dailymax
        )
        SELECT * FROM final ORDER BY variable, UTC_TIME
        """
        with sqlite3.connect(self.db_name) as cnx:
            return pd.read_sql_query(sql, cnx)

    def query_data_total(self, start_dt: str, end_dt: str) -> pd.DataFrame:
        """Query the TOTAL table for a time range."""
        stamp_od = self.generate_stamp(start_dt)
        stamp_do = self.generate_stamp(end_dt)
        if stamp_od == -1 or stamp_do == -1:
            return pd.DataFrame()
        sql_query = f"""
        SELECT UTC_TIME, U_IN, V_IN, W_IN, ATLAS, BUPI, RENDER
        FROM TOTAL
        WHERE UTC_TIME BETWEEN {stamp_od} AND {stamp_do}
        ORDER BY UTC_TIME
        """
        with sqlite3.connect(self.db_name) as cnx:
            return pd.read_sql_query(sql_query, cnx)