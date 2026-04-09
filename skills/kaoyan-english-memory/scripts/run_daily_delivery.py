import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the dated daily plan and optionally push it.")
    parser.add_argument("--date", required=True, help="Plan date in YYYY-MM-DD format.")
    parser.add_argument("--push", action="store_true", help="Push the rendered markdown after building the plan.")
    parser.add_argument("--dry-run-push", action="store_true", help="Dry-run channel delivery without network calls.")
    parser.add_argument("--force-rebuild", action="store_true", help="Rebuild the plan even if the date already exists.")
    return parser.parse_args()


def run_step(command: list[str]) -> None:
    print(f"$ {' '.join(command)}")
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    args = parse_args()
    build_cmd = ["python3", "scripts/build_daily_plan.py", "--date", args.date, "--update-state"]
    if args.force_rebuild:
        build_cmd.append("--force-rebuild")

    try:
        run_step(build_cmd)
        if args.push or args.dry_run_push:
            push_cmd = ["python3", "scripts/push_daily_plan.py"]
            if args.dry_run_push:
                push_cmd.append("--dry-run")
            run_step(push_cmd)
    except subprocess.CalledProcessError as exc:
        print(f"Daily delivery failed on: {' '.join(exc.cmd)}", file=sys.stderr)
        raise SystemExit(exc.returncode) from exc

    print("Daily delivery completed.")


if __name__ == "__main__":
    main()
