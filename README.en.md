**English** | [简体中文](./README.md)

# AI Content Digest Pipeline (auto-digest)

Given an article (either a **local text file** or **a web page URL**), this tool uses an LLM to
distill it into a structured summary (title / one-line takeaway / key-point list), writes the result
to a Markdown file, and prints it; optionally pushes to a group chat bot.

The core stage of a "**fetch → LLM summarize → push**" automation flow.
Use cases: daily news briefs, competitor / industry monitoring, fast reading of long articles, topic sourcing.

## Tech Stack
- **LLM**: DeepSeek (`deepseek-chat`, OpenAI-compatible API, cheap and reliable)
- **Client library**: `openai` (just swap `base_url` to talk to DeepSeek directly)
- **Web scraping**: `requests` + `trafilatura` (extracts main content, strips nav/ad noise)
- **Push**: `requests` POST to Feishu / DingTalk group bot webhook (optional)
- Lightweight pure-LLM approach, **no embedding / torch dependency**, fast to install

## Features
1. **Stable format**: constrained via the system prompt, the output is always "title / one-line takeaway / 3-6 key points",
   ready to drop straight into a daily brief or group message with no extra cleanup.
2. **Automation-ready**: takes both local files and web URLs; add a webhook and you have a complete
   "fetch → summarize → push" pipeline that runs on a schedule via crontab / GitHub Actions.

---

## Getting Started

### 1. Prepare a DeepSeek key
Create an API key at https://platform.deepseek.com/. Copy `.env.example` to `.env` and fill in the key:
```
DEEPSEEK_API_KEY=sk-your-key
```

### 2. Install dependencies (with uv)
```bash
cd ~/pyProjects/ai-content-digest
uv venv --python 3.12
uv pip install -r requirements.txt
```

### 3. Run it
```bash
# Summarize a local file
uv run python digest.py samples/示例文章.md

# Summarize a web page
uv run python digest.py https://some-article-url
```
On each run it will: (1) print the summary to the terminal; (2) generate a Markdown file with metadata
under `output/`; (3) if `WEBHOOK_URL` is set in `.env`, automatically push to the Feishu/DingTalk group.

---

## Project Structure
```
ai-content-digest/
├── digest.py            # Core logic: read input → call DeepSeek → write Markdown → optional push
├── samples/
│   └── 示例文章.md      # Built-in sample article, lets you verify the flow offline
├── output/              # Generated summary Markdown (auto-created, gitignored)
├── requirements.txt
├── .env.example
└── README.md
```

## Workflow
```
input(file/URL) → content extraction(trafilatura) → DeepSeek structured summary → write Markdown ┬→ print to terminal
                                                                                                 └→ webhook push(optional)
```

## Possible Extensions
- Scheduled jobs: crontab / GitHub Actions to fetch RSS or specific pages daily and push a brief
- Batch mode: feed a list of URLs at once, aggregated into a single "today's multi-article digest"
- Multiple outputs: beyond Markdown, export to Feishu docs, Notion, or email
- Long-article segmented summary + aggregation (map-reduce) for handling very long articles
- Custom summary style: number of key points, tone, etc., exposed as command-line arguments
- More push channels: WeChat Official Account / WeCom / Telegram, and more
