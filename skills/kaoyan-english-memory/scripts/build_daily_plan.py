import argparse
import json
from copy import deepcopy
from datetime import date, datetime, timedelta
from pathlib import Path

from common import (
    CONTRAST_PAIRS_PATH,
    DAILY_PLAN_CONFIG_PATH,
    DAILY_PLAN_SAMPLE_JSON_PATH,
    DAILY_PLAN_SAMPLE_MD_PATH,
    LEARNING_PROGRESS_PATH,
    SCENE_UNITS_OUTPUT_PATH,
    STUDY_WORDS_OUTPUT_PATH,
    ensure_parent,
    load_json,
    read_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the daily kaoyan English study plan.")
    parser.add_argument("--date", default=date.today().isoformat(), help="Plan date in YYYY-MM-DD format.")
    parser.add_argument("--config", type=Path, default=DAILY_PLAN_CONFIG_PATH, help="Path to daily_plan.json.")
    parser.add_argument("--state", type=Path, default=LEARNING_PROGRESS_PATH, help="Path to learning progress state.")
    parser.add_argument("--study-words", type=Path, default=STUDY_WORDS_OUTPUT_PATH, help="Path to study_words.jsonl.")
    parser.add_argument("--scene-units", type=Path, default=SCENE_UNITS_OUTPUT_PATH, help="Path to scene_units.jsonl.")
    parser.add_argument("--contrast-pairs", type=Path, default=CONTRAST_PAIRS_PATH, help="Path to contrast_pairs.json.")
    parser.add_argument("--json-output", type=Path, default=DAILY_PLAN_SAMPLE_JSON_PATH, help="Path to JSON output.")
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=DAILY_PLAN_SAMPLE_MD_PATH,
        help="Path to markdown output.",
    )
    parser.add_argument("--update-state", action="store_true", help="Persist the generated plan into state.")
    parser.add_argument("--force-rebuild", action="store_true", help="Rebuild even if the date already exists in state.")
    return parser.parse_args()


def load_state(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "version": 1,
        "started_at": None,
        "introduced_words": [],
        "completed_scene_units": [],
        "completed_contrast_pairs": [],
        "plans_by_date": {},
    }


def save_state(path: Path, state: dict) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def canonical_pair(pair: list[str]) -> str:
    return "|".join(sorted(pair))


def _sort_rows(rows: list[dict]) -> list[dict]:
    def sort_key(row: dict):
        rank = row.get("source_rank")
        try:
            rank_value = int(rank)
        except (TypeError, ValueError):
            rank_value = 10**9
        return (rank_value, row["word_id"])

    return sorted(rows, key=sort_key)


def _word_item(row: dict) -> dict:
    return {
        "word": row["word_id"],
        "meaning": "；".join(row.get("meaning_zh", [])[:2]),
        "learning_mode": row.get("learning_mode"),
        "scene_tags": row.get("scene_tags", []),
    }


def _scene_unit_words(unit: dict, include_support_words: bool) -> list[str]:
    words = list(unit.get("core_words", []))
    if include_support_words:
        for word in unit.get("support_words", []):
            if word not in words:
                words.append(word)
    return words


def _build_scene_entries(selected_units: list[dict], word_map: dict, include_support_words: bool) -> tuple[list[dict], list[str]]:
    entries = []
    introduced = []
    for unit in selected_units:
        core_items = [_word_item(word_map[word]) for word in unit.get("core_words", []) if word in word_map]
        support_words = unit.get("support_words", []) if include_support_words else []
        support_items = [_word_item(word_map[word]) for word in support_words if word in word_map]
        entries.append(
            {
                "unit_id": unit["unit_id"],
                "scene_id": unit["scene_id"],
                "title": unit["title"],
                "memory_chain": unit["memory_chain"],
                "difficulty": unit.get("difficulty", 3),
                "core_words": core_items,
                "support_words": support_items,
            }
        )
        for word in _scene_unit_words(unit, include_support_words):
            if word in word_map and word not in introduced:
                introduced.append(word)
    return entries, introduced


def _build_contrast_entries(pairs: list[list[str]], word_map: dict) -> tuple[list[dict], list[str]]:
    entries = []
    introduced = []
    for pair in pairs:
        words = [word for word in pair if word in word_map]
        if len(words) != 2:
            continue
        entries.append(
            {
                "pair_id": canonical_pair(words),
                "words": [_word_item(word_map[word]) for word in words],
            }
        )
        for word in words:
            if word not in introduced:
                introduced.append(word)
    return entries, introduced


def _select_review_words(state: dict, plan_date: date, word_map: dict, offsets: list[int], limit: int) -> list[dict]:
    review_words = []
    plans_by_date = state.get("plans_by_date", {})
    for offset in offsets:
        target = (plan_date - timedelta(days=offset)).isoformat()
        entry = plans_by_date.get(target)
        if not entry:
            continue
        for word in entry.get("new_words", []):
            if word in word_map and word not in review_words:
                review_words.append(word)
            if len(review_words) >= limit:
                break
        if len(review_words) >= limit:
            break
    return [_word_item(word_map[word]) for word in review_words[:limit]]


def render_markdown(plan: dict) -> str:
    lines = [f"# 考研英语今日计划 · {plan['date']}", ""]
    progress = plan["progress"]
    lines.append(
        f"进度：已引入 {progress['introduced_after']} / {progress['study_total']} 个学习词，剩余 {progress['remaining_after']} 个。"
    )
    lines.append("")

    scene_units = plan["plan"].get("scene_units", [])
    if scene_units:
        lines.append("## 场景单元")
        lines.append("")
        for unit in scene_units:
            lines.append(f"### {unit['title']}")
            lines.append(unit["memory_chain"])
            lines.append("")
            lines.append("核心词：")
            for item in unit["core_words"]:
                lines.append(f"- {item['word']}: {item['meaning']}")
            if unit["support_words"]:
                lines.append("辅助词：")
                for item in unit["support_words"]:
                    lines.append(f"- {item['word']}: {item['meaning']}")
            lines.append("")

    contrast_pairs = plan["plan"].get("contrast_pairs", [])
    if contrast_pairs:
        lines.append("## 对比记忆")
        lines.append("")
        for pair in contrast_pairs:
            joined = " / ".join(item["word"] for item in pair["words"])
            lines.append(f"- {joined}")
            for item in pair["words"]:
                lines.append(f"  - {item['word']}: {item['meaning']}")
        lines.append("")

    extra_words = plan["plan"].get("extra_words", [])
    if extra_words:
        lines.append("## 补充新词")
        lines.append("")
        for item in extra_words:
            tag_text = f" [{item['learning_mode']}]" if item.get("learning_mode") else ""
            lines.append(f"- {item['word']}: {item['meaning']}{tag_text}")
        lines.append("")

    review_words = plan["plan"].get("review_words", [])
    if review_words:
        lines.append("## 今日复习")
        lines.append("")
        for item in review_words:
            lines.append(f"- {item['word']}: {item['meaning']}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def main() -> None:
    args = parse_args()
    plan_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    config = load_json(args.config)
    state = load_state(args.state)
    word_rows = read_jsonl(args.study_words)
    scene_units = read_jsonl(args.scene_units)
    contrast_pairs = load_json(args.contrast_pairs)

    word_map = {row["word_id"]: row for row in word_rows}
    if not args.force_rebuild and args.date in state.get("plans_by_date", {}):
        plan = state["plans_by_date"][args.date]["plan"]
    else:
        introduced_before = set(state.get("introduced_words", []))
        completed_scene_units = set(state.get("completed_scene_units", []))
        completed_contrast_pairs = set(state.get("completed_contrast_pairs", []))

        include_support_words = bool(config.get("include_scene_support_words", True))

        selected_scene_units = []
        for unit in sorted(scene_units, key=lambda item: item["unit_id"]):
            unit_words = _scene_unit_words(unit, include_support_words)
            if unit["unit_id"] in completed_scene_units:
                continue
            if not any(word not in introduced_before for word in unit_words):
                continue
            selected_scene_units.append(unit)
            if len(selected_scene_units) >= int(config.get("scene_units_per_day", 1)):
                break

        scene_entries, scene_introduced = _build_scene_entries(selected_scene_units, word_map, include_support_words)

        selected_pairs = []
        for pair in contrast_pairs:
            cleaned = [item.strip().lower() for item in pair if item]
            if len(cleaned) != 2 or not all(word in word_map for word in cleaned):
                continue
            pair_id = canonical_pair(cleaned)
            if pair_id in completed_contrast_pairs:
                continue
            if not any(word not in introduced_before for word in cleaned):
                continue
            selected_pairs.append(cleaned)
            if len(selected_pairs) >= int(config.get("contrast_pairs_per_day", 1)):
                break

        contrast_entries, contrast_introduced = _build_contrast_entries(selected_pairs, word_map)

        excluded_words = introduced_before | set(scene_introduced) | set(contrast_introduced)
        candidate_rows = [row for row in word_rows if row["word_id"] not in excluded_words]

        if config.get("prioritize_scene_words_in_extra", True):
            priority = {"scene": 0, "contrast": 1, "standard": 2}
            candidate_rows = sorted(
                candidate_rows,
                key=lambda row: (
                    priority.get(row.get("learning_mode"), 9),
                    int(row["source_rank"]) if row.get("source_rank") is not None else 10**9,
                    row["word_id"],
                ),
            )
        else:
            candidate_rows = _sort_rows(candidate_rows)

        extra_rows = candidate_rows[: int(config.get("extra_words_per_day", 8))]
        extra_entries = [_word_item(row) for row in extra_rows]
        extra_introduced = [row["word_id"] for row in extra_rows]

        review_entries = _select_review_words(
            state,
            plan_date,
            word_map,
            [int(item) for item in config.get("review_day_offsets", [1, 3, 7])],
            int(config.get("review_words_per_day", 6)),
        )

        new_words = []
        for bucket in (scene_introduced, contrast_introduced, extra_introduced):
            for word in bucket:
                if word not in new_words:
                    new_words.append(word)

        introduced_after = introduced_before | set(new_words)
        remaining_after = len(word_rows) - len(introduced_after)

        plan = {
            "date": args.date,
            "progress": {
                "study_total": len(word_rows),
                "introduced_before": len(introduced_before),
                "introduced_after": len(introduced_after),
                "remaining_after": remaining_after,
            },
            "plan": {
                "scene_units": scene_entries,
                "contrast_pairs": contrast_entries,
                "extra_words": extra_entries,
                "review_words": review_entries,
            },
        }

        if args.update_state:
            if not state.get("started_at"):
                state["started_at"] = args.date
            state.setdefault("plans_by_date", {})[args.date] = {
                "date": args.date,
                "scene_unit_ids": [item["unit_id"] for item in selected_scene_units],
                "contrast_pair_ids": [canonical_pair(pair) for pair in selected_pairs],
                "new_words": new_words,
                "review_words": [item["word"] for item in review_entries],
                "plan": deepcopy(plan),
            }
            state["introduced_words"] = sorted(introduced_after)
            state["completed_scene_units"] = sorted(completed_scene_units | {item["unit_id"] for item in selected_scene_units})
            state["completed_contrast_pairs"] = sorted(
                completed_contrast_pairs | {canonical_pair(pair) for pair in selected_pairs}
            )
            save_state(args.state, state)

    markdown = render_markdown(plan)

    ensure_parent(args.json_output)
    args.json_output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ensure_parent(args.markdown_output)
    args.markdown_output.write_text(markdown, encoding="utf-8")

    print(f"Wrote JSON plan to {args.json_output}")
    print(f"Wrote markdown plan to {args.markdown_output}")
    print(
        f"Progress: {plan['progress']['introduced_after']} / {plan['progress']['study_total']} introduced, {plan['progress']['remaining_after']} remaining"
    )


if __name__ == "__main__":
    main()
