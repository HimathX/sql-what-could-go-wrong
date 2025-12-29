import sqlite3
import pandas as pd
from sqlalchemy import create_engine
import urllib.parse
from dotenv import load_dotenv
import os


load_dotenv()

# Final Connection String
MIGRATION_URL = os.getenv("MIGRATION_URI")

SQLITE_DB_PATH = "./Chinook.db"

def migrate():
    try:
        sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
        # Use a small connect_timeout to catch errors faster
        pg_engine = create_engine(MIGRATION_URL , connect_args={'connect_timeout': 10})

        tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table';", sqlite_conn)
        
        for name in tables['name']:
            if name.startswith('sqlite_'): continue
            
            print(f"Migrating table: {name}...")
            df = pd.read_sql_query(f'SELECT * FROM "{name}"', sqlite_conn)
            
            # chunksize helps prevent timeouts on large tables
            df.to_sql(name, pg_engine, if_exists='replace', index=False, method='multi', chunksize=1000)
            print(f"✅ Successfully migrated {name}")

        print("\n🚀 All done!")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        sqlite_conn.close()

if __name__ == "__main__":
    migrate()
