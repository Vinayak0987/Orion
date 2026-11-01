"""Compare SQLite and MongoDB departments to identify missing fields."""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.db.sqlite import connection
from app.auth import store as auth_store

print("Comparing SQLite vs MongoDB for departments...")
print(f"SQLite DB: {settings.sqlite_file}\n")

# Check departments
print("=== DEPARTMENTS ===")
with connection() as conn:
    sqlite_depts = conn.execute("SELECT * FROM departments LIMIT 3").fetchall()
    if sqlite_depts:
        print("SQLite department fields:")
        for key in sqlite_depts[0].keys():
            print(f"  - {key}")
    else:
        print("No departments in SQLite")

db = auth_store.get_db()
mongo_depts = list(db.departments.find().limit(1))
if mongo_depts:
    print("\nMongoDB department fields:")
    for key in mongo_depts[0].keys():
        print(f"  - {key}")
else:
    print("No departments in MongoDB")

# Compare field sets
print("\n=== FIELD COMPARISON ===")
if sqlite_depts and mongo_depts:
    sqlite_fields = set(sqlite_depts[0].keys())
    mongo_fields = set(mongo_depts[0].keys())
    
    print(f"\nSQLite-only fields (missing in MongoDB):")
    missing_in_mongo = sqlite_fields - mongo_fields
    if missing_in_mongo:
        for f in sorted(missing_in_mongo):
            print(f"  - {f}")
    else:
        print("  None")
    
    print(f"\nMongoDB-only fields (not in SQLite):")
    extra_in_mongo = mongo_fields - sqlite_fields
    if extra_in_mongo:
        for f in sorted(extra_in_mongo):
            print(f"  - {f}")
    else:
        print("  None")
    
    print(f"\nCommon fields:")
    common = sqlite_fields & mongo_fields
    for f in sorted(common):
        print(f"  - {f}")

# Sample data comparison
print("\n=== SAMPLE DEPARTMENT DATA ===")
with connection() as conn:
    sample = conn.execute("SELECT * FROM departments LIMIT 1").fetchone()
    if sample:
        print("SQLite sample:")
        for key, value in dict(sample).items():
            print(f"  {key}: {value}")

mongo_sample = db.departments.find_one()
if mongo_sample:
    print("\nMongoDB sample:")
    for key, value in mongo_sample.items():
        print(f"  {key}: {value}")

# Check department_members
print("\n=== DEPARTMENT MEMBERS ===")
with connection() as conn:
    sqlite_members = conn.execute("SELECT * FROM department_members LIMIT 3").fetchall()
    if sqlite_members:
        print("SQLite department_members fields:")
        for key in sqlite_members[0].keys():
            print(f"  - {key}")
    else:
        print("No department_members in SQLite")

mongo_members = list(db.department_members.find().limit(1))
if mongo_members:
    print("\nMongoDB department_members fields:")
    for key in mongo_members[0].keys():
        print(f"  - {key}")
else:
    print("No department_members in MongoDB")

# Compare member field sets
if sqlite_members and mongo_members:
    sqlite_member_fields = set(sqlite_members[0].keys())
    mongo_member_fields = set(mongo_members[0].keys())
    
    print(f"\nSQLite-only member fields (missing in MongoDB):")
    missing_in_mongo = sqlite_member_fields - mongo_member_fields
    if missing_in_mongo:
        for f in sorted(missing_in_mongo):
            print(f"  - {f}")
    else:
        print("  None")
    
    print(f"\nMongoDB-only member fields (not in SQLite):")
    extra_in_mongo = mongo_member_fields - sqlite_member_fields
    if extra_in_mongo:
        for f in sorted(extra_in_mongo):
            print(f"  - {f}")
    else:
        print("  None")
