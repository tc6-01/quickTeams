#!/usr/bin/env python3
"""Update lead heartbeat for a run."""

import sys
import time
import json
sys.path.insert(0, "/Users/roubaojiasudu/Desktop/code AI/repo/quickTeams")

from sidecar.config import HEARTBEAT_TTL
from sidecar.db import get_db

def update_heartbeat(run_id: str, holder: str) -> None:
    """Update heartbeat for a lead."""
    now = int(time.time())
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO leases (run_id, holder, last_heartbeat, expires_at, status)
            VALUES (?, ?, ?, ?, 'HEALTHY')
            ON CONFLICT(run_id) DO UPDATE SET
                last_heartbeat = excluded.last_heartbeat,
                expires_at = excluded.last_heartbeat + ?,
                holder = excluded.holder,
                status = 'HEALTHY'
        """, [run_id, holder, now, now + HEARTBEAT_TTL, HEARTBEAT_TTL])
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: heartbeat.py <run_id> <holder>", file=sys.stderr)
        sys.exit(1)
    update_heartbeat(sys.argv[1], sys.argv[2])
    print(f"Heartbeat updated for run={sys.argv[1]} holder={sys.argv[2]}")
