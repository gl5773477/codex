---
name: interview-assist
description: 面试全流程助理。关联面试官平台自动拉取面试安排，基于岗位资源（JD/Rubrics/模板）将面试原始材料整理为结构化过程记录和评价报告，一键发布到 Redoc 分层存档。触发词：面试记录整理、生成面试报告、interview-assist、--eval、--setup、--routine、--doc
trigger: interview-assist, 面试记录, 面试报告, 面试评价, eval候选人, --help, --routine, --prepare
version: v1.4.0
dependencies:
  skills: ['read-redoc', 'write-redoc', 'data-fe-common-sso']
  skills_optional: ['hi-redoc-curd', 'calendar']
  commands: ['/interview-assist']
  external: ['python3']
repo_url: https://code.devops.xiaohongshu.com/dingyanzhi/interview-assist
intro_doc_url: https://docs.xiaohongshu.com/doc/a4dcc84e0062cb248fc687309b0cbe44
---

# Interview Assist

> 面试助理。不替代面试官判断——从日程拉取到材料整理到 Redoc 存档，端到端覆盖面试流程，让面试官专注引导和判断。

## 触发信号 (Trigger Signals)

**吟唱激活**：提供面试材料/链接，或说"帮我整理面试记录"、"今天有什么面试"

**最小激活输入**：option（`--eval` / `--setup` / `--routine` / `--doc` / `--help`）

**瞬发激活**：`/interview-assist --eval|--setup|--routine|--doc|--help [参数]`

**输入不足时**：主动读取 [docs/help.md](./docs/help.md)，输出对应选项的交互提示和示例。

## 契约 (Contract)

**资源根路径**（外置，两种环境）：
- OpenClaw：`~/workspace/interview-assist-data/`
- CodeWiz：`~/.codewiz/interview-assist-data/`

**资源目录结构**：
```
interview-assist-data/
├── config.yml                              # 存档根目录 ID 等配置
├── common/
│   ├── general_rubrics.md                 # 通用评价标准
│   ├── process_template.md               # 面试过程记录模板
│   └── report_template.md                # 面试评价报告模板
└── job/
    └── {jd-title}/
        ├── description.md                # 岗位 JD（可选）
        ├── specialized_rubrics.md        # 岗位专属评价标准
        └── candidates/
            └── {name}/
                ├── candidate_info.md     # 候选人背景摘要（自动生成）
                ├── resume.md             # 简历结构化 JSON（自动下载）
                ├── resume.pdf            # 简历 PDF 原文件（自动下载）
                ├── transcription-raw.md  # 原始转录（自动生成）
                ├── coding_test.md        # 算法题（可选）
                ├── manual_notes.md       # 面试官手记（可选）
                ├── interview_process.md  # 【产出A】过程记录
                └── interview_report.md   # 【产出B】评价报告草稿
```

**全局选项**：

| 选项 | 职责 |
|------|------|
| `--help` | 读取 docs/help.md，输出使用指南和交互示例 |
| `--setup` | 导入 rubrics、模板、配置存档根目录 |
| `--routine` | 从面试官平台拉取今日面试，下载简历和 ASR（弱依赖），创建候选人目录 |
| `--prepare` | 面试前准备：生成定制化面试流程 + 主线/辅线问题建议，引导 Qwiz 题库 |
| `--eval` | 五阶段面试评估，产出 interview_process.md + interview_report.md |
| `--doc` | 按内置存档规则发布三层 Redoc 文档 |
| `--dummy` | 生成 Mock 输入（测试用） |
| `--guard` | 验证产物质量 |

**显式不负责**：
- 不进行最终录用决策（留白由面试官填写）
- 不负责腾讯会议转录的账号登录鉴权（仅处理密码访问链接）

---

## 工作流程：--help

读取 [docs/help.md](./docs/help.md)，根据当前上下文输出对应章节。

---

## 工作流程：--setup

**输入不足时**：展示 help.md 中 --setup 章节的批量导入示例（含真实文档 URL 和中英文字段名对照），等待用户提供资源。

**Actions**：
1. 通过 read-redoc 读取各 Redoc URL 内容
2. 写入对应本地路径，每个资源确认写入后继续
3. 更新 `config.yml`（含 `archive_root_id`）

**Guards**：
- ❌ 禁止在 Skill 目录下写入用户数据
- ✅ 支持 Redoc URL、直接粘贴文字两种输入方式

**完成条件**：config.yml 中 archive_root_id 已配置，模板和 rubrics 已写入

---

## 工作流程：--routine

**目标**：从面试官平台拉取面试安排（今日 / 本周 / 未来一周），下载候选人材料，为每场面试创建目录。

**支持时间范围**：今日（默认）/ `--this-week` / `--next-week` / `--week`（本周+下周）/ `--date YYYY-MM-DD` / `--range START END`

**依赖**：`data-fe-common-sso` skill（SSO 自动获取登录态）

**Actions**：

1. 调用 `fetch_interviews.py` 获取今日日程，展示安排摘要
2. 为每场面试创建目录 `job/{岗位}/candidates/{候选人}/`（已存在则跳过）
3. 调用 `fetch_candidate_info.py --out-dir <候选人目录>` 获取结构化信息，自动下载 resume.pdf + 提取 resume.md（弱依赖 pymupdf skill）
4. 调用 `fetch_asr.py` 拉取 ASR 转录（**弱依赖**）：
   - 腾讯会议已结束 → transcription-raw.md ✅
   - 赛码网 / 未结束 → 标注"无 ASR / 待补充"，不阻塞主流程
5. 输出安排摘要（见 help.md 示例格式）
6. **检查未准备候选人**：对每场面试检查候选人目录下是否存在 `interview-plan.md`；若无，汇总列出并询问用户是否立即进入 `--prepare` 流程

**Guards**：SSO 失效时输出登录链接；❌ 禁止覆盖已有 interview_process.md / interview_report.md

---

## 工作流程：--eval（核心，分步产出）

加载 [eval-workflow.md](./docs/eval-workflow.md) 执行完整流程。

**输入不足时**：读取 help.md 中的 --eval 章节，展示三种材料输入方式。

**转录来源解析**（Phase 2 负责，按优先级）：

1. **本地文件**：`transcription-raw.md` 已存在（--routine 已下载）→ 直接读取
2. **腾讯会议转录链接**（识别格式）：
   ```
   Transcription file: https://meeting.tencent.com/ctm/{id}
   Password: {password}
   ```
   → browser 工具逐段滚动读取（SPA 懒加载，分 3 段），写入 transcription-raw.md
3. **HR 面试链接**（含 interviewScheduleId）→ `scripts/fetch_asr.py` 拉取
4. **Redoc URL** → read-redoc 读取
5. **直接粘贴文字** → 直接写入 transcription-raw.md

⚠️ **CRITICAL**：腾讯会议页面**不能用 web_fetch**，必须 browser 工具操作，约 1-2 分钟。

**流程概览**（五阶段）：
```
Phase 1: 加载上下文      → 确认所有资源已就位
Phase 2: 读取材料        → 解析转录来源，生成 transcription-raw.md
Phase 3: 过程记录 & 打标 → 按 process_template 产出 interview_process.md
Phase 4: 评价建议        → 读取 rubrics，生成亮点/风险/打分建议
Phase 5: 输出报告草稿    → 产出 interview_report.md，决策区留白
```

⚠️ **CRITICAL (x2)**：每阶段完成后**立即输出当前产物**，不等所有阶段完成再输出！

---

## 工作流程：--doc

**内置存档层级**（无需额外配置）：
```
存档根目录（archive_root_id）
└── {候选人} · {岗位} · {日期}            ← interview_report（一级）
    ├── 面试过程记录 · {候选人}            ← interview_process（二级）
    │   └── 语音转录原始记录              ← transcription-raw（三级，如有）
```

**Actions**：
1. 发布 interview_report → archive_root 一级，获取 shortcutId
2. 发布 interview_process → 步骤1的子文档
3. 如有 transcription-raw.md → 发布为 interview_process 的子文档
4. 三份文档 Redoc 链接回填到 interview_report.md

**Guards**：
- ✅ archive_root_id 未配置时提示先 --setup
- ✅ 返回所有发布文档的链接（必须至少两个）

⚠️ **CRITICAL**：`--doc` 必须返回所有发布文档的链接！

---

## 工作流程：--prepare

加载 [prepare-workflow.md](./docs/prepare-workflow.md) 执行完整流程。

**输入不足时**：读取 help.md 的 --prepare 章节，展示示例。

**资源加载（弱依赖，缺失降级不阻塞）**：
- JD / 候选人背景 / 简历 / specialized_rubrics / general_rubrics

**输出**：面试流程建议（时间分配 + 重点方向）+ 主线问题（必问，~5成）+ 辅线问题（备用，~5成）

**产物**：保存为 `candidates/{name}/interview-plan.md`（用户确认后保存）

**每次 --prepare 必须附加 Qwiz 引导提示**（见 prepare-workflow.md Step P5）

**完成条件**：输出面试流程建议 + 主线/辅线问题列表，产物写入 interview-plan.md布文档的链接！

---

## 🗺️ Roadmap

### ASR API 接入（待真实用户验证）
**目标**：`--routine` 时自动拉取腾讯会议 ASR，实现零操作材料准备。
- 当前：`fetch_asr.py` 已实现，赛码网面试无 ASR 结果属正常（非 bug）
- **TODO**：在真实腾讯会议面试场景中验证接口可用性
- 赛码网用户：始终需要手动提供转录（--eval 时导入）

### --prepare × Qwiz 深度集成（规划中）
**目标**：从"Agent 生成题目"升级为"接入内部题库"。
- 接入 Qwiz 平台（https://qwiz.devops.sit.xiaohongshu.com/）获取结构化题库
- 按岗位方向/难度/考察维度精准匹配推荐
- 与 HR 系统打通，自动关联候选人简历推荐题目

### 个人专属题库（规划中）
**目标**：让每位面试官沉淀自己的高质量私藏题目，调用时一触即发。
- 本地创建（无需上传，完全私有）
- 支持从历次 interview_process.md 中提炼优质追问
- --prepare 时优先调用个人题库 + 补充公共 Qwiz 题库

### --hunt（规划中）
**目标**：寻找合适候选人并安排面试。
- 输入岗位要求，跨平台搜索匹配候选人
- 生成候选人推荐列表（含匹配度分析）
- 对接 HR 系统发起面试邀约

---

## 质量检查清单

- [ ] 输入不足时读取 help.md 给提示？
- [ ] --routine 展示今日安排摘要（北京时间）？赛码网面试标注"无 ASR"？
- [ ] 腾讯会议转录通过 browser 工具读取（非 web_fetch）？
- [ ] --prepare 每次附加 Qwiz 引导提示？
- [ ] --eval 产出两份文件：interview_process.md + interview_report.md？最终决策区留白？
- [ ] --doc 三层存档，返回所有 Redoc 链接？

## 资源索引

### 文档 (docs/)
- [help.md](./docs/help.md) — 使用手册（--help / 输入不足时加载）
- [eval-workflow.md](./docs/eval-workflow.md) — --eval 五阶段详细流程
- [prepare-workflow.md](./docs/prepare-workflow.md) — --prepare 详细流程
- [report-structure.md](./docs/report-structure.md) — 产物结构规范

### 脚本 (scripts/)
fetch_interviews.py ✅ / fetch_candidate_info.py ✅ / check_pending_interviews.py ✅ / fetch_asr.py ⚠️（待腾讯会议场景验证）

### [CHANGELOG.md](./CHANGELOG.md) | [test/](./test/) | [dummy/](./dummy/)
