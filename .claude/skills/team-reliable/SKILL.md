---
name: team-reliable
description: Start a reliable Claude Code team with Sidecar infrastructure (outbox, lease, watchdog, checkpoint). Use when running multi-agent teams where lead failure could stall the workflow.
license: MIT
compatibility: Requires quickTeams sidecar (Python 3.10+, pyyaml)
metadata:
  author: quickTeams
  version: "1.0"
---

# Team Reliable Skill

启动一个带 Sidecar 可靠性基础设施的 Claude Code team。当 Lead Agent 因休眠/断连卡住时，Standard OMC team 会死锁——本 skill 提供 outbox 持久化、lead lease 检测、watchdog 自动恢复。

## Usage

```
/team-reliable <workflow_name> [task]
/team-reliable reliable-agent-team-workflow "build a REST API"
```

## Core Concept

```
用户: /team-reliable <workflow> <task>
          │
          ├── 初始化 sidecar + run state
          ├── 导出环境变量到 ~/.quickteams/env.sh
          │
          ├── OMC team agent spawn 时读取 env.sh
          │       │
          │       ├── Worker 完成 → 写 outbox（通过 env.sh 中的路径）
          │       ├── Lead 阶段完成 → checkpoint + heartbeat
          │       │
          │       └── Sidecar 监控 & 恢复
          │
          └── Team 结束 → 标记 run COMPLETED
```

## Steps

### 1. Parse Arguments

```
Input format: <workflow_name> [task description]
Examples:
  "reliable-agent-team-workflow build a REST API"
  "reliable-agent-team-workflow"  (interactive mode)
```

If no task provided, ask the user what they want the team to accomplish.

### 2. Ensure Sidecar is Running

```bash
~/.quickteams/sidecarctl start
```

### 3. Initialize Run State

Create a run and export env vars:

```bash
python3 - <<'PYEOF'
import sys, time, os, json
sys.path.insert(0, '/Users/roubaojiasudu/Desktop/code AI/repo/quickTeams')

from sidecar.db import run_migrations, get_db
from sidecar.lease import manager as lease_manager
from sidecar.workflow import load_workflow

run_migrations()

run_id = 'run_' + str(int(time.time()))
now = int(time.time())
workflow_name = sys.argv[1] if len(sys.argv) > 1 else 'reliable-agent-team-workflow'

# Verify workflow exists
wf = load_workflow(workflow_name)
first_stage = wf['stages'][0]['id']

# Create run
conn = get_db()
conn.execute("""
    INSERT OR IGNORE INTO runs (id, workflow_name, status, current_stage, created_at, updated_at)
    VALUES (?, ?, 'RUNNING', ?, ?, ?)
""", [run_id, workflow_name, first_stage, now, now])
conn.commit()
conn.close()

# Acquire lease
lease_manager.acquire(run_id, 'lead')

# Export env
env = {
    'QUICKTEAMS_RUN_ID': run_id,
    'QUICKTEAMS_WORKFLOW': workflow_name,
    'QUICKTEAMS_DB_PATH': os.path.expanduser('~/.quickteams/sidecar.db'),
    'QUICKTEAMS_REPO': '/Users/roubaojiasudu/Desktop/code AI/repo/quickTeams',
}

env_lines = '\n'.join(f"export {k}='{v}'" for k, v in env.items())
os.makedirs(os.path.expanduser('~/.quickteams'), exist_ok=True)
with open(os.path.expanduser('~/.quickteams/env.sh'), 'w') as f:
    f.write(env_lines + '\n')

print(f"RUN_ID={run_id}")
print(f"WORKFLOW={workflow_name}")
print(f"FIRST_STAGE={first_stage}")

# Also write a json file for scripts to read
with open(os.path.expanduser('~/.quickteams/current_run.json'), 'w') as f:
    json.dump({'run_id': run_id, 'workflow': workflow_name, 'stage': first_stage}, f)

print("Run initialized:", run_id)
PYEOF
```

### 4. Show Team Configuration

Inform the user of the run configuration and next steps.

### 5. Start Reliable Team

Tell the user to start the team with reliable scripts. Include the run context:

```
**Reliable Team Configuration:**

- **Run ID**: `<run_id from step 3>`
- **Workflow**: `<workflow_name>`
- **First Stage**: `<first_stage>`

**To start the reliable team**, use:
```bash
# In your team command, teammates should:
source ~/.quickteams/env.sh

# Worker task completion:
python3 scripts/outbox_write.py $QUICKTEAMS_RUN_ID <stage_id> <worker_id> task_completion '<payload>'

# Lead stage completion:
python3 scripts/checkpoint_save.py $QUICKTEAMS_RUN_ID <stage_id> '<snapshot>'
python3 scripts/heartbeat.py $QUICKTEAMS_RUN_ID lead

# Monitor run:
python3 -c "
import sys; sys.path.insert(0, '$(pwd)')
from sidecar.db import get_db
conn = get_db()
r = conn.execute('SELECT id,status,current_stage FROM runs WHERE id=?', ['<run_id>']).fetchone()
print('Run:', r[0], '|', r[1], '|', r[2])
conn.close()
"
```

### 6. On Completion

When team signals completion, mark the run:

```bash
python3 -c "
import sys, time
sys.path.insert(0, '/Users/roubaojiasudu/Desktop/code AI/repo/quickTeams')
from sidecar.db import get_db

run_id = open(os.path.expanduser('~/.quickteams/current_run.json')).read()
run_id = __import__('json').loads(open(os.path.expanduser('~/.quickteams/current_run.json')).read())['run_id']

conn = get_db()
conn.execute('UPDATE runs SET status=\"COMPLETED\", completed_at=? WHERE id=?', [int(time.time()), run_id])
conn.commit()
conn.close()
print('Run', run_id, 'marked COMPLETED')
"
```

## Environment Variables

These are written to `~/.quickteams/env.sh` and should be sourced by team members:

| Variable | Description |
|----------|-------------|
| `QUICKTEAMS_RUN_ID` | Current run identifier |
| `QUICKTEAMS_WORKFLOW` | Active workflow name |
| `QUICKTEAMS_DB_PATH` | SQLite database path |
| `QUICKTEAMS_REPO` | quickTeams repository path |

## Monitoring

Check run status:
```bash
~/.quickteams/sidecarctl status
```

Check pending events:
```bash
python3 -c "
import sys; sys.path.insert(0, '/Users/roubaojiasudu/Desktop/code AI/repo/quickTeams')
from sidecar.db import get_db
run = __import__('json').loads(open('/root/.quickteams/current_run.json').read())
conn = get_db()
p = conn.execute(\"SELECT COUNT(*) FROM outbox WHERE run_id=? AND status='PENDING'\", [run['run_id']]).fetchone()[0]
a = conn.execute(\"SELECT COUNT(*) FROM outbox WHERE run_id=? AND status='ACKED'\", [run['run_id']]).fetchone()[0]
print(f'Pending: {p}, Acked: {a}')
conn.close()
"
```

## Integration Points

The skill **does not** spawn agents itself — it prepares the reliability infrastructure and tells the user how to start the team with the right context. The actual team spawning happens via `/oh-my-claudecode:team` with environment variables sourced.

**Why this design?**
- OMC team spawns separate agent sessions — skill cannot directly nest inside them
- Shared SQLite (via `~/.quickteams/sidecar.db`) is accessible from all sessions on the same machine
- Environment file (`~/.quickteams/env.sh`) propagates run context to all team members
