import argparse
import json
from pathlib import Path

from common import (
    BASIC_WORDS_OUTPUT_PATH,
    CONTRAST_WORDS_OUTPUT_PATH,
    LEARNING_ROUTE_REPORT_OUTPUT_PATH,
    SCENE_WORDS_OUTPUT_PATH,
    STANDARD_WORDS_OUTPUT_PATH,
    STUDY_WORDS_OUTPUT_PATH,
    WORDS_OUTPUT_PATH,
    ensure_parent,
    read_jsonl,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Split words.jsonl into lightweight learning routes.")
    parser.add_argument("--words", type=Path, default=WORDS_OUTPUT_PATH, help="Path to words.jsonl.")
    parser.add_argument("--study-output", type=Path, default=STUDY_WORDS_OUTPUT_PATH, help="Path to study_words.jsonl.")
    parser.add_argument("--basic-output", type=Path, default=BASIC_WORDS_OUTPUT_PATH, help="Path to basic_words.jsonl.")
    parser.add_argument("--scene-output", type=Path, default=SCENE_WORDS_OUTPUT_PATH, help="Path to scene_words.jsonl.")
    parser.add_argument(
        "--contrast-output",
        type=Path,
        default=CONTRAST_WORDS_OUTPUT_PATH,
        help="Path to contrast_words.jsonl.",
    )
    parser.add_argument(
        "--standard-output",
        type=Path,
        default=STANDARD_WORDS_OUTPUT_PATH,
        help="Path to standard_words.jsonl.",
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=LEARNING_ROUTE_REPORT_OUTPUT_PATH,
        help="Path to the learning route summary JSON.",
    )
    return parser.parse_args()


def _sample(rows, limit=12):
    return [
        {
            "word_id": row["word_id"],
            "meaning_zh": row.get("meaning_zh", [])[:2],
            "scene_tags": row.get("scene_tags", []),
            "contrast_partners": row.get("contrast_partners", []),
            "source_rank": row.get("source_rank"),
        }
        for row in rows[:limit]
    ]


def main() -> None:
    args = parse_args()
    rows = read_jsonl(args.words)

    basic_rows = [row for row in rows if row.get("learning_mode") == "basic"]
    contrast_rows = [row for row in rows if row.get("learning_mode") == "contrast"]
    scene_rows = [row for row in rows if row.get("learning_mode") == "scene"]
    standard_rows = [row for row in rows if row.get("learning_mode") == "standard"]
    study_rows = [row for row in rows if row.get("learning_enabled", True)]

    write_jsonl(args.basic_output, basic_rows)
    write_jsonl(args.study_output, study_rows)
    write_jsonl(args.scene_output, scene_rows)
    write_jsonl(args.contrast_output, contrast_rows)
    write_jsonl(args.standard_output, standard_rows)

    report = {
        "total_words": len(rows),
        "route_counts": {
            "basic": len(basic_rows),
            "scene": len(scene_rows),
            "contrast": len(contrast_rows),
            "standard": len(standard_rows),
            "study_total": len(study_rows),
        },
        "route_samples": {
            "basic": _sample(basic_rows),
            "scene": _sample(scene_rows),
            "contrast": _sample(contrast_rows),
            "standard": _sample(standard_rows),
        },
    }
    ensure_parent(args.report_output)
    args.report_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {len(basic_rows)} basic rows to {args.basic_output}")
    print(f"Wrote {len(study_rows)} study rows to {args.study_output}")
    print(f"Wrote {len(scene_rows)} scene rows to {args.scene_output}")
    print(f"Wrote {len(contrast_rows)} contrast rows to {args.contrast_output}")
    print(f"Wrote {len(standard_rows)} standard rows to {args.standard_output}")
    print(f"Wrote learning route report to {args.report_output}")


if __name__ == "__main__":
    main()
