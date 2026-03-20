# quickTeams

quickTeams 是一个面向 Claude Code + OpenSpec 的共享工作流仓库。

它把常用的变更流程入口放进仓库本身，方便团队成员在同一个项目目录里复用：
- `/opsx:explore`：先探索需求和方向
- `/opsx:propose`：一键生成 proposal / design / specs / tasks
- `/opsx:apply`：按 tasks 实施变更
- `/opsx:archive`：归档已经完成的 change

这个仓库不是传统应用源码仓库，更像一个“可共享的 AI 工作流骨架”。它的重点是：
- 让团队成员用同一套命令推进 OpenSpec 变更
- 让 proposal -> design -> tasks -> apply 这条链路可复用
- 把 demo change 和模板一起放进版本库，方便新人快速上手

## 适合谁

- 正在使用 Claude Code 的个人或团队
- 想把 OpenSpec 流程固化到仓库里的人
- 想要一个可复用的 change proposal / implementation workflow 骨架的人

## 前置依赖

必需：
- `git`
- `openspec` CLI
- Claude Code（用于识别仓库内 `.claude/commands` 和 `.claude/skills`）

可选：
- `gh`（只在你需要 GitHub 仓库、PR、远程操作时才需要）

你可以先确认：

```bash
openspec --version
git --version
```

## Quick Start

1. 克隆仓库

```bash
git clone https://github.com/tc6-01/quickTeams.git
cd quickTeams
```

2. 运行初始化检查

```bash
./scripts/bootstrap.sh
```

3. 运行只读验证

```bash
./scripts/verify.sh
```

4. 在 Claude Code 中打开这个仓库目录，然后使用：

```text
/opsx:propose add-something
```

或者直接查看 demo change：

```bash
openspec status --change "reliable-agent-team-workflow"
```

## 最小 Happy Path

如果你只想确认“这个仓库能不能用”，按下面顺序走：

1. `./scripts/bootstrap.sh`
2. `./scripts/verify.sh`
3. `openspec status --change "reliable-agent-team-workflow"`
4. 在 Claude Code 中尝试 `/opsx:propose <your-change>`

## 仓库结构

- `.claude/commands/opsx/`：仓库级 slash commands
- `.claude/skills/openspec-*`：可复用 skill 定义
- `openspec/config.yaml`：OpenSpec 项目配置
- `openspec/changes/reliable-agent-team-workflow/`：完整 demo change
- `.spec-workflow/`：额外的模板资产和历史试验内容
- `scripts/`：bootstrap / verify 脚本
- `docs/`：安装、使用、排障文档

## 共享边界

这个仓库会提交“可共享的工作流资产”，但不会提交你的本地运行状态。

已明确视为本地状态、不会纳入版本控制的内容包括：
- `.omc/`
- `.claude/settings.json`
- `.claude/settings.local.json`
- `.claude.json`
- `.env*`
- 日志、临时文件、系统垃圾文件

如果你在使用过程中生成了新的本地状态文件，先检查 `.gitignore`，再决定是否应该提交。

## Demo Change

仓库自带一个完整样例：
- `openspec/changes/reliable-agent-team-workflow/proposal.md`
- `openspec/changes/reliable-agent-team-workflow/design.md`
- `openspec/changes/reliable-agent-team-workflow/tasks.md`

这个 change 展示了如何围绕“agent team 的可靠执行与标准 workflow”构建完整 OpenSpec 工件。

## 进一步阅读

- `docs/installation.md`
- `docs/usage.md`
- `docs/demo-workflow.md`
- `docs/troubleshooting.md`

如果你想最快确认这套仓库是不是适合你，优先看 `docs/demo-workflow.md`。

## 当前定位

这是一个 MVP 级共享仓库：
- 已具备基本的说明、检查和验证路径
- 适合团队内部共享和二次定制
- 暂未覆盖自动安装依赖、交互式初始化、CI 验证等增强能力
