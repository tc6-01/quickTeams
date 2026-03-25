"""SQLite database connection and migrations."""

import sqlite3
import os
from .config import SHARED_DB_PATH

SCHEMA_TABLES = """
CREATE TABLE IF NOT EXISTS outbox (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id        TEXT NOT NULL UNIQUE,
    run_id          TEXT NOT NULL,
    stage_id        TEXT,
    worker_id       TEXT NOT NULL,
    payload         TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'PENDING',
    dispatch_count  INTEGER NOT NULL DEFAULT 0,
    last_dispatch   INTEGER,
    acked_at        INTEGER,
    created_at      INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    id              TEXT PRIMARY KEY,
    workflow_name   TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'RUNNING',
    current_stage   TEXT,
    current_agent   TEXT,
    context         TEXT,
    created_at      INTEGER NOT NULL,
    updated_at      INTEGER NOT NULL,
    completed_at    INTEGER
);

CREATE TABLE IF NOT EXISTS checkpoints (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL,
    stage_id        TEXT NOT NULL,
    snapshot        TEXT NOT NULL,
    created_at      INTEGER NOT NULL,
    is_consistent   INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (run_id) REFERENCES runs(id)
);

CREATE TABLE IF NOT EXISTS leases (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL UNIQUE,
    holder          TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'HEALTHY',
    last_heartbeat  INTEGER NOT NULL,
    expires_at      INTEGER NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(id)
);

CREATE TABLE IF NOT EXISTS dead_letter (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id        TEXT,
    run_id          TEXT,
    reason          TEXT NOT NULL,
    payload         TEXT,
    audit           TEXT,
    created_at      INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS workflows (
    name            TEXT PRIMARY KEY,
    spec            TEXT NOT NULL,
    version         TEXT NOT NULL,
    created_at      INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT,
    event_type      TEXT NOT NULL,
    detail          TEXT,
    created_at      INTEGER NOT NULL
);
"""

SCHEMA_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_outbox_status_created ON outbox(status, created_at);
CREATE INDEX IF NOT EXISTS idx_outbox_run_id ON outbox(run_id);
CREATE INDEX IF NOT EXISTS idx_runs_status_updated ON runs(status, updated_at);
CREATE INDEX IF NOT EXISTS idx_checkpoints_run_created ON checkpoints(run_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_deadletter_run_id ON dead_letter(run_id);
CREATE INDEX IF NOT EXISTS idx_deadletter_created ON dead_letter(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_run_created ON audit_log(run_id, created_at);
"""


def get_db():
    """Get a database connection with WAL mode enabled."""
    os.makedirs(os.path.dirname(SHARED_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(SHARED_DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def run_migrations():
    """Run all database migrations."""
    conn = get_db()
    try:
        conn.executescript(SCHEMA_TABLES)
        conn.executescript(SCHEMA_INDEXES)
        conn.commit()
    finally:
        conn.close()
