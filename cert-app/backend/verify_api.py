import requests
import json
import sys

# URL of the running backend
URL = "http://127.0.0.1:8000/api/v1/certs"


try:
    response = requests.get(URL, params={"q": "데이터분석", "page_size": 100})
    if response.status_code == 200:
        data = response.json()
        items = data.get("items", [])
        
        print(f"Found {len(items)} items for '데이터분석'")
        print("-" * 50)
        found_duplicates = False
        for item in items:
            # Check for the ones we know are problematic
            # Valid: 595 (ADsP), 594 (ADP), 319 (BigData)
            # Invalid: 1147 (ADSP), etc.
            status = "VALID" if item['qual_id'] in [595, 594, 319] else "SUSPICIOUS"
            print(f"ID: {item['qual_id']} | Name: {item['qual_name']} | Type: {status}")
            
            if status == "SUSPICIOUS":
                found_duplicates = True
        
        if not found_duplicates:
            print("\nVERDICT: API is returning CLEAN data.")
        else:
            print("\nVERDICT: API is returning DIRTY data (Duplicates present).")
            
    else:
        print(f"Error: API returned status code {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"Failed to connect to API: {e}")
