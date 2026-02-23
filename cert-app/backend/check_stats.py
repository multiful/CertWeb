
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")
engine = create_engine(db_url)

def check_db():
    try:
        with engine.connect() as conn:
            # Check for certifications without stats
            res = conn.execute(text("""
                SELECT q.qual_id, q.qual_name 
                FROM qualification q
                LEFT JOIN qualification_stats s ON q.qual_id = s.qual_id
                WHERE s.stat_id IS NULL
                LIMIT 5;
            """))
            rows = res.fetchall()
            print(f"Certifications without stats: {len(rows)}")
            for r in rows:
                print(f" - {r.qual_name} (ID: {r.qual_id})")
                
    except Exception as e:
        print(f"Error checking DB: {e}")

if __name__ == "__main__":
    check_db()
