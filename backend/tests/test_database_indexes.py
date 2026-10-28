from app.core.database import get_connection


def _index_names():
    conn = get_connection()
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
    conn.close()
    return {r["name"] for r in rows}


def test_indexes_are_created(client):
    names = _index_names()
    for expected in [
        "idx_chat_messages_user_id",
        "idx_health_records_user_id",
        "idx_health_records_user_type_date",
        "idx_user_memories_user_type",
        "idx_reminders_user_status",
        "idx_hospitals_city",
    ]:
        assert expected in names


def test_init_db_is_safe_to_run_twice(client):
    from app.core.database import init_db
    init_db()
    init_db()


def test_recent_messages_query_uses_the_index(client):
    conn = get_connection()
    plan = conn.execute(
        "EXPLAIN QUERY PLAN SELECT role, message, created_at FROM chat_messages "
        "WHERE user_id = ? ORDER BY id DESC LIMIT ?", ("1", 5)
    ).fetchall()
    conn.close()
    detail = " ".join(row["detail"] for row in plan)
    assert "idx_chat_messages_user_id" in detail
    assert "SCAN chat_messages" not in detail


def test_wal_mode_is_enabled(client):
    conn = get_connection()
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    conn.close()
    assert mode.lower() == "wal"
