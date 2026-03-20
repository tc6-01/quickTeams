## Context

当前 agent team 的执行高度依赖 `lead` 在线消费 worker 的完成结果，并依赖临时 prompt 和内存上下文来决定下一阶段动作。这种方式在 `lead` 休眠、短时断连、进程重启或消息未及时消费时容易导致 team 停滞；同时，因为缺少统一 workflow 模板，每次运行 team 都需要重复描述执行方式，阶段顺序和完成条件也不稳定。

这次变更需要同时解决两类问题：一类是可靠性问题，确保 worker 完成事件不会因为 lead 不可达而丢失，并且 team 可以自动检测和恢复；另一类是标准化问题，确保 team 能够通过统一入口加载预定义流程模板，按固定阶段推进，并在恢复后从一致状态继续运行。

## Goals / Non-Goals

**Goals:**
- 为 agent team 建立可恢复的执行模型，确保 worker 完成事件先持久化、后投递、支持 ACK、重试和重放。
- 为 `lead` 建立 lease/heartbeat 机制，识别 `healthy`、`suspected_sleep`、`unavailable` 状态。
- 为 team 建立 watchdog 和 reconciliation 机制，在长时间无进展时自动检测并恢复。
- 建立 workflow registry 与统一入口，使 team 可通过标准模板按阶段执行。
- 建立 checkpoint/run state 持久化，避免流程推进只保存在 lead 的短期上下文中。
- 为整个链路补充结构化日志、指标和审计轨迹，便于排障和后续调优。

**Non-Goals:**
- 不在本次设计中定义具体 UI 或控制台界面。
- 不引入复杂的跨集群调度协议或分布式一致性系统。
- 不实现任意自定义脚本执行引擎；workflow 仅覆盖 team orchestration 所需的标准阶段定义。
- 不要求一次性支持所有历史 team 运行实例的自动迁移，可先从新 workflow run 开始应用。

## Decisions

### 1. 使用 durable outbox 作为 worker 完成事件的真实来源
- 决策：worker 完成任务后，必须先将 completion event 写入 outbox，再尝试投递给 lead。
- 原因：可以避免“先发消息、后落状态”带来的事件丢失问题，并为 replay/reconcile 提供持久化依据。
- 备选方案：仅依赖内存消息队列或 lead 当前上下文。未采用，因为 lead 休眠或进程退出后无法恢复未消费结果。

### 2. lead 消费采用显式 ACK + 幂等消费
- 决策：lead 消费 completion event 后必须显式 ACK；系统基于 `eventId` 保证重复投递不会产生重复副作用。
- 原因：ACK 是推进阶段和清理 pending event 的唯一依据；幂等消费可以安全支撑 retry 和 replay。
- 备选方案：用“收到即视为成功”。未采用，因为无法区分“已送达未处理”和“真正处理完成”。

### 3. 引入 lead lease/heartbeat 而不是仅靠消息超时判断
- 决策：独立维护 `lead` 的 lease 状态，并定义 `HEALTHY / SUSPECTED_SLEEP / UNAVAILABLE` 状态转换。
- 原因：消息超时只能反映投递异常，不能准确区分短暂延迟和 lead 休眠；lease 更适合驱动恢复策略。
- 备选方案：仅基于 pending ACK 超时判定 team hang。未采用，因为误报率高，且无法表达 lead 当前健康状态。

### 4. 将 workflow 定义为独立模板，并由统一入口加载
- 决策：新增 workflow registry，统一存放阶段模板、负责角色、成功条件和失败策略；通过固定入口如 `/team-run <workflow>` 加载。
- 原因：把“执行步骤”从一次性 prompt 提升为可复用配置，减少每次重复描述并保证执行一致性。
- 备选方案：继续依赖手工 prompt 或 hook 注入大段说明。未采用，因为可维护性差，且不具备结构化阶段信息。

### 5. 用 stage engine + checkpoint 管理流程推进
- 决策：stage engine 负责当前阶段启动、完成、失败和切换；checkpoint store 持久化 run state、completed stages、pending events。
- 原因：流程推进必须依赖可恢复状态，而不是只存在于 lead 的上下文里。
- 备选方案：仅靠 lead 自身记忆当前阶段。未采用，因为 lead 重启或 handoff 后无法恢复一致状态。

### 6. 用 watchdog + reconciler 做自动补偿
- 决策：周期扫描长时间无进展的 team run；发现异常后对比 runtime state、checkpoint 和 outbox，决定 replay、resume、recovery 或 DLQ。
- 原因：自动发现和修复卡死比依赖人工日志排查更稳定，也更符合“低阻塞、高自治”的目标。
- 备选方案：只暴露手工恢复命令。未采用，因为仍会频繁出现人工介入和悬挂 run。

### 7. hook 仅做流程守卫和触发，不承担真实状态职责
- 决策：hook 只用于注入标准 SOP、更新轻量状态、触发 watchdog/recovery 检查和审计记录。
- 原因：hook 适合“在某个时机自动做事”，但不适合作为真实状态源或恢复引擎。
- 备选方案：把恢复逻辑也塞进 hook。未采用，因为 hook 缺少完整状态模型，且恢复需要 durable state 支撑。

## Risks / Trade-offs

- [持久化路径增加延迟] → 通过 append-only outbox、批量读取 pending events 和轻量 ACK 更新控制延迟开销。
- [恢复逻辑过于激进导致误恢复] → 使用 lease 阈值、重试上限和恢复前二次确认条件降低误判。
- [workflow 模板过于僵化] → 保留可配置阶段说明、成功条件和失败策略，但不开放无限制脚本能力。
- [状态机复杂度上升] → 将 outbox、lease、stage engine、reconciler 拆分为清晰模块，避免单体 runtime 继续膨胀。
- [旧 team 运行方式与新模板并存] → 先让统一入口只用于新 workflow run，逐步替换旧触发方式。
- [恢复失败后仍需人工介入] → 明确 DLQ 输出结构化诊断信息和推荐动作，避免静默失败。