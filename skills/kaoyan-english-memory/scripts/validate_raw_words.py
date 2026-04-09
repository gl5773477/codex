import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from common import RAW_WORDS_PATH, clean_word


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the raw vocabulary CSV.")
    parser.add_argument("--input", type=Path, default=RAW_WORDS_PATH, help="Path to the raw CSV file.")
    parser.add_argument("--json", action="store_true", help="Print the report as JSON.")
    return parser.parse_args()


def build_report(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("CSV file is missing a header row.")

        headers = set(reader.fieldnames)
        required = {"word", "meaning"}
        missing_required_columns = sorted(required - headers)

        rows = list(reader)

    normalized_words = [clean_word(row.get("word", "")) for row in rows]
    non_empty_words = [word for word in normalized_words if word]
    counts = Counter(non_empty_words)

    missing_word_rows = 0
    missing_meaning_rows = 0
    missing_pos_rows = 0
    missing_example_rows = 0
    usable_rows = 0

    for row in rows:
        word = clean_word(row.get("word", ""))
        meaning = (row.get("meaning") or "").strip()
        pos = (row.get("pos") or "").strip()
        example = (row.get("example") or "").strip()

        if not word:
            missing_word_rows += 1
        if not meaning:
            missing_meaning_rows += 1
        if not pos:
            missing_pos_rows += 1
        if not example:
            missing_example_rows += 1
        if word and meaning:
            usable_rows += 1

    duplicate_words = sorted([word for word, count in counts.items() if count > 1])

    return {
        "file": str(path),
        "total_rows": len(rows),
        "missing_required_columns": missing_required_columns,
        "missing_word_rows": missing_word_rows,
        "missing_meaning_rows": missing_meaning_rows,
        "missing_pos_rows": missing_pos_rows,
        "missing_example_rows": missing_example_rows,
        "usable_rows": usable_rows,
        "duplicate_word_count": len(duplicate_words),
        "duplicate_word_samples": duplicate_words[:20],
    }


def main() -> None:
    args = parse_args()
    report = build_report(args.input)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
        return

    print(f"File: {report['file']}")
    print(f"Total rows: {report['total_rows']}")
    print(f"Usable rows: {report['usable_rows']}")
    print(f"Missing required columns: {report['missing_required_columns'] or '[]'}")
    print(f"Rows missing word: {report['missing_word_rows']}")
    print(f"Rows missing meaning: {report['missing_meaning_rows']}")
    print(f"Rows missing pos: {report['missing_pos_rows']}")
    print(f"Rows missing example: {report['missing_example_rows']}")
    print(f"Duplicate word count: {report['duplicate_word_count']}")
    if report["duplicate_word_samples"]:
        print("Duplicate word samples:")
        for word in report["duplicate_word_samples"]:
            print(f"- {word}")


if __name__ == "__main__":
    main()
