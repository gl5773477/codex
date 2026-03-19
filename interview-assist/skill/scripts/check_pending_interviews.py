#!/usr/bin/env python3
"""
检查待处理的面试（已结束但未生成总结）
用法: python3 check_pending_interviews.py [date] [sso_workspace]
输出: JSON 格式，列出需要处理的面试
"""

import sys
import os
import json
import subprocess
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=8))
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.expanduser("~/.openclaw/workspace/memory/interview-done.json")
FETCH_INTERVIEWS = os.path.join(SCRIPT_DIR, "fetch_interviews.py")


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"processed": {}}


def is_processed(state: dict, schedule_id: str) -> bool:
    return str(schedule_id) in state.get("processed", {})


def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now(tz=TZ).strftime("%Y-%m-%d")
    workspace = sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser("~/.openclaw/workspace")
    now_ts = datetime.now(tz=TZ)

    # 拉面试列表
    result = subprocess.run(
        ["python3", FETCH_INTERVIEWS, date_str, workspace],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(json.dumps({"error": f"fetch_interviews failed: {result.stderr}"}))
        sys.exit(1)

    data = json.loads(result.stdout)
    if "error" in data:
        print(json.dumps({"error": data["error"]}))
        sys.exit(1)

    state = load_state()
    pending = []

    for iv in data.get("interviews", []):
        sid = str(iv.get("interviewScheduleId", ""))
        if not sid:
            continue

        # 已处理过 → 跳过
        if is_processed(state, sid):
            continue

        # 检查是否已结束（结束时间 + 5分钟缓冲）
        end_str = iv.get("interviewEndTime", "")
        if end_str:
            try:
                end_dt = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ)
                if end_dt > now_ts - timedelta(minutes=5):
                    continue  # 未结束，跳过
            except ValueError:
                pass  # 时间格式解析失败，按已结束处理

        pending.append(iv)

    print(json.dumps({
        "date": date_str,
        "pending": pending,
        "total_pending": len(pending),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
