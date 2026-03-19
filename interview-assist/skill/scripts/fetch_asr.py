#!/usr/bin/env python3
"""
腾讯会议 ASR 转录拉取脚本（通过 HR 系统 API）
用法: python3 fetch_asr.py <interviewScheduleId> [sso_workspace]
输出 JSON: {"interviewASR": "...", "docTitle": "面试-xxx-2026-03-18", "status": "ok|empty|error"}
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
    raise RuntimeError(f"SSO 获取失败: {result.stderr.strip()}")


def fetch_asr(schedule_id: str, cookie: str) -> dict:
    """从 HR 系统拉取腾讯会议 ASR 转写数据"""
    url = (
        "https://hr.xiaohongshu.com/oasis/api/recruit/recruit/"
        f"interviewController/queryInterviewAsr/{schedule_id}"
    )
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9",
        "referer": "https://hr.xiaohongshu.com/workbench/interview-evaluation-list/all",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
        "cookie": cookie,
    }
    req = urllib.request.Request(url, method="GET", headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def fetch_interview_detail(schedule_id: str, cookie: str) -> dict:
    """获取面试基本信息（用于生成 docTitle）"""
    url = (
        "https://hr.xiaohongshu.com/oasis/api/recruit/recruit/"
        f"interviewController/queryInterviewDetail/{schedule_id}"
    )
    headers = {
        "accept": "application/json, text/plain, */*",
        "cookie": cookie,
        "referer": "https://hr.xiaohongshu.com/",
        "user-agent": "Mozilla/5.0",
    }
    req = urllib.request.Request(url, method="GET", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {}


def parse_asr_text(asr_data: dict) -> str:
    """将 ASR 数据解析为可读文本"""
    # 尝试常见字段结构
    data = asr_data.get("data") or {}

    # 结构一：列表形式 [{speaker, content, startTime}]
    asr_list = None
    for key in ["asrList", "asr_list", "list", "records", "content"]:
        if isinstance(data.get(key), list):
            asr_list = data[key]
            break
    if asr_list is None and isinstance(data, list):
        asr_list = data

    if asr_list:
        lines = []
        for item in asr_list:
            speaker = item.get("speaker") or item.get("speakerName") or item.get("name") or ""
            content = item.get("content") or item.get("text") or item.get("asr") or ""
            time_ms = item.get("startTime") or item.get("start_time") or 0
            try:
                time_str = str(int(time_ms) // 1000 // 60).zfill(2) + ":" + str((int(time_ms) // 1000) % 60).zfill(2)
            except Exception:
                time_str = ""
            if content:
                prefix = f"{speaker} {time_str}".strip()
                lines.append(f"{prefix}\n{content}" if prefix else content)
        return "\n\n".join(lines)

    # 结构二：纯文本
    for key in ["asrText", "asr_text", "text", "transcription"]:
        if isinstance(data.get(key), str) and data[key].strip():
            return data[key]

    # 结构三：整个 data 是字符串
    if isinstance(data, str) and data.strip():
        return data

    return ""


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "用法: python3 fetch_asr.py <interviewScheduleId> [sso_workspace]"}, ensure_ascii=False))
        sys.exit(1)

    schedule_id = sys.argv[1]
    workspace = sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser("~/.openclaw/workspace")

    try:
        cookie = get_cookie(workspace)

        # 拉取 ASR
        asr_resp = fetch_asr(schedule_id, cookie)

        # 调试：输出原始结构（stderr，不干扰 stdout JSON）
        print(f"[DEBUG] ASR raw keys: {list((asr_resp.get('data') or asr_resp).keys()) if isinstance((asr_resp.get('data') or asr_resp), dict) else type(asr_resp.get('data'))}", file=sys.stderr)

        asr_text = parse_asr_text(asr_resp)

        # 生成 docTitle（尝试获取候选人姓名和日期）
        detail = fetch_interview_detail(schedule_id, cookie)
        detail_data = detail.get("data") or {}
        talent_name = detail_data.get("italentName") or detail_data.get("talentName") or detail_data.get("name") or "候选人"
        date_str = datetime.now(tz=TZ).strftime("%Y-%m-%d")
        doc_title = f"面试-{talent_name}-{date_str}"

        if not asr_text:
            print(json.dumps({
                "status": "empty",
                "scheduleId": schedule_id,
                "docTitle": doc_title,
                "interviewASR": "",
                "rawResp": asr_resp,
                "message": "ASR 为空，面试可能未结束或转录尚未生成"
            }, ensure_ascii=False, indent=2))
        else:
            print(json.dumps({
                "status": "ok",
                "scheduleId": schedule_id,
                "docTitle": doc_title,
                "interviewASR": asr_text,
                "charCount": len(asr_text),
            }, ensure_ascii=False, indent=2))

    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
