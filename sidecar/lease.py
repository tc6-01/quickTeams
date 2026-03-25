"""Lead lease and heartbeat manager."""

import time
from enum import Enum
from typing import Optional

from .db import get_db
from .config import HEARTBEAT_TTL, STALE_THRESHOLD, RECOVERY_TIMEOUT


class LeaseStatus(Enum):
    HEALTHY = "HEALTHY"
    SUSPECTED_SLEEP = "SUSPECTED_SLEEP"
    UNAVAILABLE = "UNAVAILABLE"


class LeaseManager:
    """Manages lead lease lifecycle and heartbeat."""

    def acquire(self, run_id: str, holder: str) -> bool:
        """Acquire a new lease. Returns False if already exists."""
        now = int(time.time())
        conn = get_db()
        try:
            cursor = conn.execute("""
                INSERT INTO leases (run_id, holder, status, last_heartbeat, expires_at)
                VALUES (?, ?, 'HEALTHY', ?, ?)
            """, [run_id, holder, now, now + HEARTBEAT_TTL])
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def renew(self, run_id: str, holder: str) -> bool:
        """Renew an existing lease. Idempotent."""
        now = int(time.time())
        conn = get_db()
        try:
            cursor = conn.execute("""
                UPDATE leases
                SET last_heartbeat = ?,
                    expires_at = ?,
                    status = 'HEALTHY',
                    holder = ?
                WHERE run_id = ?
            """, [now, now + HEARTBEAT_TTL, holder, run_id])
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_status(self, run_id: str) -> Optional[LeaseStatus]:
        """Get current lease status."""
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT status FROM leases WHERE run_id = ?",
                [run_id]
            ).fetchone()
            return LeaseStatus(row[0]) if row else None
        finally:
            conn.close()

    def transition_to(self, run_id: str, new_status: LeaseStatus) -> bool:
        """Transition lease to new status."""
        conn = get_db()
        try:
            cursor = conn.execute("""
                UPDATE leases SET status = ? WHERE run_id = ?
            """, [new_status.value, run_id])
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_stale_leases(self) -> list[dict]:
        """Get leases that have passed their expiry time."""
        now = int(time.time())
        conn = get_db()
        try:
            rows = conn.execute("""
                SELECT run_id, holder, status, last_heartbeat, expires_at
                FROM leases
                WHERE status = 'HEALTHY' AND expires_at < ?
            """, [now]).fetchall()
            return [self._row_to_lease(r) for r in rows]
        finally:
            conn.close()

    def get_suspected_sleep(self) -> list[dict]:
        """Get leases in SUSPECTED_SLEEP status."""
        conn = get_db()
        try:
            rows = conn.execute("""
                SELECT run_id, holder, status, last_heartbeat, expires_at
                FROM leases
                WHERE status = 'SUSPECTED_SLEEP'
            """).fetchall()
            return [self._row_to_lease(r) for r in rows]
        finally:
            conn.close()

    def _row_to_lease(self, row) -> dict:
        return {
            "run_id": row[0],
            "holder": row[1],
            "status": row[2],
            "last_heartbeat": row[3],
            "expires_at": row[4],
        }


# Convenience instance
manager = LeaseManager()
acquire = manager.acquire
renew = manager.renew
get_status = manager.get_status
transition_to = manager.transition_to
get_stale_leases = manager.get_stale_leases
get_suspected_sleep = manager.get_suspected_sleep
