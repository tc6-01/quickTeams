## Why

当前 agent team 执行链路在 `lead` 休眠、短时断连或未及时消费 worker 完成事件时，容易出现结果未被接收、阶段不再推进、team 长时间挂起的问题。同时，团队缺少一个可复用的标准化触发入口，导致每次都要重复描述流程，执行步骤也不一致。

现在需要把这两个问题一起标准化：一方面提供可靠执行与自动恢复能力，避免 team 因消息丢失或 lead 不可达而卡死；另一方面提供固定 workflow 模板和统一触发方式，让 agent team 可以按预定义步骤稳定运行。

## What Changes

- 新增 agent team 可靠执行能力，确保 worker 完成事件先持久化、后投递、可重试、可重放、可审计。
- 新增 lead lease 与 hang watchdog 机制，用于检测 `lead` 休眠、无心跳、无进展阶段，并触发自动恢复或补偿。
- 新增 reconciliation 与 dead-letter 处理能力，在自动恢复失败时提供可诊断、可人工接管的兜底路径。
- 新增标准化 team workflow 能力，支持通过统一入口加载预定义流程模板，按固定阶段和成功条件执行。
- 新增 checkpoint 与阶段状态管理，确保流程推进不依赖单个 lead 的内存上下文，在恢复后能够从一致状态继续执行。
- 为上述能力补充日志、指标与审计记录，便于定位卡死原因、重试过程和恢复结果。

## Capabilities

### New Capabilities
- `agent-team-reliability`: 为 agent team 提供 worker 完成事件持久化、ACK、重试、重放、lead 休眠检测、watchdog、reconcile 和 DLQ 能力。
- `agent-team-workflows`: 为 agent team 提供标准化 workflow 模板、统一触发入口、阶段推进和 checkpoint 恢复能力。

### Modified Capabilities

## Impact

- 受影响系统：agent team runtime、lead/worker 协作链路、任务派发与阶段推进逻辑。
- 新增持久化状态：run state、checkpoint、worker completion outbox、lead lease、dead-letter records。
- 新增运行机制：ACK/replay、hang watchdog、自动恢复策略、统一 workflow registry。
- 受影响代码范围预计包括：team 入口命令、runtime 调度器、任务完成回调、恢复与观测模块。
- 对外行为变化：team 执行将从临时 prompt 驱动转向模板化、可恢复、可审计的标准流程。