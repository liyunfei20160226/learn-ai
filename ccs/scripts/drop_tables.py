"""
Drop tables from postgres database
"""

import sys
import psycopg2
from psycopg2 import sql

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'postgres',
    'password': 'postgres',
    'database': 'postgres',
}

TABLES = [
    'acceptance_data',
    'box_status',
    'process_management',
    'small_box_relation',
    'small_box_info',
]

def main():
    try:
        print(f"Trying to drop tables from postgres database...\n")

        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cursor = conn.cursor()

        for table in TABLES:
            try:
                cursor.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE;").format(
                    sql.Identifier(table)
                ))
                print(f"✓ DROPPED: {table}")
            except Exception as e:
                print(f"✗ FAILED: {table} - {e}")

        print(f"\n✅ Done! All tables dropped from postgres database.")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise

if __name__ == "__main__":
    main()
