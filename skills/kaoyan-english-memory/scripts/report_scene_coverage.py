import argparse
import json
from collections import Counter
from pathlib import Path

from common import SCENES_PATH, WORDS_OUTPUT_PATH, read_jsonl


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report scene coverage for kb/words.jsonl.")
    parser.add_argument("--words", type=Path, default=WORDS_OUTPUT_PATH, help="Path to words.jsonl.")
    parser.add_argument("--scenes", type=Path, default=SCENES_PATH, help="Path to scenes.json.")
    parser.add_argument(
        "--limit-unmatched",
        type=int,
        default=20,
        help="How many unmatched words to print.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the report as JSON.",
    )
    return parser.parse_args()


def build_report(words_path: Path, scenes_path: Path, limit_unmatched: int) -> dict:
    words = read_jsonl(words_path)
    scenes = json.loads(scenes_path.read_text(encoding="utf-8"))

    scene_counts = Counter()
    unmatched = []
    study_scene_counts = Counter()
    study_unmatched = []
    study_total = 0

    for row in words:
        scene_tags = row.get("scene_tags", [])
        if scene_tags:
            for scene_id in scene_tags:
                scene_counts[scene_id] += 1
        else:
            unmatched.append(
                {
                    "word_id": row["word_id"],
                    "meaning_zh": row.get("meaning_zh", []),
                }
            )

        if row.get("learning_enabled", True):
            study_total += 1
            if scene_tags:
                for scene_id in scene_tags:
                    study_scene_counts[scene_id] += 1
            else:
                study_unmatched.append(
                    {
                        "word_id": row["word_id"],
                        "meaning_zh": row.get("meaning_zh", []),
                    }
                )

    total_words = len(words)
    matched_words = total_words - len(unmatched)
    coverage_ratio = round((matched_words / total_words), 4) if total_words else 0.0
    study_matched_words = study_total - len(study_unmatched)
    study_coverage_ratio = round((study_matched_words / study_total), 4) if study_total else 0.0

    scene_lookup = {item["scene_id"]: item["name"] for item in scenes}
    scene_summary = []
    study_scene_summary = []
    for item in scenes:
        scene_id = item["scene_id"]
        scene_summary.append(
            {
                "scene_id": scene_id,
                "scene_name": scene_lookup[scene_id],
                "word_count": scene_counts.get(scene_id, 0),
            }
        )
        study_scene_summary.append(
            {
                "scene_id": scene_id,
                "scene_name": scene_lookup[scene_id],
                "word_count": study_scene_counts.get(scene_id, 0),
            }
        )

    return {
        "total_words": total_words,
        "matched_words": matched_words,
        "unmatched_words": len(unmatched),
        "coverage_ratio": coverage_ratio,
        "scene_summary": scene_summary,
        "unmatched_samples": unmatched[:limit_unmatched],
        "study_total_words": study_total,
        "study_matched_words": study_matched_words,
        "study_unmatched_words": len(study_unmatched),
        "study_coverage_ratio": study_coverage_ratio,
        "study_scene_summary": study_scene_summary,
        "study_unmatched_samples": study_unmatched[:limit_unmatched],
    }


def main() -> None:
    args = parse_args()
    report = build_report(args.words, args.scenes, args.limit_unmatched)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
        return

    print(f"Total words: {report['total_words']}")
    print(f"Matched words: {report['matched_words']}")
    print(f"Unmatched words: {report['unmatched_words']}")
    print(f"Coverage ratio: {report['coverage_ratio']:.2%}")
    print("")
    print("Scene counts:")
    for item in report["scene_summary"]:
        print(f"- {item['scene_id']}: {item['word_count']}")

    if report["unmatched_samples"]:
        print("")
        print("Unmatched samples:")
        for item in report["unmatched_samples"]:
            print(f"- {item['word_id']}: {'；'.join(item['meaning_zh'])}")

    print("")
    print("Learning-enabled coverage:")
    print(f"Study words: {report['study_total_words']}")
    print(f"Matched study words: {report['study_matched_words']}")
    print(f"Unmatched study words: {report['study_unmatched_words']}")
    print(f"Study coverage ratio: {report['study_coverage_ratio']:.2%}")
    print("")
    print("Study scene counts:")
    for item in report["study_scene_summary"]:
        print(f"- {item['scene_id']}: {item['word_count']}")

    if report["study_unmatched_samples"]:
        print("")
        print("Study unmatched samples:")
        for item in report["study_unmatched_samples"]:
            print(f"- {item['word_id']}: {'；'.join(item['meaning_zh'])}")


if __name__ == "__main__":
    main()
