from app.database import SessionLocal
from sqlalchemy import text
from collections import defaultdict

def analyze_and_prune():
    db = SessionLocal()
    try:
        # 1. Fetch all qualifications
        results = db.execute(text("SELECT qual_id, qual_name FROM qualification")).fetchall()
        id_to_name = {r.qual_id: str(r.qual_name) if r.qual_name else "" for r in results}
        
        # 2. Check stats to identify "real" vs "fake"
        stats_check = db.execute(text("SELECT DISTINCT qual_id FROM qualification_stats")).fetchall()
        ids_with_stats = {r[0] for r in stats_check}
        
        prune_targets = [] # list of (fake_id, real_id)
        
        # Strategy: Find pairs (A, B) where B.name == A.name + "(...)" 
        # OR both share a base name and B has stats while A doesn't.
        
        all_quals = list(results)
        for i, q1 in enumerate(all_quals):
            name1 = str(q1.qual_name).strip() if q1.qual_name else ""
            if not name1: continue
            
            for j, q2 in enumerate(all_quals):
                if i == j: continue
                name2 = str(q2.qual_name).strip() if q2.qual_name else ""
                if not name2: continue
                
                # Case 1: SQL전문가 vs SQL전문가(SQLP)
                # name2 starts with name1 and contains parens
                if name2.startswith(name1) and "(" in name2 and name2 != name1:
                    # If name2 has stats and name1 doesn't, prune name1
                    if q2.qual_id in ids_with_stats and q1.qual_id not in ids_with_stats:
                        prune_targets.append((q1.qual_id, q2.qual_id))
        
        # Strategy 2: Remove specific ones from suggested_pruning
        # ID S233: 철도교통안전관리자, S345: 교통안전관리자, M120: 전산회계
        # These IDs might differ in DB, so search by name + no stats
        target_names = ["철도교통안전관리자", "교통안전관리자", "전산회계"]
        for q in all_quals:
            name = str(q.qual_name).strip() if q.qual_name else ""
            if name in target_names and q.qual_id not in ids_with_stats:
                # Find a corresponding "real" one if possible, or just delete
                # For 교통안전관리자, there are specific ones like (도로), (철도)
                real_for_this = None
                for candidate in all_quals:
                    cname = str(candidate.qual_name)
                    if cname.startswith(name) and "(" in cname and candidate.qual_id in ids_with_stats:
                        real_for_this = candidate.qual_id
                        break
                if real_for_this:
                    prune_targets.append((q.qual_id, real_for_this))
                else:
                    # If no specific "real" one found but it's a known generic to prune
                    prune_targets.append((q.qual_id, None))

        # 3. Handle Pruning
        final_prune = {} # fake -> real
        to_delete_only = set()
        
        for fake, real in prune_targets:
            if real:
                final_prune[fake] = real
            else:
                to_delete_only.add(fake)

        print(f"Plan to migrate and prune {len(final_prune)} entries:")
        for fake_id, real_id in final_prune.items():
            fake_name = id_to_name[fake_id]
            real_name = id_to_name[real_id]
            print(f"  - MIGRATE: {fake_name} ({fake_id}) -> {real_name} ({real_id})")
            
            # Migrate Major Maps
            db.execute(text("""
                UPDATE major_qualification_map 
                SET qual_id = :real 
                WHERE qual_id = :fake 
                AND NOT EXISTS (
                    SELECT 1 FROM major_qualification_map m2 
                    WHERE m2.major = major_qualification_map.major 
                    AND m2.qual_id = :real
                )
            """), {"real": real_id, "fake": fake_id})
            db.execute(text("DELETE FROM major_qualification_map WHERE qual_id = :fake"), {"fake": fake_id})
            
            # Migrate Job Maps
            try:
                db.execute(text("""
                    UPDATE qualification_job_map 
                    SET qual_id = :real 
                    WHERE qual_id = :fake 
                    AND NOT EXISTS (
                        SELECT 1 FROM qualification_job_map j2 
                        WHERE j2.job_id = qualification_job_map.job_id 
                        AND j2.qual_id = :real
                    )
                """), {"real": real_id, "fake": fake_id})
                db.execute(text("DELETE FROM qualification_job_map WHERE qual_id = :fake"), {"fake": fake_id})
            except Exception: pass
            
            db.execute(text("DELETE FROM qualification_stats WHERE qual_id = :fake"), {"fake": fake_id})
            db.execute(text("DELETE FROM qualification WHERE qual_id = :fake"), {"fake": fake_id})

        print(f"Plan to delete {len(to_delete_only)} stray entries:")
        for fake_id in to_delete_only:
            if fake_id in final_prune: continue
            print(f"  - DELETE: {id_to_name[fake_id]} ({fake_id})")
            db.execute(text("DELETE FROM major_qualification_map WHERE qual_id = :fake"), {"fake": fake_id})
            try: db.execute(text("DELETE FROM qualification_job_map WHERE qual_id = :fake"), {"fake": fake_id})
            except Exception: pass
            db.execute(text("DELETE FROM qualification_stats WHERE qual_id = :fake"), {"fake": fake_id})
            db.execute(text("DELETE FROM qualification WHERE qual_id = :fake"), {"fake": fake_id})

        db.commit()
        print("Pruning process finished.")
        
    finally:
        db.close()

if __name__ == "__main__":
    analyze_and_prune()
