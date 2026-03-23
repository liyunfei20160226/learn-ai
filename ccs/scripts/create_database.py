"""
Create database tables in ccs database
If ccs database doesn't exist, create it first
"""

import sys
import psycopg2
from pathlib import Path
from psycopg2 import sql

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# First connect to postgres to create ccs database if it doesn't exist
DEFAULT_DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'postgres',
    'password': 'postgres',
    'database': 'postgres',
}

TARGET_DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'postgres',
    'password': 'postgres',
    'database': 'ccs',
}

def main():
    # Read DDL file
    ddl_path = Path(__file__).parent.parent / 'sql' / '01_create_tables.sql'

    with open(ddl_path, 'r', encoding='utf-8') as f:
        ddl_sql = f.read()

    print(f"Reading DDL: {ddl_path.name}")
    print("=" * 60)

    try:
        # Check if ccs database exists
        print("Checking if ccs database exists...")
        conn = psycopg2.connect(**DEFAULT_DB_CONFIG)
        conn.autocommit = True
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 1 FROM pg_database WHERE datname = 'ccs';
        """)
        exists = cursor.fetchone()

        if not exists:
            print("Creating ccs database...")
            cursor.execute(sql.SQL("CREATE DATABASE {};").format(sql.Identifier('ccs')))
            print("✅ ccs database created")
        else:
            print("✅ ccs database already exists")

        cursor.close()
        conn.close()

        # Connect to ccs database and execute DDL
        print(f"\nConnecting to ccs database: {TARGET_DB_CONFIG['host']}:{TARGET_DB_CONFIG['port']}")
        conn = psycopg2.connect(**TARGET_DB_CONFIG)
        conn.autocommit = True
        cursor = conn.cursor()

        print("\nExecuting DDL to create tables...")
        cursor.execute(ddl_sql)

        print("\n✅ Execution complete!")

        # Verify tables created
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name IN ('small_box_info', 'acceptance_data', 'process_management', 'small_box_relation', 'box_status')
            ORDER BY table_name;
        """)

        tables = cursor.fetchall()

        print(f"\nCreated tables ({len(tables)}/5):")
        for table in tables:
            print(f"  - {table[0]}")

        if len(tables) == 5:
            print("\n✅ All 5 tables created successfully in ccs database!")
        else:
            print(f"\n⚠️  Only {len(tables)}/5 tables created")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise

if __name__ == "__main__":
    main()
