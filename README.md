[English](./README.en.md) | **简体中文**

# AI 内容摘要流水线（auto-digest）

给定一篇文章（**本地文本文件** 或 **一个网页 URL**），用大模型自动提炼成结构化摘要
（标题 / 一句话总结 / 要点清单），输出为 Markdown 文件并打印；可选推送到群机器人。

「**抓取 → LLM 总结 → 推送**」自动化流程的核心环节。
适用场景：每日资讯简报、竞品 / 行业动态监控、长文速读、选题搜集。

## 技术栈
- **大模型**：DeepSeek（`deepseek-chat`，OpenAI 兼容接口，便宜稳定）
- **调用库**：`openai`（换 `base_url` 即可直连 DeepSeek）
- **网页抓取**：`requests` + `trafilatura`（自动提取正文，去掉导航/广告噪声）
- **推送**：`requests` POST 到飞书 / 钉钉群机器人 webhook（可选）
- 轻量纯 LLM 方案，**不依赖 embedding / torch**，装起来快

## 特点
1. **格式稳定**：通过 system prompt 约束，输出永远是「标题 / 一句话总结 / 3-6 条要点」，
   可以直接拼进日报或群消息，无需二次清洗。
2. **可接自动化**：本地文件、网页 URL 都能吃；配上 webhook 就是一条完整的
   「抓取→总结→推送」流水线，配合 crontab / GitHub Actions 即可定时跑。

---

## 怎么跑起来

### 1. 准备 DeepSeek Key
去 https://platform.deepseek.com/ 创建 API key。把 `.env.example` 复制成 `.env`，填入 key：
```
DEEPSEEK_API_KEY=sk-你的key
```

### 2. 装依赖（用 uv）
```bash
cd ~/pyProjects/ai-content-digest
uv venv --python 3.12
uv pip install -r requirements.txt
```

### 3. 跑起来
```bash
# 总结本地文件
uv run python digest.py samples/示例文章.md

# 总结一个网页
uv run python digest.py https://某篇文章的网址
```
运行后会：① 终端打印摘要；② 在 `output/` 下生成带元信息的 Markdown 文件；
③ 若 `.env` 里配置了 `WEBHOOK_URL`，自动推送到飞书/钉钉群。

---

## 目录结构
```
ai-content-digest/
├── digest.py            # 核心逻辑：读输入→调 DeepSeek→写 Markdown→可选推送
├── samples/
│   └── 示例文章.md      # 内置示例文章，离线也能验证流程
├── output/              # 生成的摘要 Markdown（自动创建，已 gitignore）
├── requirements.txt
├── .env.example
└── README.md
```

## 工作流程
```
输入(文件/URL) → 正文提取(trafilatura) → DeepSeek 结构化摘要 → 写 Markdown ┬→ 终端打印
                                                                          └→ webhook 推送(可选)
```

## 可拓展方向
- 定时任务：crontab / GitHub Actions 每天定点抓取 RSS 或指定页面并推送日报
- 批量模式：一次喂一个 URL 列表，汇总成一份「今日多篇速读」
- 多种输出：除 Markdown 外，导出飞书云文档、Notion、邮件
- 长文分段摘要 + 汇总（map-reduce），处理超长文章
- 自定义摘要风格：要点数量、语气等，做成命令行参数
- 接微信公众号 / 企业微信 / Telegram 等更多推送渠道
