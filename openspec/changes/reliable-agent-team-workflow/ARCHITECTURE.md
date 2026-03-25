# Sidecar 可靠性架构

## 1. 概述

### 1.1 设计目标

本架构解决的核心问题：Claude Code lead agent 因休眠/断连导致 worker 完成事件丢失、team 死锁。

采用**方案 C — Sidecar 进程模式**：
- Claude Code 只负责按 workflow 模板执行 agent，不承担可靠性职责
- Sidecar 是独立进程，负责可靠性（outbox、lease、watchdog、reconciler）
- 通过**共享 SQLite** 通信，零网络依赖
- Claude Code 本身**零修改**

### 1.2 核心原则

| 原则 | 说明 |
|------|------|
| **持久化优先** | worker 完成事件先落盘、后投递；ACK 才允许推进阶段 |
| **幂等消费** | 重复投递不产生重复副作用，基于 `eventId` 去重 |
| **状态外置** | 流程推进不依赖 lead 内存上下文，基于 checkpoint 恢复 |
| **最小侵入** | Claude Code 不感知 Sidecar 的存在，只操作共享存储 |
| **可审计** | 所有状态转换、恢复动作、DLQ 入队均有记录 |

---

## 2. 系统架构

### 2.1 组件拓扑

```
┌─────────────────────────────────────────────────────────────┐
│                     Claude Code (Lead)                       │
│  ┌─────────────┐   ┌──────────────┐   ┌─────────────────┐  │
│  │  Workflow   │   │  Stage       │   │  Completion     │  │
│  │  Loader     │   │  Engine      │   │  Dispatcher     │  │
│  └─────────────┘   └──────────────┘   └─────────────────┘  │
│         │                  │                   │            │
│         └──────────────────┼───────────────────┘            │
│                            │ write/read                        │
│                   ┌────────▼─────────┐                        │
│                   │   Shared SQLite  │                         │
│                   │  (sidecar.db)    │                         │
│                   └────────┬─────────┘                        │
│                            │                                  │
│         ┌──────────────────┼──────────────────┐               │
│         │                  │                  │                │
│  ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐         │
│  │   Outbox   │   │   Lease     │   │  Checkpoint │         │
│  │   Store    │   │   Manager   │   │  Store      │         │
│  └────────────┘   └─────────────┘   └─────────────┘         │
│                                                              │
│  ┌────────────┐   ┌─────────────┐   ┌──────────────┐        │
│  │  Watchdog  │   │ Reconciler  │   │ Dead Letter  │        │
│  │  (Timer)   │   │ (On-demand) │   │    Queue     │        │
│  └────────────┘   └─────────────┘   └──────────────┘        │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ fork / exec
                    ┌─────────┴──────────┐
                    │   Sidecar Process  │
                    │  (sidecar.py)      │
                    └────────────────────┘
```

**关键约束**：Claude Code 与 Sidecar 运行在同一台机器，共享同一个 SQLite 文件。两者通过文件锁协调并发，不依赖网络 socket。

---

## 3. Sidecar 进程与 Claude Code 的交互协议

### 3.1 交互原则

Claude Code 是"不知情的合作者"：
- Claude Code **不知道** Sidecar 存在
- Claude Code **只操作**共享 SQLite（读 workflow 模板、写完成事件）
- Sidecar **监视** SQLite 变化，驱动可靠性逻辑

### 3.2 Claude → Sidecar 的通知机制

**方式：文件修改时间戳轮询**

Claude Code 写 SQLite（如插入 completion event）→ SQLite 的 mtime 变化 → Sidecar 的 inotify/dnotify 监听器收到通知。

实现层：
```python
# Sidecar 端（Unix/macOS）
import watchdog.events
class SQLiteChangeHandler(watchdog.events.FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path == SHARED_DB_PATH:
            self.sidecar.on_db_modified()

# Claude Code 端无需任何额外代码，只需正常写 SQLite
```

**为什么不用 subprocess 回调？**
- subprocess 要求 Claude Code 主动调用 sidecar script，违反了"零侵入"原则
- 文件轮询让 Claude Code 完全不需要感知 sidecar 的存在

### 3.3 Sidecar → Claude Code 的影响机制

**方式：Workflow 模板 + Checkpoint 文件**

Claude Code 在每个 workflow 阶段开始前，从 SQLite 读取当前 `current_stage` 和 `pending_events`。如果 Sidecar 已经修复了状态，Claude Code 会自动从修复后的位置继续。

```
Claude Code 启动
    ↓
读取 runs 表，找 current_stage
    ↓
发现 stage = "stage_2_dispatch"（Sidecar 已修复）
    ↓
从 Checkpoint 恢复上下文，继续执行
```

Sidecar 通过写 `runs.current_stage`、`checkpoints` 表来"指导"Claude Code 的执行路径，无需修改 Claude Code 自身。

### 3.4 接口定义

#### 3.4.1 Claude Code 侧（只读/写 SQLite）

| 操作 | 目标表 | 说明 |
|------|--------|------|
| 读取 workflow 模板 | `workflows` | 启动时加载 |
| 写入 completion event | `outbox` | worker 任务完成时 |
| 读取 pending events | `outbox` | 轮询待处理事件 |
| 写入 checkpoint | `checkpoints` | 阶段边界保存状态 |
| 更新 run 状态 | `runs` | 推进当前阶段 |

#### 3.4.2 Sidecar 侧（监视 + 修复）

| 操作 | 目标表 | 说明 |
|------|--------|------|
| 轮询 outbox | `outbox` | 检测未投递事件 |
| 更新 event 状态 | `outbox` | 标记 DISPATCHED / ACKED |
| 写入 lease heartbeat | `leases` | Lead heartbeat 更新 |
| 扫描 stale runs | `runs` | Watchdog 触发 |
| 写恢复动作 | `checkpoints` | Replay / Resume 写入 |
| 移动到 DLQ | `dead_letter` | 不可恢复事件归档 |

---

## 4. Outbox 存储格式

### 4.1 SQLite 表结构

```sql
-- 共享数据库路径：~/.quickteams/sidecar.db

CREATE TABLE IF NOT EXISTS outbox (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id        TEXT NOT NULL UNIQUE,        -- UUID，幂等键
    run_id          TEXT NOT NULL,               -- 关联的 run
    stage_id        TEXT,                         -- 事件来自的阶段
    worker_id       TEXT NOT NULL,                -- worker 标识
    payload         TEXT NOT NULL,                -- JSON 事件内容
    status          TEXT NOT NULL DEFAULT 'PENDING',
                    -- PENDING → DISPATCHED → ACKED
                    -- PENDING → RETRYING → ACKED
                    -- PENDING → DEAD_LETTER
    dispatch_count  INTEGER NOT NULL DEFAULT 0,
    last_dispatch   INTEGER,                      -- Unix ts，最后投递时间
    acked_at        INTEGER,                      -- Unix ts，ACK 时间
    created_at      INTEGER NOT NULL,              -- Unix ts
    PRIMARY KEY (id),
    INDEX idx_status_created (status, created_at),
    INDEX idx_run_id (run_id)
);

CREATE TABLE IF NOT EXISTS runs (
    id              TEXT PRIMARY KEY,
    workflow_name   TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'RUNNING',
                    -- RUNNING / SUSPENDED / COMPLETED / FAILED / DEAD
    current_stage   TEXT,                          -- 当前阶段 ID
    current_agent   TEXT,                          -- 当前负责的 agent
    context         TEXT,                          -- JSON，运行上下文
    created_at      INTEGER NOT NULL,
    updated_at      INTEGER NOT NULL,
    completed_at    INTEGER,
    INDEX idx_status_updated (status, updated_at)
);

CREATE TABLE IF NOT EXISTS checkpoints (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL,
    stage_id        TEXT NOT NULL,
    snapshot        TEXT NOT NULL,                 -- JSON，运行快照
    created_at      INTEGER NOT NULL,
    is_consistent   INTEGER NOT NULL DEFAULT 1,     -- 1=一致，0=恢复点
    FOREIGN KEY (run_id) REFERENCES runs(id),
    INDEX idx_run_created (run_id, created_at DESC)
);

CREATE TABLE IF NOT EXISTS leases (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL UNIQUE,
    holder          TEXT NOT NULL,                  -- 当前 lease 持有者
    status          TEXT NOT NULL DEFAULT 'HEALTHY',
                    -- HEALTHY / SUSPECTED_SLEEP / UNAVAILABLE
    last_heartbeat  INTEGER NOT NULL,                -- Unix ts
    expires_at      INTEGER NOT NULL,                -- Unix ts，lease 过期时间
    FOREIGN KEY (run_id) REFERENCES runs(id)
);

CREATE TABLE IF NOT EXISTS dead_letter (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id        TEXT,                           -- 关联 event（可为 NULL）
    run_id          TEXT,
    reason          TEXT NOT NULL,                  -- 失败原因
    payload         TEXT,                           -- 原始 payload
    audit           TEXT,                           -- JSON，诊断上下文
    created_at      INTEGER NOT NULL,
    INDEX idx_run_id (run_id),
    INDEX idx_created (created_at)
);

CREATE TABLE IF NOT EXISTS workflows (
    name            TEXT PRIMARY KEY,
    spec            TEXT NOT NULL,                  -- YAML/JSON 模板内容
    version         TEXT NOT NULL,
    created_at      INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT,
    event_type      TEXT NOT NULL,                   -- LEASE_TRANSITION / STAGE_COMPLETE / RECOVERY 等
    detail          TEXT,                            -- JSON
    created_at      INTEGER NOT NULL,
    INDEX idx_run_created (run_id, created_at)
);
```

### 4.2 Outbox 状态机

```
PENDING
  │
  ├─── [dispatch] ────→ DISPATCHED
  │                       │
  │                       └─── [ACK 超时] ────→ RETRYING
  │                                              │
  │                       ◄── [重试成功] ─────────┘
  │                       │
  │                       └─── [重试耗尽] ────→ DEAD_LETTER
  │
  └─── [永久失败] ────→ DEAD_LETTER
```

### 4.3 Event Payload Schema

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "run_id": "run_20260325_001",
  "stage_id": "stage_2_dispatch",
  "worker_id": "worker_architect",
  "event_type": "task_completion",
  "payload": {
    "task_id": "design_doc",
    "result": "completed",
    "output": { ... }
  },
  "created_at": 1743004800
}
```

---

## 5. Lead Lease / Heartbeat 机制

### 5.1 设计选择：数据库字段 vs 文件

**采用：数据库字段**（`leases` 表）

| 对比项 | 文件方案 | 数据库方案 |
|--------|----------|------------|
| 原子更新 | 需文件锁 | SQLite 事务原子 |
| 跨进程可见 | 需额外同步 | 自然共享 |
| 过期检测查询 | 需 stat + 解析 | `WHERE expires_at < now` |
| 状态聚合 | 需读多个文件 | SQL 聚合 |

### 5.2 Lease 状态机

```
HEALTHY
  │
  ├─── [heartbeat 超时 `stale_threshold`] ────→ SUSPECTED_SLEEP
  │                                              │
  │                                              ├─── [恢复超时 `recovery_timeout` 内 heartbeat 恢复] ───→ HEALTHY
  │                                              │
  │                                              ├─── [超时耗尽] ────→ UNAVAILABLE
  │                                              │
  │                                              └─── [Watchdog 触发 reconcile] ───→ SUSPECTED_SLEEP
  │
  └─── [主动放弃 / explicit handoff] ────→ UNAVAILABLE
```

### 5.3 Heartbeat 更新机制

**采用：Lead 主动写入（推荐） + Sidecar 兜底轮询**

Lead 在每个 workflow 阶段完成时主动更新心跳：
```python
# Claude Code 端（可封装为轻量 script 调用）
def update_heartbeat(run_id: str, holder: str):
    now = int(time.time())
    db.execute("""
        INSERT INTO leases (run_id, holder, last_heartbeat, expires_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(run_id) DO UPDATE SET
            last_heartbeat = excluded.last_heartbeat,
            expires_at = excluded.last_heartbeat + HEARTBEAT_TTL
    """, [run_id, holder, now, now + HEARTBEAT_TTL])
```

Sidecar 监视线程定期扫描 `leases` 表，对于 `HEALTHY` 但 `expires_at < now` 的记录，升级为 `SUSPECTED_SLEEP`。

### 5.4 配置参数

```python
HEARTBEAT_TTL = 30          # 秒，heartbeat 有效期
STALE_THRESHOLD = 60        # 秒，无 heartbeat 视为可疑
RECOVERY_TIMEOUT = 180      # 秒，SUSPECTED_SLEEP 后尝试恢复的窗口
WATCHDOG_INTERVAL = 15      # 秒，Sidecar 扫描间隔
MAX_DISPATCH_RETRIES = 5    # 次，单事件最大重试次数
```

---

## 6. Watchdog + Reconciler 触发条件

### 6.1 Hang 检测标准

**触发 Watchdog 检查的条件（满足任一）：**

| 条件 | 说明 |
|------|------|
| `runs.updated_at` 早于 `now - hang_timeout` | 阶段无进展超时 |
| `leases.status = SUSPECTED_SLEEP` 超过 `recovery_timeout` | Lead 健康状态异常 |
| `outbox` 中存在 `DISPATCHED` 状态超过 `ack_timeout` 未 ACK | 事件未确认 |

**默认阈值：**
```python
HANG_TIMEOUT = 300          # 5 分钟无进展视为 hang
ACK_TIMEOUT = 120           # 2 分钟未 ACK 视为投递失败
```

### 6.2 Recovery 决策树

```
Watchdog 检测到异常 run
    │
    ├─── Checkpoint 存在且 is_consistent=1？
    │        │
    │        ├─── YES: 比较 checkpoint.stage vs runs.current_stage
    │        │         │
    │        │         ├─── 一致：可能是 Lead 崩溃未通知 → RESUME
    │        │         │
    │        │         ├─── 不一致：阶段推进丢失 → REPLAY from checkpoint
    │        │
    │        └─── NO: 无一致 checkpoint
    │                  │
    │                  └─── 检查 outbox 是否有未 ACK 的 PENDING 事件
    │                            │
    │                            ├─── 有：LEAD 无状态，尝试从 outbox REPLAY
    │                            │
    │                            └─── 无：无法恢复 → DEAD / 告警
```

**恢复动作类型：**

| 动作 | 触发条件 | 说明 |
|------|----------|------|
| `RESUME` | checkpoint 一致，Lead 未通知完成 | 从 checkpoint 恢复，继续当前阶段 |
| `REPLAY` | 有未 ACK 的 PENDING 事件 | 重放 outbox 中未确认事件 |
| `REPAIR` | 状态不一致，可推断正确状态 | 修正 runs.current_stage |
| `WAKED` | Lead 从 SUSPECTED_SLEEP 恢复 | 重连后补发 pending events |
| `HANDOFF` | Lead UNAVAILABLE，workflow 仍需推进 | 转移 lease 到新 holder |
| `DEAD` | 超过最大恢复次数 | 移入 DLQ，标记 run 为 DEAD |

### 6.3 Watchdog 伪代码

```python
class Watchdog:
    def tick(self):
        now = int(time.time())

        # 1. 检测 hang runs
        stale_runs = db.query("""
            SELECT * FROM runs
            WHERE status = 'RUNNING'
              AND updated_at < ?
        """, [now - HANG_TIMEOUT])

        for run in stale_runs:
            self.reconciler.reconcile(run)

        # 2. 检测 stale leases
        stale_leases = db.query("""
            SELECT * FROM leases
            WHERE status = 'HEALTHY'
              AND expires_at < ?
        """, [now])

        for lease in stale_leases:
            lease.transition_to('SUSPECTED_SLEEP')
            self.audit_log('LEASE_TRANSITION', {
                'run_id': lease.run_id,
                'from': 'HEALTHY',
                'to': 'SUSPECTED_SLEEP',
                'reason': 'stale_heartbeat'
            })

        # 3. 检测失联后恢复的 lead
        recovered = db.query("""
            SELECT * FROM leases
            WHERE status = 'SUSPECTED_SLEEP'
              AND last_heartbeat > ?
        """, [now - STALE_THRESHOLD])

        for lease in recovered:
            lease.transition_to('HEALTHY')
            self.reconciler.replay_pending_events(lease.run_id)
```

---

## 7. Workflow 模板格式

### 7.1 格式选择：YAML

选择 YAML 而非 JSON 的理由：
- 可读性强，便于手工编辑 workflow 模板
- 支持多行字符串和注释，适合阶段说明
- 被所有主流语言良好支持（PyYAML、js-yaml）

### 7.2 Template Schema

```yaml
# 完整 workflow 模板示例
name: reliable-agent-team-workflow
version: "1.0"
description: 标准 agent team 可靠执行工作流

settings:
  hang_timeout: 300        # 阶段无进展超时（秒）
  ack_timeout: 120         # 事件 ACK 超时（秒）
  heartbeat_ttl: 30        # Lease TTL（秒）
  max_retries: 5           # 最大重试次数

stages:
  - id: stage_1_planning
    name: Planning
    owner: lead
    instructions: |
      分析任务需求，制定执行计划。
      识别关键里程碑和依赖关系。
    success_criteria:
      - plan_document_created: true
      - milestones_identified: true
    failure_policy:
      action: retry
      max_attempts: 3
      backoff: exponential
    next:
      - stage_2_dispatch

  - id: stage_2_dispatch
    name: Task Dispatch
    owner: lead
    instructions: |
      将任务分配给 worker agents。
      初始化每个 worker 的任务上下文。
    success_criteria:
      - workers_notified: true
      - tasks_queued: true
    failure_policy:
      action: pause_and_wait
      timeout: 600
    next:
      - stage_3_execution

  - id: stage_3_execution
    name: Parallel Execution
    owner: workers
    instructions: |
      Workers 并行执行分配的任务。
      每完成一个任务，写入 outbox。
    success_criteria:
      - all_tasks_completed: true
    failure_policy:
      action: partial_retry
      affected_only: true
    next:
      - stage_4_aggregation

  - id: stage_4_aggregation
    name: Result Aggregation
    owner: lead
    instructions: |
      收集并验证所有 worker 的完成事件。
      汇总结果，生成最终输出。
    success_criteria:
      - all_events_acked: true
      - output_generated: true
    failure_policy:
      action: deadlock_detection
    next: []  # 终止阶段

roles:
  lead:
    description: 主协调 agent，负责阶段推进和决策
    max_consecutive_failures: 3
  architect:
    description: 架构设计 agent
  executor:
    description: 执行 agent，负责具体任务完成
  verifier:
    description: 验证 agent，负责结果验收

failure_handling:
  global:
    max_total_retries: 10
    deadlock_detection: true
    dlq_on_exhaustion: true
```

### 7.3 模板存储

```sql
INSERT INTO workflows (name, spec, version, created_at) VALUES (
  'reliable-agent-team-workflow',
  '<yaml content>',
  '1.0',
  1743004800
);
```

---

## 8. 目录布局与核心模块

### 8.1 目录结构

```
quickTeams/
├── sidecar/                        # Sidecar 实现（独立 Python 包）
│   ├── __init__.py
│   ├── main.py                     # 入口：sidecar run
│   ├── db.py                       # SQLite 连接和迁移
│   ├── outbox.py                   # Outbox store 实现
│   ├── lease.py                    # Lease / heartbeat manager
│   ├── watchdog.py                 # Watchdog timer + scan
│   ├── reconciler.py               # 恢复决策引擎
│   ├── checkpoint.py               # Checkpoint store
│   ├── deadletter.py               # DLQ 管理
│   ├── workflow.py                 # Workflow 模板加载器
│   ├── audit.py                    # 审计日志
│   └── config.py                   # 配置常量
│
├── scripts/                        # Claude Code 可调用的脚本
│   ├── sidecarctl                  # Sidecar 控制脚本（start/stop/status）
│   ├── workflowctl                 # Workflow 管理脚本（load/run/list）
│   ├── heartbeat.py                # Lead heartbeat 更新（Claude Code 调用）
│   ├── outbox_write.py             # Worker 完成事件写入（Claude Code 调用）
│   └── checkpoint_save.py          # Checkpoint 保存（Claude Code 调用）
│
├── workflows/                      # Workflow 模板注册表
│   ├── reliable-agent-team-workflow.yaml
│   └── ...更多模板
│
├── tests/                           # 测试套件
│   ├── unit/
│   │   ├── test_outbox.py
│   │   ├── test_lease.py
│   │   ├── test_watchdog.py
│   │   └── test_reconciler.py
│   └── integration/
│       ├── test_lead_sleep_recovery.py
│       └── test_outbox_replay.py
│
└── docs/
    └── sidecar-arch.md             # 本文档
```

### 8.2 核心模块职责

| 模块 | 职责 | 公共 API |
|------|------|----------|
| `db.py` | SQLite 连接、 WAL 模式、迁移 | `get_db()`, `run_migrations()` |
| `outbox.py` | append, dispatch, ack, retry, dlq | `enqueue()`, `fetch_pending()`, `mark_acked()`, `mark_dead_letter()` |
| `lease.py` | heartbeat 更新、状态转换 | `acquire()`, `renew()`, `get_status()`, `transition_to()` |
| `watchdog.py` | 定时扫描、异常检测 | `Watchdog.tick()`, `start()`, `stop()` |
| `reconciler.py` | 恢复决策、Replay/Resume | `reconcile()`, `decide_recovery_action()`, `replay_pending()` |
| `checkpoint.py` | 快照保存/恢复 | `save()`, `load_latest()`, `load_at()` |
| `deadletter.py` | DLQ 操作和查询 | `enqueue()`, `list()`, `get_diagnostics()` |
| `workflow.py` | YAML 加载、模板验证 | `load()`, `list()`, `validate()` |
| `audit.py` | 审计日志写入 | `log()`, `query_by_run()` |

### 8.3 入口脚本

| 脚本 | 调用方 | 用途 |
|------|--------|------|
| `sidecar run` | 用户手动或 supervisor | 启动 Sidecar 进程 |
| `sidecarctl start` | 启动脚本 | 后台启动 sidecar |
| `heartbeat.py <run_id>` | Claude Code (lead) | 每个阶段完成后调用，更新 lease |
| `outbox_write.py <event_json>` | Claude Code (worker) | 任务完成时调用，写入 outbox |
| `checkpoint_save.py <run_id> <stage_id> <snapshot_json>` | Claude Code (lead) | 阶段边界保存 checkpoint |

---

## 9. 关键流程序列图

### 9.1 Workflow 启动流程

```
Operator                   Claude Code (Lead)              Sidecar
   │                             │                            │
   │── /team-run workflow_001 ──►│                            │
   │                             │                            │
   │                             │── SELECT workflows ───────►│
   │                             │◄─ YAML template ──────────│
   │                             │                            │
   │                             │── INSERT runs ───────────►│
   │                             │── INSERT leases ──────────►│
   │                             │                            │
   │                             │── SELECT current_stage ───►│
   │                             │◄─ stage_1_planning ───────│
   │                             │                            │
   │                             │ [执行 stage_1_planning]    │
   │                             │                            │
   │                             │── python heartbeat.py ───►│ (lease 更新)
   │                             │                            │
   │                             │ [阶段完成]                  │
   │                             │                            │
   │                             │── python checkpoint_save ─►│
   │                             │◄─ OK ──────────────────────│
   │                             │                            │
   │                             │── python outbox_write ────►│ (completion event)
   │                             │◄─ OK ──────────────────────│
   │                             │                            │
   │                             │                            │◄─ [检测到 PENDING]
   │                             │                            │─── WATCHDOG tick()
   │                             │                            │
   │                             │◄─ SELECT pending ─────────│
   │                             │─── [处理 completion event]  │
   │                             │                            │
   │                             │── UPDATE outbox ACK ─────►│
```

### 9.2 Lead 休眠检测与恢复流程

```
Time 0                      Sidecar                        Claude Code (Lead)
   │                           │                                  │
   │                           │─── WATCHDOG tick() ─────────────►│
   │                           │◄─ lease.last_heartbeat = T0 ────│
   │                           │                                   │
   │                           │       [Lead 休眠 / 断连]          │
   │                           │                                   │
 T0+60s                       │─── WATCHDOG tick()                 │
   │                           │─── SELECT leases                  │
   │                           │    WHERE expires_at < now          │
   │                           │◄─ lease.expires_at = T0+30 < T0+60│
   │                           │                                    │
   │                           │── UPDATE leases                   │
   │                           │    SET status = SUSPECTED_SLEEP  │
   │                           │◄─ OK ─────────────────────────────│
   │                           │                                    │
 T0+180s                      │─── WATCHDOG tick()                 │
   │                           │─── lease.status = SUSPECTED_SLEEP │
   │                           │    expires_at < now                │
   │                           │                                    │
   │                           │─── reconcile(run_id)               │
   │                           │    ├── CHECKPOINT exists? YES     │
   │                           │    ├── runs.current_stage vs      │
   │                           │    │   checkpoint.stage_id        │
   │                           │    └── Decision: RESUME           │
   │                           │                                    │
   │                           │─── UPDATE runs                   │
   │                           │    SET current_stage = <修复后>   │
   │                           │◄─ OK ─────────────────────────────│
   │                           │                                    │
   │                           │ [如果 Lead 恢复，重连后]           │
   │                           │                                    │
   │                           │◄─ SELECT runs WHERE status=...   │
   │                           │─── [从修复后的状态继续]            │
```

### 9.3 Outbox 重放流程

```
Scenario: Lead 崩溃后重新上线，发现有未 ACK 的 PENDING 事件

Sidecar                        Claude Code (Lead)              Outbox
   │                               │                              │
   │─── replay_pending_events() ──►│                              │
   │                               │                              │
   │                               │── SELECT * FROM outbox ────►│
   │                               │    WHERE status = 'PENDING'   │
   │                               │◄─ [e1, e2, e3] ─────────────│
   │                               │                              │
   │                               │ [逐个处理 e1, e2, e3]         │
   │                               │                              │
   │                               │── UPDATE outbox ───────────►│
   │                               │    SET status = 'ACKED'      │
   │                               │◄─ OK ───────────────────────│
   │                               │                              │
   │                               │── UPDATE runs ─────────────►│
   │                               │    SET current_stage = ...   │
   │                               │◄─ OK ───────────────────────│
```

---

## 10. 实现顺序（分阶段）

### Phase 1: 基础设施（1-2天）

**目标**：建立 SQLite 结构、workflow 模板加载、最小化 Claude Code 接口脚本

1. 实现 `db.py`：创建所有表、WAL 模式、迁移框架
2. 实现 `workflow.py`：YAML 模板加载器，支持 `load()` 和 `list()`
3. 创建 `workflows/reliable-agent-team-workflow.yaml` 示例模板
4. 实现 `scripts/heartbeat.py`、`scripts/outbox_write.py`、`scripts/checkpoint_save.py`
5. 验证：Claude Code 能正常读写 SQLite，workflow 模板能被解析

### Phase 2: Outbox + ACK（2-3天）

**目标**：worker 完成事件可靠持久化和幂等消费

1. 实现 `outbox.py`：append、fetch_pending、mark_dispatched、mark_acked、mark_dead_letter
2. 实现幂等保护：基于 `event_id` 的唯一约束 + 去重查询
3. 实现 `scripts/outbox_write.py` 并验证事件写入
4. 验证：并发写入不丢失、重复投递不产生双副作用

### Phase 3: Lease + Watchdog（2天）

**目标**：Lead 健康状态跟踪和 hang 检测

1. 实现 `lease.py`：acquire、renew、transition_to、expire 检测
2. 实现 `watchdog.py`：定时扫描 stale runs 和 stale leases
3. 实现 `audit.py`：审计日志
4. 验证：Lead 断连后能在 `STALE_THRESHOLD` 秒内被标记为 SUSPECTED_SLEEP

### Phase 4: Reconciler + Recovery（2-3天）

**目标**：自动恢复 hang 的 workflow run

1. 实现 `checkpoint.py`：save、load_latest、load_at
2. 实现 `reconciler.py`：decide_recovery_action、replay_pending、resume_from_checkpoint
3. 实现 `deadletter.py`：DLQ 入队和诊断信息
4. 验证：
   - Lead 休眠后能自动 RESUME
   - 有未 ACK 事件时能 REPLAY
   - 超过最大重试次数移入 DLQ

### Phase 5: 集成 + 测试（2天）

**目标**：端到端验证和稳定性

1. 实现 `scripts/sidecarctl`：Sidecar 进程管理
2. 编写集成测试：lead sleep / worker backlog / replay / resume
3. 运行 openspec 校验
4. 完善文档

---

## 11. 安全性与边界条件

### 11.1 并发安全

- SQLite WAL 模式允许多进程并发读写
- Lease 获取使用 `INSERT ... ON CONFLICT` 原子更新
- Watchdog 和 Claude Code 可能同时修改 `runs` 表：通过 `UPDATE ... WHERE updated_at = ?` 的乐观锁防止 stomping

### 11.2 文件权限

```bash
# sidecar.db 应该限制在 quickTeams 用户组内
chmod 0600 ~/.quickteams/sidecar.db
```

### 11.3 边界条件处理

| 场景 | 处理方式 |
|------|----------|
| Claude Code 写入时 SQLite 被 Sidecar 读 | WAL 模式保证读写不阻塞 |
| Sidecar 崩溃重启 | Watchdog 使用独立 Timer 进程或外部 supervisor 管理 |
| 数据库文件损坏 | 定期 `PRAGMA integrity_check`，DLQ 保留原始 event_id 可重放 |
| Workflow 模板格式错误 | `workflow.py` 启动时验证 schema，错误模板拒绝加载 |
| 循环依赖（stage A → B → A） | YAML 解析时检测环，不允许注册 |

---

## 12. 配置清单

所有配置集中在 `sidecar/config.py`（或环境变量）：

```python
# 数据库
SHARED_DB_PATH = os.path.expanduser("~/.quickteams/sidecar.db")

# Heartbeat / Lease
HEARTBEAT_TTL = 30           # 秒
STALE_THRESHOLD = 60         # 秒
RECOVERY_TIMEOUT = 180       # 秒

# Watchdog
WATCHDOG_INTERVAL = 15       # 秒
HANG_TIMEOUT = 300           # 秒

# Outbox
ACK_TIMEOUT = 120            # 秒
MAX_DISPATCH_RETRIES = 5
RETRY_BACKOFF_BASE = 2       # 秒，乘数

# Workflow
DEFAULT_WORKFLOW = "reliable-agent-team-workflow"
WORKFLOW_REGISTRY_PATH = "./workflows"

# DLQ
DLQ_RETENTION_DAYS = 30
```

---

## 13. 总结

本架构通过以下设计实现"零侵入 Claude Code"前提下的可靠 team 执行：

1. **共享 SQLite** 作为唯一的事实来源，Claude Code 和 Sidecar 无需相互感知
2. **Outbox + 显式 ACK** 保证 worker 完成事件不丢失
3. **Lease + Watchdog** 实现 lead 休眠的自动检测
4. **Checkpoint + Reconciler** 实现从任意一致状态的自动恢复
5. **YAML Workflow 模板** 将执行流程从 prompt 提升为可版本化的配置

下一步建议从 Phase 1 基础设施开始实现，逐步叠加可靠性能力。
