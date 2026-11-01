"""Update existing MongoDB records with missing fields from SQLite.

This script syncs any fields that were missing in the initial migration.
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.db.sqlite import connection
from app.auth import store as auth_store

print("Updating migrated data with missing fields...")
print(f"SQLite DB: {settings.sqlite_file}\n")

db = auth_store.get_db()

# Update missions
print("Updating missions...")
with connection() as conn:
    rows = conn.execute("SELECT * FROM missions").fetchall()
    print(f"Found {len(rows)} missions in SQLite")

updated_count = 0
for row in rows:
    mission = dict(row)
    mission_id = mission.get("id")
    if not mission_id:
        continue

    # Get existing Mongo document
    existing = db.missions.find_one({"_id": mission_id})
    if not existing:
        continue

    # Check for missing fields and update
    updates = {}
    if mission.get("mode") and existing.get("mode") != mission.get("mode"):
        updates["mode"] = mission.get("mode")
    if mission.get("status") and existing.get("status") != mission.get("status"):
        updates["status"] = mission.get("status")
    if mission.get("completed_at") and existing.get("completed_at") != mission.get("completed_at"):
        updates["completed_at"] = mission.get("completed_at")
    if mission.get("created_at") and existing.get("created_at") != mission.get("created_at"):
        updates["created_at"] = mission.get("created_at")

    if updates:
        db.missions.update_one({"_id": mission_id}, {"$set": updates})
        updated_count += 1
        print(f"  Updated {mission_id}: {list(updates.keys())}")

print(f"Updated {updated_count} missions\n")

# Update departments
print("Updating departments...")
with connection() as conn:
    rows = conn.execute("SELECT * FROM departments").fetchall()
    print(f"Found {len(rows)} departments in SQLite")

updated_count = 0
for row in rows:
    dept = dict(row)
    dept_id = dept.get("id")
    if not dept_id:
        continue

    existing = db.departments.find_one({"_id": dept_id})
    if not existing:
        continue

    updates = {}
    if dept.get("dept_type") and existing.get("dept_type") != dept.get("dept_type"):
        updates["dept_type"] = dept.get("dept_type")
    if dept.get("status") and existing.get("status") != dept.get("status"):
        updates["status"] = dept.get("status")
    if dept.get("is_default") is not None and existing.get("is_default") != dept.get("is_default"):
        updates["is_default"] = dept.get("is_default")
    if dept.get("updated_at") and existing.get("updated_at") != dept.get("updated_at"):
        updates["updated_at"] = dept.get("updated_at")

    if updates:
        db.departments.update_one({"_id": dept_id}, {"$set": updates})
        updated_count += 1
        print(f"  Updated {dept_id}: {list(updates.keys())}")

print(f"Updated {updated_count} departments\n")

# Update agents
print("Updating agents...")
with connection() as conn:
    rows = conn.execute("SELECT * FROM agents").fetchall()
    print(f"Found {len(rows)} agents in SQLite")

updated_count = 0
for row in rows:
    agent = dict(row)
    agent_id = agent.get("id")
    if not agent_id:
        continue

    existing = db.agents.find_one({"_id": agent_id})
    if not existing:
        continue

    updates = {}
    if agent.get("memory_ttl_days") is not None and existing.get("memory_ttl_days") != agent.get("memory_ttl_days"):
        updates["memory_ttl_days"] = agent.get("memory_ttl_days")
    if agent.get("version") and existing.get("version") != agent.get("version"):
        updates["version"] = agent.get("version")
    if agent.get("origin") and existing.get("origin") != agent.get("origin"):
        updates["origin"] = agent.get("origin")
    if agent.get("role_title") and existing.get("role_title") != agent.get("role_title"):
        updates["role_title"] = agent.get("role_title")
    if agent.get("updated_at") and existing.get("updated_at") != agent.get("updated_at"):
        updates["updated_at"] = agent.get("updated_at")

    if updates:
        db.agents.update_one({"_id": agent_id}, {"$set": updates})
        updated_count += 1
        print(f"  Updated {agent_id}: {list(updates.keys())}")

print(f"Updated {updated_count} agents\n")

print("Update complete!")
