# Installation

## 目标

把 `quickTeams` 放到一个新环境后，确认它满足最小可用条件：
- `openspec` 可执行
- 仓库关键目录存在
- Claude Code 能在仓库中读取 `.claude/commands` 和 `.claude/skills`
- demo change 可被 `openspec status` 正常识别

## 1. 克隆仓库

```bash
git clone https://github.com/tc6-01/quickTeams.git
cd quickTeams
```

## 2. 安装前置依赖

### 必需工具
- `git`
- `openspec`
- Claude Code

### 可选工具
- `gh`

> `gh` 不是使用本仓库工作流的必要条件；只有在你需要创建远程仓库、PR、查看 PR 或执行 GitHub 相关操作时才需要。

## 3. 运行 bootstrap

```bash
./scripts/bootstrap.sh
```

这个脚本会：
- 检查 `git` 和 `openspec`
- 把 `gh` 标记为可选项
- 检查关键目录和 demo change
- 给出下一步验证提示

## 4. 运行 verify

```bash
./scripts/verify.sh
```

这个脚本会做只读验证，并运行：

```bash
openspec status --change "reliable-agent-team-workflow"
```

如果这个命令成功，说明仓库至少已经具备最小 OpenSpec 使用条件。

## 5. 在 Claude Code 中使用

在 Claude Code 中进入该仓库后，仓库级命令和 skill 应该可被识别。

典型入口：
- `/opsx:explore`
- `/opsx:propose`
- `/opsx:apply`
- `/opsx:archive`

## 6. 首次使用建议

第一次使用时，不要直接改动 demo change。

建议顺序：
1. 先运行 `./scripts/bootstrap.sh`
2. 再运行 `./scripts/verify.sh`
3. 阅读 `README.md`
4. 查看 demo change
5. 用一个新的 change 名称试一次 `/opsx:propose`
