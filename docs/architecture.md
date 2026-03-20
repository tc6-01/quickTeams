# Architecture

## 仓库定位

`quickTeams` 不是传统应用源码仓库，而是一套围绕 Claude Code + OpenSpec 的共享工作流骨架。

它的核心目标是：
- 把常用的 OpenSpec 工作流入口放进仓库
- 让团队成员复用统一的 propose / apply / archive 路径
- 保留一个可验证的 demo change，帮助新人理解和上手

## 主线结构

### `.claude/`

这是 Claude Code 的仓库级入口资产。

- `.claude/commands/opsx/`
  - 定义 `/opsx:*` 命令入口
  - 当前包括 `explore`、`propose`、`apply`、`archive`
- `.claude/skills/openspec-*`
  - 定义可复用 skill
  - 与 `opsx` 命令形成配套工作流

这是共享仓库的一部分，应该提交。

## `openspec/`

这是 OpenSpec 的主工作区。

- `openspec/config.yaml`
  - 提供 schema、项目上下文和基本规则
- `openspec/changes/`
  - 存放所有 change
- `openspec/changes/reliable-agent-team-workflow/`
  - 当前仓库自带 demo change

这是主线中的另一部分，也是共享仓库的核心资产。

## `scripts/`

这是新人接入和仓库自检的辅助层。

- `scripts/bootstrap.sh`
  - 做前置依赖和路径检查
- `scripts/verify.sh`
  - 做只读验收
- `scripts/doctor.sh`
  - 做更细粒度的诊断和问题定位

它们的目标不是自动安装一切，而是快速告诉用户：
- 当前环境缺什么
- 仓库是否完整
- 下一步该怎么走

## `docs/`

这是对外说明层。

- `docs/installation.md`
- `docs/usage.md`
- `docs/demo-workflow.md`
- `docs/troubleshooting.md`
- `docs/architecture.md`

建议阅读顺序：
1. `README.md`
2. `docs/demo-workflow.md`
3. `docs/usage.md`
4. 需要时再看安装与排障文档

## `.spec-workflow/`

这是附加模板与历史试验资产，不是当前仓库的主线入口。

它的价值主要在于：
- 提供另一套 spec workflow 模板参考
- 保留一些模板资产，便于后续扩展

如果你只是想最快上手 quickTeams，可以先忽略这一层。

## `.specstory/`

这是 SpecStory 相关目录。

这里面可能同时包含：
- 可共享的说明文件
- 历史或本地产物

因此它不是主线入口。对普通使用者来说，默认只需要知道：
- 它不是运行时必需部分
- 它不应主导你对仓库主线的理解

## `.omc/`

这是本地运行态目录，不属于共享仓库资产。

它通常会包含：
- 会话状态
- 子 agent 跟踪
- 本机路径和临时上下文

因此已经通过 `.gitignore` 排除。

## 推荐主线

对第一次接触这个仓库的人，推荐按这条线理解：

1. `README.md`
2. `.claude/commands/opsx/`
3. `.claude/skills/openspec-*`
4. `openspec/config.yaml`
5. `openspec/changes/reliable-agent-team-workflow/`
6. `scripts/bootstrap.sh` / `scripts/verify.sh`
7. `docs/demo-workflow.md`

这条路径能覆盖：
- 命令入口
- 工作流定义
- 示例 change
- 环境检查和验证

## 当前架构取舍

当前仓库选择的是“文档 + 轻量脚本 + demo change”方案，而不是“全自动安装器”。

原因是：
- `openspec`、Claude Code、`gh` 都属于仓库外依赖
- 在 MVP 阶段，先把依赖声明、验证路径和失败诊断做好，比盲目自动安装更稳

后续如果仓库继续演进，可以再加入：
- 交互式 init
- 更完整的模板集
- GitHub Actions 持续验证
- 更多 demo workflow
