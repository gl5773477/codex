# interview-assist 使用手册

> 按需加载。当用户调用 `--help` 或输入不充分时读取本文件。

---

## 快速导航

| 你想做什么 | 用哪个选项 |
|-----------|-----------|
| 第一次使用，配置岗位资源 | `--setup` |
| 从日历/面试官平台自动拉取今日面试 | `--routine` |
| 面试结束，整理记录出报告 | `--eval` |
| 把报告发布到 Redoc 存档 | `--doc` |
| 查看此手册 | `--help` |

---

## --setup：配置岗位资源

**用途**：导入 rubrics、模板、设置 Redoc 存档根目录。配置一次，长期复用。

**最简调用**：
```
/interview-assist --setup
```
随后交互式引导。或者一次性给全：

```
/interview-assist --setup

通用评价标准 general_rubrics:
https://docs.xiaohongshu.com/doc/129f5caa083a25771756d1f2411391b8

岗位专属评价标准 specialized_rubrics（岗位方向：讨论客户端iOS）:
https://docs.xiaohongshu.com/doc/3e5e96c467b30272bb16f671e398af46

面试评价报告模板 report_template:
https://docs.xiaohongshu.com/doc/fbe49d57a41f43945d32637b9e3f8000

面试过程记录模板 process_template:
https://docs.xiaohongshu.com/doc/79699ce615122b54d1accf34b0e412ff

岗位 JD jd:
https://docs.xiaohongshu.com/doc/02684b8e1195e73bfee0e23545c0b697

面试历史存档根目录 doc存档根目录:
（在 Redoc 中新建一个文件夹，把链接粘贴在这里，所有面试报告将归档在此目录下）
```

> 💡 以上均为**可直接使用的参考文档**，覆盖通用 iOS 客户端方向。你也可以替换为自己团队的版本。

**配置后目录结构**：
```
interview-assist-data/
├── config.yml                     # 存档根目录 ID 等配置
├── common/
│   ├── general_rubrics.md         # 通用评价标准
│   ├── process_template.md        # 面试过程记录模板
│   └── report_template.md         # 面试评价报告模板
└── job/
    └── {岗位方向}/
        ├── specialized_rubrics.md # 岗位专属评价标准
        └── description.md         # 岗位 JD（可选）
```

---

## --routine：获取今日面试安排

**用途**：关联面试官平台（hr.xiaohongshu.com），自动拉取今日面试列表，为每场面试创建候选人目录并下载简历和 ASR 转录数据。

**调用**：
```
/interview-assist --routine                          # 今日
/interview-assist --routine --this-week             # 本周（含过去）
/interview-assist --routine --next-week             # 下周
/interview-assist --routine --week                  # 本周 + 下周（14天）
/interview-assist --routine --date 2026-03-23       # 指定日期
/interview-assist --routine --range 2026-03-19 2026-03-25  # 自定义区间
```

**执行内容**：
1. 通过 SSO（data-fe-common-sso）获取登录态
2. 拉取今日（北京时间）面试列表，展示今日安排摘要
3. 对每场面试自动创建目录：`job/{岗位}/candidates/{候选人}/`
4. 下载候选人简历 PDF（resume.pdf）+ 用 pymupdf skill 提取为 resume.md（弱依赖，跳过不影响主流程）
5. 尝试拉取 ASR 转录（弱依赖，见下）
6. 生成 candidate_info.md（基本背景：学历/工作年限/最近经历）

**ASR 转录说明（弱依赖）**：

> ⚠️ ASR 仅在腾讯会议面试中有效。若使用赛码网（acmcoder.com）等其他面试平台，ASR 无结果，Skill 会提示手动提供转录。

| 场景 | 处理方式 |
|------|---------|
| 腾讯会议面试，已结束 | 自动拉取 ASR，保存为 transcription-raw.md ✅ |
| 腾讯会议面试，未结束 | 标记"待补充"，提示面试后重新 --routine |
| 赛码网面试 | 无 ASR 结果，提示通过腾讯会议转录链接或粘贴方式在 --eval 时导入 |
| 其他平台 | 同上，手动提供 |

**安排输出示例**：
```
📅 2026-03-17 ~ 2026-03-23 面试安排（北京时间）

2026-03-18（已结束）
1. 黄贤宇  19:00-20:00  讨论客户端iOS（一面）
   简历 ✅ | resume.md ✅ | ASR：⚠️ 赛码网，无自动转录 | 面试准备 ✅

2026-03-23
2. 吕成翘  19:00-20:00  讨论客户端iOS（一面）
   简历 ✅ | resume.md ✅ | ASR：待（面试后重拉） | 面试准备 ❌
3. 尚谦    21:00-22:00  讨论客户端iOS（一面）
   简历 ✅ | resume.md ✅ | ASR：待 | 面试准备 ❌

⚠️  有 2 场面试尚未准备（无 interview-plan.md）：
   - 吕成翘（03-23 19:00）
   - 尚谦（03-23 21:00）
要现在进入准备流程吗？（是/否，或指定候选人名字）
```

---

## --eval：面试评估

**用途**：传入材料，五阶段分步产出过程记录 + 评价报告草稿。

**最简调用**：
```
/interview-assist --eval 候选人:张三 岗位:讨论客户端iOS
```

**转录来源（三种方式）**：

**方式 A：腾讯会议转录链接（Skill 自动 browser 读取，约 1-2 分钟）**
```
/interview-assist --eval 候选人:张三 岗位:讨论客户端iOS

Transcription: Transcription_Started by 凡瑟(丁彦植)
Date: 2026-03-18 19:10:27
Transcription file: https://meeting.tencent.com/ctm/2kYZWyV612
Password: HKJR
```

**方式 B：HR 系统面试链接（含 interviewScheduleId，Skill 调 API 拉取）**
```
/interview-assist --eval 候选人:张三 岗位:讨论客户端iOS
面试链接: https://hr.xiaohongshu.com/applicant-evaluation?talentId=xxx&interviewId=yyy&interviewScheduleId=zzz
```

**方式 C：Redoc 转录 URL 或直接粘贴文字**

**附加面试官评语（任何方式均可）**：
```
面试官评价关键词：
- 某某地方表现不错
- 某某问题回答得比较浅
```

**五阶段输出（每阶段完成后立即可见）**：
1. Phase 1：资源确认 + 上下文加载
2. Phase 2：材料读取 + transcription-raw.md 生成
3. Phase 3：结构化过程记录（interview_process.md）
4. Phase 4：各维度评分建议
5. Phase 5：评价报告草稿（interview_report.md）

---

## --doc：发布到 Redoc 存档

**调用**：
```
/interview-assist --doc 候选人:张三 岗位:讨论客户端iOS
```

**默认存档层级**（内置，无需配置）：
```
存档根目录
└── 张三 · 讨论客户端iOS · 2026-03-18      ← 评价报告（一级）
    ├── 面试过程记录 · 张三                 ← 过程记录（二级）
    │   └── 语音转录原始记录               ← 转录原文（三级，如有）
```

---

## 资源目录说明

| 路径 | 内容 | 必须/可选 |
|------|------|---------|
| `common/general_rubrics.md` | 通用评价维度（全岗位共用） | 必须 |
| `common/process_template.md` | 面试过程记录模板 | 必须 |
| `common/report_template.md` | 面试评价报告模板 | 必须 |
| `job/{jd}/specialized_rubrics.md` | 岗位专属评价标准 | 推荐 |
| `job/{jd}/description.md` | 岗位 JD | 可选 |
| `job/{jd}/candidates/{name}/resume.md` | 候选人简历 JSON（自动下载） | 自动 |
| `job/{jd}/candidates/{name}/resume.pdf` | 候选人简历 PDF（自动下载） | 自动 |
| `job/{jd}/candidates/{name}/candidate_info.md` | 候选人背景摘要（自动生成） | 自动 |
| `job/{jd}/candidates/{name}/transcription-raw.md` | 转录原文（自动生成） | 自动 |

---

## 常见问题

**Q：没有做过 --setup，能直接 --eval 吗？**
A：可以，Skill 会提示缺少哪些资源，可临时提供内容，或中断先做 --setup。

**Q：转录读取很慢怎么办？**
A：腾讯会议转录页面需 browser 操作约 1-2 分钟。如已做过 --routine，ASR 可能已自动下载好，直接 --eval 即可。也可直接粘贴转录文字。

**Q：可以只生成 interview_process，不生成 report 吗？**
A：--eval 总是产出两份文件，忽略 report 部分即可。

**Q：--routine 和 --eval 是什么关系？**
A：--routine 负责"准备材料"（创建目录、下载简历和 ASR），--eval 负责"分析产出"（整理记录、生成报告）。--routine 完成后直接 --eval 效率最高。

**Q：赛码网面试没有转录怎么办？**
A：赛码网不提供 ASR，--routine 会提示手动提供。面试结束后把腾讯会议转录链接或转录文字在 --eval 时导入即可。

---

## --prepare：面试前准备

**用途**：面试开始前，根据候选人信息 + 岗位 JD + Rubrics，生成定制化的面试流程和问题建议。

**调用**：
```
/interview-assist --prepare 候选人:张三 岗位:讨论客户端iOS
```

**生成内容（弱依赖，缺资源时仍可运行）**：
- **面试流程建议**：时间分配、环节顺序、重点考察方向
- **主线问题（约 5 成）**：大概率要问、必须覆盖的核心题
- **辅线问题（约 5 成）**：可选冗余，根据现场情况灵活选用

**示例输出**：
```
📋 面试准备：张三 × 讨论客户端iOS

⏱️ 建议时间分配（60分钟）：
  5min  开场/破冰
  15min 算法题
  25min 技术深度（架构/稳定性）
  10min 项目复盘
  5min  反问/收尾

🎯 主线问题（必问，5题）：
  1. [技术深度] UIKit 主线程模型与渲染机制...
  ...

💡 辅线问题（备用，按情况选）：
  A. [架构] 如果让你设计一个评论组件...
  ...
```

**Qwiz 题库**：想探索更多结构化题目？

👉 前往 [Qwiz 平台](https://qwiz.devops.sit.xiaohongshu.com/) 浏览内部题库，可按语言/方向/难度筛选。

> 🔭 **Roadmap**：未来将支持创建个人专属题库（沉淀你的高质量私藏面试题），届时 --prepare 可直接调用你的题库生成更贴合风格的问题。敬请期待。
