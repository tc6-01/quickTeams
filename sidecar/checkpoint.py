"""Checkpoint store for workflow state persistence and recovery."""

import json
from typing import Optional

from .db import get_db


class CheckpointStore:
    """Manages workflow checkpoints."""

    def save(self, run_id: str, stage_id: str, snapshot: dict,
             is_consistent: bool = True) -> int:
        """Save a checkpoint. Returns checkpoint id."""
        conn = get_db()
        try:
            cursor = conn.execute("""
                INSERT INTO checkpoints (run_id, stage_id, snapshot, created_at, is_consistent)
                VALUES (?, ?, ?, ?, ?)
            """, [run_id, stage_id, json.dumps(snapshot), int(__import__('time').time()),
                  1 if is_consistent else 0])
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def load_latest(self, run_id: str) -> Optional[dict]:
        """Load the latest checkpoint for a run."""
        conn = get_db()
        try:
            row = conn.execute("""
                SELECT id, stage_id, snapshot, created_at, is_consistent
                FROM checkpoints
                WHERE run_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, [run_id]).fetchone()
            return self._row_to_checkpoint(row) if row else None
        finally:
            conn.close()

    def load_latest_consistent(self, run_id: str) -> Optional[dict]:
        """Load the latest consistent checkpoint."""
        conn = get_db()
        try:
            row = conn.execute("""
                SELECT id, stage_id, snapshot, created_at, is_consistent
                FROM checkpoints
                WHERE run_id = ? AND is_consistent = 1
                ORDER BY created_at DESC
                LIMIT 1
            """, [run_id]).fetchone()
            return self._row_to_checkpoint(row) if row else None
        finally:
            conn.close()

    def _row_to_checkpoint(self, row) -> dict:
        return {
            "id": row[0],
            "stage_id": row[1],
            "snapshot": json.loads(row[2]) if isinstance(row[2], str) else row[2],
            "created_at": row[3],
            "is_consistent": bool(row[4]),
        }


store = CheckpointStore()
save = store.save
load_latest = store.load_latest
load_latest_consistent = store.load_latest_consistent
