"""Watchdog timer for hang detection and recovery triggering."""

import time
import threading
from typing import Callable, Optional

from .db import get_db
from .config import WATCHDOG_INTERVAL, HANG_TIMEOUT, STALE_THRESHOLD
from .lease import manager as lease_manager
from .outbox import store as outbox_store


class Watchdog:
    """Periodically scans for stale runs and triggers reconciliation."""

    def __init__(self, on_reconcile: Callable[[str], None] = None):
        self.on_reconcile = on_reconcile  # callback(run_id)
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Start watchdog in background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the watchdog thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def tick(self):
        """Single watchdog scan. Call this from tests or manual triggers."""
        self._scan_stale_leases()
        self._scan_suspected_sleep()
        self._scan_stale_runs()

    def _run(self):
        """Main watchdog loop."""
        while self._running:
            self.tick()
            time.sleep(WATCHDOG_INTERVAL)

    def _scan_stale_leases(self):
        """Promote HEALTHY but expired leases to SUSPECTED_SLEEP."""
        stale = lease_manager.get_stale_leases()
        for lease in stale:
            lease_manager.transition_to(lease["run_id"], "SUSPECTED_SLEEP")
            self._audit("LEASE_TRANSITION", lease["run_id"], {
                "from": "HEALTHY",
                "to": "SUSPECTED_SLEEP",
                "reason": "stale_heartbeat",
            })

    def _scan_suspected_sleep(self):
        """Check if suspected-sleep leads have recovered or should be UNAVAILABLE."""
        suspected = lease_manager.get_suspected_sleep()
        now = int(time.time())
        for lease in suspected:
            age = now - lease["last_heartbeat"]
            if age < STALE_THRESHOLD:
                # Recovered
                lease_manager.transition_to(lease["run_id"], "HEALTHY")
                self._audit("LEASE_TRANSITION", lease["run_id"], {
                    "from": "SUSPECTED_SLEEP",
                    "to": "HEALTHY",
                    "reason": "heartbeat_recovered",
                })
                # Trigger replay of pending events
                if self.on_reconcile:
                    self.on_reconcile(lease["run_id"])

    def _scan_stale_runs(self):
        """Detect runs with no progress and trigger reconciliation."""
        cutoff = int(time.time()) - HANG_TIMEOUT
        conn = get_db()
        try:
            rows = conn.execute("""
                SELECT id FROM runs
                WHERE status = 'RUNNING' AND updated_at < ?
            """, [cutoff]).fetchall()
            for (run_id,) in rows:
                self._audit("HANG_DETECTED", run_id, {
                    "reason": "no_progress",
                    "cutoff": cutoff,
                })
                if self.on_reconcile:
                    self.on_reconcile(run_id)
        finally:
            conn.close()

    def _audit(self, event_type: str, run_id: str, detail: dict):
        """Write audit log entry."""
        conn = get_db()
        try:
            import json
            conn.execute("""
                INSERT INTO audit_log (run_id, event_type, detail, created_at)
                VALUES (?, ?, ?, ?)
            """, [run_id, event_type, json.dumps(detail), int(time.time())])
            conn.commit()
        finally:
            conn.close()
