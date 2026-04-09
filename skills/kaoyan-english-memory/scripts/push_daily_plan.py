import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "push_channels.json"
DEFAULT_MARKDOWN = ROOT / "kb" / "daily_plan_sample.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Push the rendered daily study plan to configured channels.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to push channel config.")
    parser.add_argument("--markdown-input", type=Path, default=DEFAULT_MARKDOWN, help="Path to markdown plan.")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without sending network requests.")
    return parser.parse_args()


def load_channels(path: Path) -> list[dict]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj.get("channels", [])


def read_markdown(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def slack_payload(text: str) -> dict:
    return {"text": text}


def wecom_payload(text: str) -> dict:
    return {"msgtype": "markdown", "markdown": {"content": text}}


def send_json(url: str, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        response.read()


def main() -> None:
    args = parse_args()
    channels = load_channels(args.config)
    markdown = read_markdown(args.markdown_input)

    sent = 0
    skipped = 0
    for channel in channels:
        if not channel.get("enabled", False):
            skipped += 1
            continue

        webhook_env = channel.get("webhook_env")
        webhook_url = os.environ.get(webhook_env or "")
        if not webhook_url:
            print(f"Skip {channel.get('channel_id')}: missing env {webhook_env}")
            skipped += 1
            continue

        channel_type = channel.get("type")
        if channel_type == "slack_webhook":
            payload = slack_payload(markdown)
        elif channel_type == "wecom_webhook":
            payload = wecom_payload(markdown)
        else:
            print(f"Skip {channel.get('channel_id')}: unsupported channel type {channel_type}")
            skipped += 1
            continue

        if args.dry_run:
            print(f"DRY RUN {channel.get('channel_id')} -> {channel_type}")
            sent += 1
            continue

        try:
            send_json(webhook_url, payload)
        except urllib.error.URLError as exc:
            raise SystemExit(f"Push failed for {channel.get('channel_id')}: {exc}") from exc
        print(f"Sent to {channel.get('channel_id')} ({channel_type})")
        sent += 1

    print(f"Push summary: sent={sent}, skipped={skipped}")


if __name__ == "__main__":
    main()
