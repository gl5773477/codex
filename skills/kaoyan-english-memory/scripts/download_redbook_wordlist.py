import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

from common import ROOT, ensure_parent

SOURCE_URL = "https://raw.githubusercontent.com/3056810551/2027-kaoyan-english-redbook-json/main/words.json"
SOURCE_REPO = "3056810551/2027-kaoyan-english-redbook-json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download the raw redbook vocabulary JSON.")
    parser.add_argument("--source-url", default=SOURCE_URL, help="Source JSON URL.")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "raw" / "kaoyan_redbook_words.json",
        help="Where to store the raw redbook words JSON.",
    )
    parser.add_argument(
        "--metadata-output",
        type=Path,
        default=ROOT / "data" / "raw" / "kaoyan_redbook_words.metadata.json",
        help="Where to store the source metadata.",
    )
    return parser.parse_args()


def download_json(url: str):
    with urlopen(url) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return json.loads(response.read().decode(charset))


def main() -> None:
    args = parse_args()
    payload = download_json(args.source_url)
    if not isinstance(payload, list):
        raise ValueError("Unexpected redbook format: expected a top-level list.")

    ensure_parent(args.output)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    metadata = {
        "dataset": SOURCE_REPO,
        "source_url": args.source_url,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "row_count": len(payload),
        "data_shape": "list[page,index,word,meaning]",
        "notes": [
            "Repository README states the JSON was extracted from a circulated 2027 redbook PDF.",
            "Repository includes an MIT license file, but README also says the project is for learning exchange and not commercial use.",
            "Review source licensing and downstream usage before redistribution.",
        ],
    }
    ensure_parent(args.metadata_output)
    args.metadata_output.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Downloaded {len(payload)} redbook rows from {args.source_url}")
    print(f"Wrote raw JSON to {args.output}")
    print(f"Wrote metadata to {args.metadata_output}")


if __name__ == "__main__":
    main()
