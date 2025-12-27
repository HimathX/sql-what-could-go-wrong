import sqlite3
import pandas as pd
from sqlalchemy import create_engine
import urllib.parse

# --- CONFIGURATION ---
SQLITE_DB_PATH = 'Chinook.db'

# 1. NEW POOLER DETAILS (Found in Supabase Dashboard -> Connect)
# Note the host ends in .pooler.supabase.com
# Note the user format: "postgres.[your-project-ref]"
user = "postgres.xaktpivqlivofxbrcubi"  # Add your project ref after a dot
password = "Adminuser!234"
host = "aws-0-us-east-1.pooler.supabase.com" # Check your dashboard for your specific region
port = "5432" # 5432 for Session mode (recommended for migrations), 6543 for Transaction mode
database = "postgres"

safe_password = urllib.parse.quote_plus(password)

# Final Connection String
SUPABASE_POSTGRES_URL = "postgresql://postgres.xaktpivqlivofxbrcubi:Adminuser!234@aws-1-ap-south-1.pooler.supabase.com:5432/postgres"

def migrate():
    try:
        sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
        # Use a small connect_timeout to catch errors faster
        pg_engine = create_engine(SUPABASE_POSTGRES_URL, connect_args={'connect_timeout': 10})

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
