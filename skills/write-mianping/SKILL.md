---
name: write-mianping
description: Draft concise Chinese interview evaluations ("面评", "面试评价", "候选人评价", pass/fail recommendation) from resumes, interview notes, and past examples. Use when Codex needs to summarize candidate background, interview evidence, strengths, risks, and recommendation into a consistent internal-review style, especially for outputs like "总评 + 核心说明", score + recommendation, or rewrites that match an existing team tone.
---

# Write Mianping

Use this skill to write concise, evidence-based Chinese interview evaluations for hiring panels.
Prioritize factual consistency, calibrated judgment, and team style over generic praise.

## Workflow

1. Gather sources.
- Read the resume, interview notes, and sample evaluations or screenshots.
- Confirm whether all notes belong to the same candidate before merging facts.
- Split evidence into three buckets: resume facts, interview-demonstrated strengths, and open questions or risks.
- Treat interview notes as the primary source for evaluative writing. Use the resume mainly for background, project names, and chronology.

2. Decide the recommendation.
- Judge pass/fail/continue mainly from interview evidence, not resume polish.
- Keep the score at the front if the user or team already uses one.
- Calibrate praise. Prefer `扎实` / `比较清楚` / `有实践` over exaggerated wording unless the evidence is unusually strong.

3. Write in house style.
- Start with a short conclusion paragraph that states recommendation, current company or domain, main responsibility, and strongest strengths.
- Follow with 2-3 short paragraphs or flat bullets that expand only the most decision-relevant topics.
- Keep the center of gravity on demonstrated engineering value: business understanding, architecture, stability, performance, ownership, and collaboration.
- Mention AI/application engineering only when both conditions are true: the candidate really has AI experience, and the interview notes contain usable evidence about what they did, how deep they went, or what judgment the interviewer formed.

4. Validate before finishing.
- Remove unsupported claims and repeated points.
- Distinguish sample style from sample facts.
- Re-check AI statements: do not turn framework exposure into deep expertise unless the interview proved it.
- If the interview record does not meaningfully discuss AI, omit the AI paragraph even if the resume contains AI keywords.

## House Style

- Use concise Chinese prose. Prefer short paragraphs over long outlines.
- Lead with the conclusion. The first paragraph should already tell the reader whether the candidate is worth推进.
- Blend business context and technical judgment in the first paragraph.
- Sound like an interviewer: specific, grounded, slightly conservative.
- Mention communication style only if it affects hiring judgment.
- Keep the tone supportive but not inflated.

## Content Rubric

### First Paragraph

Cover most of the following in one compact paragraph:

- score and recommendation, if available
- current company, team, or business domain
- 1-2 main responsibilities or projects
- 2-3 strongest judgments
- communication signal, if relevant

### Core Explanation

Usually expand 2-3 topics:

- one proven engineering topic such as platformization, stability, performance, migration, or consistency
- one domain or business topic that shows business understanding or ownership
- one AI topic only if the candidate has real AI experience and the interview showed real implementation depth or concrete interviewer judgment

### Risk Calibration

- For pass cases, phrase weaknesses as calibration, not veto.
- Anchor every risk on missing evidence or shallow depth, not on vague feeling.
- Example: `AI 应用落地经验是有的，但对框架底层机制的理解还不算特别深入。`

## Guardrails

- Never mix facts from different candidates.
- If the user provides a sample note that clearly belongs to another person, use it only for style unless asked otherwise.
- Do not overstate leadership, system ownership, or AI depth when the notes only show participation or exploration.
- Prefer `主导/独立负责` only when the source material supports it.
- Do not add an AI section by default. AI is optional content, not a required section.

## Output Template

```md
[分数，可选]，[结论]。目前在[公司/业务]，主要负责[职责/项目]，涉及[2-3 个关键方向]。候选人[最强的 2-3 个判断]，[补一项沟通/协作评价，如有]，整体[结论]，建议[通过/继续推进/保留/不推进]。

[主题一]上做得比较扎实，包括[具体事项 1]、[具体事项 2]、[具体事项 3]，这些工作比较贴近真实线上复杂场景，说明其在[能力判断]上有实际经验。

[主题二，可选]，围绕[业务或 AI 主题]做了[具体动作]，也结合[技术点]做过[方案/探索]。整体看其在[判断]上是有实践的，但[保守校准句，可选]。
```

## If The User Requests A Strict Two-Part Format

- Part 1: write one short summary paragraph.
- Part 2: use a lead-in such as `核心事情的重点了解说明：`
- Keep part 2 to 2-4 flat bullets or short paragraphs.

## Use References

- For wording, calibration, and rewrite patterns, read [references/style-guide.md](references/style-guide.md).
