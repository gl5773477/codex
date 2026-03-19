# --eval 五阶段详细流程

> 核心工作流。每阶段结束后主动输出当前产物，不等全部完成。

## 参数解析

```
/interview-assist --eval 候选人:<name> 岗位:<jd-title>
```

`候选人` 和 `岗位` 缺失时交互询问。转录来源按优先级：transcription-raw.md 文件 → 腾讯会议链接（browser 读取）→ Redoc URL（read-redoc）→ 直接粘贴文字。

---

## 转录来源解析（Phase 2 前置处理）

### A. 腾讯会议转录链接格式识别

识别用户消息中包含以下格式的内容：
```
Transcription: Transcription_Started by {发起人}
Date: {yyyy-mm-dd hh:mm:ss}
Transcription file: https://meeting.tencent.com/ctm/{id}
Password: {password}（无密码则无此行）
```

**browser 读取流程**（SPA 懒加载，必须分段）：
1. `browser(action=open, profile=openclaw, url=<转录链接>)`
2. 如有 Password：`browser(action=snapshot)` 找密码输入框 → `browser(action=act, kind=type)` 输入 → 提交
3. 等待页面加载（loadState=networkidle）
4. 分三段读取：
   - `document.querySelector('.minutes-module-list')` 获取容器
   - scrollTop=0（顶部）→ snapshot 提取文本
   - scrollTop=1200（中部）→ snapshot 提取文本  
   - scrollTop=99999（底部）→ snapshot 提取文本
5. 去重合并（用 `Set` 去重），保留时间戳和说话人信息
6. 写入 `candidates/{name}/transcription-raw.md`，头部记录来源 URL + 日期

⚠️ 腾讯会议转录页面**不能用 web_fetch**，必须 browser 操作。速度较慢（约 1-2 分钟），但可行，不要跳过。

---

## Phase 1: 加载上下文

**目标**：确认所有必要资源已就位，建立本次 eval 的执行上下文

**Guards**：
- ✅ 检测资源根路径（OpenClaw 优先，CodeWiz 回退）
- ❌ 资源缺失时禁止静默跳过，必须列出缺失项并提示用户补充
- ✅ 腾讯会议转录 → browser 工具读取（不用 web_fetch）

**Checkpoint**：
- [ ] `job/{jd-title}/description.md` 存在
- [ ] `job/{jd-title}/specialized_rubrics.md` 存在（Phase 4 才需要，提前检查）
- [ ] `common/process_template.md` 存在
- [ ] `common/report_template.md` 存在
- [ ] 候选人目录 `job/{jd-title}/candidates/{name}/` 存在

**Actions**：
- 加载 JD（`description.md`）→ 提炼岗位核心要求（3-5 条，用于 Phase 3 打标参考）
- 检查转录来源：文件 → 直接读取；URL → read-redoc / web_fetch；缺失 → 提示粘贴
- 检查可选文件：`coding_test.md`、`manual_notes.md`（记录是否存在）

**阶段产出**（主动输出）：
```
✅ Phase 1 完成
岗位：{jd-title}   候选人：{name}
JD 核心要求：[提炼的 3-5 条]
资源状态：转录 ✅ | 简历 ✅ | 代码题 ✅/⚠️缺失 | 手动记录 ✅/⚠️缺失
```

---

## Phase 2: 读取候选人材料

**目标**：加载所有候选人相关原始材料，建立候选人背景认知

**Guards**：
- ✅ 简历核心背景控制在 3 行以内（避免过度摘要）
- ❌ 禁止此阶段对候选人做任何评价判断

**Actions**：
- 读取 `resume.md` → 提炼：教育背景 / 工作经历要点 / 与岗位相关度（≤ 3 行）
- 读取 `interview_transcription.md`（或已缓存内容）→ 全文加载到上下文
- 读取 `coding_test.md`（如有）→ 加载题目 + 代码
- 读取 `manual_notes.md`（如有）→ 加载面试官关键词原文

**阶段产出**（主动输出）：
```
✅ Phase 2 完成
简历摘要（≤3行）：[...]
转录长度：约 XXX 字
代码题：[题目名称] / 无
面试官手动记录：[关键词列表] / 无
```

---

## Phase 3: 过程记录 & 打标

**目标**：将转录结构化为面试过程记录，关联考察点，填入手动关键词

**Guards**：
- ✅ 基于 `process_template.md` 的结构组织内容
- ✅ 打标必须基于转录内容分析，不凭空标注
- ✅ 手动记录的关键词原样填入对应环节（不修改、不解释）
- ❌ 禁止在此阶段生成综合评价或建议（Phase 4 负责）
- ❌ 禁止因为转录口语化就删减候选人的回答内容（忠实记录）

**Actions**：
按转录时序，逐段处理：

```
对于每个对话段落：
  1. 识别话题/问题（面试官发言 → 提炼考察意图）
  2. 整理候选人回答（口语 → 书面，保留核心内容）
  3. 打标：关联 JD 核心要求 中的考察维度
  4. 如果 manual_notes 中有对应关键词 → 填入 [面试官标注] 字段
```

**阶段产出**（主动输出，Markdown 格式）：
```markdown
## 面试过程记录

### [话题/问题描述]
**候选人回答**：[结构化整理]
🏷️ **考察点**：[维度1] / [维度2]
📝 **面试官标注**：[来自 manual_notes，如有]

### [下一个话题]
...
```

---

## Phase 4: 评价建议

**目标**：读取 rubrics，回顾过程记录，生成维度评分建议和综合评价

**Guards**：
- ✅ 必须先完整读取 `specialized_rubrics.md` + `common/general_rubrics.md` 再评价
- ✅ 每个维度的建议必须引用 Phase 3 中的具体记录作为依据
- ❌ 禁止给出"通过/拒绝"等最终决策建议（整体观感可以有倾向，但不做最终结论）

**Actions**：
- 加载 `specialized_rubrics.md` 和 `general_rubrics.md`
- 逐维度回顾 Phase 3 过程记录，生成表现描述 + 建议等级
- 生成综合评价三项：
  - **亮点**：候选人表现突出的 2-3 点（需有具体依据）
  - **风险/待观察**：需要关注的 1-3 点（非否定，是提醒）
  - **整体观感**：1-2 句，描述候选人整体印象

**阶段产出**（主动输出）：
```markdown
## 综合评价

### 各维度评估
| 维度 | 表现摘要 | 建议等级 |
|------|---------|---------|
| [维度1] | [基于记录的描述] | 强/中/弱/待观察 |
...

### Agent 综合建议
**亮点**：
- ...

**风险/待观察**：
- ...

**整体观感**：[1-2 句]
```

---

## Phase 5: 输出报告草稿

**目标**：合并所有阶段产物为完整 interview_report.md，决策区严格留白

**Guards**：
- ✅ 必须基于 `report_template.md` 的结构组织最终报告
- ❌ 决策区禁止填入任何内容（包括 Agent 建议），只放留白提示
- ✅ 写入文件路径：`job/{jd-title}/candidates/{name}/interview_report.md`

**Actions**：
合并 Phase 2-4 产物，按报告模板组织，写入文件。

**报告结构**（基础骨架，最终以 report_template.md 为准）：
```markdown
# 面试报告：{候选人} × {岗位}
> 生成时间：{date} | 版本：草稿（待面试官填写决策）

## 基本信息
候选人：{name} | 岗位：{jd-title} | 面试日期：[留白] | 面试官：[留白]

## 简历摘要
[Phase 2 产出]

## 面试过程记录
[Phase 3 产出]

## 算法题评估
[代码题 + Phase 3/4 中的代码评价，如有]

## 综合评价
[Phase 4 产出]

---
## 面试官最终决策
> 请面试官填写以下内容：
> - 最终评价：
> - 决定：通过 / 拒绝 / 待定
> - 备注：
```

**完成条件**：文件写入成功，输出文件路径 + Redoc 发布提示

**阶段产出**（主动输出）：
```
✅ 报告已生成
路径：interview-assist-data/job/{jd-title}/candidates/{name}/interview_report.md
字数：约 XXX 字

💡 下一步：/interview-assist --doc --job {jd-title} --candidate {name}
```
