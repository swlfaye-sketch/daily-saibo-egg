# -*- coding: utf-8 -*-
"""赛博鸡蛋 · 清单渲染为 HTML（单文件、可直接双击打开、适配手机）。

为什么单独写一个渲染器而不是让模型每次手写 HTML：
  · 版式稳定——每天的清单长得一样，使用者一眼就认得出；
  · 省积分——渲染是确定性工作，交给脚本，模型只负责「内容」；
  · 不出错——表头、列数、转义由脚本管，模型不会漏掉 `|` 或写坏标签。

只用 Python 标准库，无第三方依赖（**不引入 markdown 库**，因为它不是标准库，
交付他人时会跑不起来）。

用法：
    python render_html.py <清单.md> [输出目录]
默认输出到清单同目录，文件名为 <清单名>.html。
"""
import html
import os
import re
import sys
from datetime import datetime

# 分栏配色：按标题关键词判断紧迫度。**「本周内到期」必须最醒目**——
# 使用者最怕的不是「没领到」，是「错过截止日期」。
SECTION_THEMES = [
    (("今天", "本周", "即将到期", "到期"), "urgent", "🔥"),
    (("无条件", "立即", "现在可领"), "ready", "🎁"),
    (("认证", "门槛"), "auth", "🪪"),
    (("永久免费", "长期", "免费层"), "free", "♾️"),
    (("在俄", "对俄"), "ru", "🇷🇺"),          # 保留给未来的扩展栏目
    (("无新增", "无变化", "对比"), "note", "📊"),
    (("免责", "声明"), "disclaimer", "ℹ️"),
]


def esc(s):
    return html.escape(s, quote=False)


def inline(s):
    """行内标记 → HTML。顺序要紧：先转义，再替换标记，否则会破坏已有标签。"""
    s = esc(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
               r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
    # 裸链接
    s = re.sub(r"(?<![\"'>=])(https?://[^\s<)]+)",
               r'<a href="\1" target="_blank" rel="noopener">\1</a>', s)
    return s


def theme_of(title):
    for keys, cls, icon in SECTION_THEMES:
        if any(k in title for k in keys):
            return cls, icon
    return "plain", ""


def render_md(md):
    """Markdown → 正文 HTML。只支持本产线实际用到的语法，不做通用解析器。"""
    out, i = [], 0
    lines = md.split("\n")
    n = len(lines)

    while i < n:
        ln = lines[i]
        s = ln.strip()

        # 空行
        if not s:
            i += 1
            continue

        # 分隔线
        if re.fullmatch(r"-{3,}", s):
            i += 1
            continue

        # 标题
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            lvl, txt = len(m.group(1)), m.group(2).strip()
            if lvl == 1:
                out.append(f'<h1>{inline(txt)}</h1>')
            elif lvl == 2:
                cls, icon = theme_of(txt)
                ic = f'<span class="icon">{icon}</span>' if icon else ""
                out.append(f'<section class="card {cls}"><h2>{ic}{inline(txt)}</h2>')
                out.append("__SECTION__")           # 占位，收尾时闭合
            else:
                out.append(f"<h{lvl}>{inline(txt)}</h{lvl}>")
            i += 1
            continue

        # 引用块（连续多行）
        if s.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip())
                i += 1
            body = " ".join(x for x in buf if x)
            out.append(f'<div class="note">{inline(body)}</div>')
            continue

        # 表格
        if s.startswith("|") and i + 1 < n and re.match(r"^\|[\s:\-|]+\|$", lines[i + 1].strip()):
            header = [c.strip() for c in s.strip("|").split("|")]
            i += 2
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                rows.append(cells)
                i += 1
            t = ['<div class="tw"><table>', "<thead><tr>"]
            t += [f"<th>{inline(c)}</th>" for c in header]
            t.append("</tr></thead><tbody>")
            for r in rows:
                t.append("<tr>")
                for c in r:
                    # 首列作为行标题，便于扫读
                    t.append(f"<td>{inline(c)}</td>")
                t.append("</tr>")
            t.append("</tbody></table></div>")
            out.append("".join(t))
            continue

        # 列表
        if re.match(r"^[-*]\s+", s):
            out.append("<ul>")
            while i < n and re.match(r"^[-*]\s+", lines[i].strip()):
                item = re.sub(r"^[-*]\s+", "", lines[i].strip())
                out.append(f"<li>{inline(item)}</li>")
                i += 1
            out.append("</ul>")
            continue

        # 有序列表
        if re.match(r"^\d+[.、]\s+", s):
            out.append("<ol>")
            while i < n and re.match(r"^\d+[.、]\s+", lines[i].strip()):
                item = re.sub(r"^\d+[.、]\s+", "", lines[i].strip())
                out.append(f"<li>{inline(item)}</li>")
                i += 1
            out.append("</ol>")
            continue

        # 普通段落
        out.append(f"<p>{inline(s)}</p>")
        i += 1

    body = "\n".join(out)
    # 闭合每个 section
    body = body.replace("__SECTION__", "")
    parts = body.split("<section class=\"card")
    fixed = parts[0]
    for p in parts[1:]:
        fixed += '<section class="card' + p + "</section>"
    return fixed


CSS = """
*{box-sizing:border-box}
body{margin:0;padding:0;background:#f5f6f8;color:#1f2329;
 font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",
 "Hiragino Sans GB",sans-serif;line-height:1.75;font-size:16px}
.wrap{max-width:900px;margin:0 auto;padding:22px 16px 60px}
h1{font-size:25px;line-height:1.4;margin:6px 0 18px;font-weight:700}
.card{background:#fff;border-radius:12px;padding:6px 18px 16px;margin:16px 0;
 box-shadow:0 1px 3px rgba(0,0,0,.06);border-left:6px solid #d0d3d8}
.card h2{font-size:19px;margin:16px 0 12px;padding:0;border:0;display:flex;
 align-items:center;gap:8px;flex-wrap:wrap}
.card .icon{font-size:20px;line-height:1}
.urgent{border-left-color:#d93025;background:linear-gradient(180deg,#fff5f4,#fff 90px)}
.urgent h2{color:#b3261e}
.ready{border-left-color:#188038;background:linear-gradient(180deg,#f2fbf5,#fff 90px)}
.ready h2{color:#0d652d}
.auth{border-left-color:#e37400;background:linear-gradient(180deg,#fff9f0,#fff 90px)}
.auth h2{color:#a35b00}
.free{border-left-color:#1a73e8;background:linear-gradient(180deg,#f2f8ff,#fff 90px)}
.free h2{color:#1558b0}
.note{border-left-color:#9aa0a6}
.disclaimer{border-left-color:#9aa0a6;background:#fafafa}
h3{font-size:17px;margin:18px 0 8px;color:#2a2f36}
h4{font-size:16px;margin:14px 0 6px;color:#2a2f36}
p{margin:10px 0}
ul,ol{margin:10px 0;padding-left:22px}
li{margin:6px 0}
.tw{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:12px 0}
table{border-collapse:collapse;width:100%;font-size:15px;min-width:520px}
th,td{padding:9px 11px;border-bottom:1px solid #e8eaed;text-align:left;vertical-align:top}
th{background:#f1f3f4;font-weight:600;white-space:nowrap;color:#3c4043}
tbody tr:nth-child(even){background:#fbfbfc}
tbody tr:hover{background:#f5f8ff}
td:first-child{font-weight:600;color:#1f2329}
code{background:#f1f3f4;border-radius:4px;padding:1px 6px;font-size:14px;
 font-family:ui-monospace,Consolas,monospace;word-break:break-all}
a{color:#1a73e8;text-decoration:none;word-break:break-all}
a:hover{text-decoration:underline}
.note{background:#f8f9fa;border-left:4px solid #c6c9ce;border-radius:6px;
 padding:11px 14px;margin:12px 0;font-size:15px;color:#454b52}
strong{color:#111}
.foot{margin-top:26px;font-size:13px;color:#8a8f96;text-align:center;line-height:1.9}
@media(max-width:600px){
 body{font-size:15px}
 .wrap{padding:14px 10px 44px}
 h1{font-size:21px}
 .card{padding:4px 13px 12px;border-left-width:5px}
 table{font-size:14px}
 th,td{padding:8px 9px}
}
"""


def main():
    if len(sys.argv) < 2:
        print("用法: python render_html.py <清单.md> [输出目录]")
        sys.exit(1)
    md_path = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(md_path))
    os.makedirs(outdir, exist_ok=True)

    with open(md_path, encoding="utf-8") as f:
        md = f.read()

    title = "赛博鸡蛋"
    m = re.search(r"^#\s+(.+)$", md, re.M)
    if m:
        title = re.sub(r"[*`]", "", m.group(1)).strip()

    body = render_md(md)
    stamp = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<title>{esc(title)}</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
{body}
<div class="foot">赛博鸡蛋 · 生成于 {stamp}<br>
信息来自各厂商公开渠道，参与前请以官方页面为准</div>
</div>
</body>
</html>
"""

    stem = os.path.splitext(os.path.basename(md_path))[0]
    out_path = os.path.join(outdir, stem + ".html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(doc)
    size = os.path.getsize(out_path)
    print(f"✅ HTML：{out_path}（{size:,} 字节）")


if __name__ == "__main__":
    main()
