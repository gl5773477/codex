# interview-assist Mock 数据标准

> `--dummy` 触发，生成标准测试输入。

## 典型测试场景

| 场景 | 描述 | 样本文件 |
|------|------|---------|
| `minimal` | 最小 eval：只有转录文字，无简历/代码题/手动记录 | `samples/minimal-eval.md` |
| `full` | 完整 eval：转录 + 简历 + 代码题 + 手动记录 | `samples/full-eval.md` |
| `setup` | --setup 初始化：JD + rubrics 内容示例 | `samples/setup-input.md` |

## 使用方式

```
/interview-assist --dummy           # 输出 minimal 场景
/interview-assist --dummy full      # 输出 full 场景
/interview-assist --dummy setup     # 输出 --setup 场景
```

## 期望产物

每个样本执行后，应在对应候选人目录下生成 `interview_report.md`，
可用 `--guard` 验证报告质量。
