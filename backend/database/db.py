import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, Optional


def _default_db_path() -> str:
    env_path = os.environ.get("VERIDIAN_DB_PATH")
    if env_path:
        return os.path.abspath(env_path)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    default_path = os.path.abspath(os.path.join(project_root, "veridian.db"))
    try:
        test_file = os.path.join(project_root, ".write_test")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return default_path
    except (PermissionError, OSError):
        return "/tmp/veridian.db"



def _resolve_path(override: Optional[str] = None) -> str:
    if override:
        return os.path.abspath(override)
    return _default_db_path()


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _create_tickets_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id TEXT PRIMARY KEY,
            employee_name TEXT,
            employee_email TEXT,
            issue TEXT NOT NULL,
            category TEXT,
            priority TEXT NOT NULL DEFAULT 'MEDIUM',
            status TEXT NOT NULL DEFAULT 'OPEN',
            assigned_team TEXT NOT NULL DEFAULT 'Human IT Review',
            escalation_reason TEXT,
            source_policy_ids TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )


def _create_audit_logs_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT,
            action TEXT NOT NULL,
            decision TEXT NOT NULL,
            issue TEXT,
            source_policy_ids TEXT,
            reason TEXT,
            timestamp TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id) ON DELETE SET NULL
        )
        """
    )


def initialize_database(db_path: Optional[str] = None) -> str:
    path = _resolve_path(db_path)
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with _connect(path) as conn:
        _create_tickets_table(conn)
        _create_audit_logs_table(conn)
        conn.commit()
    return path


@contextmanager
def get_connection(db_path: Optional[str] = None) -> Iterator[sqlite3.Connection]:
    path = _resolve_path(db_path)
    initialize_database(db_path=path)
    conn = _connect(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")
