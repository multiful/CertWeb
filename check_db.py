
import os
import psycopg2
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv("cert-app/backend/.env")
db_url = os.getenv("DATABASE_URL")
result = urlparse(db_url)
username = result.username
password = result.password
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
    
    print("=== Major check ===")
    cur.execute("SELECT count(*) FROM public.major_qualification_map WHERE detail_major LIKE '%게임공학과%'")
    print(f"Count for 게임공학과: {cur.fetchone()[0]}")

    print("\n=== Profile Foreign Keys ===")
    cur.execute("""
        SELECT
            tc.constraint_name, 
            tc.table_name, 
            kcu.column_name, 
            rc.update_rule,
            rc.delete_rule
        FROM 
            information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            JOIN information_schema.referential_constraints AS rc
              ON rc.constraint_name = tc.constraint_name
        WHERE tc.table_name = 'profiles';
    """)
    for row in cur.fetchall():
        print(row)
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
