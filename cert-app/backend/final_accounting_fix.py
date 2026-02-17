from app.database import SessionLocal
from sqlalchemy import text

def final_cleanup_accounting():
    db = SessionLocal()
    try:
        # Define the official IDs we want to keep
        official_ids = [736, 737]
        
        # 1. Update the official ones to the correct labels
        db.execute(text("""
            UPDATE qualification 
            SET qual_type = '국가공인민간자격', 
                main_field = '재무 회계' 
            WHERE qual_id IN (736, 737)
        """))
        print("Updated official accounting certifications (736, 737).")

        # 2. Find any other '회계관리' variants (including no-space versions)
        # We already merged 1118/1119 in the previous step, but let's be thorough.
        other_quals = db.execute(text("""
            SELECT qual_id, qual_name 
            FROM qualification 
            WHERE (qual_name LIKE '%회계관리%' OR qual_name LIKE '%회계 관리%')
            AND qual_id NOT IN (736, 737)
        """)).fetchall()

        for r in other_quals:
            # Determine which official one to merge into
            target_id = 736 if "1급" in r.qual_name else 737 if "2급" in r.qual_name else 736
            print(f"Merging extra accounting record: {r.qual_name} (ID: {r.qual_id}) -> {target_id}")

            # Migrate everything
            db.execute(text("UPDATE major_qualification_map SET qual_id = :target WHERE qual_id = :src"), {"target": target_id, "src": r.qual_id})
            db.execute(text("UPDATE qualification_stats SET qual_id = :target WHERE qual_id = :src"), {"target": target_id, "src": r.qual_id})
            db.execute(text("UPDATE qualification_job_map SET qual_id = :target WHERE qual_id = :src"), {"target": target_id, "src": r.qual_id})
            db.execute(text("UPDATE user_favorites SET qual_id = :target WHERE qual_id = :src"), {"target": target_id, "src": r.qual_id})
            db.execute(text("DELETE FROM qualification WHERE qual_id = :src"), {"src": r.qual_id})

        db.commit()
        print("Accounting cleanup and consolidation complete.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    final_cleanup_accounting()
