import argparse
import csv
from pathlib import Path

from common import RAW_WORDS_PATH, ROOT, ensure_parent, load_raw_words


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize the raw vocabulary CSV.")
    parser.add_argument("--input", type=Path, default=RAW_WORDS_PATH, help="Path to the raw CSV file.")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "normalized" / "kaoyan_words.normalized.csv",
        help="Path to the normalized CSV file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = load_raw_words(args.input)
    ensure_parent(args.output)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["word", "pos", "pos_summary", "meaning", "meaning_zh", "example"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "word": row["word"],
                    "pos": row["pos"],
                    "pos_summary": "|".join(row["pos_summary"]),
                    "meaning": row["meaning"],
                    "meaning_zh": "|".join(row["meaning_zh"]),
                    "example": row["example"],
                }
            )
    print(f"Wrote {len(rows)} normalized rows to {args.output}")


if __name__ == "__main__":
    main()
