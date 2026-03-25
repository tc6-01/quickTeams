# quickTeams

**解决 Claude Code team 的 lead 卡住问题 — 让 agent team 可靠执行、自动恢复。**

当 lead agent 因休眠/断连而卡住时，整个 team 陷入死锁：worker 完成了任务但无法通知 lead，其他 agent 等待 lead 的下一步指令。quickTeams 通过 Sidecar 架构，在不修改 Claude Code 的前提下，为 team 提供可靠执行能力。

## 核心问题

```
┌─────────────────────────────────────────────────────────────┐
│  Claude Code Team                                           │
│                                                              │
│  Lead ──────────────────► Workers                            │
│    │                          │                             │
│    │   "执行任务..."           │   "任务完成"               │
│    │                          │                            │
│    ◄──────────────────────────┘                            │
│                                                              │
│  问题：Lead 休眠 → 事件丢失 → Team 死锁                     │
└─────────────────────────────────────────────────────────────┘
```

## 解决方案

quickTeams 采用 **Sidecar 进程模式**：

```
┌─────────────────────────────────────────────────────────────┐
│  Claude Code（Lead + Workers）                               │
│                                                              │
│  按 workflow 模板执行                                         │
│  只操作共享 SQLite（写事件、写 checkpoint）                   │
│  不感知 Sidecar 存在                                        │
└─────────────────────────────────────────────────────────────┘
                            │ 共享 SQLite
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Sidecar 进程（独立运行）                                    │
│                                                              │
│  ┌─────────┐  ┌──────────┐  ┌────────────┐              │
│  │ Outbox  │  │  Lease   │  │  Watchdog  │              │
│  │ Store   │  │ Manager  │  │ + Reconc.  │              │
│  └─────────┘  └──────────┘  └────────────┘              │
│                                                              │
│  • 事件先持久化再投递                                        │
│  • Lead lease 检测休眠                                       │
│  • 自动恢复卡死的 workflow                                   │
└─────────────────────────────────────────────────────────────┘
```

## 核心能力

| 能力 | 说明 |
|------|------|
| **Dutable Outbox** | worker 完成事件先写入 SQLite，再投递；ACK 才推进阶段 |
| **幂等消费** | 基于 `eventId` 去重，重复投递不产生重复副作用 |
| **Lead Lease** | 检测 lead 健康状态：HEALTHY → SUSPECTED_SLEEP → UNAVAILABLE |
| **Watchdog** | 扫描无进展的 run，自动触发 reconciliation |
| **Checkpoint** | 阶段边界保存快照，支持从任意一致状态恢复 |
| **Workflow 模板** | YAML 格式定义 stages、roles、success criteria、failure policy |

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/tc6-01/quickTeams.git
cd quickTeams
```

### 2. 初始化检查

```bash
./scripts/bootstrap.sh
```

### 3. 启动 Sidecar

```bash
./scripts/sidecarctl start
```

### 4. 运行 workflow

在 Claude Code 中：

```
/team-run reliable-agent-team-workflow
```

## 目录结构

```
quickTeams/
├── sidecar/                    # Sidecar 实现（Python）
│   ├── main.py                 # 入口
│   ├── db.py                  # SQLite 连接和迁移
│   ├── outbox.py              # Outbox store
│   ├── lease.py               # Lease / heartbeat
│   ├── watchdog.py            # Watchdog timer
│   ├── reconciler.py          # 恢复决策
│   └── checkpoint.py          # Checkpoint store
│
├── scripts/                    # Claude Code 可调用脚本
│   ├── sidecarctl             # Sidecar 控制（start/stop/status）
│   ├── heartbeat.py           # 更新 lease
│   ├── outbox_write.py         # 写入完成事件
│   └── checkpoint_save.py      # 保存 checkpoint
│
├── workflows/                  # Workflow 模板
│   └── reliable-agent-team-workflow.yaml
│
├── openspec/                   # OpenSpec 变更管理
│   └── changes/reliable-agent-team-workflow/
│       ├── proposal.md         # 问题定义
│       ├── design.md           # 设计决策
│       ├── ARCHITECTURE.md     # 架构设计
│       └── tasks.md            # 实现任务
│
└── docs/
    └── sidecar-arch.md         # 架构详解
```

## 工作原理

### 1. Workflow 启动

1. Lead 从 SQLite 加载 workflow 模板
2. 初始化 run state 和 lease
3. 按 stage 顺序执行

### 2. Worker 完成事件

```
Worker 完成 → 写入 outbox (PENDING)
                    │
                    ├── Sidecar 检测到 PENDING
                    │        │
                    │        └── 标记 DISPATCHED
                    │
                    └── Lead 读取 → 处理 → ACK
```

### 3. Lead 休眠检测

```
Watchdog 扫描 leases 表
    │
    ├── last_heartbeat 超时 → SUSPECTED_SLEEP
    │
    └── 超过 recovery_timeout → UNAVAILABLE
                                  │
                                  └── 触发 reconcile
```

### 4. 自动恢复

```
reconcile 检查：
    │
    ├── checkpoint 存在 → RESUME from checkpoint
    │
    ├── 有未 ACK 事件 → REPLAY outbox
    │
    └── 无法恢复 → DEAD / DLQ
```

## Workflow 模板格式

```yaml
name: reliable-agent-team-workflow
version: "1.0"

settings:
  hang_timeout: 300      # 阶段无进展超时（秒）
  heartbeat_ttl: 30      # Lease TTL（秒）

stages:
  - id: stage_1_planning
    name: Planning
    owner: lead
    instructions: |
      分析任务需求，制定执行计划。
    success_criteria:
      - plan_document_created: true
    failure_policy:
      action: retry
      max_attempts: 3
    next:
      - stage_2_dispatch

roles:
  lead:
    description: 主协调 agent
  executor:
    description: 执行 agent
```

## 前置依赖

| 依赖 | 说明 |
|------|------|
| Python 3.10+ | Sidecar 实现 |
| SQLite3 | 共享存储（内置于 Python） |
| Claude Code | team 执行环境 |

## 进一步阅读

- [架构设计](openspec/changes/reliable-agent-team-workflow/ARCHITECTURE.md) — 完整 Sidecar 技术方案
- [问题定义](openspec/changes/reliable-agent-team-workflow/proposal.md) — 为什么需要这个
- [设计决策](openspec/changes/reliable-agent-team-workflow/design.md) — 关键决策记录
- [实现任务](openspec/changes/reliable-agent-team-workflow/tasks.md) — 待开发任务清单
