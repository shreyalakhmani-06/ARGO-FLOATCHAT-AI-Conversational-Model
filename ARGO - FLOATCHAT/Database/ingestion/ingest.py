import os
import psycopg2
import pandas as pd
from psycopg2 import sql
from wait_for_db import *  # ensures DB is ready before starting

# ---------------- CONFIG ----------------
DB_CONF = {
    "host": os.getenv("DB_HOST", "db"),       # Docker service name
    "port": int(os.getenv("DB_PORT", 5432)),
    "dbname": os.getenv("DB_NAME", "argo_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres")
}

# Path inside container (mounted via docker-compose)
profile_folder = "/app/profile_data"  
# ----------------------------------------

def create_profile_table(cur, table_name, df):
    """
    Create a Postgres table for a float's profile data based on DataFrame columns.
    """
    col_defs = []
    for col in df.columns:
        if col.lower() in ["juld"]:
            col_type = "TEXT"  # keep as text for now
        elif col.lower() in ["latitude", "longitude", "pres", "temp", "psal"]:
            col_type = "DOUBLE PRECISION"
        else:
            col_type = "TEXT"
        col_defs.append(sql.SQL("{} {}").format(sql.Identifier(col), sql.SQL(col_type)))

    create_query = sql.SQL("CREATE TABLE IF NOT EXISTS {} ({})").format(
        sql.Identifier(table_name),
        sql.SQL(", ").join(col_defs)
    )
    cur.execute(create_query)

def load_csv_to_table(conn, cur, filepath, float_id):
    """
    Load one CSV file into its corresponding Postgres table.
    """
    df = pd.read_csv(filepath)

    # Table name
    table_name = f"profiles_{float_id}"

    # Create table if not exists
    create_profile_table(cur, table_name, df)

    # Load data using COPY
    with open(filepath, "r", encoding="utf-8") as f:
        cur.copy_expert(
            sql.SQL("COPY {} FROM STDIN WITH CSV HEADER").format(sql.Identifier(table_name)),
            f
        )

    # Update floats_metadata with profile_table
    cur.execute(
        """
        UPDATE floats_metadata
        SET profile_table = %s
        WHERE platform_number = %s
        """,
        (table_name, float_id)
    )

    # If no row was updated → insert a new metadata row
    if cur.rowcount == 0:
        cur.execute(
            """
            INSERT INTO floats_metadata (platform_number, profile_table)
            VALUES (%s, %s)
            """,
            (float_id, table_name)
        )

def main():
    print("[*] Connecting to database...")
    conn = psycopg2.connect(**DB_CONF)
    cur = conn.cursor()

    # Ensure floats_metadata has profile_table column
    cur.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'floats_metadata' AND column_name = 'profile_table'
        ) THEN
            ALTER TABLE floats_metadata ADD COLUMN profile_table VARCHAR(100);
        END IF;
    END $$;
    """)
    conn.commit()

    # Iterate over CSV files
    for file in os.listdir(profile_folder):
        if file.endswith(".csv") and "_profile" in file:
            float_id = file.split("_")[0]  # e.g. "1900122_profile.csv" → "1900122"
            filepath = os.path.join(profile_folder, file)

            print(f"[+] Ingesting {file} into table profiles_{float_id}")

            try:
                load_csv_to_table(conn, cur, filepath, float_id)
                conn.commit()
                print(f"    -> Success for {file}")
            except Exception as e:
                conn.rollback()
                print(f"    -> Failed for {file}: {e}")

    cur.close()
    conn.close()
    print("✅ All profile CSVs ingested successfully.")

if __name__ == "__main__":
    main()
