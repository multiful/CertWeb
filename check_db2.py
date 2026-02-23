
import os
import psycopg2
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv

load_dotenv("cert-app/backend/.env")
db_url = os.getenv("DATABASE_URL")
result = urlparse(db_url)
username = result.username
password = unquote(result.password)
database = result.path[1:]
hostname = result.hostname
port = result.port

def main():
    conn = psycopg2.connect(
        database=database,
        user=username,
        password=password,
        host=hostname,
        port=port
    )
    cur = conn.cursor()
    
    with open("check_db2_out.txt", "w", encoding="utf-8") as f:
        # Check current definitions of trigger functions
        cur.execute("""
            SELECT p.proname, pg_get_functiondef(p.oid)
            FROM pg_proc p
            JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = 'public' AND p.proname LIKE '%user%';
        """)
        for name, txt in cur.fetchall():
            f.write(f"\n=== Function {name} ===\n")
            f.write(str(txt) + "\n")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
