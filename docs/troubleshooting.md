# Troubleshooting

## `openspec: command not found`

原因：
- 你的环境里没有安装 OpenSpec CLI
- 或者已经安装，但不在当前 shell 的 `PATH` 中

处理方式：
1. 先确认：

```bash
openspec --version
```

2. 如果仍然报错，先安装或修复 OpenSpec CLI 的 PATH
3. 再重新运行：

```bash
./scripts/bootstrap.sh
./scripts/verify.sh
```

## `gh` 不存在

这通常不是阻塞问题。

`gh` 只在这些场景才需要：
- 创建 GitHub 仓库
- 推送远程仓库
- 查看 PR / diff
- 运行 review 工作流

如果你只是想使用 `openspec` 和 Claude Code 工作流，可以先忽略 `gh`。

## `./scripts/bootstrap.sh` 失败

常见原因：
- 缺少 `git`
- 缺少 `openspec`
- 你不在仓库根目录运行脚本
- 仓库内容不完整

建议检查：

```bash
pwd
ls
```

并确认这些路径存在：
- `.claude/commands/opsx`
- `.claude/skills`
- `openspec/config.yaml`
- `openspec/changes/reliable-agent-team-workflow`

## `./scripts/verify.sh` 失败

最关键的一步是：

```bash
openspec status --change "reliable-agent-team-workflow"
```

如果这一步失败，优先检查：
- `openspec` 是否可执行
- `openspec/config.yaml` 是否存在
- demo change 目录是否完整

## 为什么 `.omc/` 没有提交

`.omc/` 是本地运行态目录，不属于共享仓库资产。

里面可能包含：
- 会话状态
- 子 agent 跟踪
- 临时缓存
- 本机路径信息

这些内容不应该进入公开仓库，所以已经通过 `.gitignore` 排除。

## 为什么 `.claude/settings.json` 没有提交

这是本地环境配置，可能带有你的个人偏好或机器相关设置。

仓库会提交共享的 commands / skills，但不会提交你的本地运行配置。

## 我 clone 下来后，Claude Code 没识别命令

先确认你是在这个仓库目录中运行 Claude Code。

再确认这些路径存在：
- `.claude/commands/opsx/propose.md`
- `.claude/commands/opsx/apply.md`
- `.claude/skills/openspec-propose/SKILL.md`

如果文件存在但命令仍不可用，优先检查你的 Claude Code 环境是否支持仓库级 `.claude/commands` 和 `.claude/skills`。

## 仓库里哪些内容是主线，哪些是辅助

主线：
- `.claude/commands/opsx/`
- `.claude/skills/openspec-*`
- `openspec/config.yaml`
- `openspec/changes/`
- `scripts/`
- `README.md` / `docs/`

辅助或历史资产：
- `.spec-workflow/`
- `.specstory/`

如果你只是想最快上手，先关注主线部分即可。
