
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres.xldoiqbvdxcykdlyeoiu:mkinju%212485@aws-1-ap-northeast-2.pooler.supabase.com:6543/postgres"
engine = create_engine(DATABASE_URL)

sql_commands = [
    # 1. Update existing userids to 8 chars (pad or truncate) if needed
    "UPDATE profiles SET userid = RPAD(userid, 8, '0') WHERE LENGTH(userid) < 8",
    "UPDATE profiles SET userid = LEFT(userid, 8) WHERE LENGTH(userid) > 8",
    
    # 2. Change column type to CHAR(8)
    "ALTER TABLE profiles ALTER COLUMN userid TYPE CHAR(8)",
    
    # 3. Add CHECK constraint
    "ALTER TABLE profiles DROP CONSTRAINT IF EXISTS chk_userid_len",
    "ALTER TABLE profiles ADD CONSTRAINT chk_userid_len CHECK (LENGTH(userid) = 8)"
]

with engine.connect() as conn:
    for cmd in sql_commands:
        print(f"Executing: {cmd}")
        conn.execute(text(cmd))
    conn.commit()
    print("SQL Update Success!")
