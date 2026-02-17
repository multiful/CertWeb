"""
DB schema update summary:
1. Dropped columns from job table: outlook, salary_info, description
2. Created major table with: major_id, major_name, major_category
3. Populated major table with 420 entries from integrated_major1.csv
4. Added Major model to app/models.py
5. Added MajorResponse schema to app/schemas/__init__.py
6. Added MajorCRUD to app/crud.py
7. Created /api/v1/majors endpoint for major search
8. Updated JobResponse schema (removed dropped fields)
9. Fixed duplicate __repr__ in Job model

Status: Complete
"""
