import argparse
import json
from pathlib import Path

from common import WORDS_OUTPUT_PATH, read_jsonl


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report likely basic-word candidates for manual review.")
    parser.add_argument("--words", type=Path, default=WORDS_OUTPUT_PATH, help="Path to words.jsonl.")
    parser.add_argument(
        "--rank-max",
        type=int,
        default=1200,
        help="Only inspect words with source_rank less than or equal to this value.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=80,
        help="How many candidate words to print.",
    )
    parser.add_argument("--json", action="store_true", help="Print the report as JSON.")
    return parser.parse_args()


def is_candidate(row: dict, rank_max: int) -> bool:
    rank = row.get("source_rank")
    word = row.get("word_id", "")
    if row.get("is_basic"):
        return False
    if not row.get("learning_enabled", True):
        return False
    if row.get("scene_tags"):
        return False
    if rank is None or rank > rank_max:
        return False
    if " " in word or "-" in word:
        return False
    if len(word) > 8:
        return False
    return True


def main() -> None:
    args = parse_args()
    rows = read_jsonl(args.words)
    candidates = [
        {
            "word_id": row["word_id"],
            "source_rank": row.get("source_rank"),
            "frequency": row.get("frequency"),
            "meaning_zh": row.get("meaning_zh", []),
        }
        for row in rows
        if is_candidate(row, args.rank_max)
    ]
    candidates.sort(key=lambda item: (item["source_rank"] or 10**9, item["word_id"]))
    report = {
        "candidate_count": len(candidates),
        "rank_max": args.rank_max,
        "candidates": candidates[: args.limit],
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
        return

    print(f"Candidate count: {report['candidate_count']}")
    print(f"Rank max: {report['rank_max']}")
    for item in report["candidates"]:
        print(f"- {item['source_rank']:>4} {item['word_id']}: {'；'.join(item['meaning_zh'])}")


if __name__ == "__main__":
    main()
