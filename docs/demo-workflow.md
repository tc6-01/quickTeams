# Demo Workflow

这份文档带你用仓库内置的 demo change 跑一遍最小可用流程。

目标不是改代码，而是确认：
- 你已经具备使用这个仓库的前置条件
- `openspec` 工作流能在你的机器上正常工作
- 你知道 proposal / design / tasks 之间的关系

## 前提

先在仓库根目录执行：

```bash
./scripts/bootstrap.sh
./scripts/verify.sh
```

如果这两步都通过，再继续下面的 demo。

## 第 1 步：查看 demo change 状态

```bash
openspec status --change "reliable-agent-team-workflow"
```

预期结果：
- 能看到 change 名称 `reliable-agent-team-workflow`
- 能看到 `proposal`、`design`、`specs`、`tasks` 都已经完成

这一步说明：
- 你的 `openspec` CLI 是可用的
- 仓库里的示例工件结构是完整的

## 第 2 步：阅读 proposal

先看为什么要做这个 change：

- `openspec/changes/reliable-agent-team-workflow/proposal.md`

重点关注：
- Why
- What Changes
- Capabilities

你会看到这个 demo change 关注的是两件事：
- agent team 在 lead 休眠时的可靠执行
- agent team 的标准 workflow 模板化

## 第 3 步：阅读 design

再看实现思路：

- `openspec/changes/reliable-agent-team-workflow/design.md`

重点关注：
- durable outbox
- ACK + idempotency
- lead lease / heartbeat
- watchdog / reconciler
- workflow registry / checkpoint

这一步帮助你理解 proposal 如何落成可执行设计。

## 第 4 步：阅读 tasks

最后看落地任务拆分：

- `openspec/changes/reliable-agent-team-workflow/tasks.md`

重点关注：
- 任务是否按依赖顺序组织
- 每个任务是否足够小、可验证
- workflow、reliability、verification 是否都被覆盖

这一步帮助你理解一个完整 OpenSpec change 应该怎样进入实施阶段。

## 第 5 步：在 Claude Code 中体验命令入口

在 Claude Code 中进入这个仓库后，你可以试这些入口：

```text
/opsx:explore
/opsx:propose 我想增加一个新的 workflow
/opsx:apply reliable-agent-team-workflow
```

说明：
- `/opsx:explore` 适合先梳理问题
- `/opsx:propose` 适合先生成 proposal/design/tasks
- `/opsx:apply` 适合任务已经明确时开始实施

如果你不想动 demo change，可以先新建一个自己的 change 名称。

## 第 6 步：自己跑一个最小 change

例如：

```text
/opsx:propose add-demo-note
```

你要观察的是：
- 是否能生成新的 change 目录
- 是否生成 proposal / design / specs / tasks
- 是否能继续进入 `/opsx:apply`

## 成功标准

如果下面几件事都成立，说明这个仓库对你来说已经“开箱可用”：
- `./scripts/bootstrap.sh` 成功
- `./scripts/verify.sh` 成功
- `openspec status --change "reliable-agent-team-workflow"` 成功
- 你能理解 demo change 的 proposal / design / tasks 关系
- Claude Code 能识别 `/opsx:*` 入口

## 常见误区

- 不要把 `.omc/` 当成必须提交的内容，它是本地运行状态。
- 不要把 `.specstory/` 里的历史痕迹当成主线流程的一部分。
- 如果 `openspec` 不存在，先解决 CLI 安装问题，再继续跑 demo。
- 如果命令入口未识别，先确认你是在这个仓库目录里运行 Claude Code。

## 下一步

跑完这份 demo 后，建议你立刻做两件事：

1. 用自己的需求试一次 `/opsx:propose`
2. 用新生成的 change 试一次 `/opsx:apply`

这样你就从“看懂仓库”进入“真正开始复用仓库工作流”了。
