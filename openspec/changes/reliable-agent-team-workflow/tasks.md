## 1. Workflow Entry and State Model

- [ ] 1.1 实现 `db.py`：创建所有 SQLite 表、WAL 模式、迁移框架
- [ ] 1.2 实现 `workflow.py`：YAML 模板加载器，支持 `load()` 和 `list()`
- [ ] 1.3 创建 `workflows/reliable-agent-team-workflow.yaml` 示例模板
- [ ] 1.4 实现 `scripts/heartbeat.py`、`scripts/outbox_write.py`、`scripts/checkpoint_save.py`
- [ ] 1.5 验证：Claude Code 能正常读写 SQLite，workflow 模板能被解析

## 2. Reliable Completion Delivery

- [ ] 2.1 实现 `outbox.py`：append、fetch_pending、mark_dispatched、mark_acked、mark_dead_letter
- [ ] 2.2 实现幂等保护：基于 `event_id` 的唯一约束 + 去重查询
- [ ] 2.3 实现 delivery coordinator：支持有界退避重试
- [ ] 2.4 验证：并发写入不丢失、重复投递不产生双副作用

## 3. Lead Health, Hang Detection, and Recovery

- [ ] 3.1 实现 `lease.py`：acquire、renew、transition_to、expire 检测
- [ ] 3.2 实现 `watchdog.py`：定时扫描 stale runs 和 stale leases
- [ ] 3.3 验证：Lead 断连后能在 `STALE_THRESHOLD` 秒内被标记为 SUSPECTED_SLEEP
- [ ] 3.4 实现 `audit.py`：审计日志

## 4. Reconciliation and Recovery

- [ ] 4.1 实现 `checkpoint.py`：save、load_latest、load_at
- [ ] 4.2 实现 `reconciler.py`：decide_recovery_action、replay_pending、resume_from_checkpoint
- [ ] 4.3 实现 `deadletter.py`：DLQ 入队和诊断信息
- [ ] 4.4 实现 recovery policy：RESUME / REPLAY / REPAIR / WAKED / HANDOFF / DEAD 决策
- [ ] 4.5 验证：
  - [ ] Lead 休眠后能自动 RESUME
  - [ ] 有未 ACK 事件时能 REPLAY
  - [ ] 超过最大重试次数移入 DLQ

## 5. Sidecar Process and Integration

- [ ] 5.1 实现 `sidecar/main.py`：Sidecar 入口，支持 `sidecar run`
- [ ] 5.2 实现 `scripts/sidecarctl`：Sidecar 进程管理（start/stop/status）
- [ ] 5.3 实现文件 mtime 轮询通知机制（SQLite 变化检测）
- [ ] 5.4 验证：Sidecar 能正确检测 SQLite 变化并触发相应逻辑

## 6. Verification

- [ ] 6.1 为 outbox、ACK、idempotency、lease transition 编写单元测试
- [ ] 6.2 增加集成测试：lead 休眠、worker 完成事件积压、恢复后 replay 和 workflow resume
- [ ] 6.3 增加端到端验证：统一 workflow 入口启动、阶段推进、hang 检测与自动恢复
- [ ] 6.4 运行 openspec 校验与最终状态检查
