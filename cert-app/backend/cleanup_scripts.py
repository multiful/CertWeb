import os
import sys
import traceback
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Setup DB connection
DATABASE_URL = "postgresql://postgres.xldoiqbvdxcykdlyeoiu:mkinju%212485@aws-1-ap-northeast-2.pooler.supabase.com:6543/postgres"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def cleanup_data():
    db = SessionLocal()
    try:
        print("Starting data cleanup...")

        # Helper to check if a table exists
        def table_exists(table_name):
            res = db.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :t)"), {"t": table_name}).fetchone()
            return res[0] if res else False

        # --- [ HELPER: SAFE RENAME / MERGE ] ---
        def safe_rename_or_merge(old_name, new_name):
            old = db.execute(text("SELECT qual_id FROM qualification WHERE qual_name = :name"), {"name": old_name}).fetchone()
            if not old:
                return
            src_id = old[0]

            new = db.execute(text("SELECT qual_id FROM qualification WHERE qual_name = :name"), {"name": new_name}).fetchone()
            if new:
                target_id = new[0]
                print(f"Merging '{old_name}' -> '{new_name}'")
                
                try:
                    # Point stats to target
                    db.execute(text("UPDATE qualification_stats SET qual_id = :target WHERE qual_id = :src"), {"target": target_id, "src": src_id})
                    # Handle Favorites (ignore duplicates)
                    db.execute(text("INSERT INTO user_favorites (user_id, qual_id) SELECT user_id, :target FROM user_favorites WHERE qual_id = :src ON CONFLICT DO NOTHING"), {"target": target_id, "src": src_id})
                    db.execute(text("DELETE FROM user_favorites WHERE qual_id = :src"), {"src": src_id})
                    # Handle Major Mappings
                    db.execute(text("INSERT INTO major_qualification_map (major, qual_id, score, weight, reason) SELECT major, :target, score, weight, reason FROM major_qualification_map WHERE qual_id = :src ON CONFLICT DO NOTHING"), {"target": target_id, "src": src_id})
                    db.execute(text("DELETE FROM major_qualification_map WHERE qual_id = :src"), {"src": src_id})
                    # Handle Job Mappings
                    db.execute(text("INSERT INTO qualification_job_map (qual_id, job_id) SELECT :target, job_id FROM qualification_job_map WHERE qual_id = :src ON CONFLICT DO NOTHING"), {"target": target_id, "src": src_id})
                    db.execute(text("DELETE FROM qualification_job_map WHERE qual_id = :src"), {"src": src_id})
                    
                    # Delete old record
                    db.execute(text("DELETE FROM qualification WHERE qual_id = :src"), {"src": src_id})
                    db.commit()
                except Exception as ex:
                    db.rollback()
                    print(f"Failed to merge '{old_name}': {ex}")
            else:
                print(f"Renaming '{old_name}' -> '{new_name}'")
                try:
                    db.execute(text("UPDATE qualification SET qual_name = :new WHERE qual_id = :id"), {"new": new_name, "id": src_id})
                    db.commit()
                except Exception as ex:
                    db.rollback()
                    print(f"Failed to rename '{old_name}': {ex}")

        # Renames and Merges
        actions = [
            ("신발류제조기능사", "신발제조기능사"),
            ("전지기능사", "전기기능사"),
            ("소방안전관리자특급", "소방안전관리자 특급"),
            ("소방안전관리자1급", "소방안전관리자 1급"),
            ("소방안전관리자2급", "소방안전관리자 2급"),
            ("소방안전관리자3급", "소방안전관리자 3급"),
            ("전산응용조선제도기능사", "선체설계기능사"),
            ("기계정비기능사", "설비보전기능사"),
            ("공유압기능사", "설비보전기능사"),
            ("전자계산기조직응용기사", "컴퓨터시스템기사"),
            ("전자계산기기사", "컴퓨터시스템기사"),
            ("통신선로산업기사", "정보통신산업기사"),
            ("통신선로기능사", "정보통신기능사"),
            ("통신기기기능사", "정보통신기능사")
        ]

        for old, new in actions:
            safe_rename_or_merge(old, new)

        # Final cleanup for deletions
        to_delete = ["수소전문가", "광학기능사", "원형기능사", "광고도장기능사", "재료조직평가산업기사", "전자부품장착산업기사"]
        for name in to_delete:
            try:
                db.execute(text("DELETE FROM qualification WHERE qual_name = :name"), {"name": name})
                db.commit()
            except:
                db.rollback()

        print("Cleanup process finished.")
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_data()
