
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres.xldoiqbvdxcykdlyeoiu:mkinju%212485@aws-1-ap-northeast-2.pooler.supabase.com:6543/postgres"
engine = create_engine(DATABASE_URL)

if __name__ == "__main__":
    import sys
    with open('test_results.txt', 'w', encoding='utf-8') as f:
        def log(msg):
            print(msg)
            f.write(msg + '\n')
        
        # Override print in test_constraint
        def test_constraint_logged(userid):
            log(f"Testing userid: '{userid}'")
            try:
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO profiles (id, userid, name, email) VALUES (gen_random_uuid(), :uid, 'Test User', :email)"), 
                                 {"uid": userid, "email": f"test_{userid}@example.com"})
                    conn.commit()
                    log("  Success!")
                    conn.execute(text("DELETE FROM profiles WHERE userid = :uid"), {"uid": userid})
                    conn.commit()
            except Exception as e:
                log(f"  Caught error: {str(e)[:100]}...")

        test_constraint_logged("1234567")   # 7
        test_constraint_logged("12345678")  # 8
        test_constraint_logged("123456789") # 9
