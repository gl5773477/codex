#!/usr/bin/env python3
"""
面试日程获取脚本（面试官视角）
用法:
  python3 fetch_interviews.py [date] [sso_workspace]
  python3 fetch_interviews.py --range <start> <end> [sso_workspace]
  python3 fetch_interviews.py --this-week [sso_workspace]
  python3 fetch_interviews.py --next-week [sso_workspace]

  date: 日期字符串，如 2026-03-11，默认今天
  --range start end: 拉取指定日期区间（含两端）
  --this-week: 本周一到周日
  --next-week: 下周一到周日
  sso_workspace: SSO workspace 路径，默认 ~/.openclaw/workspace
输出: JSON 格式面试列表，含 interviewScheduleId
"""

import sys
import json
import subprocess
import os
import urllib.request
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=8))

def get_cookie(workspace: str) -> str:
    sso_script = "/app/skills/data-fe-common-sso/script/run-sso.sh"
    if not os.path.exists(sso_script):
        raise RuntimeError(f"SSO script not found: {sso_script}")
    result = subprocess.run([sso_script, workspace], capture_output=True, text=True)
    if result.returncode == 0:
        cookie = result.stdout.strip()
        if cookie:
            return cookie
    raise RuntimeError(f"SSO 获取失败: {result.stderr}")


def fetch_interview_list(cookie: str, date_str: str, page_size: int = 50) -> list:
    """从 HR 系统拉取面试官的面试日程列表"""
    url = (
        "https://hr.xiaohongshu.com/oasis/api/recruit/recruit/"
        "interviewController/queryInterviewItalentByPage"
    )
    payload = {
        "pageNum": 1,
        "pageSize": page_size,
        "interviewResult": "all",
        "time": [],
        "interviewBeginTime": f"{date_str} 00:00:00",
        "interviewEndTime": f"{date_str} 23:59:59",
        "talentName": "",
        "positionId": "",
        "evaluationResult": "",
        "arrangeMan": "",
        "recruitStatus": "in_recruitment",
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9",
        "content-type": "application/json;charset=UTF-8",
        "cookie": cookie,
        "origin": "https://hr.xiaohongshu.com",
        "referer": "https://hr.xiaohongshu.com/workbench/interview-evaluation-list/all",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    }
    req = urllib.request.Request(url, data=data, method="POST", headers=headers)
    with urllib.request.urlopen(req, timeout=15) as r:
        resp = json.loads(r.read())
    return resp


def extract_interviews(resp: dict) -> list:
    """从响应里提取面试条目"""
    data = resp.get("data", {})
    if isinstance(data, dict):
        items = data.get("list", data.get("records", data.get("items", [])))
    elif isinstance(data, list):
        items = data
    else:
        items = []
    return items


def date_range(start_str: str, end_str: str):
    """生成 start ~ end（含）的日期列表"""
    from datetime import date
    start = date.fromisoformat(start_str)
    end = date.fromisoformat(end_str)
    cur = start
    while cur <= end:
        yield cur.strftime("%Y-%m-%d")
        cur += timedelta(days=1)


def week_range(offset_weeks: int = 0):
    """返回 (本周一, 本周日)，offset_weeks=1 为下周，-1 为上周"""
    today = datetime.now(tz=TZ).date()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=offset_weeks)
    sunday = monday + timedelta(days=6)
    return monday.strftime("%Y-%m-%d"), sunday.strftime("%Y-%m-%d")


def parse_item(item: dict) -> dict:
    schedule_id = item.get("interviewScheduleId") or item.get("scheduleId") or item.get("id")
    talent_id = item.get("talentId")
    interview_id = item.get("interviewId")
    return {
        "interviewScheduleId": schedule_id,
        "talentId": talent_id,
        "interviewId": interview_id,
        "talentName": item.get("italentName") or item.get("talentName") or item.get("name"),
        "positionName": item.get("positionName") or item.get("position"),
        "interviewBeginTime": item.get("interviewBeginTime") or item.get("beginTime"),
        "interviewEndTime": item.get("interviewEndTime") or item.get("endTime"),
        "interviewRound": item.get("interviewStepCode") or item.get("interviewRound") or item.get("round"),
        "hrUrl": (
            f"https://hr.xiaohongshu.com/applicant-evaluation"
            f"?talentId={talent_id}"
            f"&interviewId={interview_id}"
            f"&interviewScheduleId={schedule_id}"
        ) if talent_id and interview_id else None,
    }


def main():
    args = sys.argv[1:]
    workspace = os.path.expanduser("~/.openclaw/workspace")
    dates = []

    if not args:
        dates = [datetime.now(tz=TZ).strftime("%Y-%m-%d")]
    elif args[0] == "--range" and len(args) >= 3:
        start, end = args[1], args[2]
        dates = list(date_range(start, end))
        if len(args) > 3:
            workspace = args[3]
    elif args[0] == "--this-week":
        start, end = week_range(0)
        dates = list(date_range(start, end))
        if len(args) > 1:
            workspace = args[1]
    elif args[0] == "--next-week":
        start, end = week_range(1)
        dates = list(date_range(start, end))
        if len(args) > 1:
            workspace = args[1]
    elif args[0] == "--week":
        # 本周 + 下一周（共14天）
        s1, e1 = week_range(0)
        s2, e2 = week_range(1)
        dates = list(date_range(s1, e2))
        if len(args) > 1:
            workspace = args[1]
    else:
        dates = [args[0]]
        if len(args) > 1:
            workspace = args[1]

    try:
        cookie = get_cookie(workspace)
        all_results = []

        for date_str in dates:
            resp = fetch_interview_list(cookie, date_str)
            items = extract_interviews(resp)
            for item in items:
                parsed = parse_item(item)
                parsed["_date"] = date_str
                all_results.append(parsed)

        # 按时间排序
        all_results.sort(key=lambda x: x.get("interviewBeginTime") or "")

        print(json.dumps({
            "dateRange": f"{dates[0]} ~ {dates[-1]}" if len(dates) > 1 else dates[0],
            "total": len(all_results),
            "interviews": all_results,
        }, ensure_ascii=False, indent=2))

    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
