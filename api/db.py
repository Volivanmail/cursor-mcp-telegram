import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime

DATABASE_PATH = os.getenv("DATABASE_PATH", "/data/tasks.db")


def init_db() -> None:
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                user_id TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


@contextmanager
def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "user_id": row["user_id"],
        "done": bool(row["done"]),
        "created_at": row["created_at"],
    }


def list_tasks(user_id: str | None = None) -> list[dict]:
    with get_connection() as conn:
        if user_id:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE user_id = ? ORDER BY id DESC",
                (user_id,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM tasks ORDER BY id DESC").fetchall()
        return [_row_to_dict(row) for row in rows]


def create_task(title: str, user_id: str) -> dict:
    created_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO tasks (title, user_id, done, created_at) VALUES (?, ?, 0, ?)",
            (title, user_id, created_at),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return _row_to_dict(row)


def toggle_task(task_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            return None
        new_done = 0 if row["done"] else 1
        conn.execute("UPDATE tasks SET done = ? WHERE id = ?", (new_done, task_id))
        conn.commit()
        updated = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return _row_to_dict(updated)


def delete_task(task_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        return cursor.rowcount > 0


def get_stats() -> dict:
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        done = conn.execute("SELECT COUNT(*) FROM tasks WHERE done = 1").fetchone()[0]
        users = conn.execute("SELECT COUNT(DISTINCT user_id) FROM tasks").fetchone()[0]
        return {
            "tasks_total": total,
            "tasks_done": done,
            "tasks_open": total - done,
            "users_total": users,
        }
