"""Step 1 — verify the schema creates idempotently and all tables exist."""

from __future__ import annotations

from app.db.sqlite import connection, init_db

EXPECTED_TABLES = {
    "missions",
    "mission_tasks",
    "execution_traces",
    "agents",
    "user_settings",
}


def test_init_db_creates_all_tables():
    init_db()
    with connection() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    names = {r["name"] for r in rows}
    assert EXPECTED_TABLES.issubset(names)


def test_init_db_is_idempotent():
    init_db()
    init_db()  # second run must not raise
    with connection() as conn:
        count = conn.execute("SELECT COUNT(*) AS n FROM missions").fetchone()["n"]
    assert count == 0


def test_can_insert_and_read_mission():
    from app.db.sqlite import _now

    with connection() as conn:
        conn.execute(
            "INSERT INTO missions (id, prompt, status, created_by, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("m1", "test goal", "planning", "default-user", _now()),
        )
    with connection() as conn:
        row = conn.execute("SELECT * FROM missions WHERE id = 'm1'").fetchone()
    assert row["prompt"] == "test goal"
    assert row["status"] == "planning"
