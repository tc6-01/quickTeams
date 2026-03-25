#!/usr/bin/env python3
"""Save a workflow checkpoint."""

import sys
import json
import time
from typing import Optional
sys.path.insert(0, "/Users/roubaojiasudu/Desktop/code AI/repo/quickTeams")

from sidecar.db import get_db

def save_checkpoint(run_id: str, stage_id: str, snapshot: dict, is_consistent: bool = True) -> int:
    """Save a checkpoint for a run at a given stage."""
    now = int(time.time())
    conn = get_db()
    try:
        cursor = conn.execute("""
            INSERT INTO checkpoints (run_id, stage_id, snapshot, created_at, is_consistent)
            VALUES (?, ?, ?, ?, ?)
        """, [run_id, stage_id, json.dumps(snapshot), now, 1 if is_consistent else 0])
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def load_checkpoint(run_id: str) -> Optional[dict]:
    """Load the latest checkpoint for a run."""
    conn = get_db()
    try:
        row = conn.execute("""
            SELECT stage_id, snapshot FROM checkpoints
            WHERE run_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, [run_id]).fetchone()
        if row:
            return {"stage_id": row[0], "snapshot": json.loads(row[1])}
        return None
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: checkpoint_save.py <run_id> <stage_id> <snapshot_json> [is_consistent]", file=sys.stderr)
        sys.exit(1)

    run_id = sys.argv[1]
    stage_id = sys.argv[2]
    snapshot = json.loads(sys.argv[3])
    is_consistent = sys.argv[4].lower() != "false" if len(sys.argv) > 4 else True

    checkpoint_id = save_checkpoint(run_id, stage_id, snapshot, is_consistent)
    print(f"Checkpoint saved: id={checkpoint_id} run_id={run_id} stage_id={stage_id}")
