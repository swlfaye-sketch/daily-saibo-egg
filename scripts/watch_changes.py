# -*- coding: utf-8 -*-
"""赛博鸡蛋 · 乙路哨兵：官方渠道变更检测。

思路：每天抓一次监控目标，与上一次快照比对，**只报有变化的**。
比逐一重读网页快得多，也是「第一时间知道」的唯一可行做法。

监控目标分五类，按「什么才算真变化」分别定指纹：
  1. 定价页 / 额度页（kind="price"：只取价格数字与档位名，抗 A/B 测试文案干扰）
  2. 官方 RSS（kind="rss"：只看有无新条目）
  3. GitHub 仓库（kind="gh"：**只取 pushed_at**，星数每天微增不算变化）
  4. 接口条目（kind="json"：取排序后的条目标识，避开顺序与时间戳假变化）
  5. 表格型站点（kind="names"：只取第一列名称集合，如 llm-price.com 的模型上架表）

另有两项保命机制：
  · 跨天失败计数——单次失败是常态，**连续 3 次失败才是信源失效**，届时在报告单列「疑似失效」。
  · 快照不被失败覆盖——抓取失败时保留上次快照，下期仍能正常比对。

含境外绕行目标：境外官网不通，但 freellm.net、llm-price.com、HF 镜像、
OpenAI Status、DeepMind/GitHub 官方 RSS 均可直连，故纳入监控。
详见 `references/overseas-bypass.md`。

用法：
    python watch_changes.py <数据目录>          # 抓取并比对，输出变化报告
    python watch_changes.py <数据目录> --init   # 仅建立基线快照
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
from datetime import datetime

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
# 默认启用证书校验。原先为兼容个别镜像站关闭过校验，被平台安全扫描判为中危
# （数据外泄，指向本行）；实测全部目标站点证书链正常，故恢复 Python 默认的严格校验。
CTX = ssl.create_default_context()

# ---------- 监控目标 ----------
# kind: price（定价页：只取价格与档位）| names（表格型：只取第一列名称集合）
#       | page（网页全文指纹）| rss（订阅源新条目）| gh（GitHub 仓库最新发版）
#       | json（接口条目）
# 只收录实测可达的目标；不可达的走搜索，不列入此处。
#
# 收录原则：**只放低频变化的目标**。媒体流与热门榜天天都变（HuggingFace 趋势、
# 新闻 RSS 等），放进哨兵会天天报警、淹没真信号——那类走 fetch_overseas.py 抓取并按
# 关键词筛，不靠指纹比对。
#
# 定价页一律用 kind="price"：全文指纹对含 A/B 测试的定价页必然误报（实测 Cursor 定价页
# 同一 URL 交替返回 7474／8086 字符两个变体，相似度仅 0.7986）。
TARGETS = [
    # --- 定价页（用 price 结构化指纹：只盯价格数字与档位名，抗 A/B 测试文案差异） ---
    {"name": "Anthropic 定价", "kind": "price", "url": "https://www.anthropic.com/pricing"},
    {"name": "Cohere 定价", "kind": "price", "url": "https://cohere.com/pricing"},
    {"name": "Together 定价", "kind": "price", "url": "https://www.together.ai/pricing"},
    # GitHub Copilot 方案页实测 1,258,668 B（1.26 MB），单次需 15–25 s。
    # **必须单独放宽超时**：曾用 25 s 默认超时连续 5 次失败，被误判为「github.com 不可达」；
    # 复测 6 次 5 次成功（失败为 IncompleteRead 传输中断）。属大页面超时问题，不是封锁。
    {"name": "GitHub Copilot 方案", "kind": "price", "timeout": 75,
     "url": "https://github.com/features/copilot/plans"},
    # 【已移出】Cursor 定价 https://cursor.com/pricing
    # 理由：该站对同一 URL 做 A/B 测试，且**两个变体的套餐结构完全不同**——实测连抓 6 次，
    # 5 次返回「$20/$60/$200、档位 Free/Hobby/Pro/Ultra/Enterprise」，
    # 1 次返回「$20/$40、档位 Free/Pro/Standard/Team/Ultra/Enterprise」。
    # 任何指纹都会随交替而报警，属结构性噪声源，**不是指纹算法能解决的**。
    # Cursor 的定价变化改由国内媒体（通道三）与搜索（通道五）覆盖。
    {"name": "Manus 官网", "kind": "page", "url": "https://manus.im/"},
    {"name": "Devin 官网", "kind": "page", "url": "https://devin.ai/"},
    {"name": "v0 官网", "kind": "page", "url": "https://v0.dev/"},
    {"name": "Cerebras 官网", "kind": "page", "url": "https://www.cerebras.ai/"},
    {"name": "Fireworks 官网", "kind": "page", "url": "https://fireworks.ai/"},
    {"name": "Novita 官网", "kind": "page", "url": "https://novita.ai/"},
    {"name": "Nebius 官网", "kind": "page", "url": "https://nebius.com/"},

    # --- 境外绕行通道（官网不通，但这些通道可达；详见 references/overseas-bypass.md） ---
    {"name": "freellm.net 免费额度站", "kind": "page", "url": "https://freellm.net/"},
    # llm-price.com 每天都有新行，**必须用 names 结构化指纹**：
    # 全文指纹实测报「正文 4918 → 4897 字符」，无法行动；名称集合才反映新模型上架。
    {"name": "llm-price.com 上架模型", "kind": "names", "url": "https://llm-price.com/"},
    # 【已移出】OpenAI Status https://status.openai.com/
    # 理由：内容为服务故障公告，与「免费额度」无关。放进哨兵实测造成 2/3 的报警与此无关，
    # 属典型的「淹没真信号」。服务可用性另由 OpenAI News RSS 覆盖。
    {"name": "HF 镜像 趋势模型", "kind": "json",
     "url": "https://hf-mirror.com/api/models?sort=trendingScore&limit=30"},

    # --- 国内平台（官网可达，内容为服务端渲染的部分） ---
    {"name": "智谱官网新闻", "kind": "page", "url": "https://www.zhipuai.cn/"},
    {"name": "豆包官网", "kind": "page", "url": "https://www.doubao.com/"},
    {"name": "Kimi 官网", "kind": "page", "url": "https://www.kimi.com/"},
    {"name": "MiniMax 官网", "kind": "page", "url": "https://www.minimaxi.com/"},
    {"name": "通义千问官网", "kind": "page", "url": "https://tongyi.aliyun.com/"},
    {"name": "硅基流动模型广场", "kind": "page", "url": "https://cloud.siliconflow.cn/"},
    {"name": "小米 MiMo", "kind": "page", "url": "https://mimo.xiaomi.com/"},
    {"name": "WorkBuddy 官网", "kind": "page", "url": "https://www.workbuddy.cn/"},
    {"name": "零一万物官网", "kind": "page", "url": "https://www.01.ai/"},
    {"name": "商汤日日新", "kind": "page", "url": "https://www.sensenova.cn/"},

    # --- 官方 RSS（境外官网不通时的主要通道） ---
    {"name": "OpenAI News RSS", "kind": "rss", "url": "https://openai.com/news/rss.xml"},
    {"name": "DeepMind Blog RSS", "kind": "rss", "url": "https://deepmind.google/blog/rss.xml"},
    {"name": "GitHub Blog RSS", "kind": "rss", "url": "https://github.blog/feed/"},
    {"name": "Cloudflare Blog RSS", "kind": "rss", "url": "https://blog.cloudflare.com/rss/"},

    # --- 视频与生图平台（2026-09-20 逐站实测后新增） ---
    # 背景：评测者两次提到视频／生图类覆盖偏少，故对着 16 个站点做了一轮实测
    # （先判「能不能抓到可结构化比对的信号」，再判「这个信号自身稳不稳定」）。
    # 结论：**这类平台的官网绝大多数做不成指纹目标**——
    #   · 即梦／可灵中国站／通义万相／腾讯混元／智谱清言：SPA 壳页，正文 4–83 字，服务端不吐内容；
    #   · 即梦／可灵／海螺：正文 400–1100 字且连抓 3 次零波动，但既无价格也无档位名，
    #     拿来只能做整页指纹（改版才响），对「额度变化」没有意义，**故不收录**；
    #   · Runway 返 308、Midjourney 返 403，Pika／Luma／Krea 走代理 502、可图超时，均不可达。
    # 下面两站是实测下来唯二可用的：连抓 3 次正文字数与档位／价格集合**完全一致**（波动 0%）。
    {"name": "MiniMax 开放平台", "kind": "price", "url": "https://platform.minimaxi.com/"},
    {"name": "Flux 官方定价", "kind": "price", "url": "https://blackforestlabs.ai/"},

    # --- 官方仓库发版 ---
    {"name": "ollama 发版", "kind": "gh", "url": "https://api.github.com/repos/ollama/ollama/releases?per_page=1"},
    {"name": "mnfst 汇总仓库", "kind": "gh", "url": "https://api.github.com/repos/mnfst/awesome-free-llm-apis"},
]


# ---------- 用户自定义目标（可选，不改内置清单） ----------
# 设计取舍：内置 TARGETS 里承载了大量实测注释（某站为何移出、某页为何要放宽超时），
# 而 JSON 不支持注释——**故不把内置清单外置**，改为「叠加」：用户在数据目录放一份
# targets_user.json，脚本运行时合并。这样既保住注释里的经验，又能自行增删目标。
USER_FILE = "targets_user.json"

KINDS = ("price", "names", "page", "rss", "gh", "json")


def parse_user_file(path):
    """解析一份用户目标文件，返回 (add 列表, disable 集合, 说明列表, 错误列表)。"""
    notes, errs = [], []
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except Exception as e:
        errs.append("用户目标文件解析失败（%s）：%s" % (type(e).__name__, e))
        return [], set(), [], errs

    if not isinstance(raw, dict):
        errs.append("用户目标文件顶层须为对象（含 add／disable 两个键）")
        return [], set(), [], errs

    add = []
    for i, t in enumerate(raw.get("add") or [], 1):
        if not isinstance(t, dict):
            errs.append("add 第 %d 项不是对象，已跳过" % i)
            continue
        missing = [k for k in ("name", "kind", "url") if not t.get(k)]
        if missing:
            errs.append("add 第 %d 项缺字段 %s，已跳过" % (i, "／".join(missing)))
            continue
        if t["kind"] not in KINDS:
            errs.append("add 第 %d 项 kind=%s 不在支持范围（%s），已跳过"
                        % (i, t["kind"], "／".join(KINDS)))
            continue
        rec = {"name": t["name"], "kind": t["kind"], "url": t["url"]}
        if t.get("timeout"):
            try:
                rec["timeout"] = int(t["timeout"])
            except Exception:
                errs.append("add 第 %d 项 timeout 不是整数，已忽略该字段" % i)
        add.append(rec)

    dis = raw.get("disable") or []
    if not isinstance(dis, list):
        errs.append("disable 须为数组，已忽略")
        dis = []

    return add, set(str(x) for x in dis), notes, errs


def merge_targets(base=None, explicit=None):
    """内置清单与用户清单合并，返回 (最终清单, 说明列表, 错误列表)。

    用户文件位置：显式 `--targets` 指定的路径优先，否则取 `<数据目录>/targets_user.json`。
    两份都存在时**只认显式指定的那份**，避免来源混淆。
    """
    path = explicit or (os.path.join(base, USER_FILE) if base else "")
    if not path or not os.path.exists(path):
        if explicit:
            return list(TARGETS), [], ["--targets 指定的文件不存在：%s" % explicit]
        return list(TARGETS), [], []

    add, dis, notes, errs = parse_user_file(path)
    if errs and not add and not dis:
        # 文件存在但完全读不出内容：不静默退回，让使用者看到问题
        return list(TARGETS), notes, errs

    final = []
    for t in TARGETS:
        if t["name"] in dis or t["url"] in dis:
            notes.append("已停用内置目标：%s" % t["name"])
            continue
        final.append(t)

    builtin_urls = {t["url"] for t in TARGETS}
    seen = set(builtin_urls)
    for t in add:
        if t["url"] in builtin_urls:
            notes.append("「%s」网址与内置目标重复，已并入内置项" % t["name"])
            continue
        if t["url"] in seen:
            notes.append("「%s」网址在用户清单内重复，已跳过" % t["name"])
            continue
        seen.add(t["url"])
        final.append(t)
        notes.append("新增目标：%s（%s）" % (t["name"], t["kind"]))

    return final, notes, errs


USER_SAMPLE = """{
  "_说明": [
    "本文件用来在你自己的环境里增删监控目标，不会修改技能内置清单，升级技能时也不会被覆盖。",
    "两个键都可省略。改完直接跑 watch_changes.py，脚本会自动读取本目录下的同名文件。",
    "add 里每一项须含 name、kind、url 三个字段；kind 只支持这六种：",
    "  price  定价页，只盯价格数字与档位名（抗 A/B 测试的文案差异，定价页首选）",
    "  names  表格型页面，只取第一列名称集合（如模型上架清单）",
    "  page   整页正文指纹（适合官网首页、公告页这类整体改版才变的）",
    "  rss    订阅源，比对新增条目",
    "  gh     GitHub 仓库最新发版",
    "  json   接口返回的条目",
    "timeout 可选，单位秒，默认 45。大页面（超过 1 MB）建议放宽到 75。",
    "disable 里写内置目标的名称或网址都行，两者都能匹配。",
    "收录原则：只放低频变化的目标。媒体流与热门榜天天都变，放进哨兵会天天报警、淹没真信号。"
  ],
  "add": [
  ],
  "disable": [
  ]
}
"""


def cmd_init_user(base):
    """在数据目录生成 targets_user.json 样例。"""
    path = os.path.join(base, USER_FILE)
    if os.path.exists(path):
        print("用户目标文件已存在，未覆盖：%s" % path)
        return 1
    try:
        os.makedirs(base, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(USER_SAMPLE)
    except Exception as e:
        print("❌ 写入失败（%s）：%s" % (type(e).__name__, e))
        return 1
    print("✅ 已生成样例：%s" % path)
    print("   把要加的目标填进 add，要停用的内置目标名填进 disable，保存后直接跑即可。")
    return 0


def fetch(url, timeout=45, retries=3):
    """带重试的抓取。

    超时默认放到 45 秒，原因见「已知坑」：**大页面在紧超时下会被误判为「域名不可达」**。
    实测 github.com 的 1.26 MB 页面单次约需 15–25 s，用 25 s 超时曾连续 5 次失败，
    而放宽后又稳定可取——那不是封锁，是传输没跑完。
    IncompleteRead 属「传输中断」，与超时同类，一并重试。
    """
    last = (-1, b"")
    for i in range(retries):
        req = urllib.request.Request(url, headers={
            "User-Agent": UA, "Accept": "*/*", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"})
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and i < retries - 1:
                time.sleep(1.5 * (i + 1))
                continue
            try:
                return e.code, e.read()
            except Exception:
                return e.code, b""
        except Exception:
            last = (-1, b"")
            if i < retries - 1:
                time.sleep(1.5 * (i + 1))
    return last


def shingles(txt, k=5, n=80, step=2):
    """取文本 5-gram 哈希中的最小 n 个（MinHash 思路），用于抗抖动比对。

    为什么需要它：实测 Cursor 定价页在两次抓取间正文长度在 3551↔3749 字符之间
    反复跳动（轮播／A-B 测试内容），纯哈希必然天天误报。用集合相似度可吸收这类抖动。
    """
    if not txt:
        return []
    grams = set()
    for i in range(0, max(1, len(txt) - k), step):
        grams.add(hashlib.md5(txt[i:i + k].encode()).hexdigest()[:10])
    return sorted(grams)[:n]


def similar(a, b, thresh=0.85):
    """两个 shingle 集合的 Jaccard 相似度是否达到阈值。"""
    if not a or not b:
        return False
    sa, sb = set(a), set(b)
    uni = len(sa | sb)
    return (len(sa & sb) / uni) >= thresh if uni else False


def text_of(html_bytes):
    """去标签取可见文本，并抹掉长随机串（避免假变化）。"""
    try:
        s = html_bytes.decode("utf-8", "replace")
    except Exception:
        return ""
    s = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"&[a-z#0-9]{2,8};", " ", s)
    s = re.sub(r"\b[0-9a-fA-F]{16,}\b", " ", s)      # 长十六进制串（构建 ID、nonce）
    s = re.sub(r"\b\d{10,13}\b", " ", s)             # 时间戳
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def key_of(url):
    return hashlib.md5(url.encode()).hexdigest()[:12]


PRICE_RE = re.compile(r"(?:US)?\$\s?\d+(?:[.,]\d+)?|\b\d+(?:\.\d+)?\s*(?:USD|RMB|CNY|元|美元|美分)\b")
TIER_RE = re.compile(r"\b(Free|Pro|Pro\+|Team|Business|Enterprise|Plus|Basic|Starter|"
                     r"Ultra|Max|Advanced|Student|Education|Hobby|Personal|Standard)\b")


def price_sig(txt):
    """定价页专用结构化指纹：只取「价格数字集合 + 档位名集合」。

    为什么不能对定价页用全文指纹——实测 Cursor 定价页同一 URL 会在两个变体间交替
    （7474 / 8086 字符，全量相似度仅 0.7986），差异是套餐权益描述的 A/B 测试。
    全文指纹必然天天误报；而价格结构在 A/B 变体中相同，且真降价必然改变价格集合。
    """
    prices = sorted(set(p.replace(" ", "") for p in PRICE_RE.findall(txt)))
    tiers = sorted(set(t for t in TIER_RE.findall(txt)))
    return prices, tiers


def table_names(html):
    """从表格型页面取「第一列名称集合」。

    用于 llm-price.com 这类**天天新增行**的站点：全文指纹只会报「正文 4918 → 4897 字符」
    这种无法行动的噪声；而「名称集合」的变化＝有新模型上架或下架，才是真信号。
    """
    names = set()
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)
        if len(cells) >= 5:
            c0 = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", cells[0])).strip()
            if 3 <= len(c0) <= 80 and "Name" not in c0:
                names.add(c0)
    return sorted(names)


def snapshot_for(t):
    """返回 (状态码, 指纹, 摘要信息, 可比对键值, 抖动指纹)"""
    st, raw = fetch(t["url"], timeout=t.get("timeout", 45))
    if st != 200:
        return st, None, f"HTTP {st}", None, None

    if t["kind"] == "rss":
        txt = raw.decode("utf-8", "replace")
        titles = re.findall(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", txt, re.S)
        guids = re.findall(r"<guid[^>]*>(.*?)</guid>", txt, re.S)
        items = [g.strip() for g in guids][:40] or [x.strip() for x in titles][1:41]
        fp = hashlib.md5(("|".join(items)).encode()).hexdigest()
        return st, fp, f"条目 {len(items)} 条", {"items": items[:6]}, None

    if t["kind"] == "gh":
        try:
            j = json.loads(raw.decode("utf-8", "replace"))
        except Exception:
            return st, None, "JSON 解析失败", None, None
        if isinstance(j, dict):                       # 仓库元数据
            # 指纹**只取 pushed_at**：星数每天微增，纳入指纹会天天误报
            fp = hashlib.md5(str(j.get("pushed_at")).encode()).hexdigest()
            return st, fp, f"推送 {j.get('pushed_at')}｜星 {j.get('stargazers_count')}", \
                   {"pushed_at": j.get("pushed_at"), "stars": j.get("stargazers_count")}, None
        if isinstance(j, list) and j:                 # releases
            tag = j[0].get("tag_name")
            fp = hashlib.md5(str(tag).encode()).hexdigest()
            return st, fp, f"最新版本 {tag}", {"tag": tag, "published": j[0].get("published_at")}, None
        return st, None, "空结果", None, None

    if t["kind"] == "json":
        # 接口条目指纹：只对「排序后的条目标识」做哈希——顺序变化（如热门榜重排）不算内容变化
        try:
            j = json.loads(raw.decode("utf-8", "replace"))
        except Exception:
            return st, None, "JSON 解析失败", None, None
        rows = j if isinstance(j, list) else (j.get("data") if isinstance(j, dict) else None)
        if not isinstance(rows, list):
            return st, None, "结构非列表", None, None
        ids = sorted(str(x.get("id") or x.get("title") or x.get("name") or "") for x in rows[:40])
        fp = hashlib.md5("|".join(ids).encode()).hexdigest()
        return st, fp, f"条目 {len(rows)} 条", {"items": ids[:6]}, shingles("".join(ids))

    if t["kind"] == "names":
        # 表格型站点：指纹 = 第一列名称集合。新行出现或旧行消失才报警。
        names = table_names(raw.decode("utf-8", "replace"))
        fp = hashlib.md5("|".join(names).encode()).hexdigest()
        return st, fp, f"表格 {len(names)} 行", {"items": names[:8], "all": names}, None

    if t["kind"] == "price":
        txt = text_of(raw)
        prices, tiers = price_sig(txt)
        fp = hashlib.md5(("|".join(prices) + "#" + "|".join(tiers)).encode()).hexdigest()
        all_fp = hashlib.md5(txt.encode()).hexdigest()
        note = f"价格 {len(prices)} 项｜档位 {len(tiers)} 个"
        return st, fp, note, {"prices": prices[:12], "tiers": tiers[:12],
                              "full_fp": all_fp, "full_len": len(txt)}, None

    # page
    txt = text_of(raw)
    fp = hashlib.md5(txt.encode()).hexdigest()
    return st, fp, f"正文 {len(txt)} 字符", None, shingles(txt)


def main():
    if len(sys.argv) < 2:
        print("用法: python watch_changes.py <数据目录> [--init] [--targets <文件>] "
              "[--init-user] [--list-targets]")
        sys.exit(1)
    base = sys.argv[1]
    init_only = "--init" in sys.argv

    # 生成用户目标样例文件（不抓取，纯写盘）
    if "--init-user" in sys.argv:
        sys.exit(cmd_init_user(base))

    explicit = ""
    if "--targets" in sys.argv:
        i = sys.argv.index("--targets")
        if i + 1 >= len(sys.argv):
            print("❌ --targets 后面要跟文件路径")
            sys.exit(1)
        explicit = sys.argv[i + 1]

    targets, tnote, terr = merge_targets(base, explicit or None)
    if terr:
        for e in terr:
            print("⚠️  {} ".format(e))
    if tnote:
        print("目标清单调整：")
        for n in tnote:
            print("   · %s" % n)
    if not targets:
        print("❌ 合并后目标清单为空，请检查 disable 是否写多了")
        sys.exit(1)

    # 只列出合并后的清单，不抓取——用来确认自定义配置是否已生效
    if "--list-targets" in sys.argv:
        print("合并后共 %d 个监控目标（内置 %d 个）："
              % (len(targets), len(TARGETS)))
        for i, t in enumerate(targets, 1):
            print("  %2d. %-26s %-6s %s" % (i, t["name"], t["kind"], t["url"]))
        return 0

    snapdir = os.path.join(base, "snapshots")
    outdir = os.path.join(base, "out")
    os.makedirs(snapdir, exist_ok=True)
    os.makedirs(outdir, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    changes, failed, unchanged, baseline, jitter = [], [], [], [], []

    # 失败计数（跨天持久化）：单次失败是常态，**连续失败才是信源失效的信号**。
    # 没有这张表，一个死掉的信源会永远躺在「抓取失败」里，无人察觉。
    fpath = os.path.join(snapdir, "_failures.json")
    ftab = {}
    if os.path.exists(fpath):
        try:
            with open(fpath, encoding="utf-8") as f:
                ftab = json.load(f)
        except Exception:
            ftab = {}

    for t in targets:
        k = key_of(t["url"])
        path = os.path.join(snapdir, f"{k}.json")
        try:
            st, fp, note, extra, sh = snapshot_for(t)
        except Exception as e:
            st, fp, note, extra, sh = -1, None, f"异常 {type(e).__name__}", None, None

        if st != 200 or fp is None:
            rec = ftab.get(t["name"]) or {}
            streak = int(rec.get("streak", 0)) + 1
            ftab[t["name"]] = {"streak": streak, "last_error": note,
                               "last_fail": today, "last_ok": rec.get("last_ok", "—")}
            failed.append((t["name"], st, note, streak))
            continue

        old = None
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    old = json.load(f)
            except Exception:
                old = None

        prev = ftab.get(t["name"]) or {}
        ftab[t["name"]] = {"streak": 0, "last_error": "", "last_fail": prev.get("last_fail", "—"),
                           "last_ok": today}

        rec = {"name": t["name"], "url": t["url"], "kind": t["kind"],
               "date": today, "fingerprint": fp, "note": note,
               "extra": extra, "shingles": sh}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=1)

        if old is None:
            baseline.append(t["name"])
        elif old.get("fingerprint") != fp:
            # 指纹变了，但内容相似度仍高 → 判定为页面抖动（轮播／A-B 测试／随机推荐），
            # 不计入变化，否则会天天误报。实测 Cursor 定价页即属此类。
            if similar(old.get("shingles"), sh):
                jitter.append(t["name"])
            else:
                old_note = old.get("note", "")
                detail = ""
                if t["kind"] == "rss" and extra:
                    old_items = (old.get("extra") or {}).get("items", []) or []
                    new_items = [i for i in extra.get("items", []) if i not in old_items]
                    if new_items:
                        detail = "新增：" + " ／ ".join(new_items[:3])
                elif t["kind"] == "names" and extra:
                    old_all = (old.get("extra") or {}).get("all", []) or []
                    new_all = extra.get("all", []) or []
                    added = [x for x in new_all if x not in old_all][:3]
                    gone = [x for x in old_all if x not in new_all][:3]
                    parts = []
                    if added:
                        parts.append("上架 " + " ／ ".join(added))
                    if gone:
                        parts.append("下架 " + " ／ ".join(gone))
                    detail = "；".join(parts)
                changes.append({"name": t["name"], "url": t["url"], "kind": t["kind"],
                                "before": old_note, "after": note, "detail": detail})
        else:
            unchanged.append(t["name"])

    # 报告
    lines = [f"# 官方渠道变更报告 · {today}", "",
             f"监控目标 {len(targets)} 个｜有变化 {len(changes)} 个｜"
             f"无变化 {len(unchanged)} 个｜判为抖动 {len(jitter)} 个｜"
             f"建基线 {len(baseline)} 个｜失败 {len(failed)} 个", ""]
    if tnote:
        lines += ["**本期目标清单调整**：" + "；".join(tnote), ""]

    # 章节编号动态生成：没有内容的章节不输出，编号一并顺延。
    # 早先写死「一、二、三、四、五」，空章节不输出时就会出现「一、三、五」的跳号。
    _sec = [0]

    def sec(title):
        _sec[0] += 1
        return "## %s、%s" % ("一二三四五六七八九十"[_sec[0] - 1], title)

    if changes:
        lines += [sec("有变化（需人工确认）"), ""]
        for c in changes:
            lines.append(f"- **{c['name']}**（{c['kind']}）")
            lines.append(f"  - 变化：{c['before']} → {c['after']}")
            if c["detail"]:
                lines.append(f"  - {c['detail']}")
            lines.append(f"  - 地址：{c['url']}")
        lines.append("")
        lines.append("> 变化不等于「有新福利」——可能是新闻轮播、营销文案调整。"
                     "须打开页面确认后再写入清单。")
        lines.append("")
    else:
        lines += [sec("有变化"), "", "本期无变化。", ""]
    if jitter:
        lines += [sec("判为抖动（指纹变了但内容相似，不计入变化）"), ""]
        lines += [f"- {n}" for n in jitter]
        lines.append("")
        lines.append("> 这类页面含轮播或随机推荐元素，正文长度会在两次抓取间来回跳动。"
                     "**不判抖动就会天天误报**，故用内容相似度吸收。"
                     "若某目标连续多日出现在此处，说明该站改版较大，应考虑另设指纹方式。")
        lines.append("")
    if baseline:
        lines += [sec("首次建立基线（下期起可比对）"), ""]
        lines += [f"- {n}" for n in baseline] + [""]
    if failed:
        dead = [f for f in failed if f[3] >= 3]
        if dead:
            lines += [sec("疑似失效（连续 3 次以上抓不到）"), ""]
            lines += [f"- **{n}**｜连续失败 {s} 次｜末次成功 {ftab.get(n, {}).get('last_ok', '—')}｜{note}"
                      for n, _st, note, s in dead]
            lines.append("")
            lines.append("> 按 `references/overseas-bypass.md` 换通道："
                         "网页类改 RSS 或 API，境外不通改搜索或国内镜像。**换完更新目标清单。**")
            lines.append("")
        others = [f for f in failed if f[3] < 3]
        if others:
            lines += [sec("本次抓取失败（单次失败，快照保留上次值，不影响下期比对）"), ""]
            lines += [f"- {n}｜连续 {s} 次｜{note}" for n, _st, note, s in others]
            lines.append("")
            lines.append("> 单次失败不等于目标失效（已内置 3 次重试）。"
                         "连续 3 次才会升入上栏「疑似失效」。")
            lines.append("")

    # 失败表落盘
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(ftab, f, ensure_ascii=False, indent=1)

    rp = os.path.join(outdir, f"变更报告_{today}.md")
    with open(rp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"监控 {len(targets)} 个｜变化 {len(changes)}｜无变化 {len(unchanged)}｜"
          f"抖动 {len(jitter)}｜基线 {len(baseline)}｜失败 {len(failed)}")
    print(f"✅ 报告：{rp}")
    for c in changes:
        print(f"   🔔 {c['name']}：{c['before']} → {c['after']} {c['detail']}")
    for n in jitter:
        print(f"   ～ {n}：判为抖动，未计为变化")
    for n, _st, note, s in failed:
        flag = "❌ 疑似失效" if s >= 3 else "⚠️ "
        print(f"   {flag} {n}｜连续 {s} 次｜{note}")


if __name__ == "__main__":
    main()
