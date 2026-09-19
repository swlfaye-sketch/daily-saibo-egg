# -*- coding: utf-8 -*-
"""赛博鸡蛋 · 甲路：抓取「永久免费层」硬数据。

两条信源：
  1. mnfst/awesome-free-llm-apis —— 汇总仓库（供应商 / 免费说明 / Base URL / 模型表 / 限额）
  2. OpenRouter 模型 API —— 实时零价模型（pricing.prompt == 0 且 completion == 0）

输出：JSON（结构化）+ Markdown（人读）
用法：python fetch_tiers.py [输出目录]
"""
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

REPO = "mnfst/awesome-free-llm-apis"
RAW = f"https://raw.githubusercontent.com/{REPO}/main/README.md"
API_REPO = f"https://api.github.com/repos/{REPO}"


def fetch(url, hdr=None, timeout=30):
    h = {"User-Agent": UA, "Accept": "*/*"}
    if hdr:
        h.update(hdr)
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return -1, str(e).encode()


# ---------- 一、汇总仓库 ----------
def parse_repo(text):
    """解析 README：按 ## 分大节，按 ### 分供应商。"""
    lines = text.splitlines()
    sections, cur_sec, cur_prov = [], None, None

    for ln in lines:
        if ln.startswith("## "):
            cur_sec = {"section": ln[3:].strip(), "providers": []}
            sections.append(cur_sec)
            cur_prov = None
            continue
        if ln.startswith("### ") and cur_sec is not None:
            raw = ln[4:].strip()
            m = re.match(r"\[(.+?)\]\((.+?)\)\s*(.*)", raw)
            name, link, flag = (m.group(1), m.group(2), m.group(3).strip()) if m else (raw, "", "")
            cur_prov = {"name": name, "link": link, "flag": flag,
                        "desc": "", "base_url": "", "models": []}
            cur_sec["providers"].append(cur_prov)
            continue
        if cur_prov is None:
            continue
        s = ln.strip()
        if not s:
            continue
        if s.startswith("Base URL:"):
            cur_prov["base_url"] = s.replace("Base URL:", "").strip().strip("`")
            continue
        if s.startswith("|"):
            cells = [c.strip().strip("`") for c in s.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue
            if cells and cells[0].lower() in ("model name", "model"):
                continue
            if len(cells) >= 5:
                cur_prov["models"].append({
                    "model": cells[0], "context": cells[1], "max_output": cells[2],
                    "modality": cells[3], "rate_limit": cells[4]})
            continue
        if not cur_prov["desc"] and not s.startswith("<") and not s.startswith("["):
            cur_prov["desc"] = s

    keep = [s for s in sections if s["providers"]]
    return keep


# ---------- 二、OpenRouter 实时零价模型 ----------
def openrouter_free():
    st, raw = fetch("https://openrouter.ai/api/v1/models")
    if st != 200:
        return {"ok": False, "status": st, "models": []}
    js = json.loads(raw.decode("utf-8", "replace"))
    out = []
    for m in js.get("data", []):
        p = m.get("pricing", {}) or {}
        try:
            if float(p.get("prompt", "1") or 1) == 0 and float(p.get("completion", "1") or 1) == 0:
                out.append({"id": m.get("id"), "name": m.get("name"),
                            "context": m.get("context_length"),
                            "created": m.get("created")})
        except Exception:
            pass
    out.sort(key=lambda x: -(x.get("created") or 0))
    return {"ok": True, "status": st, "total_models": len(js.get("data", [])), "models": out}


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(outdir, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    result = {"date": today, "sources": {}}

    # 仓库
    st, raw = fetch(RAW)
    if st == 200:
        text = raw.decode("utf-8", "replace")
        secs = parse_repo(text)
        st2, raw2 = fetch(API_REPO)
        meta = {}
        if st2 == 200:
            j = json.loads(raw2.decode())
            meta = {"stars": j.get("stargazers_count"), "pushed_at": j.get("pushed_at")}
        result["sources"]["repo"] = {"ok": True, "repo": REPO, "meta": meta,
                                     "sections": secs}
    else:
        result["sources"]["repo"] = {"ok": False, "status": st, "repo": REPO}

    # OpenRouter
    result["sources"]["openrouter"] = openrouter_free()

    # 写 JSON
    jp = os.path.join(outdir, f"free_tier_{today}.json")
    with open(jp, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)

    # 写 Markdown
    md = [f"# 永久免费层抓取结果 · {today}", ""]
    r = result["sources"]["repo"]
    if r.get("ok"):
        m = r.get("meta", {})
        md.append(f"信源：`{REPO}`｜星数 {m.get('stars')}｜仓库最后推送 {m.get('pushed_at')}")
        md.append(f"抓取时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
        total = sum(len(s["providers"]) for s in r["sections"])
        md.append(f"供应商数：{total}")
        md.append("")
        for sec in r["sections"]:
            md.append(f"## {sec['section']}")
            md.append("")
            for p in sec["providers"]:
                md.append(f"### {p['name']} {p['flag']}")
                if p["desc"]:
                    md.append(f"- 说明：{p['desc']}")
                if p["base_url"]:
                    md.append(f"- Base URL：`{p['base_url']}`")
                if p["models"]:
                    md.append("")
                    md.append("| 模型 | 上下文 | 最大输出 | 模态 | 限额 |")
                    md.append("|---|---|---|---|---|")
                    for mm in p["models"]:
                        md.append(f"| `{mm['model']}` | {mm['context']} | {mm['max_output']} "
                                  f"| {mm['modality']} | {mm['rate_limit']} |")
                md.append("")
    else:
        md.append(f"⚠️ 仓库抓取失败：HTTP {r.get('status')}")

    o = result["sources"]["openrouter"]
    md.append("## OpenRouter 实时零价模型")
    md.append("")
    if o.get("ok"):
        md.append(f"模型总数 {o.get('total_models')}，其中免费 {len(o['models'])} 个"
                  f"（prompt=0 且 completion=0）")
        md.append("")
        md.append("| 模型 ID | 上下文 |")
        md.append("|---|---|")
        for mm in o["models"]:
            md.append(f"| `{mm['id']}` | {mm['context']} |")
    else:
        md.append(f"⚠️ OpenRouter 抓取失败：HTTP {o.get('status')}")
    md.append("")

    mp = os.path.join(outdir, f"free_tier_{today}.md")
    with open(mp, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    # 摘要
    print(f"[仓库] {'OK' if r.get('ok') else '失败'}", end="")
    if r.get("ok"):
        provs = sum(len(s["providers"]) for s in r["sections"])
        models = sum(len(p["models"]) for s in r["sections"] for p in s["providers"])
        print(f" | 大节 {len(r['sections'])} | 供应商 {provs} | 模型条目 {models}")
    else:
        print()
    print(f"[OpenRouter] {'OK' if o.get('ok') else '失败'}", end="")
    if o.get("ok"):
        print(f" | 总数 {o['total_models']} | 免费 {len(o['models'])}")
    else:
        print()
    print(f"\n✅ JSON: {jp}\n✅ MD  : {mp}")


if __name__ == "__main__":
    main()
