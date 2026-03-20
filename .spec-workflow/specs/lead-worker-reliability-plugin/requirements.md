# Requirements Document

## Introduction

当前团队执行链路存在一个高频故障：`lead` 进入休眠或不可达状态后，`worker` 已完成任务但完成通知未被 `lead` 消费，最终导致 `team` 卡住（hang），后续任务不再推进。  
本需求的目标是提供一个“可靠执行增强插件”，把这类问题从人工排障改为系统级自动恢复能力。

## Alignment with Product Vision

该增强插件直接提升多角色协作系统的稳定性和吞吐量，减少人工介入，避免重复处理同类故障，符合“低阻塞、高自治、可持续运行”的产品目标。

## Requirements

### Requirement 1: Worker Completion Notification Reliability

**User Story:** As an orchestration operator, I want worker completion events to be reliably delivered, so that lead can always receive execution results even after transient sleep or disconnect.

#### Acceptance Criteria

1. WHEN a worker completes a task THEN the system SHALL persist a completion event before any delivery attempt.
2. IF lead is unavailable or sleeping THEN the system SHALL retry delivery with bounded exponential backoff.
3. WHEN lead recovers THEN the system SHALL replay all unacknowledged completion events for that lead.
4. WHEN duplicate completion events are received THEN the system SHALL process them idempotently and not create duplicated downstream work.

### Requirement 2: Lead Sleep Detection and Recovery

**User Story:** As a team owner, I want lead sleep/unavailability to be detected automatically, so that the team does not remain blocked indefinitely.

#### Acceptance Criteria

1. WHEN lead heartbeat/lease is older than configured threshold THEN the system SHALL mark lead as `suspected_sleep`.
2. WHEN lead remains unavailable beyond recovery timeout THEN the system SHALL trigger automatic recovery action (wake, restart, or handoff policy).
3. IF recovery action succeeds THEN the system SHALL resume pending workflow from last consistent checkpoint.

### Requirement 3: Team Hang Watchdog and Reconciliation

**User Story:** As an operations engineer, I want hung teams to be detected and healed, so that orchestration flow can continue without manual log digging.

#### Acceptance Criteria

1. WHEN a team stage has no progress beyond `team_hang_timeout` THEN the system SHALL create a reconciliation job.
2. WHEN reconciliation runs THEN the system SHALL compare durable event state against in-memory runtime state and repair mismatch.
3. IF automatic repair fails THEN the system SHALL move the case to dead-letter queue with actionable context.

### Requirement 4: Observable and Auditable Recovery

**User Story:** As an operator, I want visibility into delivery, retries, and recovery outcomes, so that I can quickly diagnose anomalies and improve policy settings.

#### Acceptance Criteria

1. WHEN an event enters retry path THEN the system SHALL emit structured logs including team, lead, worker, event ID, and attempt number.
2. WHEN retries exceed max attempts THEN the system SHALL emit alert-grade signal and persist dead-letter record.
3. WHEN recovery action is executed THEN the system SHALL persist audit trail with trigger reason and final status.

## Non-Functional Requirements

### Code Architecture and Modularity
- **Single Responsibility Principle**: Delivery retry, lease monitoring, reconciliation, and dead-letter handling must be isolated modules.
- **Modular Design**: Plugin must integrate through clear hooks without coupling orchestration core to specific retry policy details.
- **Dependency Management**: Runtime core depends only on plugin interface; plugin may depend on storage/message abstractions.
- **Clear Interfaces**: Define explicit contracts for event persistence, ack handling, lease health checks, and reconciliation triggers.

### Performance
- Retry/replay scheduling overhead SHALL not increase normal-path task completion latency by more than 5%.
- Watchdog scanning SHALL support at least 1,000 concurrent teams per minute without starvation.

### Security
- Recovery and replay actions SHALL include actor/source metadata for audit.
- Any manual recovery command SHALL require existing operator authorization path.

### Reliability
- No single worker completion event may be silently dropped after persistence.
- Mean time to detect stuck team SHOULD be under 30 seconds (configurable).
- Mean time to auto-recover transient lead sleep SHOULD be under 2 minutes (configurable by environment).

### Usability
- Operators SHALL be able to determine why a team is stuck from one consolidated event timeline.
- Failure reasons and suggested remediation SHALL be machine-readable and human-readable.
