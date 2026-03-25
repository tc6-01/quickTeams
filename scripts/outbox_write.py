#!/usr/bin/env python3
"""Write a completion event to the outbox."""

import sys
import json
import time
import uuid
sys.path.insert(0, "/Users/roubaojiasudu/Desktop/code AI/repo/quickTeams")

from sidecar.db import get_db

def enqueue_completion(run_id: str, stage_id: str, worker_id: str,
                       event_type: str, payload: dict) -> str:
    """Write a completion event to the outbox."""
    event_id = str(uuid.uuid4())
    now = int(time.time())
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO outbox (event_id, run_id, stage_id, worker_id, payload, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'PENDING', ?)
        """, [event_id, run_id, stage_id, worker_id, json.dumps(payload), now])
        conn.commit()
    finally:
        conn.close()
    return event_id

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: outbox_write.py <run_id> [stage_id] [worker_id] [event_type] [payload_json]", file=sys.stderr)
        sys.exit(1)

    run_id = sys.argv[1]
    stage_id = sys.argv[2] if len(sys.argv) > 2 else "unknown"
    worker_id = sys.argv[3] if len(sys.argv) > 3 else "unknown"
    event_type = sys.argv[4] if len(sys.argv) > 4 else "task_completion"
    payload = json.loads(sys.argv[5]) if len(sys.argv) > 5 else {}

    event_id = enqueue_completion(run_id, stage_id, worker_id, event_type, payload)
    print(f"Event enqueued: event_id={event_id} run_id={run_id}")
