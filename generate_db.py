#!/usr/bin/env python3
import os
import sqlite3
import random
import argparse
from datetime import datetime, timedelta

EXPECTED_COLS = [
    "U_IN", "V_IN", "W_IN",
    "U_OUT", "V_OUT", "W_OUT",
    "ATLAS", "BUPI", "RENDER"
]

def create_tables(db_path):
    """(Re)create ACTUAL and TOTAL tables with the full schema."""
    # If database exists, remove it so we start fresh
    if os.path.exists(db_path):
        print(f"Removing existing database at '{db_path}'")
        os.remove(db_path)

    with sqlite3.connect(db_path) as cnx:
        cur = cnx.cursor()
        # ACTUAL
        cur.execute("""
        CREATE TABLE ACTUAL (
            UTC_TIME INTEGER,
            U_IN    REAL, V_IN    REAL, W_IN    REAL,
            U_OUT   REAL, V_OUT   REAL, W_OUT   REAL,
            ATLAS   REAL, BUPI    REAL, RENDER  REAL
        )
        """)
        # TOTAL
        cur.execute("""
        CREATE TABLE TOTAL (
            UTC_TIME INTEGER,
            U_IN    REAL, V_IN    REAL, W_IN    REAL,
            U_OUT   REAL, V_OUT   REAL, W_OUT   REAL,
            ATLAS   REAL, BUPI    REAL, RENDER  REAL
        )
        """)
        cnx.commit()
    print(f"Created fresh tables in '{db_path}'")

def populate_actual(db_path, start_dt, end_dt, interval_minutes):
    """Populate ACTUAL with one row every `interval_minutes`."""
    with sqlite3.connect(db_path) as cnx:
        cur = cnx.cursor()
        t = start_dt
        while t <= end_dt:
            ts = int(t.timestamp())
            # generate IN values
            u_in, v_in, w_in = [random.uniform(50,150) for _ in range(3)]
            # generate OUT values
            u_out, v_out, w_out = [random.uniform(30,100) for _ in range(3)]
            # other metrics
            atlas  = random.uniform(200,300)
            bupi   = random.uniform(100,200)
            render = random.uniform(150,250)
            cur.execute("""
                INSERT INTO ACTUAL
                (UTC_TIME,U_IN,V_IN,W_IN,U_OUT,V_OUT,W_OUT,ATLAS,BUPI,RENDER)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ts, u_in, v_in, w_in, u_out, v_out, w_out, atlas, bupi, render))
            t += timedelta(minutes=interval_minutes)
        cnx.commit()
    print(f"Populated ACTUAL: {((end_dt-start_dt).days*24*60)//interval_minutes + 1} rows")

def populate_total(db_path, start_date, num_days):
    """Populate TOTAL with one row per day for `num_days` days."""
    with sqlite3.connect(db_path) as cnx:
        cur = cnx.cursor()
        for i in range(num_days):
            day = start_date + timedelta(days=i)
            # timestamp at midnight UTC
            ts = int(datetime(day.year, day.month, day.day).timestamp())
            # generate IN values
            u_in, v_in, w_in = [random.uniform(1000,2000) for _ in range(3)]
            # generate OUT values
            u_out, v_out, w_out = [random.uniform(800,1500) for _ in range(3)]
            atlas  = random.uniform(500,1000)
            bupi   = random.uniform(300,800)
            render = random.uniform(400,900)
            cur.execute("""
                INSERT INTO TOTAL
                (UTC_TIME,U_IN,V_IN,W_IN,U_OUT,V_OUT,W_OUT,ATLAS,BUPI,RENDER)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ts, u_in, v_in, w_in, u_out, v_out, w_out, atlas, bupi, render))
        cnx.commit()
    print(f"Populated TOTAL: {num_days} rows")

def main():
    p = argparse.ArgumentParser(
        description="Generate a new SQLite DB with ACTUAL and TOTAL tables (full schema + sample data)."
    )
    p.add_argument(
        "--db", "-d", default="database_name.db",
        help="Path for the SQLite database to create."
    )
    p.add_argument(
        "--start", "-s", default="2024-01-01",
        help="Start date (YYYY-MM-DD) for sample data."
    )
    p.add_argument(
        "--days", "-n", type=int, default=3,
        help="How many days to populate."
    )
    p.add_argument(
        "--interval", "-i", type=int, default=60,
        help="Sampling interval in minutes for ACTUAL."
    )
    args = p.parse_args()

    # Parse dates
    start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt   = start_dt + timedelta(days=args.days) - timedelta(minutes=args.interval)

    # 1) Create tables
    create_tables(args.db)

    # 2) Populate ACTUAL every `interval` minutes
    populate_actual(args.db, start_dt, end_dt, args.interval)

    # 3) Populate TOTAL one row per day
    populate_total(args.db, start_date, args.days)

    print(f"\nAll done! Your new database is at: {args.db}")

if __name__ == "__main__":
    main()
