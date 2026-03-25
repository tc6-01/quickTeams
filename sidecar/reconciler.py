"""Reconciliation engine for recovering stalled workflow runs."""

import time
import json
from enum import Enum

from .db import get_db
from .outbox import store as outbox_store
from .lease import manager as lease_manager, LeaseStatus
from .checkpoint import store as checkpoint_store
from .deadletter import queue as dlq


class RecoveryAction(Enum):
    RESUME = "RESUME"
    REPLAY = "REPLAY"
    REPAIR = "REPAIR"
    WAKED = "WAKED"
    HANDOFF = "HANDOFF"
    DEAD = "DEAD"


class Reconciler:
    """Decides and executes recovery actions for stalled runs."""

    def reconcile(self, run_id: str) -> RecoveryAction:
        """Reconcile a stalled run and return the action taken."""
        # Get run state
        conn = get_db()
        try:
            run = conn.execute(
                "SELECT id, current_stage, status FROM runs WHERE id = ?",
                [run_id]
            ).fetchone()
            if not run:
                return RecoveryAction.DEAD
        finally:
            conn.close()

        # Get latest consistent checkpoint
        ckpt = checkpoint_store.load_latest_consistent(run_id)

        # Check for pending events
        pending = outbox_store.fetch_pending(run_id)
        dispatched = outbox_store.get_stale_dispatched()

        # Get lease status
        lease_status = lease_manager.get_status(run_id)

        # Decision tree
        if lease_status == LeaseStatus.UNAVAILABLE:
            return self._handle_unavailable(run_id)

        if ckpt:
            # Has checkpoint — check if stage matches
            if run[1] == ckpt["stage_id"]:
                return self._resume(run_id, ckpt)
            else:
                return self._replay(run_id, pending)
        else:
            # No checkpoint
            if pending or dispatched:
                return self._replay(run_id, pending + dispatched)
            else:
                return self._dead(run_id, "no_checkpoint_no_events")

    def _resume(self, run_id: str, ckpt: dict) -> RecoveryAction:
        """Resume from latest consistent checkpoint."""
        conn = get_db()
        try:
            conn.execute("""
                UPDATE runs SET status = 'RUNNING', updated_at = ?
                WHERE id = ?
            """, [int(time.time()), run_id])
            conn.commit()
        finally:
            conn.close()
        return RecoveryAction.RESUME

    def _replay(self, run_id: str, events: list) -> RecoveryAction:
        """Replay pending events."""
        for evt in events:
            outbox_store.mark_dispatched(evt["event_id"])
        return RecoveryAction.REPLAY

    def _repair(self, run_id: str, correct_stage: str) -> RecoveryAction:
        """Repair mismatched stage."""
        conn = get_db()
        try:
            conn.execute("""
                UPDATE runs SET current_stage = ?, updated_at = ?
                WHERE id = ?
            """, [correct_stage, int(time.time()), run_id])
            conn.commit()
        finally:
            conn.close()
        return RecoveryAction.REPAIR

    def _dead(self, run_id: str, reason: str) -> RecoveryAction:
        """Mark run as dead and move to DLQ."""
        conn = get_db()
        try:
            conn.execute("""
                UPDATE runs SET status = 'DEAD' WHERE id = ?
            """, [run_id])
            conn.commit()
        finally:
            conn.close()

        dlq.enqueue(None, run_id, reason, audit={"action": "DEAD"})
        return RecoveryAction.DEAD

    def decide_recovery_action(self, run_id: str) -> RecoveryAction:
        """Public API for deciding recovery action (used by watchdog callback)."""
        return self.reconcile(run_id)


reconciler = Reconciler()
reconcile = reconciler.reconcile
decide_recovery_action = reconciler.decide_recovery_action
