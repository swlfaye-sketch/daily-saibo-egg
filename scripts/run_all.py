# -*- coding: utf-8 -*-
"""一键跑完抓取三件套，可选接上渲染与推送。

用法：
    python run_all.py <数据目录> [选项]

选项：
    --targets <文件>   指定用户自定义目标清单（默认取 <数据目录>/targets_user.json）
    --init             给哨兵建基线（只在首次运行当天需要，之后不必再加）
    --skip-overseas    跳过境外信源那一趟（网络不稳时可先跑另两趟）
    --html <清单.md>   跑完三趟后，把指定清单渲染成单文件 HTML
    --html-out <目录>  HTML 输出目录（默认与清单同目录）
    --push <配置.json> 跑完后再执行推送
    --check            只做环境自检：各脚本能否导入、目录是否可写，不抓取

设计说明：
    · **只做串联，不重复实现**——每一趟仍是各自独立的脚本，本文件不改它们的行为，
      也不替它们做判断；单独跑任意一个脚本的效果与经本文件串联完全一致。
    · **某趟失败不中断后续**：抓取类任务里单站失败是常态，中断只会让整轮白跑。
      末尾统一汇总各趟的退出码，由使用者决定是否补跑。
    · **不内置汇总成清单这一步**：把抓取结果归纳成「今天能领什么」需要理解语义，
      是宿主（或人）的活，脚本只负责把原料备齐。
"""

import io
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

# Windows 控制台默认可能是 GBK，输出中文会抛 UnicodeEncodeError；
# 统一按 UTF-8 且出错不中断（无法重设时忽略，不影响功能）。
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

STEPS = [
    ("甲路·永久免费层", "fetch_tiers.py", 1, "约 10 秒"),
    ("境外路·绕行信源", "fetch_overseas.py", 1, "约 40 秒"),
    ("哨兵·变更检测", "watch_changes.py", 1, "约 60 秒"),
]

USAGE = __doc__.split("设计说明")[0].strip()


def out(msg=""):
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


def run(script, args):
    """运行一个脚本，输出直通终端，返回 (退出码, 耗时秒)。"""
    path = os.path.join(HERE, script)
    if not os.path.exists(path):
        out("   ❌ 找不到脚本：%s" % path)
        return 127, 0.0
    t0 = time.time()
    try:
        p = subprocess.run([PY, path] + list(args))
        rc = p.returncode
    except Exception as e:
        out("   ❌ 启动失败（%s）：%s" % (type(e).__name__, e))
        rc = 1
    return rc, time.time() - t0


def main():
    if len(sys.argv) < 2:
        out(USAGE)
        return 1

    base = sys.argv[1]
    argv = sys.argv[2:]

    init = "--init" in argv
    skip_overseas = "--skip-overseas" in argv
    check_only = "--check" in argv

    def opt(name):
        if name in argv:
            i = argv.index(name)
            if i + 1 < len(argv):
                return argv[i + 1]
        return ""

    targets = opt("--targets")
    html_md = opt("--html")
    html_out = opt("--html-out")
    push_cfg = opt("--push")

    # ---- 写权限自检：目录建不出来就没必要往下跑 ----
    out("=" * 68)
    out("每天领赛博鸡蛋 · 一键流程")
    out("=" * 68)
    out("数据目录：%s" % base)
    try:
        os.makedirs(os.path.join(base, "out"), exist_ok=True)
    except Exception as e:
        out("❌ 数据目录不可写（%s）：%s" % (type(e).__name__, e))
        out("   换一个可写目录，或检查该路径是否被占用。")
        return 1
    out("Python　：%s" % PY)
    out()

    if check_only:
        out("自检模式：只核对脚本是否齐备，不联网。")
        bad = 0
        for _label, script, _nargs, _t in STEPS:
            ok = os.path.exists(os.path.join(HERE, script))
            out("   %s %s" % ("✅" if ok else "❌", script))
            bad += 0 if ok else 1
        for script in ("render_html.py", "push_report.py"):
            ok = os.path.exists(os.path.join(HERE, script))
            out("   %s %s" % ("✅" if ok else "❌", script))
            bad += 0 if ok else 1
        if targets:
            ok = os.path.exists(targets)
            out("   %s 自定义目标清单：%s" % ("✅" if ok else "❌", targets))
            bad += 0 if ok else 1
        else:
            auto = os.path.join(base, "targets_user.json")
            out("   %s 自定义目标清单：%s"
                % ("✅" if os.path.exists(auto) else "·（未提供，用内置清单）", auto))
        out()
        out("自检%s。" % ("通过" if not bad else "发现 %d 处缺失" % bad))
        return 0 if not bad else 1

    # ---- 依次执行 ----
    results = []
    for label, script, _nargs, est in STEPS:
        if skip_overseas and script == "fetch_overseas.py":
            out("── %s：已按要求跳过" % label)
            out()
            continue
        args = [base]
        if script == "watch_changes.py":
            if init:
                args.append("--init")
            if targets:
                args += ["--targets", targets]
        out("── %s（%s，%s）" % (label, script, est))
        rc, dt = run(script, args)
        results.append((label, script, rc, dt))
        out("   %s %.1f 秒" % ("✅ 完成" if rc == 0 else "⚠️ 退出码 %d" % rc, dt))
        out()

    # ---- 可选：渲染 HTML ----
    if html_md:
        out("── 渲染 HTML（%s）" % os.path.basename(html_md))
        if not os.path.exists(html_md):
            out("   ❌ 清单文件不存在：%s" % html_md)
            results.append(("渲染 HTML", "render_html.py", 1, 0.0))
        else:
            args = [html_md] + ([html_out] if html_out else [])
            rc, dt = run("render_html.py", args)
            results.append(("渲染 HTML", "render_html.py", rc, dt))
            out("   %s %.1f 秒" % ("✅ 完成" if rc == 0 else "⚠️ 退出码 %d" % rc, dt))
        out()

    # ---- 可选：推送 ----
    if push_cfg:
        out("── 推送（%s）" % os.path.basename(push_cfg))
        if not os.path.exists(push_cfg):
            out("   ❌ 配置文件不存在：%s" % push_cfg)
            results.append(("推送", "push_report.py", 1, 0.0))
        else:
            args = ["--config", push_cfg, "--probe"]
            rc, dt = run("push_report.py", args)
            results.append(("推送·通道自检", "push_report.py", rc, dt))
            out("   %s %.1f 秒" % ("✅ 完成" if rc == 0 else "⚠️ 退出码 %d" % rc, dt))
        out()

    # ---- 汇总 ----
    ok = sum(1 for r in results if r[2] == 0)
    out("=" * 68)
    out("汇总：%d 趟完成，%d 趟有问题" % (ok, len(results) - ok))
    for label, script, rc, dt in results:
        out("   %s %-22s %6.1f 秒%s"
            % ("✅" if rc == 0 else "⚠️", label, dt, "" if rc == 0 else "（退出码 %d）" % rc))

    o = os.path.join(base, "out")
    out()
    out("原料已落在：%s" % o)
    out("接下来（需要理解语义，故未写成脚本）：")
    out("   1. 读 out/ 里的三份结果，归纳成「今天到期／本周／本月／长期有效」清单；")
    out("   2. 每条写清额度、领取条件、截止日期、信源级别；")
    out("   3. 存成 out/清单_<日期>.md，再用 render_html.py 出一份手机可读的 HTML。")
    out()
    if any(r[2] != 0 for r in results):
        out("有趟数失败：抓取类脚本单站失败是常态，先看该趟自己的输出定位；")
        out("连续 3 次抓不到的目标才算失效，届时按 references/overseas-bypass.md 换通道。")
    return 0 if ok == len(results) else 2


if __name__ == "__main__":
    sys.exit(main())
