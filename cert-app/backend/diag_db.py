
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load env from parent dir if needed
load_dotenv()

# Build DB URL
db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("DATABASE_URL not found in environment")
    sys.exit(1)

engine = create_engine(db_url)

def check_db():
    try:
        with engine.connect() as conn:
            # Check if embedding column exists
            print("Checking qualification table structure...")
            res = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'qualification' AND column_name = 'embedding';
            """))
            has_embedding = res.fetchone() is not None
            print(f"Has embedding column: {has_embedding}")
            
            # Check count
            res = conn.execute(text("SELECT count(*) FROM qualification;"))
            count = res.fetchone()[0]
            print(f"Total certifications in DB: {count}")
            
            if not has_embedding:
                print("\nACTION REQUIRED: Run the following SQL in your Supabase SQL Editor:")
                print("CREATE EXTENSION IF NOT EXISTS vector;")
                print("ALTER TABLE qualification ADD COLUMN IF NOT EXISTS embedding VECTOR(1536);")
                
    except Exception as e:
        print(f"Error checking DB: {e}")

if __name__ == "__main__":
    check_db()
