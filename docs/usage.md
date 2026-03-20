# Usage

## 这套仓库怎么用

`quickTeams` 提供的是仓库级工作流入口，不是一个需要 `npm start` 的应用。

你主要会通过 Claude Code 的命令和 OpenSpec CLI 来使用它。

## 主要命令

### 1. 探索

```text
/opsx:explore
```

适合：
- 需求不够清楚
- 需要先梳理问题
- 需要形成 change 方向

### 2. 生成 change 草案

```text
/opsx:propose add-user-auth
```

或者：

```text
/opsx:propose 我想加一个用户认证流程
```

它会尝试生成：
- `proposal.md`
- `design.md`
- `tasks.md`
- 对应 capability 的 `specs/**/spec.md`

### 3. 实施 change

```text
/opsx:apply add-user-auth
```

适合：
- proposal / design / tasks 都已经准备好
- 你要开始真正落代码或补实现

### 4. 归档 change

```text
/opsx:archive add-user-auth
```

适合：
- 变更已经完成
- 你要把这个 change 收尾归档

## 使用 demo change

如果你想按步骤走一遍，先看 `docs/demo-workflow.md`。

仓库自带一个 demo change：

```bash
openspec status --change "reliable-agent-team-workflow"
```

推荐你先读这几个文件：
- `openspec/changes/reliable-agent-team-workflow/proposal.md`
- `openspec/changes/reliable-agent-team-workflow/design.md`
- `openspec/changes/reliable-agent-team-workflow/tasks.md`

它们展示了这个仓库里一条完整的 propose -> design -> tasks 工作流是什么样子。

## 建议的新人路径

### 路径 A：先看现成样例
1. 运行 `./scripts/bootstrap.sh`
2. 运行 `./scripts/verify.sh`
3. 查看 demo change
4. 再自己提一个新 change

### 路径 B：直接新建 change
1. 运行 `./scripts/bootstrap.sh`
2. 在 Claude Code 中执行 `/opsx:propose <你的需求>`
3. 检查生成的 OpenSpec 工件
4. 执行 `/opsx:apply <change-name>`

## 目录的正确理解

### `.claude/`
仓库级 Claude Code 入口资产。

- `commands/opsx/`：slash command 定义
- `skills/openspec-*`：skill 定义

### `openspec/`
OpenSpec 的主工作区。

- `config.yaml`：项目配置
- `changes/`：所有 change

### `.spec-workflow/`
额外模板与历史试验资产。它不是当前主线入口，但保留作为可复用模板参考。

### `.specstory/`
SpecStory 相关产物目录。这里面有一部分是本地或历史痕迹，不应被误解为运行时必需内容。
