import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh the kaoyan English skill workspace outputs.")
    parser.add_argument("--validate-raw", action="store_true", help="Validate raw CSV before rebuilding.")
    return parser.parse_args()


def run_step(command: list[str]) -> None:
    print(f"$ {' '.join(command)}")
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    args = parse_args()
    steps = []
    if args.validate_raw:
        steps.append(["python3", "scripts/validate_raw_words.py"])
    steps.extend(
        [
            ["python3", "scripts/build_words_jsonl.py"],
            ["python3", "scripts/split_learning_wordlists.py"],
            ["python3", "scripts/build_scene_units.py"],
            ["python3", "scripts/report_scene_coverage.py"],
            ["python3", "scripts/report_high_frequency_scene_memory.py"],
            ["python3", "scripts/build_ai_payload.py", "--output", "kb/sample_ai_payload.json"],
        ]
    )

    try:
        for step in steps:
            run_step(step)
    except subprocess.CalledProcessError as exc:
        print(f"Refresh failed on: {' '.join(exc.cmd)}", file=sys.stderr)
        raise SystemExit(exc.returncode) from exc

    print("Workspace refresh completed.")


if __name__ == "__main__":
    main()
