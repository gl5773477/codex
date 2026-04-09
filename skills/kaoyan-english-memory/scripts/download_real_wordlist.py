import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

from common import RAW_WORDS_PATH, ROOT, ensure_parent

SOURCE_URL = "https://raw.githubusercontent.com/exam-data/NETEMVocabulary/master/netem_full_list.json"
SOURCE_LICENSE = "CC BY-NC-SA 4.0"
SOURCE_DATASET_NAME = "exam-data/NETEMVocabulary"
SOURCE_ROOT_KEY = "5530考研词汇词频排序表"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download and convert a real kaoyan vocabulary list.")
    parser.add_argument("--source-url", default=SOURCE_URL, help="Source JSON URL.")
    parser.add_argument(
        "--source-output",
        type=Path,
        default=ROOT / "data" / "source" / "netem_full_list.json",
        help="Where to store the downloaded source JSON.",
    )
    parser.add_argument(
        "--metadata-output",
        type=Path,
        default=ROOT / "data" / "source" / "source_metadata.json",
        help="Where to store source metadata.",
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=RAW_WORDS_PATH,
        help="Where to store the converted CSV.",
    )
    return parser.parse_args()


def download_json(url: str) -> dict:
    with urlopen(url) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return json.loads(response.read().decode(charset))


def write_source_json(path: Path, payload: dict) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_metadata(path: Path, source_url: str, row_count: int) -> None:
    metadata = {
        "dataset": SOURCE_DATASET_NAME,
        "source_url": source_url,
        "license": SOURCE_LICENSE,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "row_count": row_count,
        "root_key": SOURCE_ROOT_KEY,
    }
    ensure_parent(path)
    path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def convert_to_rows(payload: dict) -> list:
    items = payload.get(SOURCE_ROOT_KEY)
    if not isinstance(items, list):
        raise ValueError(f"Unexpected source format: missing list under key {SOURCE_ROOT_KEY!r}")

    rows = []
    for item in items:
        word = str(item.get("单词", "")).strip()
        meaning = str(item.get("释义", "")).strip()
        if not word or not meaning:
            continue
        rows.append(
            {
                "word": word,
                "pos": "",
                "meaning": meaning,
                "example": "",
                "frequency": item.get("词频", ""),
                "source_rank": item.get("序号", ""),
                "other_spellings": item.get("其他拼写") or "",
                "source_dataset": SOURCE_DATASET_NAME,
            }
        )
    return rows


def write_csv(path: Path, rows: list) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "word",
                "pos",
                "meaning",
                "example",
                "frequency",
                "source_rank",
                "other_spellings",
                "source_dataset",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    payload = download_json(args.source_url)
    rows = convert_to_rows(payload)
    write_source_json(args.source_output, payload)
    write_metadata(args.metadata_output, args.source_url, len(rows))
    write_csv(args.csv_output, rows)
    print(f"Downloaded {len(rows)} rows from {args.source_url}")
    print(f"Wrote source JSON to {args.source_output}")
    print(f"Wrote CSV to {args.csv_output}")


if __name__ == "__main__":
    main()
