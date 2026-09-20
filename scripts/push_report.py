# -*- coding: utf-8 -*-
"""把每日清单推到手机／群：八类通道，纯标准库，零第三方依赖。

支持的通道（配置文件里逐个启用，互不影响）：

    dingtalk    钉钉自定义机器人（支持加签）
    feishu      飞书自定义机器人（支持加签）
    wecom       企业微信群机器人
    serverchan  Server酱（微信推送）
    pushplus    PushPlus（微信推送）
    bark        Bark（iOS 推送）
    ntfy        ntfy（开源推送，免注册即可用）
    email       SMTP 邮件（HTML 报告可直接当正文）

用法：

    # 1. 生成配置样例，填好凭据
    python scripts/push_report.py --init

    # 2. 只做通道自检（每个启用的通道各发一条极短测试消息）
    python scripts/push_report.py --config push_config.json --probe

    # 3. 推送当日报告
    python scripts/push_report.py --config push_config.json --report out/最新一期.md

    # 4. 只看会发什么、不发出去
    python scripts/push_report.py --config push_config.json --report out/最新一期.md --dry-run

设计取舍：

  - 各通道有各自的长度上限（企业微信 markdown 仅 4096 字节），超长一律
    截断并附一行说明，**不发半截被平台静默丢弃的内容**；
  - 发送失败不中断其余通道，逐通道报告成功／失败与可行动的提示；
  - 凭据只从配置文件读，不写死在脚本里，也不接受命令行明文传参（避免进 shell 历史）。
"""

import argparse
import base64
import hashlib
import hmac
import io
import json
import os
import smtplib
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 严格证书校验，不提供关闭开关
CTX = ssl.create_default_context()
UA = "saibo-egg-push/1.0"

TITLE_DEFAULT = "今天能领什么"

# 各通道正文上限（字节），留出安全余量
LIMITS = {
    "dingtalk": 18000,
    "feishu": 18000,
    "wecom": 3900,
    "serverchan": 30000,
    "pushplus": 20000,
    "bark": 1800,
    "ntfy": 3900,
    "email": 400000,
}

# 各通道常见错误码的可行动解释。命中即给出下一步，而不是甩一个数字。
ERR_HINT = {
    "dingtalk": {
        300001: "access_token 无效，到群机器人设置里重新复制",
        300005: "access_token 不存在：多半是复制时漏了尾部字符，或该机器人已被删除，回群设置里重新取一次",
        310000: "安全设置不匹配：机器人若开了「自定义关键词」，消息里必须含该词；若开了「加签」，需在配置里填 secret",
        130101: "发送过于频繁，钉钉限每分钟 20 条，稍后重试",
        400013: "消息内容为空或被判定为违规",
    },
    "feishu": {
        19021: "签名校验失败：检查 secret 是否正确、系统时间是否偏差过大",
        19024: "关键词不匹配：机器人开了关键词过滤，正文需含所设关键词",
        9499: "请求体过大，缩短正文",
        19001: "webhook 地址无效或机器人已停用",
    },
    "wecom": {
        93000: "webhook key 无效，到群机器人设置里重新复制",
        45009: "调用超过频率限制",
        40008: "消息内容为空",
        40058: "消息过长，企业微信 markdown 上限 4096 字节",
    },
    "serverchan": {
        40001: "SendKey 错误，到 sct.ftqq.com 复制新的",
        40003: "发送内容为空",
        43004: "免费额度已用完，次日恢复",
    },
    "pushplus": {
        903: "token 无效，到 pushplus.plus 复制新的",
        902: "当日推送次数已用完",
        999: "请求参数有误",
    },
    "bark": {
        400: "推送内容为空或格式有误",
        404: "device key 不存在，检查 Bark 应用里显示的 key",
    },
    "ntfy": {
        429: "发送过于频繁，ntfy 对同一主题有速率限制",
        413: "消息体过大，缩短正文",
    },
}

CONFIG_SAMPLE = {
    "_说明": "把 enabled 改为 true 的通道才会被推送。凭据只填本机文件，勿提交到版本库。",
    "dingtalk": {
        "enabled": False,
        "access_token": "",
        "secret": "",
        "_备注": "secret 仅在机器人开启「加签」时填写；开启「自定义关键词」时，把关键词写进 keyword 由脚本自动补进标题",
        "keyword": "",
    },
    "feishu": {
        "enabled": False,
        "webhook": "https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx",
        "secret": "",
    },
    "wecom": {"enabled": False, "key": "", "_备注": "群机器人 webhook 的 key 参数值"},
    "serverchan": {"enabled": False, "sendkey": ""},
    "pushplus": {"enabled": False, "token": "", "topic": ""},
    "bark": {
        "enabled": False,
        "device_key": "",
        "server": "https://api.day.app",
        "_备注": "自建 Bark 服务端时改 server",
    },
    "ntfy": {
        "enabled": False,
        "topic": "",
        "server": "https://ntfy.sh",
        "_备注": "topic 自取一个不易撞名的字符串，手机装 ntfy 应用订阅同一主题即可收；无需注册",
    },
    "email": {
        "enabled": False,
        "smtp_host": "smtp.qq.com",
        "smtp_port": 465,
        "use_ssl": True,
        "user": "",
        "password": "",
        "to": [],
        "_备注": "password 填邮箱授权码而非登录密码；465 用 SSL，587 用 STARTTLS（use_ssl 置 false）",
    },
}


# ---------------------------------------------------------------- 工具

def out(msg=""):
    print(msg)


def truncate(text, limit, note="……（超长已截断，完整版见输出目录）"):
    """按字节截断，且不把多字节字符切一半。"""
    raw = text.encode("utf-8")
    if len(raw) <= limit:
        return text
    keep = limit - len(note.encode("utf-8"))
    cut = raw[:keep]
    # 回退到最后一个完整字符边界
    while cut:
        try:
            s = cut.decode("utf-8")
            return s + note
        except UnicodeDecodeError:
            cut = cut[:-1]
    return note


def http_post(url, data=None, headers=None, timeout=20, method="POST"):
    hdrs = {"User-Agent": UA}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    op = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=CTX)
    )
    with op.open(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", "replace")


def post_json(url, payload, timeout=20):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return http_post(url, body, {"Content-Type": "application/json; charset=utf-8"}, timeout)


def hint(channel, code, default=""):
    m = ERR_HINT.get(channel) or {}
    try:
        return m.get(int(code)) or default
    except (TypeError, ValueError):
        return default


def read_report(path):
    with io.open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


# ---------------------------------------------------------------- 各通道发送

def send_dingtalk(cfg, title, body):
    token = cfg.get("access_token") or ""
    if not token:
        return False, "未填 access_token"
    url = "https://oapi.dingtalk.com/robot/send?access_token=" + urllib.parse.quote(token)
    secret = cfg.get("secret") or ""
    if secret:
        ts = str(int(time.time() * 1000))
        sign_src = "%s\n%s" % (ts, secret)
        sign = urllib.parse.quote_plus(
            base64.b64encode(
                hmac.new(secret.encode("utf-8"), sign_src.encode("utf-8"), hashlib.sha256).digest()
            ).decode("utf-8")
        )
        url += "&timestamp=%s&sign=%s" % (ts, sign)
    kw = cfg.get("keyword") or ""
    if kw and kw not in title:
        title = "%s %s" % (kw, title)
    payload = {"msgtype": "markdown", "markdown": {"title": title, "text": body}}
    st, txt = post_json(url, payload)
    d = json.loads(txt) if txt.strip().startswith("{") else {}
    if d.get("errcode") == 0:
        return True, "已推送"
    return False, "errcode=%s %s" % (d.get("errcode"), hint("dingtalk", d.get("errcode"), d.get("errmsg", "")))


def send_feishu(cfg, title, body):
    url = cfg.get("webhook") or ""
    if not url:
        return False, "未填 webhook"
    secret = cfg.get("secret") or ""
    if secret:
        ts = str(int(time.time()))
        sign_src = "%s\n%s" % (ts, secret)
        sign = base64.b64encode(
            hmac.new(sign_src.encode("utf-8"), b"", hashlib.sha256).digest()
        ).decode("utf-8")
        payload = {
            "timestamp": ts,
            "sign": sign,
            "msg_type": "text",
            "content": {"text": "%s\n\n%s" % (title, body)},
        }
    else:
        payload = {"msg_type": "text", "content": {"text": "%s\n\n%s" % (title, body)}}
    st, txt = post_json(url, payload)
    d = json.loads(txt) if txt.strip().startswith("{") else {}
    code = d.get("code", d.get("StatusCode"))
    if code == 0:
        return True, "已推送"
    return False, "code=%s %s" % (code, hint("feishu", code, d.get("msg", "")))


def send_wecom(cfg, title, body):
    key = cfg.get("key") or ""
    if not key:
        return False, "未填 key"
    url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=" + urllib.parse.quote(key)
    payload = {"msgtype": "markdown", "markdown": {"content": "**%s**\n%s" % (title, body)}}
    st, txt = post_json(url, payload)
    d = json.loads(txt) if txt.strip().startswith("{") else {}
    if d.get("errcode") == 0:
        return True, "已推送"
    return False, "errcode=%s %s" % (d.get("errcode"), hint("wecom", d.get("errcode"), d.get("errmsg", "")))


def send_serverchan(cfg, title, body):
    key = cfg.get("sendkey") or ""
    if not key:
        return False, "未填 sendkey"
    url = "https://sctapi.ftqq.com/%s.send" % urllib.parse.quote(key)
    form = urllib.parse.urlencode({"title": title, "desp": body}).encode("utf-8")
    st, txt = http_post(url, form, {"Content-Type": "application/x-www-form-urlencoded"})
    d = json.loads(txt) if txt.strip().startswith("{") else {}
    code = d.get("code")
    if code == 0:
        return True, "已推送"
    return False, "code=%s %s" % (code, hint("serverchan", code, d.get("message", "")))


def send_pushplus(cfg, title, body):
    token = cfg.get("token") or ""
    if not token:
        return False, "未填 token"
    payload = {"token": token, "title": title, "content": body, "template": "markdown"}
    if cfg.get("topic"):
        payload["topic"] = cfg["topic"]
    st, txt = post_json("https://www.pushplus.plus/send", payload)
    d = json.loads(txt) if txt.strip().startswith("{") else {}
    if str(d.get("code")) == "200":
        return True, "已推送"
    return False, "code=%s %s" % (d.get("code"), hint("pushplus", d.get("code"), str(d.get("msg", ""))[:120]))


def send_bark(cfg, title, body):
    key = cfg.get("device_key") or ""
    if not key:
        return False, "未填 device_key"
    server = (cfg.get("server") or "https://api.day.app").rstrip("/")
    payload = {"title": title, "body": body, "group": "赛博鸡蛋"}
    st, txt = post_json("%s/push" % server, payload)
    d = json.loads(txt) if txt.strip().startswith("{") else {}
    if str(d.get("code")) == "200":
        return True, "已推送"
    return False, "code=%s %s" % (d.get("code"), hint("bark", d.get("code"), str(d.get("message", ""))[:120]))


def send_ntfy(cfg, title, body):
    topic = cfg.get("topic") or ""
    if not topic:
        return False, "未填 topic（自取一个不易撞名的字符串即可，无需注册）"
    server = (cfg.get("server") or "https://ntfy.sh").rstrip("/")
    from email.header import Header as _H
    headers = {
        # Title 是 HTTP 头，中文必须做 RFC 2047 编码，否则会在编解码链路上被破坏
        "Title": _H(title, "utf-8").encode(),
        "Markdown": "yes",
        "Content-Type": "text/markdown; charset=utf-8",
    }
    st, txt = http_post("%s/%s" % (server, urllib.parse.quote(topic)), body.encode("utf-8"), headers)
    if st == 200:
        return True, "已推送"
    return False, "HTTP %s %s" % (st, hint("ntfy", st, txt[:120]))


def send_email(cfg, title, body, html_body=None):
    host = cfg.get("smtp_host") or ""
    user = cfg.get("user") or ""
    pwd = cfg.get("password") or ""
    to = cfg.get("to") or []
    if isinstance(to, str):
        to = [x.strip() for x in to.replace(";", ",").split(",") if x.strip()]
    if not (host and user and pwd and to):
        return False, "smtp_host／user／password／to 必须齐全"
    port = int(cfg.get("smtp_port") or 465)
    use_ssl = cfg.get("use_ssl", True)
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.utils import formataddr, formatdate

    msg = MIMEMultipart("alternative") if html_body else MIMEText(body, "plain", "utf-8")
    msg["Subject"] = title
    msg["From"] = formataddr((str(header_safe(user)), user))
    msg["To"] = ", ".join(to)
    msg["Date"] = formatdate(localtime=True)
    if html_body:
        msg.attach(MIMEText(body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))
    raw = msg.as_string().encode("utf-8")

    if use_ssl:
        s = smtplib.SMTP_SSL(host, port, timeout=30, context=CTX)
    else:
        s = smtplib.SMTP(host, port, timeout=30)
        s.ehlo()
        s.starttls(context=CTX)
        s.ehlo()
    try:
        s.login(user, pwd)
        s.sendmail(user, to, raw)
        return True, "已投递至 %s" % ", ".join(to)
    finally:
        try:
            s.quit()
        except Exception:
            pass


def header_safe(user):
    """发件人显示名：非 ASCII 交由 MIMEText 编码。"""
    return user.split("@")[0]


SENDERS = {
    "dingtalk": send_dingtalk,
    "feishu": send_feishu,
    "wecom": send_wecom,
    "serverchan": send_serverchan,
    "pushplus": send_pushplus,
    "bark": send_bark,
    "ntfy": send_ntfy,
}


# ---------------------------------------------------------------- 主流程

def cmd_init(path):
    if os.path.exists(path):
        out("配置文件已存在，未覆盖：%s" % path)
        return 1
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        try:
            os.makedirs(parent)
        except OSError as e:
            out("无法创建目录 %s：%s" % (parent, e))
            out("请确认该路径的盘符存在且有写入权限。")
            return 1
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(CONFIG_SAMPLE, ensure_ascii=False, indent=2))
    out("已生成配置样例：%s" % path)
    out("把要用的通道 enabled 改为 true 并填好凭据，再跑 --probe 自检。")
    out("提醒：该文件含凭据，勿提交到公开仓库（`.gitignore` 已含 push_config.json）。")
    return 0


def load_config(path):
    with io.open(path, "r", encoding="utf-8", errors="replace") as f:
        cfg = json.load(f)
    enabled = [k for k, v in cfg.items() if isinstance(v, dict) and v.get("enabled")]
    return cfg, enabled


def run(channels, cfg, title, body, html_body, dry, probe):
    ok_n, fail_n = 0, 0
    for ch in channels:
        conf = cfg.get(ch) or {}
        text = truncate(body, LIMITS.get(ch, 18000))
        head = "[通道自检] %s" % title if probe else title
        if dry:
            out("  [dry-run] %-11s 标题=%s  正文 %d 字节"
                % (ch, head, len(text.encode("utf-8"))))
            continue
        try:
            if ch == "email":
                ok, msg = send_email(conf, head, text, html_body)
            else:
                ok, msg = SENDERS[ch](conf, head, text)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:160]
            ok, msg = False, "HTTP %s %s" % (e.code, hint(ch, e.code, detail))
        except Exception as e:
            ok, msg = False, "%s: %s" % (type(e).__name__, str(e)[:160])
        if ok:
            ok_n += 1
            out("  [成功]     %-11s %s" % (ch, msg))
        else:
            fail_n += 1
            out("  [失败]     %-11s %s" % (ch, msg))
    return ok_n, fail_n


def main():
    ap = argparse.ArgumentParser(description="把每日清单推送到手机／群（八类通道）")
    ap.add_argument("--init", action="store_true", help="生成配置样例")
    ap.add_argument("--config", default="push_config.json", help="配置文件路径")
    ap.add_argument("--report", help="要推送的报告文件（.md）")
    ap.add_argument("--html", help="可选：同名 HTML，邮件正文用它")
    ap.add_argument("--title", default=TITLE_DEFAULT, help="推送标题")
    ap.add_argument("--channel", action="append", default=[],
                    help="只推指定通道，可重复；默认推送配置中所有已启用通道")
    ap.add_argument("--probe", action="store_true", help="只做通道自检")
    ap.add_argument("--dry-run", action="store_true", help="只打印，不发送")
    a = ap.parse_args()

    if a.init:
        return cmd_init(a.config)

    if not os.path.exists(a.config):
        out("找不到配置文件：%s" % a.config)
        out("先运行：python scripts/push_report.py --init")
        return 1

    try:
        cfg, enabled = load_config(a.config)
    except ValueError as e:
        out("配置文件不是合法 JSON：%s" % e)
        out("提示：JSON 里不能有多余逗号，字符串必须用双引号。")
        return 1

    channels = a.channel or enabled
    if not channels:
        out("配置里没有任何 enabled=true 的通道。")
        out("打开 %s，把要用的通道改为 true 并填凭据；若只想先看效果，可加 --dry-run。" % a.config)
        return 1

    unknown = [c for c in channels if c not in LIMITS]
    if unknown:
        out("不认识的通道名：%s" % ", ".join(unknown))
        out("可用通道：%s" % ", ".join(sorted(LIMITS)))
        return 1

    if a.probe:
        title, body, html_body = "推送链路自检", "这是一条通道自检消息，收到即表示链路可用。", None
    else:
        if not a.report:
            out("缺少 --report 参数（要推送的报告文件）。")
            out("例：python scripts/push_report.py --config %s --report out/最新一期.md" % a.config)
            return 1
        if not os.path.exists(a.report):
            out("报告文件不存在：%s" % a.report)
            out("先跑完每日流程生成清单，再来推送。")
            return 1
        body = read_report(a.report)
        title = a.title
        # 标题补当日日期，便于在手机上区分
        date = time.strftime("%Y-%m-%d")
        if date not in title:
            title = "%s %s" % (date, title)
        html_body = None
        if a.html and os.path.exists(a.html):
            html_body = read_report(a.html)
        elif a.report.endswith(".md"):
            guess = a.report[:-3] + ".html"
            if os.path.exists(guess):
                html_body = read_report(guess)

    mode = "自检" if a.probe else ("预演" if a.dry_run else "推送")
    out("通道%s：%s" % (mode, ", ".join(channels)))
    out("-" * 56)
    ok_n, fail_n = run(channels, cfg, title, body, html_body, a.dry_run, a.probe)
    if a.dry_run:
        out("-" * 56)
        out("预演完成，未发出任何消息。去掉 --dry-run 即真实推送。")
        return 0
    out("-" * 56)
    out("成功 %d 个，失败 %d 个。" % (ok_n, fail_n))
    if fail_n and not ok_n:
        out("全部通道失败：先确认配置文件里的凭据是否为刚复制的，再检查本机网络。")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
