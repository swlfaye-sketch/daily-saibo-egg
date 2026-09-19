# -*- coding: utf-8 -*-
"""赛博鸡蛋 · 境外信源抓取（绕行通道版）。

背景：本机网络下境外约半数域名不可达（Google 全系、Mistral、HuggingFace、
xAI、Meta、Perplexity、Luma、Pika 直连失败；OpenAI 官网 403）。
本脚本只走**实测可达的绕行通道**，不硬试不通的域名：

  镜像站替代      HuggingFace → hf-mirror.com；GitHub raw 直连优先、失败再轮换加速镜像
  官方 RSS 直连   OpenAI News / DeepMind Blog / GitHub Blog（官网 403 但 RSS 通）
  免费额度专门站  freellm.net（30 家 provider，标注速率限制与是否需信用卡）
  价格对比站      llm-price.com（含「上架时间」，最能反映新模型与降价）
  零价模型接口    OpenRouter（免密钥，比汇总仓库实时）
  国内媒体搬运    量子位 / IT之家 / 爱范儿 / InfoQ / 开源中国（关键词过滤）

只用 Python 标准库，无第三方依赖。

用法：
    python fetch_overseas.py <输出目录>
"""
import hashlib
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# GitHub raw 加速镜像：实测可用者在前，逐个轮换，防单点失效
GH_MIRRORS = [
    "https://ghproxy.net/",
    "https://gh-proxy.com/",
    "https://gh.xxooo.cf/",
    "https://cdn.jsdelivr.net/gh/",   # jsDelivr 走另一套路径规则，单独处理
]

# RSSHub 公共实例：实测仅 4/29 路由可用，只作补充
RSSHUB = "https://rsshub.rssforever.com"

# 国内媒体 RSS —— 境外厂商消息的第一时间中文搬运渠道
MEDIA_FEEDS = [
    ("量子位", "https://www.qbitai.com/feed"),
    ("IT之家", "https://www.ithome.com/rss/"),
    ("爱范儿", "https://www.ifanr.com/feed"),
    ("InfoQ 中国", "https://www.infoq.cn/feed"),
    ("开源中国", "https://www.oschina.net/news/rss"),
    ("少数派", "https://sspai.com/feed"),
]

# 官方 RSS（官网不可达但 RSS 直连可用）
OFFICIAL_FEEDS = [
    ("OpenAI News", "https://openai.com/news/rss.xml"),
    ("Google DeepMind Blog", "https://deepmind.google/blog/rss.xml"),
    ("GitHub Blog", "https://github.blog/feed/"),
]

# 关键词：从国内媒体流里筛出「与免费额度相关」的条目
KEYWORDS = ["免费", "赠送", "额度", "降价", "价格", "开放", "试用",
            "free", "token", "积分", "订阅", "涨价", "限免", "开源"]


def fetch(url, timeout=25, retries=3):
    """返回 (状态码, bytes)。任何异常都返回 (-1, b"")，不抛出。

    带重试：境外站点偶发超时与 429/503 限流是常态——实测 freellm.net 首页
    在并发抓详情页时曾整体超时（HTTP -1），单次失败不足以判定信源失效。
    """
    last = (-1, b"")
    for i in range(retries):
        req = urllib.request.Request(url, headers={
            "User-Agent": UA, "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"})
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and i < retries - 1:
                time.sleep(1.5 * (i + 1))
                continue
            return e.code, b""
        except Exception:
            last = (-1, b"")
            if i < retries - 1:
                time.sleep(1.5 * (i + 1))
    return last


def strip_tags(s):
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"&nbsp;?", " ", s)
    s = re.sub(r"&amp;", "&", s)
    s = re.sub(r"&[a-z#0-9]{2,8};", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def rss_items(raw, limit=25):
    """解析 RSS/Atom，返回 [(标题, 链接, 日期)]。"""
    out = []
    try:
        root = ET.fromstring(raw)
    except Exception:
        # 兜底：正则拆 item
        txt = raw.decode("utf-8", "replace")
        blocks = re.findall(r"<item>(.*?)</item>", txt, re.S)[:limit]
        for b in blocks:
            t = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", b, re.S)
            l = re.search(r"<link>(.*?)</link>", b, re.S)
            d = re.search(r"<pubDate>(.*?)</pubDate>", b, re.S)
            out.append((strip_tags(t.group(1)) if t else "",
                        (l.group(1).strip() if l else ""),
                        (d.group(1).strip() if d else "")))
        return out

    ns = {"a": "http://www.w3.org/2005/Atom"}
    entries = root.findall(".//item") or root.findall(".//a:entry", ns)
    for e in entries[:limit]:
        t = e.find("title")
        if t is None:
            t = e.find("a:title", ns)
        link = e.find("link")
        if link is not None and link.get("href"):
            href = link.get("href")
        elif link is not None and link.text:
            href = link.text
        else:
            al = e.find("a:link", ns)
            href = al.get("href") if al is not None else ""
        d = e.find("pubDate") or e.find("a:updated", ns) or e.find("a:published", ns)
        out.append((strip_tags(t.text or "") if t is not None else "",
                    (href or "").strip(),
                    (d.text or "").strip() if d is not None else ""))
    return out


# ---------------------------------------------------------------- 各源抓取

# 需要抓详情页的重点境外供应商（详情页才含速率限制、免费模型清单等干货）
KEY_PROVIDERS = [
    "google-gemini", "openrouter", "groq", "mistral-ai", "xai", "grok-xai",
    "hugging-face", "github-models", "nvidia-nim", "cloudflare-workers-ai",
    "cohere", "sambanova", "nebius", "deepseek", "z-ai-zhipu-ai",
    "siliconflow", "modelscope", "alibaba-cloud-model-studio",
]


def fetch_provider_detail(slug):
    """抓单个 provider 详情页，抽出速率限制、免费模型数、是否需信用卡、最近更新。"""
    st, raw = fetch(f"https://freellm.net/providers/{slug}", timeout=25)
    if st != 200:
        return {"slug": slug, "ok": False, "note": f"HTTP {st}"}
    t = raw.decode("utf-8", "replace")
    txt = strip_tags(t)

    rates = list(dict.fromkeys(re.findall(r"([\d,]{1,7})\s*(RPM|RPD|RPH|TPM|RPS)", txt)))
    n_free = re.search(r"(\d+)\s*free models", txt, re.I)
    no_card = bool(re.search(r"(no credit card|credit card not required|"
                             r"no phone|not required)", txt, re.I))
    ctxs = list(dict.fromkeys(re.findall(r"(\d+(?:\.\d+)?[KM])\s*(?:context|tokens)", txt, re.I)))
    upd = re.search(r"Last Updated[^0-9]{0,40}(\d{4}-\d{2}-\d{2})", txt)
    if not upd:
        upd = re.search(r"Last Updated[^A-Za-z]{0,10}([A-Z][a-z]+ \d{1,2}, \d{4})", txt)

    # 模型 ID：页面上模型名带 flash/pro/lite/instruct 等后缀。
    # 须排除两类噪声：
    #   ① Astro 生成的 CSS 类名与 HTML 属性名（provider-shell / related-provider-row /
    #      data-provider-protocol-evidence 等），它们同样满足「带连字符的小写串」；
    #   ② 页脚「相关 provider」区块的通用模型名——这类无法靠前缀识别，
    #      改由 src_freellm 做**跨页共现过滤**剔除（见 filter_cross_page）。
    NOISE_PREFIX = ("provider-", "related-", "data-", "astro-", "hero-", "logo-")
    mids = re.findall(r"\b([a-z][a-z0-9]*[\-\.][a-z0-9][a-z0-9\-\.]{4,44})\b", t)
    mids = [m for m in dict.fromkeys(mids)
            if not m.startswith(NOISE_PREFIX)
            and re.search(r"(flash|pro|lite|mini|turbo|instruct|latest|preview|"
                          r"max|ultra|thinking|reason)", m)]
    rates_s = "／".join(f"{n} {u}" for n, u in rates[:4]) or "—"
    return {
        "slug": slug, "ok": True,
        "free_models": int(n_free.group(1)) if n_free else None,
        "rates": rates_s,
        "context": "／".join(ctxs[:2]) or "—",
        "no_credit_card": no_card,
        "updated": (upd.group(1) if upd else "—"),
        "model_ids": mids[:8],
        "url": f"https://freellm.net/providers/{slug}",
    }


def filter_cross_page(details, threshold=3):
    """跨页共现过滤：一个模型 ID 若出现在 ≥threshold 个不同 provider 页上，
    说明它是页脚「相关推荐」区块的通用内容，**不是该家的免费模型**，一律剔除。

    这一步是防「串行错位」的关键——不剔除就会把 A 家的模型写到 B 家名下，
    正是信源纪律里明令禁止的丙级信源毛病。
    """
    from collections import Counter
    cnt = Counter()
    for d in details:
        if d.get("ok"):
            for m in set(d.get("model_ids") or []):
                cnt[m] += 1
    noise = {m for m, c in cnt.items() if c >= threshold}
    for d in details:
        if d.get("ok"):
            d["model_ids"] = [m for m in (d.get("model_ids") or []) if m not in noise]
            d["model_ids_dropped"] = len(noise & set(d.get("model_ids") or []))
    return noise


def src_freellm():
    """freellm.net：免费额度专门站。

    首页只有跑马灯，**数据在逐家详情页**——故：首页取清单与准确名称，
    再并发抓重点 provider 详情页拿速率限制等干货。
    """
    st, raw = fetch("https://freellm.net/")
    if st != 200:
        return {"ok": False, "note": f"HTTP {st}", "providers": [], "details": []}
    t = raw.decode("utf-8", "replace")

    # 名称取 title 属性（比从邻近文本猜更准）
    pairs = re.findall(r'href="/providers/([a-z0-9\-]+)"\s+title="([^"]*)"', t)
    if not pairs:
        pairs = [(s, s.replace("-", " ").title())
                 for s in dict.fromkeys(re.findall(r'href="/providers/([a-z0-9\-]+)"', t))]
    seen, provs = set(), []
    for slug, name in pairs:
        if slug in seen:
            continue
        seen.add(slug)
        provs.append({"slug": slug, "name": (name or slug).strip(),
                      "url": f"https://freellm.net/providers/{slug}"})

    # 并发抓详情页（并发压到 4：实测 6 并发会把该站打成限流，导致首页都取不回来）
    details = []
    try:
        with ThreadPoolExecutor(max_workers=4) as ex:
            details = list(ex.map(fetch_provider_detail, KEY_PROVIDERS))
    except Exception as e:
        details = [{"slug": "-", "ok": False, "note": type(e).__name__}]

    # 跨页共现去噪：剔掉页脚「相关推荐」的通用模型名
    noise = filter_cross_page(details, threshold=3)

    return {"ok": True, "count": len(provs), "providers": provs,
            "details": details, "cross_page_noise": sorted(noise)}


def src_llm_price():
    """llm-price.com：模型价格对比表，含「上架时间」，最能反映新模型与降价。"""
    st, raw = fetch("https://llm-price.com/", timeout=30)
    if st != 200:
        return {"ok": False, "note": f"HTTP {st}", "rows": []}
    t = raw.decode("utf-8", "replace")
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S):
        cells = [strip_tags(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
        if len(cells) >= 5 and cells[0] and "Name" not in cells[0]:
            # 供应商列常为图标+文本，strip 后可能为空；模型名本身带「供应商: 模型」前缀，故兜底从前缀取
            prov = cells[6] if len(cells) > 6 and cells[6] else ""
            if not prov and ":" in cells[0]:
                prov = cells[0].split(":")[0].strip()
            rows.append({"model": cells[0][:70], "released": cells[1],
                         "context": cells[2], "input": cells[3],
                         "output": cells[4] if len(cells) > 4 else "",
                         "provider": prov})
    return {"ok": True, "count": len(rows), "rows": rows[:60]}


def src_hf_mirror():
    """hf-mirror.com：HuggingFace 的境内镜像，可当替身用。"""
    out = {"ok": True}
    st, raw = fetch("https://hf-mirror.com/api/models?sort=trendingScore&limit=20")
    if st == 200:
        try:
            js = json.loads(raw.decode("utf-8", "replace"))
            out["trending_models"] = [
                {"id": m.get("id"), "downloads": m.get("downloads"),
                 "likes": m.get("likes"), "created": (m.get("createdAt") or "")[:10]}
                for m in js]
        except Exception as e:
            out["trending_models"] = []
            out["models_note"] = f"解析失败 {type(e).__name__}"
    else:
        out["trending_models"] = []
        out["models_note"] = f"HTTP {st}"

    st, raw = fetch("https://hf-mirror.com/api/daily_papers")
    if st == 200:
        try:
            js = json.loads(raw.decode("utf-8", "replace"))
            out["daily_papers"] = [
                {"title": (p.get("paper") or {}).get("title") or p.get("title"),
                 "published": (p.get("publishedAt") or "")[:10],
                 "upvotes": (p.get("paper") or {}).get("upvotes"),
                 "id": (p.get("paper") or {}).get("id")}
                for p in js[:15]]
        except Exception as e:
            out["daily_papers"] = []
            out["papers_note"] = f"解析失败 {type(e).__name__}"
    else:
        out["daily_papers"] = []
        out["papers_note"] = f"HTTP {st}（实测该接口有 429 限流，失败属正常）"
    return out


def src_openrouter():
    st, raw = fetch("https://openrouter.ai/api/v1/models", timeout=30)
    if st != 200:
        return {"ok": False, "note": f"HTTP {st}", "free": []}
    try:
        js = json.loads(raw.decode("utf-8", "replace"))
    except Exception as e:
        return {"ok": False, "note": f"解析失败 {type(e).__name__}", "free": []}
    data = js.get("data", js if isinstance(js, list) else [])
    free = []
    for m in data:
        pr = m.get("pricing") or {}
        try:
            pi, po = float(pr.get("prompt", 1)), float(pr.get("completion", 1))
        except Exception:
            continue
        if pi == 0 and po == 0:
            free.append({"id": m.get("id"), "name": m.get("name"),
                         "context": m.get("context_length")})
    return {"ok": True, "total": len(data), "free_count": len(free), "free": free[:60]}


def src_gh_repo(mirror=None):
    """取 GitHub raw。

    **直连优先**（复测 6/6 可达，28,367 B，7.9 s）；直连失败再轮换加速镜像。
    初版曾写「直连不通、必须走镜像」——那是单次抖动造成的误判，已推翻。
    """
    path = "mnfst/awesome-free-llm-apis/main/README.md"
    tried = []
    urls = ["https://raw.githubusercontent.com/" + path]      # 直连优先
    if mirror:
        urls.append(mirror + "https://raw.githubusercontent.com/" + path)
    for m in GH_MIRRORS[:3]:
        urls.append(m + "https://raw.githubusercontent.com/" + path)
    urls.append("https://cdn.jsdelivr.net/gh/" + path)
    for u in urls:
        st, raw = fetch(u, timeout=30)
        host = u.split("/")[2]
        tried.append(f"{host}={st}")
        if st == 200 and len(raw) > 5000 and b"Provider" in raw:
            txt = raw.decode("utf-8", "replace")
            return {"ok": True, "via": host, "bytes": len(raw),
                    "tried": tried,
                    "sections": len(re.findall(r"^### ", txt, re.M)),
                    "providers": re.findall(r"^### (.+)$", txt, re.M)[:30]}
    return {"ok": False, "via": None, "tried": tried}


def src_feed(name, url, kw_only=False):
    st, raw = fetch(url, timeout=25)
    if st != 200:
        return {"name": name, "ok": False, "note": f"HTTP {st}", "items": []}
    items = rss_items(raw, limit=30)
    if kw_only:
        items = [i for i in items
                 if any(k.lower() in i[0].lower() for k in KEYWORDS)]
    return {"name": name, "ok": True, "count": len(items),
            "items": items[:15]}


def main():
    if len(sys.argv) < 2:
        print("用法: python fetch_overseas.py <输出目录>")
        sys.exit(1)
    outdir = sys.argv[1]
    os.makedirs(outdir, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    print("=" * 84)
    print(f"赛博鸡蛋 · 境外信源抓取（绕行通道）  {today}")
    print("=" * 84)

    # 并行抓取各源
    with ThreadPoolExecutor(max_workers=6) as ex:
        f_freellm = ex.submit(src_freellm)
        f_price = ex.submit(src_llm_price)
        f_hf = ex.submit(src_hf_mirror)
        f_or = ex.submit(src_openrouter)
        f_gh = ex.submit(src_gh_repo)
        f_media = ex.submit(lambda: [src_feed(n, u, kw_only=True) for n, u in MEDIA_FEEDS])
        f_off = ex.submit(lambda: [src_feed(n, u) for n, u in OFFICIAL_FEEDS])
        freellm, price, hf, orouter = f_freellm.result(), f_price.result(), f_hf.result(), f_or.result()
        gh, media, official = f_gh.result(), f_media.result(), f_off.result()

    rpt = []
    rpt.append(f"# 境外信源抓取报告（绕行通道） · {today}")
    rpt.append("")
    rpt.append("> 本报告只走本机网络下**实测可达**的通道，不通的域名不硬试。")
    rpt.append("")

    # 1 freellm
    rpt.append("## 一、免费额度专门站 freellm.net")
    rpt.append("")
    if freellm["ok"]:
        rpt.append(f"收录 provider **{freellm['count']} 家**。"
                   f"首页只有清单，**干货在逐家详情页**，故下两节分开列。")
        rpt.append("")

        det = [d for d in (freellm.get("details") or []) if d.get("ok")]
        if det:
            rpt.append("### 1.1 重点 provider 详情（速率限制／免费模型／是否需信用卡）")
            rpt.append("")
            rpt.append("| 供应商 | 免费模型数 | 速率限制 | 上下文 | 免信用卡 | 最近更新 |")
            rpt.append("|---|---|---|---|---|---|")
            for d in det:
                rpt.append(f"| {d['slug']} | {d['free_models'] if d['free_models'] is not None else '—'} "
                           f"| {d['rates']} | {d['context']} "
                           f"| {'是' if d['no_credit_card'] else '—'} | {d['updated']} |")
            rpt.append("")
            rpt.append("**各 provider 免费模型 ID（节选）**：")
            rpt.append("")
            for d in det:
                if d["model_ids"]:
                    rpt.append(f"- **{d['slug']}**：{'、'.join(d['model_ids'][:6])}")
            noise = freellm.get("cross_page_noise") or []
            if noise:
                rpt.append("")
                rpt.append(f"> 已剔除跨页通用噪声 **{len(noise)} 个**"
                           f"（如 {'、'.join(noise[:5])}）：这些模型名在多个 provider 页面上共同出现，"
                           f"属页面底部的「相关推荐」区块，**不是该家供应商的免费模型**。"
                           f"不作剔除即会造成「把 A 家的模型写到 B 家名下」的串行错位。")
            rpt.append("")

        rpt.append(f"### 1.2 全部 {freellm['count']} 家 provider 清单")
        rpt.append("")
        rpt.append("| 供应商 | 详情页 |")
        rpt.append("|---|---|")
        for p in freellm["providers"]:
            rpt.append(f"| {p['name']} | {p['url']} |")
        print(f"  ① freellm.net：{freellm['count']} 家 provider，"
              f"详情页成功 {len([d for d in freellm['details'] if d.get('ok')])} 家")
    else:
        rpt.append(f"抓取失败：{freellm.get('note')}")
        print(f"  ① freellm.net 失败：{freellm.get('note')}")
    rpt.append("")

    # 2 价格
    rpt.append("## 二、模型价格与上架动态 llm-price.com")
    rpt.append("")
    rpt.append("> 「上架时间」列最能反映新模型上线与降价，是境外厂商动作的灵敏哨点。")
    rpt.append("")
    if price["ok"]:
        rpt.append(f"共 {price['count']} 行，取前 25 行：")
        rpt.append("")
        rpt.append("| 模型 | 上架 | 上下文 | 输入 | 输出 | 供应商 |")
        rpt.append("|---|---|---|---|---|---|")
        for r in price["rows"][:25]:
            rpt.append(f"| {r['model']} | {r['released']} | {r['context']} "
                       f"| {r['input']} | {r['output']} | {r['provider']} |")
        print(f"  ② llm-price.com：{price['count']} 行")
    else:
        rpt.append(f"抓取失败：{price.get('note')}")
        print(f"  ② llm-price.com 失败：{price.get('note')}")
    rpt.append("")

    # 3 HF 镜像
    rpt.append("## 三、HuggingFace 镜像（hf-mirror.com，替代不通的 huggingface.co）")
    rpt.append("")
    tm = hf.get("trending_models") or []
    if tm:
        rpt.append("**趋势模型**（按热度）：")
        rpt.append("")
        rpt.append("| 模型 | 下载 | 点赞 | 创建 |")
        rpt.append("|---|---|---|---|")
        for m in tm[:15]:
            rpt.append(f"| {m['id']} | {m['downloads']} | {m['likes']} | {m['created']} |")
        print(f"  ③ hf-mirror 趋势模型：{len(tm)} 条")
    else:
        rpt.append(f"趋势模型抓取失败：{hf.get('models_note')}")
        print(f"  ③ hf-mirror 模型失败：{hf.get('models_note')}")
    rpt.append("")
    dp = hf.get("daily_papers") or []
    if dp:
        rpt.append("**每日论文**（反映新模型与新技术动向）：")
        rpt.append("")
        for p in dp[:12]:
            rpt.append(f"- {p['title']}（{p['published']}）")
        print(f"     每日论文：{len(dp)} 条")
    else:
        rpt.append(f"每日论文抓取失败：{hf.get('papers_note')}")
    rpt.append("")

    # 4 OpenRouter
    rpt.append("## 四、OpenRouter 零价模型（免密钥接口，比汇总仓库实时）")
    rpt.append("")
    if orouter["ok"]:
        rpt.append(f"全站 {orouter['total']} 个模型中，输入输出**双零价**的有 "
                   f"**{orouter['free_count']} 个**：")
        rpt.append("")
        rpt.append("| 模型 | 上下文 |")
        rpt.append("|---|---|")
        for m in orouter["free"][:40]:
            rpt.append(f"| {m['name'] or m['id']} | {m.get('context') or '—'} |")
        print(f"  ④ OpenRouter：{orouter['free_count']}/{orouter['total']} 零价")
    else:
        rpt.append(f"抓取失败：{orouter.get('note')}")
        print(f"  ④ OpenRouter 失败：{orouter.get('note')}")
    rpt.append("")

    # 5 GitHub 汇总仓库
    rpt.append("## 五、GitHub 汇总仓库（经加速镜像取回）")
    rpt.append("")
    if gh["ok"]:
        rpt.append(f"经 **{gh['via']}** 取回，{gh['bytes']} 字节，"
                   f"收录 {gh['sections']} 家供应商。")
        rpt.append("")
        rpt.append("镜像轮换记录：" + "、".join(gh["tried"]))
        print(f"  ⑤ GitHub 汇总仓库：经 {gh['via']} 取回 {gh['bytes']}B")
    else:
        rpt.append("所有镜像均失败，建议改走搜索。")
        rpt.append("")
        rpt.append("尝试记录：" + "、".join(gh["tried"]))
        print(f"  ⑤ GitHub 汇总仓库：全部镜像失败")
    rpt.append("")

    # 6 官方 RSS
    rpt.append("## 六、官方 RSS 新条目（官网不可达，RSS 直连可用）")
    rpt.append("")
    for f in official:
        if f["ok"] and f["items"]:
            rpt.append(f"**{f['name']}**（{f['count']} 条）")
            rpt.append("")
            for t, l, d in f["items"][:8]:
                rpt.append(f"- [{t}]({l}) — {d}")
            rpt.append("")
        else:
            rpt.append(f"**{f['name']}**：抓取失败（{f.get('note','无条目')}）")
            rpt.append("")
    print(f"  ⑥ 官方 RSS：{sum(1 for f in official if f['ok'])}/{len(official)} 可用")

    # 7 国内媒体
    rpt.append("## 七、国内媒体搬运的境外消息（关键词过滤）")
    rpt.append("")
    rpt.append("> 境外厂商消息在国内媒体上的中文报道，是绕行通道中时效性最好的一路。")
    rpt.append("")
    for f in media:
        if f["ok"] and f["items"]:
            rpt.append(f"**{f['name']}**（命中 {f['count']} 条）")
            rpt.append("")
            for t, l, d in f["items"][:8]:
                rpt.append(f"- [{t}]({l})")
            rpt.append("")
    print(f"  ⑦ 国内媒体：{sum(1 for f in media if f['ok'])}/{len(media)} 可用")

    # 落盘
    json_path = os.path.join(outdir, f"overseas_{today}.json")
    with open(json_path, "w", encoding="utf-8") as fp:
        json.dump({"date": today, "freellm": freellm, "llm_price": price,
                   "hf_mirror": hf, "openrouter": orouter, "github": gh,
                   "official_feeds": official, "media_feeds": media},
                  fp, ensure_ascii=False, indent=1)
    md_path = os.path.join(outdir, f"境外信源_{today}.md")
    with open(md_path, "w", encoding="utf-8") as fp:
        fp.write("\n".join(rpt))

    print()
    print(f"✅ JSON：{json_path}")
    print(f"✅ 报告：{md_path}")


if __name__ == "__main__":
    main()
