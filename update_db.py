
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
    conn.autocommit = True
    cur = conn.cursor()
    
    # 1. Foreign Key with ON DELETE CASCADE
    try:
        cur.execute("ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS profiles_id_fkey;")
        cur.execute("""
            ALTER TABLE public.profiles 
            ADD CONSTRAINT profiles_id_fkey 
            FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE;
        """)
        print("Successfully added profiles_id_fkey with CASCADE.")
    except Exception as e:
        print(f"Error adding foreign key: {e}")

    # 2. Update trigger function for handle_new_user
    try:
        cur.execute("""
            CREATE OR REPLACE FUNCTION public.handle_new_user()
            RETURNS trigger AS $$
            BEGIN
              INSERT INTO public.profiles (id, userid, name, email, nickname)
              VALUES (
                new.id, 
                COALESCE(new.raw_user_meta_data->>'userid', 'user_' || substr(md5(random()::text), 1, 8)), 
                COALESCE(new.raw_user_meta_data->>'name', split_part(new.email, '@', 1)), 
                new.email,
                COALESCE(new.raw_user_meta_data->>'nickname', split_part(new.email, '@', 1))
              );
              RETURN new;
            END;
            $$ LANGUAGE plpgsql SECURITY DEFINER;
        """)
        print("Successfully updated handle_new_user function.")
        
        # Make sure the trigger exists
        cur.execute("DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;")
        cur.execute("""
            CREATE TRIGGER on_auth_user_created
            AFTER INSERT ON auth.users
            FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
        """)
        print("Successfully recreated the trigger on auth.users.")
    except Exception as e:
        print(f"Error updating trigger: {e}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
