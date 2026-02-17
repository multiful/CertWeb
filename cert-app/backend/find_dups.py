
import csv
import re
import os

def find_duplicates(file_path):
    duplicates = []
    certs = []
    
    with open(file_path, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("자격증명") or "").strip()
            if not name: continue
            
            # Check if has stats
            has_stats = False
            for year in [2022, 2023, 2024]:
                for round_num in [1, 2, 3]:
                    prefix = f"{year}년 {round_num}차"
                    pr = row.get(f"{prefix} 합격률")
                    cc = row.get(f"{prefix} 응시자 수") or row.get(f"{prefix} 응시자수") or row.get(f"{prefix} 응시자  수")
                    if (pr and pr.strip() and pr.strip() != '0') or (cc and cc.strip() and cc.strip() != '0'):
                        has_stats = True
                        break
                if has_stats: break
            
            certs.append({
                "name": name,
                "id": row.get("자격증ID"),
                "has_stats": has_stats,
                "original_row": row
            })

    # Find duplicates by name similarity
    processed_indices = set()
    for i in range(len(certs)):
        if i in processed_indices: continue
        
        c1 = certs[i]
        n1 = c1['name']
        n1_clean = re.sub(r'\(.*?\)', '', n1).strip() # Remove (SQLD) etc
        
        matches = []
        for j in range(i + 1, len(certs)):
            if j in processed_indices: continue
            c2 = certs[j]
            n2 = c2['name']
            n2_clean = re.sub(r'\(.*?\)', '', n2).strip()
            
            # Match if clean names are same OR one contains the other
            if n1_clean == n2_clean or n1 == n2 or (len(n1_clean) > 2 and (n1_clean in n2 or n2_clean in n1)):
                matches.append(j)
        
        if matches:
            # We found a group of potential duplicates
            group = [i] + matches
            # Only report if there's an inconsistency in has_stats or just multiple entries
            # Actually user specifically asked for "stats exist = real"
            has_with_stats = any(certs[idx]['has_stats'] for idx in group)
            has_without_stats = any(not certs[idx]['has_stats'] for idx in group)
            
            if has_with_stats and has_without_stats:
                dup_info = {
                    "names": [certs[idx]['name'] for idx in group],
                    "ids": [certs[idx]['id'] for idx in group],
                    "stats_status": [certs[idx]['has_stats'] for idx in group]
                }
                duplicates.append(dup_info)
            
            for idx in group:
                processed_indices.add(idx)

    return duplicates

if __name__ == "__main__":
    file_path = os.path.join("dataset", "data_cert1.csv")
    if os.path.exists(file_path):
        dups = find_duplicates(file_path)
        print(f"### Found {len(dups)} duplicate groups in data_cert1.csv ###\n")
        for d in dups:
            print(f"Group: {', '.join(d['names'])}")
            for name, mid, stat in zip(d['names'], d['ids'], d['stats_status']):
                status = "Real (Has Stats)" if stat else "Duplicate (No Stats)"
                print(f"  - {name} [{mid}]: {status}")
            print("-" * 30)
    else:
        print("File not found.")
