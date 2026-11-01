"""Check MongoDB data to diagnose visibility issues."""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.auth import store as auth_store

print("Checking MongoDB data...")

# Check missions
print("\n=== MISSIONS ===")
db = auth_store.get_db()
missions = list(db.missions.find().limit(5))
if missions:
    print(f"Total missions: {db.missions.count_documents({})}")
    print("Sample missions:")
    for m in missions:
        print(f"  ID: {m.get('_id')}, User: {m.get('user_id')}, Dept: {m.get('department_id')}, Status: {m.get('status')}")
else:
    print("No missions found")

# Check departments
print("\n=== DEPARTMENTS ===")
depts = list(db.departments.find().limit(5))
if depts:
    print(f"Total departments: {db.departments.count_documents({})}")
    print("Sample departments:")
    for d in depts:
        print(f"  ID: {d.get('_id')}, User: {d.get('created_by')}, Name: {d.get('name')}")
else:
    print("No departments found")

# Check unique user_ids
print("\n=== USER IDS ===")
mission_users = db.missions.distinct("user_id")
dept_users = db.departments.distinct("created_by")
print(f"Mission user_ids: {mission_users}")
print(f"Department created_by: {dept_users}")

# Check oauth_connections
print("\n=== OAUTH CONNECTIONS ===")
try:
    from app.db.sqlite import connection
    with connection() as c:
        rows = c.execute("SELECT user_id FROM oauth_connections LIMIT 5").fetchall()
        if rows:
            print(f"OAuth user_ids: {[r['user_id'] for r in rows]}")
        else:
            print("No OAuth connections found")
except Exception as e:
    print(f"Error checking OAuth: {e}")
