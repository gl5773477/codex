---
name: role-model-reminder
description: Maintain a role-model reminder library and generate one concise daily reminder from figures such as 曾国藩、丁元英、梅长苏、8号陪审员、稻盛和夫、南仁东、黄旭华.
metadata:
  short-description: Curate role-model materials and generate daily reminders
---

# Role Model Reminder

Use this skill for two recurring jobs:

1. Periodic material collection and curation
2. Daily reminder generation

## Files

- `config/people.json`: tracked figures, themes, and target coverage
- `data/seed/materials.json`: stable seed materials
- `data/inbox/*.json`: newly collected materials waiting to be merged
- `data/curated/materials.json`: merged, deduplicated material library, generated if missing
- `kb/material_coverage.json`: coverage report by figure and tag, generated if missing
- `kb/reminder_candidates.jsonl`: derived reminder candidates for daily delivery, generated if missing
- `data/state/push_history.json`: delivery history
- `scripts/refresh_materials.py`: validate, merge, dedupe, and report coverage
- `scripts/build_reminders.py`: turn curated materials into reminder candidates
- `scripts/generate_daily_push.py`: pick one reminder for a date and render markdown

## Material Collection Workflow

Use this when the user asks to enrich the reminder library, review current coverage, or prepare the weekly update job.

1. Read `kb/material_coverage.json` if it exists. Focus on people or themes that are under-covered.
2. Add `2-5` new materials in a new file under `data/inbox/`, for example `data/inbox/2026-04-08-zeng-ding.json`.
3. Each material must contain:
   - `person_id`
   - `person_name`
   - `material_type` (`story` or `thought`)
   - `title`
   - `summary`
   - `principle`
   - `reminder`
   - `reflection_question`
   - `tags`
   - `source_hint`
   - optional: `story_case`, `story_vignette`
4. Prefer concrete stories, practices, or thought patterns. Do not write generic admiration.
5. Prefer paraphrase. Only use direct quotations if they are verified and materially important.
6. Keep the tone restrained. The reminder should feel like an internal standard, not a motivational slogan.
7. If possible, add `story_vignette`: a shorter, more atmospheric version of the scene for daily delivery.

After adding materials, run these commands from the skill root:

```bash
python3 scripts/refresh_materials.py
python3 scripts/build_reminders.py
```

## Daily Push Workflow

Use this when the user asks for today's reminder or when a daily automation runs.

Run:

```bash
python3 scripts/generate_daily_push.py --update-history
```

The output is already suitable for an inbox item or chat push. Keep this output shape:

If `data/curated/materials.json`, `kb/material_coverage.json`, or `kb/reminder_candidates.jsonl` are missing, the script will rebuild them from `data/seed/` and `data/inbox/` before rendering the daily push.

- `一句提醒`
- `-- 人物`
- `一幕故事`

Tone requirements:

- concise
- sober
- non-performative
- no generic chicken-soup phrasing
- avoid card-style metadata overload
- prefer one memorable scene over many labels
- when using a story, prefer one concrete scene over abstract explanation
- omit reflective prompts in the default daily push
- prefer `story_vignette` when available so the daily push reads like a short note, not a dossier

## Suggested Automation Split

Use two OpenClaw scheduled tasks instead of one mixed task:

1. Weekly curation:
   - inspect coverage
   - collect or add a few new materials
   - run refresh and rebuild scripts
2. Daily push:
   - run `python3 scripts/generate_daily_push.py --update-history`
   - send the markdown result directly

If the user only asks for the daily reminder, do not expand the material library unless the library is obviously broken or empty.
