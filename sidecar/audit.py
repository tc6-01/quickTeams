"""Audit log for tracking state transitions and recovery actions."""

import json
import time
from typing import Optional

from .db import get_db


def log(run_id: Optional[str], event_type: str, detail: dict):
    """Write an audit log entry."""
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO audit_log (run_id, event_type, detail, created_at)
            VALUES (?, ?, ?, ?)
        """, [run_id, event_type, json.dumps(detail), int(time.time())])
        conn.commit()
    finally:
        conn.close()


def query_by_run(run_id: str, limit: int = 100) -> list[dict]:
    """Get audit entries for a run."""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT id, run_id, event_type, detail, created_at
            FROM audit_log
            WHERE run_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, [run_id, limit]).fetchall()
        return [_row_to_entry(r) for r in rows]
    finally:
        conn.close()


def _row_to_entry(row) -> dict:
    detail = row[3]
    if isinstance(detail, str):
        detail = json.loads(detail)
    return {
        "id": row[0],
        "run_id": row[1],
        "event_type": row[2],
        "detail": detail,
        "created_at": row[4],
    }
