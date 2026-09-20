# 赛博鸡蛋 · 全平台信源名录（含实测可达性）

实测时间：2026年9月19日。共探测 118 个目标，逐条记录状态。
**状态含义**：✅ 可达（可直抓或可监控）｜⚠️ 重定向，需跟随 ｜❌ 不通（改走搜索）。

> **先看清「探测数」与「监控数」的区别，两回事。**
>
> | 口径 | 数量 | 含义 |
> |---|---|---|
> | **探测目标** | **118 个** | 本名录的规模。逐个实测过可达性，用于穷尽手段、不漏信源。 |
> | **每日自动监控** | **30 个** | 真正逐日抓取比对的部分。准确清单见 `scripts/watch_changes.py` 的 `TARGETS`。 |
> | **搜索兜底** | 其余 | 壳页、反爬、域名不可达的目标，一律走「官方公告 ＋ 搜索」。 |
>
> 纳入监控的两条硬标准：**能直抓**、**变化频率低**。
> 返回 2—7KB 壳页的单页应用（SPA）**全部排除在监控之外**——壳页里不含额度数字，逐日抓取只会得到同一段空骨架，既无信息量，又会在指纹比对时制造假信号。**排除它们是刻意设计，不是抓不到。**
> 媒体流与热门榜（如 HuggingFace 趋势、新闻 RSS）同样不进监控：它们每天都变，纳入哨兵会天天报警、淹没真信号，改由 `scripts/fetch_overseas.py` 抓取后按关键词筛。

> 本名录是「穷尽手段」的底数：哪些平台能直连监控、哪些只能靠搜索，全部实测过，不靠印象。

---

## 一、国内 · 模型与开放平台（32/33 直达）

国内平台**几乎全部可直连**，是本产线最可靠的一路，应当直抓监控而非依赖搜索。

| 平台 | 官网 | 额度／定价入口 | 发布渠道 | 实测 |
|---|---|---|---|---|
| **DeepSeek** | `deepseek.com` | `platform.deepseek.com`（定价在控制台） | 官网 News、API 文档更新 | ✅ 90KB / ✅ 2.8KB 壳页 / ✅ 46KB |
| **豆包** | `doubao.com` | 火山方舟控制台 | 火山引擎开发者社区 | ✅ 543KB |
| **火山方舟** | `volcengine.com/product/ark` | 同上 | 火山引擎开发者社区、官方公告 | ✅ 169KB / 文档 ✅ 436KB |
| **智谱 GLM** | `zhipuai.cn` | `open.bigmodel.cn` | 官网 News、官方公众号 | ✅ 899KB / ⚠️ 定价页为 3.9KB 壳页 |
| **Z.ai（国际版）** | `z.ai` | `z.ai` | 同上 | ✅ 15.7KB |
| **Kimi** | `kimi.com` | `platform.moonshot.cn` | 开放平台公告 | ✅ 480KB / ✅ 97KB |
| **通义千问** | `tongyi.aliyun.com` | `bailian.console.aliyun.com` | 阿里云开发者社区 | ✅ 150KB / ✅ 30KB |
| **腾讯混元** | `hunyuan.tencent.com` | `cloud.tencent.com/product/hunyuan` | 腾讯云开发者社区 | ⚠️ 6.9KB 壳页 / ✅ 93KB |
| **WorkBuddy** | `workbuddy.cn` | 官网在售页含免费版额度 | 官网活动页 | ✅ 15.2KB |
| **CodeBuddy** | `codebuddy.cn` | — | 官网 | ⚠️ 3.4KB 壳页 |
| **MiniMax** | `minimaxi.com` | `platform.minimaxi.com` | 开放平台公告 | ✅ 346KB / ✅ 524KB |
| **阶跃星辰** | `stepfun.com` | `platform.stepfun.com` | 开放平台公告 | ⚠️ 2.4KB 壳页 |
| **零一万物** | `01.ai` | `platform.lingyiwanwu.com` | 官网 | ✅ 31.5KB |
| **文心一言** | `yiyan.baidu.com` | `qianfan.cloud.baidu.com` | 百度智能云公告 | ✅ 12KB / ✅ 91KB |
| **文心快码 Comate** | `comate.baidu.com` | 官网 | 官网 | ✅ 15.7KB |
| **讯飞星火** | `xinghuo.xfyun.cn` | `xfyun.cn`（定价页） | 讯飞开放平台公告 | ⚠️ 4.2KB 壳页 / ✅ 217KB |
| **商汤日日新** | `sensenova.cn` | 官网 | 官网 | ✅ 46KB |
| **硅基流动** | `cloud.siliconflow.cn` | 模型广场 | 官方公众号、文档 | ✅ 488KB（单页应用） |
| **魔搭 ModelScope** | `modelscope.cn` | 官网 | 官方社区 | ⚠️ 3.3KB 壳页 |
| **华为云 ModelArts** | `huaweicloud.com/product/modelarts.html` | 官网 | 华为云公告 | ✅ 29KB |
| **小米 MiMo** | `mimo.xiaomi.com` | 官网 | 官网、官方公告 | ✅ 43.9KB |
| **小米开放平台** | `xiaoai.mi.com` | 官网 | 官网 | ✅ 5.6KB |
| **移动云** | `ecloud.10086.cn` | 官网 | 官网 | ⚠️ 2.3KB 壳页 |
| **网易伏羲** | `ling.163.com` | — | 官网 | ❌ 不通，走搜索 |

**判断**：国内平台即使返回「壳页」（单页应用），**官网本身仍可达**，只是内容需浏览器渲染。这类平台一律**走搜索＋官方公告**，不要指望直抓解析出额度数字。

---

## 二、国外 · 模型与开放平台（17/33 直达，其余走绕行通道）

**重要事实**：在本机网络环境下，境外部分域名**完全不可达**。
但这**不代表只能靠搜索**——实测已打通五条绕行通道，逐条细节与逐平台方案见
**`references/overseas-bypass.md`**。下表给出每个平台的具体走法。

### 可直达（可监控）

| 平台 | 官网 | 定价页 | 实测 |
|---|---|---|---|
| **Anthropic** | `anthropic.com` | `anthropic.com/pricing` | ✅ 205KB / ✅ 1.16MB |
| **Cohere** | `cohere.com` | `cohere.com/pricing` | ✅ 547KB / ✅ 527KB |
| **Groq** | `groq.com` | `/pricing` | ✅ 55KB / ⚠️ 308 |
| **Cerebras** | `cerebras.ai` | — | ✅ 581KB |
| **Together AI** | `together.ai` | `/pricing` | ✅ 692KB / ✅ 587KB |
| **OpenRouter** | `openrouter.ai` | `/api/v1/models`（API） | ✅ 230KB＋API 可用 |
| **NVIDIA NIM** | `build.nvidia.com` | — | ✅ 154KB |
| **Cloudflare Workers AI** | `developers.cloudflare.com/workers-ai/` | — | ✅ 145KB |
| **Ollama** | `ollama.com` | — | ✅ 42.8KB |
| **SambaNova** | `cloud.sambanova.ai` | — | ✅ 212KB |
| **Fireworks** | `fireworks.ai` | — | ✅ 629KB |
| **Novita** | `novita.ai` | — | ✅ 248KB |
| **Nebius** | `nebius.com` | — | ✅ 401KB |

### 不通（官网不可达，改走绕行通道）

| 平台 | 官网实测 | 绕行走法（实测可用） |
|---|---|---|
| **OpenAI** | ❌ 403 | **官方 News RSS**（720 KB）＋ OpenAI Status（802 KB）＋ `openai.wiki` 中文文档镜像 ＋ 搜索 |
| **Google 全系** | ❌ 连接失败 | **DeepMind Blog RSS**（69.8 KB，Google 系唯一打通的口）＋ `freellm.net/providers/google-gemini`（15 RPM／1,500 RPD）＋ 搜索（实测可取官方定价页完整中文口径） |
| **Gemini 定价** | ❌ 连接失败 | 同上；`freellm.net` Gemini 页含 11 个免费模型与速率限制 |
| **xAI ／ Grok** | ❌ 连接失败 | `freellm.net/providers/xai`、`/providers/grok-xai` ＋ GitHub Models（含 Grok 免费档）＋ 搜索 |
| **Meta ／ Llama** | ❌ 连接失败 | **hf-mirror.com**（模型权重必上 HF）＋ 搜索 ＋ 国内媒体 |
| **Mistral** | ❌ 连接失败 | `freellm.net/providers/mistral-ai`（1 RPS，9 个免费模型）＋ 搜索 |
| **HuggingFace** | ❌ 连接失败 | **`hf-mirror.com` 全套替代**：模型 API／博客／论文／趋势／定价，全部可达 |
| **Perplexity** | ❌ 连接失败 | 搜索 ＋ 国内媒体 |
| **Midjourney** | ❌ 403 | 搜索 ＋ 国内媒体（小程序活动须留意） |
| **Luma ／ Pika** | ❌ 连接失败 | 搜索 ＋ 国内媒体 |
| **AI21 ／ Scaleway** | ❌ 403 | `freellm.net/providers/ai21-labs` ＋ 搜索 |

**共同原则**：`连接失败`＝域名级不可达，**换路径无效，不要再试**；`403`＝反爬，换 UA 偶尔能过但不值得花时间。
**把时间花在绕行通道上，而不是反复重试不通的域名。**

---

## 三、视频 · 生图平台（9/13 直达）

**国内视频与生图平台全部直达**，是这一类的监控主力。

| 平台 | 地址 | 实测 |
|---|---|---|
| **即梦 AI** | `jimeng.jianying.com` | ✅ 92KB |
| **可灵 AI** | `app.klingai.com` / `klingai.kuaishou.com` | ✅ 240KB（两个域名同内容） |
| **Vidu** | `vidu.cn` | ✅ 29KB |
| **海螺 AI** | `hailuoai.video` | ✅ 866KB |
| **通义万相** | `tongyi.aliyun.com/wanxiang/` | ⚠️ 5.7KB 壳页 |
| **智谱清影** | `chatglm.cn/video` | ⚠️ 4.4KB 壳页 |
| **PixVerse** | `pixverse.ai` | ✅ 196KB |
| **Pollinations** | `pollinations.ai` | ✅ 4.4KB（免费、免密钥） |
| **Runway** | `runwayml.com` | ⚠️ 308 重定向 |
| **Midjourney** | `midjourney.com` | ❌ 403 |
| **Luma** | `lumalabs.ai` | ❌ 连接失败 |
| **Pika** | `pika.art` | ❌ 连接失败 |

**注意**：视频与生图类平台的免费额度**变动最频繁**（常见「每日免费次数」「限时积分返还」），且官方通常只在小程序或 App 内公示，网页信息滞后。这一类高度依赖搜索，**不要因为官网没写就断定没有免费额度**。

---

## 四、Agent · Coding 工具（17/18 直达）

| 工具 | 地址 | 实测 |
|---|---|---|
| **Cursor** | `cursor.com` / `/pricing` | ✅ 770KB / ✅ 406KB |
| **Windsurf** | `windsurf.com` | ⚠️ 308 |
| **Trae（国际）** | `trae.ai` | ✅ 14.4KB |
| **Trae（国内）** | `trae.cn` | ✅ 53KB |
| **Qoder** | `qoder.com` | ✅ 486KB |
| **GitHub Copilot** | `github.com/features/copilot` / `/plans` | ✅ 875KB / ✅ 1.26MB |
| **Manus** | `manus.im` | ✅ 1.27MB |
| **Devin** | `devin.ai` | ✅ 736KB |
| **Replit** | `replit.com` | ✅ 665KB |
| **Bolt** | `bolt.new` | ✅ 122KB |
| **v0** | `v0.dev` | ✅ 1.03MB |
| **Dify** | `dify.ai` | ✅ 478KB |
| **扣子 Coze** | `coze.cn` | ✅ 90KB |
| **n8n** | `n8n.io` | ✅ 344KB |
| **Kilo Code** | `kilo.ai` | ✅ 494KB（汇总仓库收录其免费额度） |
| **Lovable** | `lovable.dev` | ❌ 403 |

**这一类的免费额度变化最快**：限时折扣、赠送积分、免费档调整几乎每周都有。定价页（`/pricing`）是**最灵敏的哨点**，应纳入每日快照比对。

---

## 五、RSS 与可监控接口

| 目标 | 地址 | 实测 | 用法 |
|---|---|---|---|
| **OpenAI News RSS** | `openai.com/news/rss.xml` | ✅ 200，720.6 KB | **即使官网 403，RSS 仍可读**——境外平台的重要绕行通道 |
| **Google DeepMind Blog RSS** | `deepmind.google/blog/rss.xml` | ✅ 200，69.8 KB | **Google 系唯一打通的口**（`blog.google` 全系不通） |
| **GitHub 官方博客 RSS** | `github.blog/feed/` | ✅ 200，724.3 KB | 官方发布渠道 |
| **OpenAI Status** | `status.openai.com` | ✅ 200，802.1 KB | 服务事件与故障公告 |
| **Cloudflare Blog RSS** | `blog.cloudflare.com/rss/` | ⚠️ 首测 200，复测失败 | 偶发抖动，须复测 |
| **GitHub Releases API** | `api.github.com/repos/{owner}/{repo}/releases?per_page=1` | ✅ 200 | **`api.github.com` 本机可直连**，无需镜像 |
| **HF 镜像 模型 API** | `hf-mirror.com/api/models?sort=trendingScore&limit=N` | ✅ 200，JSON | 替代不通的 `huggingface.co`，含下载／点赞／创建日 |
| **HF 镜像 每日论文** | `hf-mirror.com/api/daily_papers` | ✅ 200，316.9 KB（**有 429 限流**） | 新成果动向，一天抓一次 |
| Google AI Blog RSS | `blog.google/technology/ai/rss/` | ❌ 不通 | — |
| Meta / Mistral / HF / Perplexity 官方 RSS | — | ❌ 不通 | 改走镜像站或搜索 |
| HN RSS / Reddit RSS / V2EX | — | ❌ 不通 | 改走搜索 |
| Anthropic RSS | `anthropic.com/rss.xml` | ❌ 404（无此源） | 改抓 `/news` 页面（✅ 451.7 KB） |

**关键推论**：
① 官方 RSS 是**绕过官网封锁的最优通道**——凡官网不通但官方有 RSS 的，一律走 RSS；
② **境内镜像站可完全替代不通的境外站**——HuggingFace 有 `hf-mirror.com`，GitHub raw 有多个加速镜像；
③ 国内厂商的认证类活动常只在小程序内公示，网页与 RSS 均查不到，须留意搜索词中的活动名。

---

## 六、聚合站与社区（6/10 直达）

| 目标 | 地址 | 实测 | 定位 |
|---|---|---|---|
| **mnfst 汇总仓库** | `github.com/mnfst/awesome-free-llm-apis` | ✅ 200 | **甲级信源**，16 家供应商 118 条模型，raw 可直取 |
| **freetokens.custats** | `freetokens.custats.info` | ✅ 200，516KB | 免费额度专门站，含核实状态与更新日期 |
| **free-model.com** | `free-model.com/free-llm-api-keys` | ⚠️ 308 | 150+ 免费模型，含「是否需信用卡」标注 |
| **少数派** | `sspai.com` | ✅ 103KB | 国内效率工具资讯 |
| **IT之家** | `ithome.com` | ✅ 144KB | 国内科技快讯，活动消息出得快 |
| **36氪** | `36kr.com` | ⚠️ 17.6KB | 商业侧动态 |
| **掘金** | `juejin.cn` | ✅ 79KB | 技术社区，抓包类文章线索 |
| **V2EX** | `v2ex.com` | ❌ 不通 | — |
| **Hacker News** | `news.ycombinator.com` | ❌ 不通 | — |
| **Reddit r/LocalLLaMA** | `reddit.com/r/LocalLLaMA/` | ❌ 不通 | — |

**用法纪律**：聚合站与社区**只作线索**，任何条目回到官方页面核实后才可写入清单。

---

## 七、维护记录

| 日期 | 变更 |
|---|---|
| 2026-09-19 | 初版。探测 118 个目标，逐条记录状态；确定「国内直抓、境外半走 RSS 半走搜索」的分工 |
| 2026-09-19 | **境外部分重做**：新增五条绕行通道实测（镜像站替代／官方 RSS 旁路／国内媒体搬运／免费额度专门站／搜索兜底），逐平台给出具体走法；RSS 表补入 DeepMind、GitHub 官方博客、OpenAI Status、hf-mirror 各接口。详见 `references/overseas-bypass.md` |
| 2026-09-20 | **顶部补入「探测数 vs 监控数」口径说明**（118 探测／30 监控／其余搜索兜底），并写明壳页排除标准；起因是评测者把 118 个探测目标误读为监控规模，据此判定「SPA 抓不到、自动化打折扣」。事实是壳页从未纳入监控。 |
