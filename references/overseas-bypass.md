# 赛博鸡蛋 · 境外信源绕行通道（实测）

实测时间：2026年9月19日。**本文件解决一个问题：境外官网在本机网络下不通时，怎么照样拿到它的免费额度消息。**

所有通道均为实测结论，非推测。探测脚本在项目 `_probe/` 下，可复跑复核。

---

## 零、一句话结论

境外平台**不是只能靠搜索**。实测打通五条通道，其中**镜像站替代**与**国内媒体搬运**最可靠，
**搜索**是唯一能覆盖全部境外平台（含 Google 全系）的兜底。

| 通道 | 覆盖对象 | 可靠性 | 是否可程序化 |
|---|---|---|---|
| 一、镜像站替代 | HuggingFace（**必需**）、GitHub（**仅作冗余，直连可用**）、OpenAI 文档 | ★★★★★ | ✅ |
| 二、官方 RSS / 旁路 | OpenAI、Google DeepMind、GitHub、Anthropic、Stability | ★★★★ | ✅ |
| 三、国内媒体搬运 | 全部境外厂商（中文报道） | ★★★★ | ✅ |
| 四、免费额度／价格专门站 | 境外全行业横向对比 | ★★★★ | ✅ |
| 五、搜索 | **全部**，含 Google 全系官方页 | ★★★★★ | 半（需工具） |
| 附、RSSHub 公共实例 | 仅 4 个路由可用 | ★★ | ✅ |

---

## 一、通道一：镜像站替代（最可靠）

### 1.1 HuggingFace → `hf-mirror.com`

`huggingface.co` 直连失败，但**境内镜像 `hf-mirror.com` 全套可用**，可当替身：

| 路径 | 实测 |
|---|---|
| `hf-mirror.com/` | ✅ 200，13.7 KB |
| `hf-mirror.com/api/models?sort=trendingScore&limit=N` | ✅ 200，返回 JSON（含 id／下载／点赞／创建日） |
| `hf-mirror.com/models?sort=trending` | ✅ 200，369.7 KB（趋势模型页） |
| `hf-mirror.com/blog` | ✅ 200，291.1 KB |
| `hf-mirror.com/api/daily_papers` | ✅ 200，316.9 KB，50 条（含标题／摘要／上票） |
| `hf-mirror.com/papers` | ✅ 200，444.1 KB |
| `hf-mirror.com/pricing` | ✅ 200，13.1 KB |

**实测取回的模型**（证明是真数据，不是壳页）：`deepseek-ai/DeepSeek-V4.1-Flash`、
`Qwen/Qwen3.8-27B`、`Edge0/Edge0-35B-A3B-preview`。

**注意**：`/papers` 复测出现 **429 限流**。镜像站限流比源站严，**不要高频连抓**，一天一次足够。

### 1.2 GitHub：raw 与 API 均可直连，镜像只作冗余

**先纠正一条错记录**：本文件初版写「`raw.githubusercontent.com` 直连不通（超时）」，经 6 次复测**推翻**——
**直连稳定可达（6/6，28,367 B，7.9 s）**，且与镜像取回的字节数完全一致。当时那次「超时」是网络抖动窗口，不构成域名级封锁。

| 通道 | 实测 | 说明 |
|---|---|---|
| **`raw.githubusercontent.com` 直连** | ✅ **6/6**，28,367 B，7.9 s | **首选**，不必绕镜像 |
| **`api.github.com`** | ✅ **6/6**，7,399 B／37,648 B | 仓库元数据与 Release 走它 |
| **`github.com` 主站首页** | ✅ 6/6，575,829 B，22.4 s | 网页可达 |
| **`github.com/trending`** | ✅ 6/6，646,404 B，31.5 s | 慢但可用 |
| **`github.com` 仓库页** | ⚠️ 5/6，495,032 B | 一次 `IncompleteRead`（传输中断） |
| **`github.com/features/copilot/plans`** | ⚠️ 5/6，**1,258,668 B** | 1.26 MB，单次 15–25 s，**须放宽超时** |
| **`github.blog/feed/`** | ✅ 6/6，741,733 B，12.2 s | 官方发布渠道 |

**加速镜像（保留作冗余与抗抖动，不再是唯一通道）**：

| 镜像 | 实测 | 用法 |
|---|---|---|
| `ghproxy.net` | ✅ 6/6，28,367 B，10.8 s | `ghproxy.net/https://raw.githubusercontent.com/<path>` |
| `gh-proxy.com` | ✅ 200，28,367 B（复测偶发超时） | 同上路径拼接 |
| `gh.xxooo.cf` | ✅ 200，27.7 KB，2,448 ms | 同上 |
| `cdn.jsdelivr.net/gh/<owner>/<repo>@<branch>/<file>` | ✅ 200 | 路径规则不同，走 CDN |
| ~~`gh.llkk.cc`／`ghp.ci`／`github.moeyy.xyz`／`hub.gitmirror.com`／`raw.gitmirror.com`／`raw.kkgithub.com`~~ | ❌ 全部不通 | 不要再用 |

**纪律**：直连优先，**失败再轮换镜像**（`ghproxy.net` → `gh-proxy.com` → `gh.xxooo.cf` → jsDelivr）。
脚本 `fetch_overseas.py` 已按此顺序实现。

### 1.3 OpenAI 文档 → `openai.wiki`（中文镜像）

`platform.openai.com/docs` 返回 403，但 `openai.wiki` 可达（✅ 200，102.7 KB），
是 OpenAI 文档的中文镜像站，可作文档类信息的替代通道。

---

## 二、通道二：官方 RSS 与旁路路径（直连）

**这是绕开官网封锁的最优通道**：官网首页封锁，但 RSS 端点常不设防。

| 目标 | 地址 | 实测 | 说明 |
|---|---|---|---|
| **OpenAI News RSS** | `openai.com/news/rss.xml` | ✅ 200，**720.6 KB** | 官网 403，RSS 通。主通道 |
| OpenAI Blog RSS | `openai.com/blog/rss.xml` | ✅ 200，720.6 KB | 同上（两条内容一致） |
| **OpenAI Status** | `status.openai.com` | ✅ 200，802.1 KB | 服务事件与故障公告 |
| **Google DeepMind Blog RSS** | `deepmind.google/blog/rss.xml` | ✅ 200，69.8 KB | **Google 系唯一打通的口** |
| **GitHub 官方博客 RSS** | `github.blog/feed/` | ✅ 200，**724.3 KB** | 官方发布渠道 |
| GitHub 官方博客 | `github.blog` | ✅ 200，280.7 KB | — |
| Anthropic News 页 | `anthropic.com/news` | ✅ 200，451.7 KB | Anthropic 官网本身可达 |
| Stability AI News | `stability.ai/news` | ✅ 200，314.7 KB | 生图类中少数可达者 |

### 已确认不通，不要浪费时间去试

| 目标 | 实测 |
|---|---|
| `blog.google/technology/ai/rss/` | ❌ 连接失败 |
| `developers.googleblog.com/feeds/posts/default` | ❌ 连接失败 |
| `cloudblog.withgoogle.com/rss/` | ❌ 连接失败 |
| `blog.google/rss/` | ❌ 连接失败 |
| `ai.meta.com/blog/rss/`、`ai.meta.com/blog/` | ❌ 连接失败 |
| `mistral.ai/news`、`docs.mistral.ai` | ❌ 连接失败 |
| `x.ai/news` | ❌ 连接失败 |
| `huggingface.co/blog/feed.xml` | ❌ 连接失败（**改走 hf-mirror**） |
| `perplexity.ai/hub/blog` | ❌ 连接失败 |
| `midjourney.com/updates` | ❌ 403 |
| `runwayml.com/news` | ❌ 连接失败 |
| `lumalabs.ai/news`、`pika.art/blog` | ❌ 连接失败 |
| `platform.openai.com/docs/changelog` | ❌ 403 |
| `lmarena.ai` | ❌ 连接失败 |
| ~~`github.com/trending`~~ | ✅ **实为可达**（6/6，646 KB，31.5 s）——初版记为「超时」系误判，已纠正 |

**判据**：`连接失败`＝域名级不可达，换路径也无用；`403`＝服务端反爬（Cloudflare），
换 UA 或加 Referer 偶尔能过，但**不值得为它花时间**，直接转通道三／五。

### ⚠️ 判定「不可达」前必须排除的三种假象

本产线**两次**把可达的域名误判为不可达，原因都不是封锁，而是下面三种假象。下结论前逐条排除：

| 假象 | 实测案例 | 排除办法 |
|---|---|---|
| **大页面在紧超时内传不完** | `github.com/features/copilot/plans` 1.26 MB，用 25 s 超时**连续 5 次失败**（RemoteDisconnected／TimeoutError），误判为「github.com 被墙」；放宽到 45–75 s 后 **5/6 成功** | **页面越大超时越要放宽**。0.5 MB 以上给 45 s，1 MB 以上给 75 s |
| **传输中断（IncompleteRead）** | 495 KB 的仓库页 6 次中 1 次 `IncompleteRead` | 属传输未完成，**与超时同类，一并重试**，不是封锁 |
| **单次网络抖动窗口** | `raw.githubusercontent.com` 初测超时被记为「直连不通」，复测 **6/6 稳定可达**（28,367 B，7.9 s） | **至少 5–6 次复测**才可判定；单次结果一律不定论 |

**唯一可信的判据**：同一目标**多次复测仍全败**，且换路径（RSS／API／镜像）同样全败。
只测一两次就写进「不可达」名单，会把好通道封死——**这比漏掉一个信源更糟**。

---

## 三、通道三：国内科技媒体搬运（时效性最好的一路）

境外厂商的动作，国内媒体通常几小时内出中文稿。**实测 17/17 主站可达、5 条 RSS 可读**。

### 可读 RSS（推荐，直接进脚本）

| 媒体 | RSS | 实测 |
|---|---|---|
| **量子位** | `qbitai.com/feed` | ✅ 200，6.3 KB（备用 `/feed/atom` 7.1 KB） |
| **IT之家** | `ithome.com/rss/` | ✅ 200，**208.9 KB** |
| **爱范儿** | `ifanr.com/feed` | ✅ 200，**474.5 KB** |
| **InfoQ 中国** | `infoq.cn/feed` | ✅ 200，13.5 KB |
| **开源中国** | `oschina.net/news/rss` | ✅ 200，42.6 KB |
| **少数派** | `sspai.com/feed` | ✅ 200，6.2 KB |

### 主站可达（需解析页面）

新智元（`aiera.com.cn`，110 KB）、通往 AGI 之路（`waytoagi.com`，224 KB）、
AI 工具集（`ai-bot.cn`，724 KB）、AIBase（`aibase.com`，185 KB；资讯页 `news.aibase.com/zh/news`）、
智东西、雷峰网、钛媒体、虎嗅、品玩、cnBeta、新浪科技、网易科技、澎湃科技、观察者网科技、
C114 通信、DONEWS、CSDN AI、36氪 AI。

### 不可达

知乎热榜（403）、知乎专栏（403）、极客公园（403）、IT桔子（412）、
今日头条科技（可达但仅 4.8 KB，无有效内容）。

**用法纪律**：国内媒体的报道**属乙级信源**——可采信、须标注来源，
但**涉及具体额度数字与截止日期时，仍要回官方页面核实**。国内媒体转述常省略限制条件。

---

## 四、通道四：免费额度与价格专门站（全在境外，但本机可直连）

**这是本轮最重要的发现之一**：几个专门做「免费额度」与「价格对比」的站点，
虽是境外主体，**本机网络下全部可直连**，且信息密度远高于综合聚合站。

| 站点 | 地址 | 实测 | 价值 |
|---|---|---|---|
| **freellm.net** | `freellm.net` | ✅ 200，156.9 KB | **最高**。收录 **30 家 provider**，逐家一页 |
| **llm-price.com** | `llm-price.com` | ✅ 200，300.4 KB | **最高**。价格对比表含**上架时间**（"yesterday"／"2 days ago"） |
| **freetokens** | `freetokens.custats.info` | ✅ 200，504.2 KB | 免费额度专门站，含核实状态与更新日期 |
| **Artificial Analysis** | `artificialanalysis.ai` | ✅ 200，1,735.2 KB | 模型能力与价格综合对比（响应慢，约 14 s） |
| **free-llm.com** | `free-llm.com` | ✅ 200，168.6 KB | 免费 API 汇总（**数据靠 JS 加载，直抓取不到表格**，只作线索） |
| **llm-prices.com** | `llm-prices.com` | ✅ 200，39.5 KB | 价格表（表格窄，价值低于 llm-price.com） |
| **aipricing.guru** | `aipricing.guru` | ✅ 200，111.3 KB | 价格对比（慢，约 18 s） |
| **OpenRouter API** | `openrouter.ai/api/v1/models` | ✅ 200，722.4 KB | 免密钥；双零价模型实时判定 |
| ~~`free-model.com`~~ | — | ⚠️ 308 | 需跟随重定向 |
| ~~`tokenprice.io`~~／~~`openllmleaderboard.com`~~ | — | ❌ 403／连接失败 | 不要用 |

### freellm.net 的用法（重点）

它**逐家 provider 一页**，页面含：免费模型清单、速率限制（RPM／RPD）、
上下文长度、**是否需要信用卡**、最近更新日期。实测 Gemini 页读出：
`15 RPM / 500 RPD`、`1M context`、11 个免费模型（`gemini-3.8-flash` 至 `gemini-2.5-flash-lite`）。

抓 **`/providers/<slug>`** 页面即可拿到该家境外平台当前的免费档细节——
**这是替代「直连境外官网」的最佳单点方案。**

已探明的 30 个 slug：`nvidia-nim`、`openrouter`、`ollama-cloud`、`google-gemini`、
`agnes-ai`、`modelscope`、`kilo-code`、`llm7-io`、`cloudflare-workers-ai`、`cline`、
`ovhcloud-ai-endpoints`、`z-ai-zhipu-ai`、`opencode`、`groq`、`github-models`、
`mistral-ai`、`cohere`、`glhf-chat`、`siliconflow`、`aion-labs`、`chutes-ai`、
`hugging-face`、`grok-xai`、`sambanova`、`xai`、`deepseek`、
`alibaba-cloud-model-studio`、`ai21-labs`、`nebius`、`nscale`。

### llm-price.com 的用法（重点）

表格结构规整：`名称 | 上架时间 | 上下文 | 输入价 | 输出价 | 总价 | 供应商`。
**「上架时间」列是境外厂商动作最灵敏的哨点**——新模型上线、降价都会立刻反映。
实测读出样例：`PrismML: Ternary Bonsai 2 27B`（yesterday）、`DeepSeek: DeepSeek Pro Latest`（5 days ago）。

---

## 五、通道五：搜索（覆盖全部，含最难的 Google）

**这是唯一能覆盖 100% 境外平台的通道。**
实测：`ai.google.dev`（本机完全不通）的官方定价页，经搜索取回了**完整中文官方口径**——
Gemini 3.5 Flash 免费档、`$1.50/$9.00` 付费价、每月 5,000 次免费搜索等，数据完整可用。

搜索引擎可达性实测：

| 引擎 | 实测 |
|---|---|
| Bing 国际 | ✅ 200，96.7 KB |
| Bing 中国 | ✅ 200，92.9 KB |
| 搜狗 | ✅ 200（仅 5.5 KB，疑壳页） |
| 百度 | ✅ 200（仅 1.5 KB，疑壳页） |
| DuckDuckGo HTML | ❌ 连接失败 |

**注意**：Bing 结果页**可达但不可直接解析**——实测 `cn.bing.com/search` 返回 96 KB，
但按 `<h2><a href=...>` 结构解析出**0 条**（页面结构已变或结果为 JS 渲染）。
程序化搜索不要指望 Bing 抓取，**直接用工具的搜索能力**。

---

## 附、RSSHub 公共实例：可用但覆盖率低（勿高估）

RSSHub 能把任意网站变 RSS，理论上是最强绕行手段。**但实测公共实例覆盖率很低**：

| 实例 | 实测 |
|---|---|
| `rsshub.rssforever.com` | ✅ 可达 |
| `rsshub.liumingye.cn` | ✅ 可达 |
| `rsshub.woodland.cafe` | ✅ 可达 |
| `rsshub.app`（官方） | ❌ 不通 |
| `rss.shab.fun`／`rsshub.pseudoyu.com`／`rsshub.hanxitoday.com`／`rsshub.henry.wang`／`rsshub.ktachibana.workers.dev` | ❌ 全部不通 |
| `rsshub.owo.nz` | ❌ HTTP 错误 |

**路由覆盖率实测：仅 4/29 可用**（大量 503——公共实例访问境外源站同样受限）：

| 可用路由 | 说明 |
|---|---|
| `/openai/news` | ✅ 353 KB RSS，三个实例均可用 |
| `/huggingface/daily-papers` | ✅ 54.7 KB，三实例均可用 |
| `/hackernews/best` | ✅ 16.4 KB，9 条（2/3 实例可用） |
| `/ithome/it` | ✅ 77 KB（2/3 实例可用） |

不可用路由（503／超时）：`/google/ai/blog`、`/xai/news`、`/mistral/news`、
`/meta/ai/blog`、`/anthropic/news`、`/deepmind/blog`、`/github/blog`、
`/github/trending`、`/reddit/subreddit/LocalLLaMA`、`/twitter/user/OpenAI`、
`/arxiv/cs/AI`、`/v2ex/topics/hot`、`/36kr/newsflash` 等。

**结论**：RSSHub 只作**补充**，不列为境外主通道。**「RSSHub 能变出任何 RSS」是误解**，
至少公共实例做不到——公共实例自身也受网络与限流约束。

---

## 六、境外平台 → 绕行方案对照表（按平台查，直接用）

| 平台 | 官网状态 | 走哪条通道 |
|---|---|---|
| **OpenAI** | ❌ 403 | 官方 News RSS（720 KB）＋ OpenAI Status ＋ `openai.wiki` ＋ freellm.net `/providers/azure-openai` 类页 ＋ 搜索 |
| **Google ／ Gemini** | ❌ 连接失败 | **DeepMind Blog RSS** ＋ freellm.net `/providers/google-gemini`（含 15 RPM/500 RPD）＋ 搜索（实测可取官方定价页中文口径） |
| **xAI ／ Grok** | ❌ 连接失败 | freellm.net `/providers/xai`、`/providers/grok-xai` ＋ GitHub Models（含 Grok 免费档）＋ 搜索 |
| **Meta ／ Llama** | ❌ 连接失败 | 搜索 ＋ 国内媒体 ＋ hf-mirror（模型权重必上 HF） |
| **Mistral** | ❌ 连接失败 | freellm.net `/providers/mistral-ai` ＋ 搜索 |
| **HuggingFace** | ❌ 连接失败 | **hf-mirror.com 全套**（模型 API／博客／论文／趋势） |
| **Perplexity** | ❌ 连接失败 | 搜索 ＋ 国内媒体 |
| **Midjourney** | ❌ 403 | 搜索 ＋ 国内媒体（小程序活动须留意） |
| **Runway ／ Luma ／ Pika** | ❌ 403／连接失败 | 搜索 ＋ 国内媒体 |
| **Anthropic** | ✅ 官网可达 | 直抓 `anthropic.com/pricing`（哨兵已监控） |
| **Cohere／Groq／Together／Cerebras／NVIDIA／SambaNova／Cloudflare／Novita／Nebius／Fireworks** | ✅ 部分可达 | 官网直抓（403 者）＋ freellm.net 对应 provider 页 |
| **GitHub Models** | ✅ 可达 | 直抓 ＋ freellm.net `/providers/github-models`（含 Grok 免费档） |

---

## 七、维护记录

| 日期 | 变更 |
|---|---|
| 2026-09-19 | 初版。四轮探测共 80 余个目标，打通五条境外绕行通道；发现 hf-mirror 可当 HuggingFace 替身、freellm.net 与 llm-price.com 为境外最佳专门站；推翻「RSSHub 可变任意站为 RSS」的设想（实测公共实例仅 4/29 路由可用） |
| 2026-09-19 | **纠错**：初版记「`raw.githubusercontent.com` 直连不通」为误判——复测 6/6 稳定可达（28,367 B，7.9 s），镜像降为冗余；`github.com` 首页／趋势页／API 均 6/6 可达，`github.com/trending` 的「超时」记录同样作废。新增〈判定「不可达」前必须排除的三种假象〉一节 |
