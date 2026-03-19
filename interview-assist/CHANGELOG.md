# Changelog

## [v1.4.0] - 2026-03-19

### Added
- `--routine` 支持时间范围：`--this-week` / `--next-week` / `--week` / `--date` / `--range`
- `--routine` 自动下载 resume.pdf 并用 pymupdf skill 提取为 resume.md（弱依赖，失败不阻塞）
- `--routine` 结束后检查未准备候选人（interview-plan.md 是否存在），汇总提示并引导进入 --prepare
- `--prepare` 产物从 `interview_prepare.md` 重命名为 `interview-plan.md`
- `fetch_interviews.py` 新增 `--range` / `--this-week` / `--next-week` / `--week` 模式
- `fetch_candidate_info.py` 新增 `--out-dir` 参数，自动写入 candidate_info.md / resume.pdf / resume.md

---

## [v1.3.0] - 2026-03-19

### Added
- `--prepare` 选项：面试前准备，生成定制化面试流程 + 主线/辅线问题建议
- `docs/prepare-workflow.md`：--prepare 五步详细流程（资源加载/流程建议/主线/辅线/Qwiz 引导）
- Qwiz 题库引导（https://qwiz.devops.sit.xiaohongshu.com/），每次 --prepare 必须输出
- 个人专属题库 Roadmap 条目（沉淀私藏高质量题目，未来 --prepare 直接调用）
- --help 快速导航新增 `--prepare`

### Changed
- ASR 标记为**弱依赖**：赛码网面试无 ASR 属正常，Skill 主动提示；不阻塞 --routine
- --setup 示例更新为参考文档的真实 URL（129f5caa / 3e5e96c4 / fbe49d57 / 79699ce6 / 02684b8e）
- --routine help.md 补充 ASR 弱依赖说明表格（腾讯会议 / 赛码网 / 未结束三种场景）
- Roadmap 重组：ASR 待验证 / --prepare × Qwiz 深度集成 / 个人专属题库 / --hunt

---

## [v1.2.2] - 2026-03-19

### Fixed
- `report_template.md` 路径统一到 `common/`（原 `templates/` 目录废弃）
- 同步修正 SKILL.md 目录树、help.md 资源表、eval-workflow.md Checkpoint

### Published（Redoc 参考文档）
- [通用评价标准【参考】](https://docs.xiaohongshu.com/doc/129f5caa083a25771756d1f2411391b8)
- [面试过程模板【参考】](https://docs.xiaohongshu.com/doc/79699ce615122b54d1accf34b0e412ff)
- [客户端iOS评价标准【参考】](https://docs.xiaohongshu.com/doc/3e5e96c467b30272bb16f671e398af46)
- [JD【参考】](https://docs.xiaohongshu.com/doc/02684b8e1195e73bfee0e23545c0b697)
- [面试评价报告模板【参考】](https://docs.xiaohongshu.com/doc/fbe49d57a41f43945d32637b9e3f8000)

---

## [v1.2.1] - 2026-03-18

### Added
- `--routine` 选项：关联面试官平台（hr.xiaohongshu.com），拉取今日面试日程，自动下载简历（PDF + JSON）和 ASR 转录，创建候选人目录
- `scripts/fetch_interviews.py` — 拉取面试官平台今日日程（基于 HR 系统 API）
- `scripts/fetch_asr.py` — 拉取腾讯会议 ASR 转录数据（已有 SSO 自动鉴权）
- `scripts/fetch_candidate_info.py` — 下载候选人简历（结构化 JSON + 背景摘要）
- `scripts/check_pending_interviews.py` — 检查待补充 ASR 的面试
- Roadmap 章节：`--prepare`（Qwiz 平台面试题推荐）、`--hunt`（候选人寻访）
- help.md 新增 `--routine` 章节说明 + 中英文字段名对照

### Changed
- `--setup` 示例中资源字段增加中文名称前缀（如"通用评价标准 general_rubrics"）
- 依赖新增 `data-fe-common-sso`（SSO 登录态）、`python3`（参考脚本运行）

---

## [v1.2.0] - 2026-03-18

### Added
- `--help` 选项：读取 docs/help.md，输出使用指南和交互示例
- `docs/help.md`：完整使用手册（--setup / --eval / --doc 示例、材料输入方式、FAQ）
- 腾讯会议转录解析：识别 `Transcription file + Password` 格式，browser 工具自动读取，保存为 transcription-raw.md
- `--doc` 存档三层结构：report(1级) → process(2级) → transcription-raw(3级)
- 输入不足时主动读取 help.md 给提示，不再等待用户猜测格式

### Changed
- Redoc 存档层级规则内置到 SKILL.md（不再依赖外置 config.yml doc_naming 字段），用户只需配置 archive_root_id
- eval-workflow.md 补充腾讯会议 browser 读取详细步骤（分三段滚动 + 去重）
- transcription-raw 文件名统一为 `transcription-raw.md`（去掉日期后缀）

---

## [v1.1.0] - 2026-03-18

### Added
- `interview_process.md` 作为独立产出文件（之前只有 interview_report.md）
- `--eval` Phase 3 专门产出 interview_process.md，Phase 5 产出 interview_report.md
- `--doc` Redoc 存档层级规则：
  - `interview_report` → archive_root 的一级子文档
  - `interview_process` → interview_report 对应 Redoc 的子文档
- config.yml 新增字段：`archive_root_id` / `archive_root_url` / `doc_naming`
- `--doc` 完成后将两份文档链接回填到 interview_report.md 的过程引用区
- `--doc` 必须返回两个链接（report + process）

### Changed
- 资源目录中 `interview_transcription.md` 更名为 `transcription-raw-*.md`（与实际文件对齐）
- SKILL.md 质量检查清单更新，增加两份产物和双链接验证

---

## [v1.0.0] - 2026-03-18

### Added
- 初始版本
- `--eval`：五阶段分步产出（加载上下文→读取材料→过程记录&打标→评价建议→报告草稿）
- `--setup`：初始化/更新岗位资源（JD、rubrics、模板、Redoc config）
- `--doc`：将 interview_report.md 发布为 Redoc 文档
- 支持面试官手动记录关键词（`manual_notes.md`）输入，填入过程记录
- 支持转录来源：文件 / Redoc URL（read-redoc / web_fetch）/ 粘贴文字
- 双环境路径：OpenClaw（workspace/interview-assist-data/）+ CodeWiz（~/.codewiz/interview-assist-data/）
- 全局选项 `--dummy` 和 `--guard`
- 配套 Command：`/interview-assist`
- docs/eval-workflow.md：五阶段详细流程和 Guards
- docs/report-structure.md：产物结构规范
- test/ 和 dummy/ 框架（含 minimal-eval 样本）

### Notes
- v1.0.0 中 specialized_rubrics 由用户提供，不自动生成
- 最终录用决策严格留白，不由 Agent 填写
