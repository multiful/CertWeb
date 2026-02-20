
from sqlalchemy import create_engine, text
import json

engine = create_engine('postgresql://postgres.xldoiqbvdxcykdlyeoiu:mkinju%212485@aws-1-ap-northeast-2.pooler.supabase.com:6543/postgres')

with open('db_output.txt', 'w', encoding='utf-8') as f:
    with engine.connect() as conn:
        res = conn.execute(text("SELECT * FROM profiles"))
        f.write(f"Profiles columns: {res.keys()}\n")
        for row in res:
            f.write(f"Profile row: {row}\n")
        
        f.write("\n")
        res = conn.execute(text("SELECT * FROM user_favorites"))
        f.write(f"Favorites columns: {res.keys()}\n")
        for row in res:
            f.write(f"Favorite row: {row}\n")
