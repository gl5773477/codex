#!/usr/bin/env python3
"""
候选人简历信息获取脚本
用法: python3 fetch_candidate_info.py <interviewId> [sso_workspace] [--out-dir DIR]
输出: JSON格式候选人背景信息，含学历、毕业状态、工作年限、resume_pdf_path、resume_md_path
--out-dir: 指定输出目录，自动下载 resume.pdf 并提取为 resume.md（弱依赖 pymupdf）
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


def fetch_resume_info(interview_id: str, cookie: str) -> dict:
    url = (
        "https://hr.xiaohongshu.com/oasis/api/recruit/recruit/"
        f"applicantController/queryResumeInfoByInterviewId/{interview_id}"
    )
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9",
        "referer": "https://hr.xiaohongshu.com/applicant-evaluation",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
        "cookie": cookie,
    }
    req = urllib.request.Request(url, method="GET", headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode("utf-8")
    result = json.loads(body)
    if result.get("success") or result.get("code") == 0:
        return result.get("data") or {}
    raise RuntimeError(f"API 返回异常: {result}")


def parse_graduation_status(data: dict) -> dict:
    """
    解析毕业状态：
    - 取 resumeEducationInfo 最高学历条目的 endDate / toPresent
    - 对比今天判断是否已毕业，以及毕业了多少年
    """
    edu_list = data.get("resumeEducationInfo") or []
    graduation_date_str = data.get("graduationDate")  # 顶层字段，格式 "2028-06"

    # 优先用教育列表里最高学历的结束时间
    highest_edu = None
    for edu in edu_list:
        if not highest_edu:
            highest_edu = edu
        # 简单按 degree 排序：博士 > 硕士 > 本科
        degree_rank = {"博士研究生": 4, "硕士研究生": 3, "本科": 2, "大专": 1}
        if degree_rank.get(edu.get("degree", ""), 0) > degree_rank.get(highest_edu.get("degree", ""), 0):
            highest_edu = edu

    end_date_str = None
    to_present = False
    if highest_edu:
        end_date_str = highest_edu.get("endDate")  # 格式 "2028-06" 或 None
        to_present = highest_edu.get("toPresent", False)
    if not end_date_str:
        end_date_str = graduation_date_str

    now = datetime.now(tz=TZ)

    graduated = False
    years_since_graduation = None
    graduation_year_month = None

    if to_present:
        # 学历至今 = 在读
        graduated = False
    elif end_date_str:
        graduation_year_month = end_date_str  # e.g. "2028-06"
        try:
            # 只有年月，取当月1日做对比
            parts = end_date_str.split("-")
            grad_dt = datetime(int(parts[0]), int(parts[1]), 1, tzinfo=TZ)
            if grad_dt <= now:
                graduated = True
                delta_months = (now.year - grad_dt.year) * 12 + (now.month - grad_dt.month)
                years_since_graduation = round(delta_months / 12, 1)
            else:
                graduated = False
        except Exception:
            pass

    return {
        "graduated": graduated,
        "graduation_year_month": graduation_year_month,
        "years_since_graduation": years_since_graduation,
        "to_present": to_present,
    }


def build_background_summary(data: dict, grad_status: dict) -> str:
    """
    生成自然语言的候选人背景描述，供注入 prompt 使用
    """
    name = data.get("name") or "候选人"
    age = data.get("age")
    work_years = data.get("workYears")
    highest_education = data.get("highestEducation") or ""
    school = data.get("highestEducationCollege") or ""
    major = data.get("highestEducationMajor") or ""
    recent_company = data.get("recentCompany") or ""
    recent_job = data.get("recentJob") or ""

    edu_list = data.get("resumeEducationInfo") or []
    edu_desc = ""
    if edu_list:
        edu = edu_list[0]
        start = edu.get("startDate", "")
        end = edu.get("endDate", "")
        to_present = edu.get("toPresent", False)
        end_display = "至今（在读）" if to_present else (end or "未知")
        real_school = edu.get("city") or edu.get("schoolName") or school  # city 字段存的是完整校名
        edu_desc = f"{real_school}，{edu.get('degree', highest_education)}，{edu.get('major', major)}，{start} ~ {end_display}"

    # 毕业状态描述
    if not grad_status["graduated"]:
        if grad_status["graduation_year_month"]:
            grad_desc = f"在读（预计 {grad_status['graduation_year_month']} 毕业）"
        else:
            grad_desc = "在读"
    else:
        yrs = grad_status["years_since_graduation"]
        grad_desc = f"已毕业约 {yrs} 年（{grad_status['graduation_year_month']}）"

    lines = [
        f"候选人基本背景：",
        f"- 姓名：{name}，年龄：{age} 岁",
        f"- 最高学历：{highest_education}，{edu_desc}" if edu_desc else f"- 最高学历：{highest_education}，{school} {major}",
        f"- 毕业状态：{grad_desc}",
        f"- 工作年限：{work_years} 年（读博前）" if work_years else "",
        f"- 最近经历：{recent_company} / {recent_job}" if recent_company else "",
    ]
    return "\n".join(l for l in lines if l)


def download_pdf(pdf_url: str, out_path: str) -> bool:
    """下载简历 PDF 到指定路径，返回是否成功"""
    try:
        req = urllib.request.Request(pdf_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            with open(out_path, "wb") as f:
                f.write(resp.read())
        return True
    except Exception as e:
        sys.stderr.write(f"⚠️  PDF 下载失败: {e}\n")
        return False


def extract_pdf_to_md(pdf_path: str, out_dir: str) -> str | None:
    """
    用 pymupdf skill 提取 PDF 为 markdown，返回 md 文件路径。
    弱依赖：pymupdf 不可用时返回 None，不抛异常。
    """
    try:
        import fitz  # noqa: F401 — 仅用于检测是否安装
    except ImportError:
        sys.stderr.write("⚠️  pymupdf 未安装，跳过 PDF 提取（pip install pymupdf）\n")
        return None

    # 找 pymupdf skill 脚本
    skill_script = os.path.expanduser(
        "~/.openclaw/workspace/skills/pymupdf-pdf-parser-clawdbot-skill/scripts/pymupdf_parse.py"
    )
    if not os.path.exists(skill_script):
        skill_script = "/app/skills/pymupdf-pdf-parser-clawdbot-skill/scripts/pymupdf_parse.py"
    if not os.path.exists(skill_script):
        sys.stderr.write("⚠️  pymupdf skill 脚本未找到，跳过 PDF 提取\n")
        return None

    tmp_outroot = os.path.join(out_dir, "_pdf_tmp")
    result = subprocess.run(
        ["python3", skill_script, pdf_path, "--format", "md", "--outroot", tmp_outroot],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        sys.stderr.write(f"⚠️  PDF 提取失败: {result.stderr}\n")
        return None

    # pymupdf 输出在 tmp_outroot/<pdf_basename>/output.md
    pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]
    extracted_md = os.path.join(tmp_outroot, pdf_basename, "output.md")
    if not os.path.exists(extracted_md):
        sys.stderr.write(f"⚠️  PDF 提取输出不存在: {extracted_md}\n")
        return None

    # 移动到目标目录
    dest_md = os.path.join(out_dir, "resume.md")
    import shutil
    shutil.copy2(extracted_md, dest_md)
    shutil.rmtree(tmp_outroot, ignore_errors=True)
    return dest_md


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "用法: python3 fetch_candidate_info.py <interviewId> [sso_workspace] [--out-dir DIR]"}))
        sys.exit(1)

    interview_id = sys.argv[1]
    workspace = os.path.expanduser("~/.openclaw/workspace")
    out_dir = None

    # 解析参数
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--out-dir" and i + 1 < len(sys.argv):
            out_dir = sys.argv[i + 1]
            i += 2
        else:
            workspace = sys.argv[i]
            i += 1

    try:
        cookie = get_cookie(workspace)
        data = fetch_resume_info(interview_id, cookie)
        grad_status = parse_graduation_status(data)
        background_summary = build_background_summary(data, grad_status)

        pdf_url = data.get("resumeUrl") or data.get("previewResumeUrl")
        resume_pdf_path = None
        resume_md_path = None

        # 若指定了 out_dir，自动下载 PDF + 提取 MD
        if out_dir and pdf_url:
            os.makedirs(out_dir, exist_ok=True)
            resume_pdf_path = os.path.join(out_dir, "resume.pdf")
            if download_pdf(pdf_url, resume_pdf_path):
                sys.stderr.write(f"✅ resume.pdf 已下载 ({os.path.getsize(resume_pdf_path)//1024} KB)\n")
                resume_md_path = extract_pdf_to_md(resume_pdf_path, out_dir)
                if resume_md_path:
                    sys.stderr.write(f"✅ resume.md 已提取\n")
            else:
                resume_pdf_path = None

        # 写 candidate_info.md（若有 out_dir）
        if out_dir:
            info_path = os.path.join(out_dir, "candidate_info.md")
            with open(info_path, "w", encoding="utf-8") as f:
                f.write(f"# 候选人背景 · {data.get('name', '?')}\n\n")
                f.write(background_summary + "\n\n")
                if resume_pdf_path:
                    f.write(f"- resume.pdf: {resume_pdf_path}\n")
                if resume_md_path:
                    f.write(f"- resume.md: {resume_md_path}\n")

        print(json.dumps({
            "name": data.get("name"),
            "age": data.get("age"),
            "highestEducation": data.get("highestEducation"),
            "school": data.get("highestEducationCollege"),
            "major": data.get("highestEducationMajor"),
            "graduated": grad_status["graduated"],
            "graduationYearMonth": grad_status["graduation_year_month"],
            "yearsSinceGraduation": grad_status["years_since_graduation"],
            "workYears": data.get("workYears"),
            "recentCompany": data.get("recentCompany"),
            "recentJob": data.get("recentJob"),
            "resumePdfUrl": pdf_url,
            "resumePdfPath": resume_pdf_path,
            "resumeMdPath": resume_md_path,
            "backgroundSummary": background_summary,
        }, ensure_ascii=False, indent=2))

    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
