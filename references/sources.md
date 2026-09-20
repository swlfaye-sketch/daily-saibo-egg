# 赛博鸡蛋 · 信源清单与实测状态

实测时间：2026年9月19日。**下方状态为实测结论，信源失效时先查本表再换源。**

> **平台级名录（118 个探测目标的逐条可达性、官方渠道、绕行方案；其中 32 个纳入每日自动监控）见 `references/platforms.md`。**
> **境外官网不通时的五条绕行通道见 `references/overseas-bypass.md`——境外部分以该文件为准。**
> 本表侧重「信源本身可用不可用」，platforms.md 侧重「每个平台该用哪条路」。三份配合看。

---

## 一、甲级信源（可直接程序化抓取）

| 信源 | 地址 | 实测状态 | 说明 |
|---|---|---|---|
| 免费 LLM API 汇总仓库 | `https://raw.githubusercontent.com/mnfst/awesome-free-llm-apis/main/README.md` | ✅ **直连可用**（6/6，28,367 B，7.9 s） | 16 家供应商、118 条模型。初版曾记「直连超时」——系单次抖动误判，已复测纠正；镜像只作冗余 |
| 同上·仓库元数据 | `https://api.github.com/repos/mnfst/awesome-free-llm-apis` | ✅ 200 | 7,700+ 星；`api.github.com` 本机可直连，无需镜像 |
| OpenRouter 模型列表 | `https://openrouter.ai/api/v1/models` | ✅ 200，722.4 KB | 447 个模型，25 个零价；免密钥 |
| **freellm.net** | `https://freellm.net/providers/<slug>` | ✅ 200 | **境外免费额度最佳单点信源**：30 家 provider，逐家一页，含速率限制／免费模型数／是否需信用卡／更新日 |
| **llm-price.com** | `https://llm-price.com/` | ✅ 200，300.4 KB | 价格对比表，含**上架时间**（"yesterday"／"5 days ago"）——上线与降价的灵敏哨点 |
| **HF 镜像 模型接口** | `https://hf-mirror.com/api/models?sort=trendingScore&limit=N` | ✅ 200，JSON | 替代不通的 `huggingface.co`；含下载／点赞／创建日 |
| **HF 镜像 每日论文** | `https://hf-mirror.com/api/daily_papers` | ✅ 200，316.9 KB（**有 429 限流**） | 50 条，含标题／摘要／上票 |
| **DeepMind Blog RSS** | `https://deepmind.google/blog/rss.xml` | ✅ 200，69.8 KB | **Google 系唯一打通的口** |
| **GitHub 官方博客 RSS** | `https://github.blog/feed/` | ✅ 200，724.3 KB | 官方发布渠道 |
| **OpenAI Status** | `https://status.openai.com/` | ✅ 200，802.1 KB | 服务事件与故障公告 |
| 腾讯云 TokenHub 新人包 | `https://www.tencentcloud.com/zh/document/product/1300/80423` | ✅ 200 | 官方文档页，含额度规则 |

## 二、已失效 / 不可用信源（不要再用）

| 信源 | 实测 | 说明 |
|---|---|---|
| `cheahjs/free-llm-api-resources` | ❌ HTTP 404 | 该领域曾最知名的仓库，现已不存在 |
| **GitHub 加速镜像的多数候选** | ❌ 全部不通 | `gh.llkk.cc`／`ghp.ci`／`github.moeyy.xyz`／`hub.gitmirror.com`／`raw.gitmirror.com`／`raw.kkgithub.com`。**可用者仅 4 个**：`ghproxy.net`／`gh-proxy.com`／`gh.xxooo.cf`／`cdn.jsdelivr.net`。注：GitHub raw **可直连**，镜像仅作冗余 |
| ~~`raw.githubusercontent.com` 直连~~ | ✅ **实为可达** | 初版记「超时不可达」，复测 6/6 稳定（28,367 B，7.9 s）。**已纠正** |
| **RSSHub 公共实例的大多数** | ❌ 不通 | `rsshub.app`／`rss.shab.fun`／`rsshub.pseudoyu.com`／`rsshub.hanxitoday.com`／`rsshub.henry.wang`／`rsshub.ktachibana.workers.dev` 全部不可达；可用的仅 3 个（见第五节） |
| **RSSHub 的多数路由** | ❌ HTTP 503 | 实测 29 条常用路由**仅 4 条可用**，其余大量 503。**「能变任意站为 RSS」不成立** |
| `free-model.com` | ⚠️ HTTP 308 | 需跟随重定向 |
| `tokenprice.io` | ❌ HTTP 403 | 不可用 |
| `openllmleaderboard.com` | ❌ 连接失败 | 不可用 |
| `cloud.siliconflow.cn/models` 直抓 | ⚠️ 200 但为 487 KB 单页应用 | 直抓取不到结构化额度，改走文档与搜索 |
| `open.bigmodel.cn/pricing` 直抓 | ⚠️ 200 仅 3.9 KB 壳页 | 单页应用，无内容 |
| `free-llm.com` 的数据表 | ⚠️ 靠 JS 加载 | 主站可达但取不到表格，**只作线索** |
| Bing 结果页解析 | ⚠️ 200 但解析 0 条 | 结果页可达，但 `<h2><a>` 结构解析不出条目，**程序化搜索不要走它** |

## 三、可达性实测（用于判断该直抓还是该搜索）

### 国内平台

| 平台 | 直抓结果 | 结论 |
|---|---|---|
| 硅基流动·模型广场 | 200，487 KB | 页面可达，额度信息走文档 |
| 智谱·开放平台 | 200，3.9 KB | 壳页，走搜索 |
| 阿里百炼 | 200，30 KB | 可达 |
| 百度千帆 | 200，91 KB | 可达 |
| 腾讯混元 | 200，93 KB | 可达 |
| 火山方舟（豆包） | 200，169 KB | 可达 |
| 讯飞星火 | 200，4.2 KB | 壳页，走搜索 |
| MiniMax | 200，524 KB | 可达 |
| 阶跃星辰 | 200，116 KB | 可达 |
| 零一万物 | 200，8.4 KB | 壳页 |
| DeepSeek | 200，2.8 KB | 壳页 |
| Kimi 开放平台 | ❌ 连接失败 | 走搜索 |

### 国外平台

| 平台 | 直抓结果 | 结论 |
|---|---|---|
| OpenRouter | ✅ 200，230 KB | 且模型 API 可用 |
| Cloudflare Workers AI | ✅ 200，145 KB | 可达 |
| GitHub Models | ✅ 200，45 KB | 可达 |
| Cohere | ✅ 200，26 KB | 可达 |
| NVIDIA NIM | ✅ 200，154 KB | 可达 |
| SambaNova | ✅ 200，212 KB | 可达 |
| Groq Console | ❌ 403 | Cloudflare 反爬，走搜索 |
| Cerebras | ❌ 403 | 同上 |
| Together AI | ❌ 403 | 同上 |
| Google AI Studio | ❌ 连接失败 | 走搜索 |
| Mistral Console | ❌ 连接失败 | 走搜索 |
| HuggingFace | ❌ 连接失败 | 走搜索 |

### 视频 / 生图平台

| 平台 | 直抓结果 |
|---|---|
| 可灵 AI | ✅ 200，240 KB |
| 即梦 AI | ✅ 200，92 KB |
| Vidu | ✅ 200，29 KB |
| 海螺 AI | ✅ 200，895 KB |
| 通义万相 | ✅ 200，5.7 KB |
| Runway | ⚠️ 308 重定向 |
| Pollinations | ✅ 200，4.4 KB |
| Luma | ❌ 连接失败 |
| Pika | ❌ 连接失败 |

---

## 四、乙级参考源（搜索用）

| 类型 | 用法 |
|---|---|
| 厂商官方活动页 / 官方文档 | 直接采信，写入清单时附链接 |
| 官方开发者社区发文（如阿里云开发者社区） | 采信，标注来源 |
| 第三方「AI 工具福利大全」聚合文章 | **只作线索**，逐条回官方核对；核不上的标「待确认」 |

**已知聚合文章的质量特征**：覆盖面广（一次可列二十余家厂商的产品线福利），但会过时、会串行错位（把 A 厂商的活动写到 B 厂商名下）。**绝不能直接转述，必须回到官方页面验证截止日期与额度。**

---

## 五、官方发布渠道与订阅源实测

「额度变化的真正首发地」，与官网首页分开对待：

| 渠道 | 地址 | 实测 | 用法 |
|---|---|---|---|
| OpenAI News RSS | `openai.com/news/rss.xml` | ✅ 200，720.6 KB | **官网 403 时的主要绕行通道** |
| DeepMind Blog RSS | `deepmind.google/blog/rss.xml` | ✅ 200，69.8 KB | Google 系唯一打通的口 |
| GitHub 官方博客 RSS | `github.blog/feed/` | ✅ 200，724.3 KB | 官方发布渠道 |
| OpenAI Status | `status.openai.com` | ✅ 200，802.1 KB | 服务事件 |
| Anthropic News 页 | `anthropic.com/news` | ✅ 200，451.7 KB | 官网可达，直抓 |
| Stability AI News | `stability.ai/news` | ✅ 200，314.7 KB | 生图类少数可达者 |
| Cloudflare Blog RSS | `blog.cloudflare.com/rss/` | ⚠️ 首测 200，复测失败 | 偶发抖动，须复测，不可据单次结果判定失效 |
| GitHub Releases API | `api.github.com/repos/{owner}/{repo}/releases?per_page=1` | ✅ 200 | 监控官方仓库发版 |
| GitHub 仓库元数据 | `api.github.com/repos/{owner}/{repo}` | ✅ 200 | 取 `pushed_at`，判断仓库是否仍在维护 |
| Google AI Blog RSS | `blog.google/technology/ai/rss/` | ❌ 不通 | 改走搜索 |
| HuggingFace Blog RSS | `huggingface.co/blog/feed.xml` | ❌ 不通 | **改走 `hf-mirror.com/blog`** |
| Mistral News RSS | `mistral.ai/news/feed.xml` | ❌ 不通 | 改走 `freellm.net/providers/mistral-ai` |
| Anthropic RSS | `anthropic.com/rss.xml` | ❌ 404（无此源） | 改抓 `/news` 页面 |
| HN RSS / Reddit RSS / V2EX | — | ❌ 不通 | 改走搜索 |

### 国内媒体 RSS（境外消息的中文搬运渠道，全部可读）

| 媒体 | RSS | 实测 |
|---|---|---|
| 量子位 | `qbitai.com/feed` | ✅ 6.3 KB（备用 `/feed/atom` 7.1 KB） |
| IT之家 | `ithome.com/rss/` | ✅ 208.9 KB |
| 爱范儿 | `ifanr.com/feed` | ✅ 474.5 KB |
| InfoQ 中国 | `infoq.cn/feed` | ✅ 13.5 KB |
| 开源中国 | `oschina.net/news/rss` | ✅ 42.6 KB |
| 少数派 | `sspai.com/feed` | ✅ 6.2 KB |

### RSSHub 可用实例与可用路由（覆盖率低，仅作补充）

可用实例 3 个：`rsshub.rssforever.com`、`rsshub.liumingye.cn`、`rsshub.woodland.cafe`。
可用路由仅 4 条：`/openai/news`、`/huggingface/daily-papers`、`/hackernews/best`、`/ithome/it`。
**其余 25 条常用路由实测 503 或超时。**

**推论**：官方 RSS 是绕行封锁的最优通道——凡官网不通但官方有 RSS 的，一律走 RSS；
官网与 RSS 都不通的，走**镜像站**（HuggingFace → hf-mirror）或**国内媒体搬运**。
国内厂商的认证类活动常只在小程序内公示，网页与 RSS 均查不到，须留意搜索词中的活动名。

---

## 六、维护记录

| 日期 | 变更 |
|---|---|
| 2026-09-19 | 初版；实测 40 余个信源，确定甲路双信源与乙路搜索模板 |
| 2026-09-19 | 补充官方发布渠道实测；新增 `references/platforms.md`（118 个目标全量探测） |
| 2026-09-19 | **境外绕行通道实测**（四轮探测 80 余个目标）：新增 freellm.net、llm-price.com、hf-mirror、DeepMind RSS、GitHub 官方博客 RSS、OpenAI Status 等甲级信源；作废不可用的 GitHub 加速镜像与 RSSHub 实例／路由；新增 `references/overseas-bypass.md` |
| 2026-09-19 | **纠错**：`raw.githubusercontent.com` 直连可达（6/6）被误记为「直连不通」，已更正；GitHub 加速镜像由「必需」降为「冗余」。教训记入 SKILL.md 第九节第一条（大页面超时 ≠ 域名不可达） |
