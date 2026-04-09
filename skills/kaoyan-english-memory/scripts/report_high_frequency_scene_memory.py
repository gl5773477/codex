import argparse
import json
from collections import Counter
from pathlib import Path

from common import (
    ACTION_CHAINS_PATH,
    BASIC_WORDS_PATH,
    CONTRAST_PAIRS_PATH,
    CORE_HIGH_FREQUENCY_MIN_FREQUENCY,
    ROOT,
    SCENE_KEYWORDS_PATH,
    SCENES_PATH,
    clean_word,
    ensure_parent,
    infer_scene_tags,
    load_basic_words,
    load_json,
    load_raw_words,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assess whether the high-frequency list is suitable for scene-memory construction.")
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "data" / "raw" / "kaoyan_core_high_frequency_words.csv",
        help="Path to the high-frequency raw CSV.",
    )
    parser.add_argument("--scenes", type=Path, default=SCENES_PATH, help="Path to scenes.json.")
    parser.add_argument(
        "--scene-keywords",
        type=Path,
        default=SCENE_KEYWORDS_PATH,
        help="Path to scene_keywords.json.",
    )
    parser.add_argument(
        "--action-chains",
        type=Path,
        default=ACTION_CHAINS_PATH,
        help="Path to action_chains.json.",
    )
    parser.add_argument(
        "--contrast-pairs",
        type=Path,
        default=CONTRAST_PAIRS_PATH,
        help="Path to contrast_pairs.json.",
    )
    parser.add_argument(
        "--basic-words",
        type=Path,
        default=BASIC_WORDS_PATH,
        help="Path to basic_words.txt.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "kb" / "high_frequency_scene_memory_report.json",
        help="Where to store the JSON report.",
    )
    parser.add_argument("--json", action="store_true", help="Also print the report as JSON.")
    return parser.parse_args()


def evaluate_units(action_chains, available_learning_words):
    summary = []
    valid_units = 0
    complete_units = 0
    for chain in action_chains:
        core_words = [clean_word(word) for word in chain.get("core_words", []) if clean_word(word) in available_learning_words]
        support_words = [clean_word(word) for word in chain.get("support_words", []) if clean_word(word) in available_learning_words]
        item = {
            "scene_id": chain["scene_id"],
            "title": chain["title"],
            "available_core_words": core_words,
            "available_support_words": support_words[:5],
            "core_word_count": len(core_words),
            "is_valid_unit": len(core_words) >= 4,
            "is_complete_unit": len(core_words) == len(chain.get("core_words", [])),
        }
        if item["is_valid_unit"]:
            valid_units += 1
        if item["is_complete_unit"]:
            complete_units += 1
        summary.append(item)
    return summary, valid_units, complete_units


def assess(report):
    if report["learning_scene_coverage_ratio"] >= 0.25 and report["valid_unit_count"] >= 3:
        return "good_seed_for_scene_memory"
    if report["learning_scene_coverage_ratio"] >= 0.12 and report["valid_unit_count"] >= 2:
        return "usable_but_needs_more_scene_rules"
    return "not_ready_needs_rule_expansion"


def main() -> None:
    args = parse_args()
    rows = load_raw_words(args.input)
    scenes = load_json(args.scenes)
    scene_keywords = load_json(args.scene_keywords)
    action_chains = load_json(args.action_chains)
    contrast_pairs = load_json(args.contrast_pairs)
    basic_words = load_basic_words(args.basic_words)

    scene_counts = Counter()
    unmatched_learning = []
    matched_learning = 0
    matched_total = 0
    learning_total = 0
    available_learning_words = set()

    for row in rows:
        word = row["word"]
        is_basic = word in basic_words
        scene_tags = infer_scene_tags(word, row["meaning_zh"], scenes, action_chains, contrast_pairs, scene_keywords)

        if scene_tags:
            matched_total += 1
            for scene_id in scene_tags:
                scene_counts[scene_id] += 1

        if not is_basic:
            learning_total += 1
            available_learning_words.add(word)
            if scene_tags:
                matched_learning += 1
            else:
                unmatched_learning.append(
                    {
                        "word_id": word,
                        "meaning_zh": row["meaning_zh"],
                        "frequency": int(row["frequency"]) if row.get("frequency") else None,
                        "source_rank": int(row["source_rank"]) if row.get("source_rank") else None,
                    }
                )

    unit_summary, valid_units, complete_units = evaluate_units(action_chains, available_learning_words)

    report = {
        "input_file": str(args.input),
        "high_frequency_threshold": CORE_HIGH_FREQUENCY_MIN_FREQUENCY,
        "total_words": len(rows),
        "basic_words": len(rows) - learning_total,
        "learning_words": learning_total,
        "matched_total_words": matched_total,
        "matched_learning_words": matched_learning,
        "learning_scene_coverage_ratio": round((matched_learning / learning_total), 4) if learning_total else 0.0,
        "scene_counts": dict(scene_counts),
        "valid_unit_count": valid_units,
        "complete_unit_count": complete_units,
        "unit_summary": unit_summary,
        "learning_unmatched_samples": unmatched_learning[:30],
    }
    report["assessment"] = assess(report)

    ensure_parent(args.output)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote high-frequency scene-memory report to {args.output}")
    print(f"Assessment: {report['assessment']}")
    print(f"Learning coverage ratio: {report['learning_scene_coverage_ratio']:.2%}")
    print(f"Valid units: {report['valid_unit_count']}")
    print(f"Complete units: {report['complete_unit_count']}")

    if args.json:
        print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
