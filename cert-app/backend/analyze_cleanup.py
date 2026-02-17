import re
from app.database import SessionLocal
from sqlalchemy import text

def canonicalize(name):
    # Remove spaces, parentheses, and convert to lowercase
    return re.sub(r'[\s\(\)]', '', name).lower()

db = SessionLocal()
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

to_delete = []
for q_no in quals_without_stats:
    canon_no = canonicalize(q_no.qual_name)
    for q_yes in quals_with_stats:
        canon_yes = canonicalize(q_yes.qual_name)
        if canon_no == canon_yes:
            to_delete.append((q_no.qual_id, q_no.qual_name, q_yes.qual_id, q_yes.qual_name))
            break

with open("cleanup_report.txt", "w", encoding="utf-8") as f:
    f.write("Detected Duplicates (to delete the first one):\n")
    f.write("-" * 50 + "\n")
    for d in to_delete:
        f.write(f"DELETE: {d[0]} | {d[1]} (0 stats) vs KEEP: {d[2]} | {d[3]}\n")

# Actually delete them if requested, but let's just see first
print(f"Found {len(to_delete)} duplicates to clean up.")
db.close()
