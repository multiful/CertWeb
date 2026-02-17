import re
from app.database import SessionLocal
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def canonicalize(name):
    # Remove spaces, parentheses, and convert to lowercase
    return re.sub(r'[\s\(\)]', '', name).lower()

def clean_duplicates():
    db = SessionLocal()
    try:
        # 1. Provide a safety check: Get all quals and their stats counts
        sql = text("SELECT qual_id, qual_name FROM qualification")
        all_quals = db.execute(sql).fetchall()

        stats_sql = text("SELECT qual_id, COUNT(*) as c FROM qualification_stats GROUP BY qual_id")
        stats_res = db.execute(stats_sql).fetchall()
        stats_map = {r.qual_id: r.c for r in stats_res}

        quals_with_stats = []
        quals_without_stats = []

        for q in all_quals:
            count = stats_map.get(q.qual_id, 0)
            if count > 0:
                quals_with_stats.append(q)
            else:
                quals_without_stats.append(q)

        ids_to_delete = []
        
        # 2. Identify duplicates
        for q_no in quals_without_stats:
            canon_no = canonicalize(q_no.qual_name)
            for q_yes in quals_with_stats:
                canon_yes = canonicalize(q_yes.qual_name)
                # Check for exact canonical match
                if canon_no == canon_yes:
                    logger.info(f"Marking for deletion: {q_no.qual_id} ({q_no.qual_name}) - Duplicate of {q_yes.qual_id}")
                    ids_to_delete.append(q_no.qual_id)
                    break
        
        if not ids_to_delete:
            logger.info("No duplicates found to delete.")
            return

        # 3. Execute Deletion
        logger.info(f"Deleting {len(ids_to_delete)} duplicate qualifications...")
        
        # Verify we're not deleting the one with stats (double check)
        # (The logic above only selects from quals_without_stats, so it's safe)
        
        delete_sql = text("DELETE FROM qualification WHERE qual_id = :qual_id")
        for q_id in ids_to_delete:
            db.execute(delete_sql, {"qual_id": q_id})
            
        db.commit()
        logger.info("Deletion complete.")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    clean_duplicates()
