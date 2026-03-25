"""Outbox store with ACK, idempotency, and retry support."""

import json
import time
import uuid
from typing import Optional

from .db import get_db
from .config import (
    ACK_TIMEOUT, MAX_DISPATCH_RETRIES, RETRY_BACKOFF_BASE
)


class OutboxStore:
    """Manages completion events with durable persistence and idempotent delivery."""

    def enqueue(self, run_id: str, stage_id: str, worker_id: str,
                payload: dict) -> str:
        """Enqueue a new completion event. Returns event_id."""
        event_id = str(uuid.uuid4())
        now = int(time.time())
        conn = get_db()
        try:
            conn.execute("""
                INSERT INTO outbox
                (event_id, run_id, stage_id, worker_id, payload, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'PENDING', ?)
            """, [event_id, run_id, stage_id, worker_id, json.dumps(payload), now])
            conn.commit()
        finally:
            conn.close()
        return event_id

    def fetch_pending(self, run_id: str, limit: int = 100) -> list[dict]:
        """Fetch pending events for a run."""
        conn = get_db()
        try:
            rows = conn.execute("""
                SELECT event_id, run_id, stage_id, worker_id, payload, created_at,
                       dispatch_count
                FROM outbox
                WHERE run_id = ? AND status = 'PENDING'
                ORDER BY created_at ASC
                LIMIT ?
            """, [run_id, limit]).fetchall()
            return [self._row_to_event(r) for r in rows]
        finally:
            conn.close()

    def mark_dispatched(self, event_id: str) -> bool:
        """Mark event as dispatched. Returns False if event not found or already acked."""
        conn = get_db()
        try:
            cursor = conn.execute("""
                UPDATE outbox
                SET status = 'DISPATCHED',
                    dispatch_count = dispatch_count + 1,
                    last_dispatch = ?
                WHERE event_id = ? AND status = 'PENDING'
            """, [int(time.time()), event_id])
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def mark_acked(self, event_id: str) -> bool:
        """Mark event as acknowledged. Idempotent — safe to call multiple times."""
        conn = get_db()
        try:
            cursor = conn.execute("""
                UPDATE outbox
                SET status = 'ACKED', acked_at = ?
                WHERE event_id = ? AND status != 'ACKED'
            """, [int(time.time()), event_id])
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def mark_retry(self, event_id: str) -> bool:
        """Reset PENDING for retry. Returns False if max retries exceeded."""
        conn = get_db()
        try:
            # Check retry count
            row = conn.execute(
                "SELECT dispatch_count FROM outbox WHERE event_id = ?",
                [event_id]
            ).fetchone()
            if not row or row[0] >= MAX_DISPATCH_RETRIES:
                return False

            cursor = conn.execute("""
                UPDATE outbox
                SET status = 'PENDING'
                WHERE event_id = ? AND dispatch_count < ?
            """, [event_id, MAX_DISPATCH_RETRIES])
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def mark_dead_letter(self, event_id: str, reason: str,
                         audit: dict) -> bool:
        """Move event to dead letter queue."""
        conn = get_db()
        try:
            # Get original event
            row = conn.execute(
                "SELECT run_id, payload FROM outbox WHERE event_id = ?",
                [event_id]
            ).fetchone()
            if not row:
                return False

            now = int(time.time())
            conn.execute("""
                INSERT INTO dead_letter (event_id, run_id, reason, payload, audit, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [event_id, row[0], reason, row[1], json.dumps(audit), now])

            conn.execute(
                "UPDATE outbox SET status = 'DEAD_LETTER' WHERE event_id = ?",
                [event_id]
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def is_duplicate(self, event_id: str) -> bool:
        """Check if event has already been processed (ACKED)."""
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT status FROM outbox WHERE event_id = ?",
                [event_id]
            ).fetchone()
            return row is not None and row[0] == 'ACKED'
        finally:
            conn.close()

    def get_stale_dispatched(self, timeout: int = ACK_TIMEOUT) -> list[dict]:
        """Get dispatched events that have not been acked within timeout."""
        cutoff = int(time.time()) - timeout
        conn = get_db()
        try:
            rows = conn.execute("""
                SELECT event_id, run_id, stage_id, worker_id, payload,
                       created_at, dispatch_count
                FROM outbox
                WHERE status = 'DISPATCHED' AND last_dispatch < ?
            """, [cutoff]).fetchall()
            return [self._row_to_event(r) for r in rows]
        finally:
            conn.close()

    def _row_to_event(self, row) -> dict:
        return {
            "event_id": row[0],
            "run_id": row[1],
            "stage_id": row[2],
            "worker_id": row[3],
            "payload": json.loads(row[4]) if isinstance(row[4], str) else row[4],
            "created_at": row[5],
            "dispatch_count": row[6],
        }


# Convenience instance
store = OutboxStore()
enqueue = store.enqueue
fetch_pending = store.fetch_pending
mark_dispatched = store.mark_dispatched
mark_acked = store.mark_acked
mark_retry = store.mark_retry
mark_dead_letter = store.mark_dead_letter
is_duplicate = store.is_duplicate
get_stale_dispatched = store.get_stale_dispatched
