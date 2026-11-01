"""Compare SQLite and MongoDB to identify missing fields."""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.db.sqlite import connection
from app.auth import store as auth_store

print("Comparing SQLite vs MongoDB...")
print(f"SQLite DB: {settings.sqlite_file}\n")

# Check missions
print("=== MISSIONS ===")
with connection() as conn:
    sqlite_missions = conn.execute("SELECT * FROM missions LIMIT 3").fetchall()
    if sqlite_missions:
        print("SQLite mission fields:")
        for key in sqlite_missions[0].keys():
            print(f"  - {key}")
    else:
        print("No missions in SQLite")

db = auth_store.get_db()
mongo_missions = list(db.missions.find().limit(1))
if mongo_missions:
    print("\nMongoDB mission fields:")
    for key in mongo_missions[0].keys():
        print(f"  - {key}")
else:
    print("No missions in MongoDB")

# Check departments
print("\n=== DEPARTMENTS ===")
with connection() as conn:
    sqlite_depts = conn.execute("SELECT * FROM departments LIMIT 3").fetchall()
    if sqlite_depts:
        print("SQLite department fields:")
        for key in sqlite_depts[0].keys():
            print(f"  - {key}")
    else:
        print("No departments in SQLite")

mongo_depts = list(db.departments.find().limit(1))
if mongo_depts:
    print("\nMongoDB department fields:")
    for key in mongo_depts[0].keys():
        print(f"  - {key}")
else:
    print("No departments in MongoDB")

# Check agents
print("\n=== AGENTS ===")
with connection() as conn:
    sqlite_agents = conn.execute("SELECT * FROM agents LIMIT 3").fetchall()
    if sqlite_agents:
        print("SQLite agent fields:")
        for key in sqlite_agents[0].keys():
            print(f"  - {key}")
    else:
        print("No agents in SQLite")

mongo_agents = list(db.agents.find().limit(1))
if mongo_agents:
    print("\nMongoDB agent fields:")
    for key in mongo_agents[0].keys():
        print(f"  - {key}")
else:
    print("No agents in MongoDB")

# Sample mission data comparison
print("\n=== SAMPLE MISSION DATA ===")
with connection() as conn:
    sample = conn.execute("SELECT * FROM missions LIMIT 1").fetchone()
    if sample:
        print("SQLite sample:")
        print(dict(sample))

mongo_sample = db.missions.find_one()
if mongo_sample:
    print("\nMongoDB sample:")
    print(mongo_sample)
