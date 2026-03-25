"""Dead letter queue for unprocessable events."""

import json
import time
from typing import Optional

from .db import get_db


class DeadLetterQueue:
    """Manages dead letter queue and diagnostics."""

    def enqueue(self, event_id: Optional[str], run_id: Optional[str],
                reason: str, payload: Optional[dict] = None,
                audit: Optional[dict] = None) -> int:
        """Add an item to the dead letter queue. Returns DLQ id."""
        conn = get_db()
        try:
            cursor = conn.execute("""
                INSERT INTO dead_letter (event_id, run_id, reason, payload, audit, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                event_id,
                run_id,
                reason,
                json.dumps(payload) if payload else None,
                json.dumps(audit) if audit else None,
                int(time.time())
            ])
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def list(self, run_id: Optional[str] = None, limit: int = 50) -> list[dict]:
        """List DLQ entries, optionally filtered by run_id."""
        conn = get_db()
        try:
            if run_id:
                rows = conn.execute("""
                    SELECT id, event_id, run_id, reason, payload, audit, created_at
                    FROM dead_letter
                    WHERE run_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, [run_id, limit]).fetchall()
            else:
                rows = conn.execute("""
                    SELECT id, event_id, run_id, reason, payload, audit, created_at
                    FROM dead_letter
                    ORDER BY created_at DESC
                    LIMIT ?
                """, [limit]).fetchall()
            return [self._row_to_entry(r) for r in rows]
        finally:
            conn.close()

    def get_diagnostics(self, dlq_id: int) -> Optional[dict]:
        """Get detailed diagnostics for a DLQ entry."""
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT id, event_id, run_id, reason, payload, audit, created_at FROM dead_letter WHERE id = ?",
                [dlq_id]
            ).fetchone()
            return self._row_to_entry(row) if row else None
        finally:
            conn.close()

    def _row_to_entry(self, row) -> dict:
        return {
            "id": row[0],
            "event_id": row[1],
            "run_id": row[2],
            "reason": row[3],
            "payload": json.loads(row[4]) if row[4] else None,
            "audit": json.loads(row[5]) if row[5] else None,
            "created_at": row[6],
        }


queue = DeadLetterQueue()
enqueue = queue.enqueue
list = queue.list
get_diagnostics = queue.get_diagnostics
