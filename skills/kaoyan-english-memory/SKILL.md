---
name: kaoyan-english-memory
description: Maintain a self-contained kaoyan English vocabulary skill, refresh the knowledge base, split words into basic/scene/contrast/standard routes, generate a dated daily study plan, and optionally push the markdown plan to Slack or WeCom webhooks.
metadata:
  short-description: 刷新考研英语词库并生成每日学习计划与推送
---

# Kaoyan English Memory

Use this skill for four jobs:

1. Refresh the embedded kaoyan English vocabulary knowledge base
2. Rebuild lightweight learning routes and scene units
3. Generate a dated daily study plan with progress state
4. Push the rendered markdown plan to configured channels

## Skill Root

This skill is self-contained. Run all commands from the skill root:

- `skills/kaoyan-english-memory`

Do not depend on an external project directory unless the user explicitly asks to sync from one.

## Key Files

- `config/daily_plan.json`: daily quotas for scene units, contrast pairs, extra words, and review words
- `config/push_channels.json`: delivery channel definitions
- `config/action_chains.json`: scene-unit templates
- `config/contrast_pairs.json`: contrast-memory pairs
- `config/basic_words.txt`: excluded basic words
- `data/raw/kaoyan_words.csv`: merged raw vocabulary source
- `data/state/learning_progress.json`: progress state
- `kb/words.jsonl`: full structured word base
- `kb/scene_words.jsonl`: scene-oriented study words
- `kb/contrast_words.jsonl`: contrast-oriented study words
- `kb/standard_words.jsonl`: standard study words
- `kb/scene_units.jsonl`: scene learning units
- `kb/learning_route_report.json`: route summary
- `kb/daily_plan_sample.json`: latest JSON plan
- `kb/daily_plan_sample.md`: latest markdown plan

## Refresh Workflow

Use this when the user asks to refresh the skill data after config or raw-word changes.

Run:

```bash
python3 scripts/refresh_workspace.py
```

If the raw CSV has changed and you want a sanity check first, run:

```bash
python3 scripts/refresh_workspace.py --validate-raw
```

This rebuilds:

- `kb/words.jsonl`
- `kb/basic_words.jsonl`
- `kb/scene_words.jsonl`
- `kb/contrast_words.jsonl`
- `kb/standard_words.jsonl`
- `kb/scene_units.jsonl`
- `kb/learning_route_report.json`
- `kb/high_frequency_scene_memory_report.json`
- `kb/sample_ai_payload.json`

Only run download or merge scripts when the user explicitly asks to refresh upstream sources.

## Daily Plan Workflow

Use this when the user asks for today's study content or when a daily automation runs.

Build the dated plan and persist progress:

```bash
python3 scripts/run_daily_delivery.py --date YYYY-MM-DD
```

Build and dry-run delivery:

```bash
python3 scripts/run_daily_delivery.py --date YYYY-MM-DD --dry-run-push
```

Build and actually deliver:

```bash
python3 scripts/run_daily_delivery.py --date YYYY-MM-DD --push
```

The daily plan shape should stay stable:

- one dated title
- one progress line
- one scene unit
- one contrast pair when available
- extra words
- review words when available

## Push Channel Policy

Delivery is configured in `config/push_channels.json`.

Supported channel types:

- `slack_webhook`
- `wecom_webhook`

Secrets must come from environment variables referenced by `webhook_env`. Do not hardcode webhook URLs in the skill files.

If channels are disabled or env vars are missing, report the skip clearly and continue without crashing the whole refresh flow.

## Route Policy

Do not try to force every word into a scene.

Use the lightweight routes already computed in `kb/words.jsonl`:

- `basic`: excluded from the main learning flow
- `scene`: prefer to introduce through scene units or scene-priority extras
- `contrast`: prefer to introduce through contrast pairs
- `standard`: introduce through ordinary daily extras

If the user asks how the routing works, explain it in those four buckets instead of discussing full word graphs.

## Planning Guidance

When updating daily-plan behavior:

1. Keep the plan simple and repeatable
2. Prefer one scene unit per day
3. Prefer one contrast pair per day
4. Use extra words to keep progress moving
5. Use recent offsets for review instead of random review
6. Optimize for stable daily learning, not full semantic coverage
