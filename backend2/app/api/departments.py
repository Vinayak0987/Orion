"""Departments REST API — the org layer + live activity for the rich UI."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.departments import store

router = APIRouter(tags=["departments"])
DEFAULT_USER = "default-user"


def _owner() -> str:
    """Resolve the acting owner. Single-tenant: prefer the one real signed-in
    user (who owns OAuth connections) so custom departments + missions line up."""
    try:
        from app.db.sqlite import connection
        with connection() as c:
            row = c.execute("SELECT user_id FROM oauth_connections LIMIT 1").fetchone()
        if row:
            return row["user_id"]
    except Exception:  # noqa: BLE001
        pass
    return DEFAULT_USER


class CreateDepartmentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    purpose: str = ""
    responsibilities: list[str] = Field(default_factory=list)
    dept_type: str = "custom"
    instructions: str = ""


class UpdateDepartmentRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    purpose: str | None = None
    responsibilities: list[str] | None = None
    dept_type: str | None = None
    instructions: str | None = None
    status: str | None = None


class ArchitectRequest(BaseModel):
    description: str = Field(min_length=1, max_length=8000)


@router.post("/departments/architect")
async def architect(req: ArchitectRequest) -> dict:
    from app.departments import architect as arch
    from app.llm.client import AllProvidersFailedError
    from app.settings import store as settings_store
    try:
        keys = settings_store.decrypted_keys(_owner())
    except Exception:  # noqa: BLE001
        keys = None
    try:
        return await arch.design_department(req.description, user_keys=keys)
    except AllProvidersFailedError as e:
        raise HTTPException(503, f"No LLM available: {e}") from e


@router.get("/departments")
async def list_departments(status: str | None = None, search: str | None = None) -> dict:
    depts = store.list_departments_with_stats(created_by=_owner(), status=status, search=search)
    return {"departments": depts, "count": len(depts)}


@router.post("/departments", status_code=201)
async def create_department(req: CreateDepartmentRequest) -> dict:
    did = store.create_department(created_by=_owner(), **req.model_dump())
    return {"department_id": did, "department": store.get_department(did, created_by=_owner())}


@router.get("/departments/{dept_id}")
async def get_department(dept_id: str) -> dict:
    d = store.get_department(dept_id, created_by=_owner())
    if d is None:
        raise HTTPException(404, f"Department '{dept_id}' not found")
    d["members"] = store.list_members(dept_id)
    d["head"] = store.get_head(dept_id)
    d["stats"] = store.department_stats(dept_id)
    return d


@router.put("/departments/{dept_id}")
async def update_department(dept_id: str, req: UpdateDepartmentRequest) -> dict:
    changes = {k: v for k, v in req.model_dump(exclude_unset=True).items()}
    updated = store.update_department(dept_id, changes, created_by=_owner())
    if updated is None:
        raise HTTPException(404, f"Department '{dept_id}' not found")
    return {"department": updated}


@router.delete("/departments/{dept_id}")
async def archive_department(dept_id: str) -> dict:
    if not store.archive_department(dept_id, created_by=_owner()):
        raise HTTPException(404, "Department not found or cannot be archived (default)")
    return {"archived": dept_id}


@router.get("/departments/{dept_id}/members")
async def list_members(dept_id: str) -> dict:
    if store.get_department(dept_id, created_by=_owner()) is None:
        raise HTTPException(404, f"Department '{dept_id}' not found")
    return {"members": store.list_members(dept_id), "head": store.get_head(dept_id)}


@router.get("/departments/{dept_id}/missions")
async def department_missions(dept_id: str) -> dict:
    """Missions targeted at this department (for the Missions tab + Live Activity)."""
    from app.db.sqlite import connection
    with connection() as c:
        rows = c.execute(
            "SELECT id, prompt, title, status, mode, created_at, completed_at FROM missions "
            "WHERE department_id=? ORDER BY created_at DESC LIMIT 50", (dept_id,),
        ).fetchall()
    return {"missions": [dict(r) for r in rows]}


@router.get("/departments/{dept_id}/activity")
async def department_activity(dept_id: str) -> dict:
    """Live activity: currently-running missions + their latest tasks/agents/tools."""
    from app.db.sqlite import connection
    with connection() as c:
        running = c.execute(
            "SELECT id, prompt, title, status, created_at FROM missions "
            "WHERE department_id=? AND status IN ('planning','running','awaiting_input') "
            "ORDER BY created_at DESC", (dept_id,),
        ).fetchall()
        items = []
        for m in running:
            tasks = c.execute(
                "SELECT title, agent_id, status FROM mission_tasks WHERE mission_id=? ORDER BY created_at",
                (m["id"],),
            ).fetchall()
            tools = c.execute(
                "SELECT tool_name, success, created_at FROM execution_traces "
                "WHERE mission_id=? AND trace_type='tool' ORDER BY created_at DESC LIMIT 10",
                (m["id"],),
            ).fetchall()
            items.append({
                "mission_id": m["id"], "title": m["title"] or m["prompt"][:60],
                "status": m["status"], "created_at": m["created_at"],
                "tasks": [dict(t) for t in tasks],
                "recent_tools": [dict(t) for t in tools],
            })
    return {"running": items, "count": len(items)}


# ---- Schedules (cron-ish recurring department tasks) -----------------------
class CreateScheduleRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=2000)
    mode: str = "planning"
    cadence: str = "daily"            # interval | daily | weekly
    interval_minutes: int = 1440
    first_run_in_minutes: int = 0


@router.get("/departments/{dept_id}/schedules")
async def list_schedules(dept_id: str) -> dict:
    from app.missions import scheduler
    return {"schedules": scheduler.list_schedules(department_id=dept_id)}


@router.post("/departments/{dept_id}/schedules", status_code=201)
async def create_schedule(dept_id: str, req: CreateScheduleRequest) -> dict:
    if store.get_department(dept_id, created_by=_owner()) is None:
        raise HTTPException(404, f"Department '{dept_id}' not found")
    from app.missions import scheduler
    sid = scheduler.create_schedule(
        prompt=req.prompt, created_by=_owner(), department_id=dept_id, mode=req.mode,
        cadence=req.cadence, interval_minutes=req.interval_minutes,
        first_run_in_minutes=req.first_run_in_minutes,
    )
    return {"schedule_id": sid}


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(schedule_id: str) -> dict:
    from app.missions import scheduler
    if not scheduler.delete_schedule(schedule_id):
        raise HTTPException(404, "Schedule not found")
    return {"deleted": schedule_id}


@router.post("/schedules/{schedule_id}/toggle")
async def toggle_schedule(schedule_id: str, enabled: bool = True) -> dict:
    from app.missions import scheduler
    if not scheduler.set_enabled(schedule_id, enabled):
        raise HTTPException(404, "Schedule not found")
    return {"schedule_id": schedule_id, "enabled": enabled}
