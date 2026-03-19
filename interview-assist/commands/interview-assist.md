---
name: interview-assist
description: 面试助理 — 意图还原器，将面试记录整理/评估/发布请求映射为 interview-assist skill 的精确调用。支持 --eval（评估）/ --setup（初始化资源）/ --doc（发布报告）。
---

# /interview-assist

> Command 是意图还原器：解析面试相关请求，还原为 interview-assist skill 的完整调用。

## 触发

```
/interview-assist --eval [--job <jd-title>] [--candidate <name>]
/interview-assist --setup [--job <jd-title>]
/interview-assist --doc [--job <jd-title>] [--candidate <name>]
/interview-assist --dummy [minimal|full|setup]
/interview-assist --guard [--job <jd-title>] [--candidate <name>]
```

## 意图映射

调用 [`interview-assist`](~/.openclaw/workspace/skills/interview-assist/SKILL.md)。

**参数补全策略**：

| 参数 | 获取方式 | 缺失时 |
|------|---------|-------|
| `--job` | 命令参数 | 列出已有岗位供选择，或询问 |
| `--candidate` | 命令参数 | 列出该岗位下已有候选人，或询问 |
| 转录内容 | 文件 / URL / 粘贴 | 询问来源方式 |

## 执行流程

### 1. Option 识别
- 识别主 option（`--eval` / `--setup` / `--doc` / `--dummy` / `--guard`）
- 缺失时询问意图

### 2. 参数补全
- `--eval` / `--doc` / `--guard`：确认 job + candidate
- `--setup`：确认 job，收集需要写入的资源

### 3. 调用 interview-assist skill 执行

## 示例

```
/interview-assist --eval --job ios-engineer --candidate zhang-san
/interview-assist --eval
/interview-assist --setup --job ios-engineer
/interview-assist --doc --job ios-engineer --candidate zhang-san
/interview-assist --dummy
/interview-assist --guard --job ios-engineer --candidate zhang-san
```

## 关联

- **Skill**: [`interview-assist`](~/.openclaw/workspace/skills/interview-assist/SKILL.md)

## 注意

- `--eval` 分五阶段输出，每阶段完成后主动输出，不等全部完成
- `--doc` 需要先完成 `--setup` 配置 Redoc 信息
- rubrics 文件由用户提供，v1.0.0 不自动生成
