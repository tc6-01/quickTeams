## 1. Workflow Entry and State Model

- [ ] 1.1 定义 workflow registry 与模板结构，支持按名称加载标准化 team workflow
- [ ] 1.2 实现统一 workflow 入口命令，创建新的 team run 并初始化运行上下文
- [ ] 1.3 定义 durable run state 与 checkpoint 数据结构，覆盖当前阶段、参与 agent、完成阶段和 pending events
- [ ] 1.4 实现 stage engine 的基础状态迁移接口，支持阶段启动、完成、失败和切换

## 2. Reliable Completion Delivery

- [ ] 2.1 实现 worker completion outbox store，支持 append、mark dispatched、mark acked、fetch pending 和 move to dead letter
- [ ] 2.2 实现 completion event 的显式 ACK 机制，确保只有 ACK 后才允许阶段推进
- [ ] 2.3 实现基于 event identifier 的幂等消费保护，避免 retry/replay 产生重复副作用
- [ ] 2.4 实现 delivery coordinator，支持有界退避重试和 lead 恢复后的 pending event replay

## 3. Lead Health, Hang Detection, and Recovery

- [ ] 3.1 实现 lead lease/heartbeat manager，维护 `HEALTHY`、`SUSPECTED_SLEEP` 和 `UNAVAILABLE` 状态转换
- [ ] 3.2 实现 team watchdog，扫描长时间无进展的 team run 并触发 reconciliation
- [ ] 3.3 实现 reconciler，对比 runtime state、checkpoint 和 outbox 状态并执行 replay、resume 或 repair
- [ ] 3.4 实现 recovery policy，支持 wake、restart 或 handoff 等恢复动作及触发条件
- [ ] 3.5 实现 dead-letter handling，记录无法自动恢复的 event/run 与可操作诊断信息

## 4. Hooks and Observability

- [ ] 4.1 定义 workflow lifecycle hooks，覆盖 pre-run、post-stage、worker-done、lead-idle、tick 和 exit 等关键时机
- [ ] 4.2 实现 hook 与 runtime/reliability 的边界，确保 hook 只做守卫、注入和触发，不承担真实状态
- [ ] 4.3 为 retry、replay、lease transition、recovery 和 dead-letter 补充结构化日志与审计记录
- [ ] 4.4 增加关键指标输出，覆盖 event delivery、retry、hang detection、recovery success 和 dlq inflow

## 5. Verification

- [ ] 5.1 为 outbox、ACK、idempotency、lease transition 和 stage engine 编写单元测试
- [ ] 5.2 增加集成测试，覆盖 lead 休眠、worker 完成事件积压、恢复后 replay 和 workflow resume
- [ ] 5.3 增加端到端验证，覆盖统一 workflow 入口启动、阶段推进、hang 检测与自动恢复
- [ ] 5.4 运行 openspec 校验与最终状态检查，确保 proposal、design、specs、tasks 全部可用于 apply