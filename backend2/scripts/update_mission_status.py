"""Update MongoDB missions with status and completion data from SQLite.

This script will update existing MongoDB missions with:
- status (planning/running/completed/failed/partial)
- completed_at timestamp
- progress data (will be calculated from mission_tasks)

Run this to fix missions showing as "Planning" with 0% progress.
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.db.sqlite import connection
from app.auth import store as auth_store


def update_mission_status():
    """Update mission status and completion data from SQLite to MongoDB."""
    print("Updating mission status from SQLite to MongoDB...")
    with connection() as conn:
        sqlite_missions = conn.execute("SELECT * FROM missions").fetchall()
        print(f"Found {len(sqlite_missions)} missions in SQLite")

    updated = 0
    for row in sqlite_missions:
        mission = dict(row)
        mission_id = mission.get("id") or mission.get("_id")
        if not mission_id:
            continue

        # Get task count to calculate progress
        with connection() as conn:
            tasks = conn.execute(
                "SELECT status FROM mission_tasks WHERE mission_id=?",
                (mission_id,)
            ).fetchall()

        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks if t["status"] == "completed")

        # Calculate progress percentage
        progress = int((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0

        # Get mission status from SQLite
        status = mission.get("status", "planning")
        completed_at = mission.get("completed_at")

        # Update MongoDB mission
        try:
            update_data = {
                "status": status,
                "completed_at": completed_at,
                "progress": progress,
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
            }

            # Also update other fields that might be missing
            if mission.get("department_id"):
                update_data["department_id"] = mission.get("department_id")
            if mission.get("conversation_id"):
                update_data["conversation_id"] = mission.get("conversation_id")
            if mission.get("mode"):
                update_data["mode"] = mission.get("mode")

            auth_store.update_mission(mission_id, **update_data)
            print(f"  Updated {mission_id}: status={status}, progress={progress}%")
            updated += 1
        except Exception as e:
            print(f"  Error updating {mission_id}: {e}")

    print(f"\nUpdated {updated} missions")
    return updated


if __name__ == "__main__":
    print("Starting mission status update...")
    print(f"SQLite DB: {settings.sqlite_file}")

    update_mission_status()

    print("\nUpdate complete!")
    print("Your missions should now show correct status and progress.")
