"""Configuration constants for quickTeams Sidecar."""

import os

# Database
SHARED_DB_PATH = os.path.expanduser("~/.quickteams/sidecar.db")

# Heartbeat / Lease
HEARTBEAT_TTL = 30          # seconds
STALE_THRESHOLD = 60         # seconds
RECOVERY_TIMEOUT = 180      # seconds

# Watchdog
WATCHDOG_INTERVAL = 15      # seconds
HANG_TIMEOUT = 300          # seconds

# Outbox
ACK_TIMEOUT = 120           # seconds
MAX_DISPATCH_RETRIES = 5
RETRY_BACKOFF_BASE = 2      # seconds multiplier

# Workflow
DEFAULT_WORKFLOW = "reliable-agent-team-workflow"
WORKFLOW_REGISTRY_PATH = "./workflows"

# DLQ
DLQ_RETENTION_DAYS = 30
