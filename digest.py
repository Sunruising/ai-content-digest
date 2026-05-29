"""
AI 内容摘要流水线（auto-digest）

给定一篇文章（本地文本文件 或 一个网页 URL），用大模型自动提炼成结构化摘要
（标题 / 一句话总结 / 要点清单），输出为 Markdown 文件并打印；可选推送到 webhook
（飞书 / 钉钉机器人）。

典型自动化场景：定时抓取资讯 → LLM 总结 → 推送到群机器人。

用法：
    uv run python digest.py samples/示例文章.md
    uv run python digest.py https://example.com/article
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
from openai import OpenAI

# 读取项目根目录下的 .env（DEEPSEEK_API_KEY / WEBHOOK_URL）
load_dotenv()

# DeepSeek 使用 OpenAI 兼容接口，换 base_url 即可
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

# 输出目录：生成的摘要 Markdown 存这里（已在 .gitignore 中忽略）
OUTPUT_DIR = Path(__file__).parent / "output"

# 提炼摘要的系统提示词：约束输出格式稳定、中文、结构化
SYSTEM_PROMPT = """你是一名专业的中文内容编辑，擅长把长文提炼成清晰的结构化摘要。

请阅读用户提供的文章，输出严格遵循以下 Markdown 格式（不要有多余的开场白或结束语）：

## 标题
（用一句话概括文章主题，作为标题，不超过 20 字）

**一句话总结**：（用一句话讲清文章的核心结论，不超过 50 字）

### 核心要点
- 要点一
- 要点二
- 要点三
（共 3 到 6 条，每条一句话，覆盖文章最重要的信息，按重要性排序）

要求：全部用中文；忠于原文，不杜撰原文没有的信息；语言精炼、信息密度高。"""


def read_input(source: str) -> str:
    """根据输入判断是 URL 还是本地文件，返回正文纯文本。"""
    if source.startswith(("http://", "https://")):
        return fetch_url(source)
    return read_file(source)


def read_file(path: str) -> str:
    """读取本地文本文件（txt / md 等）。"""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"找不到文件：{path}")
    text = p.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"文件内容为空：{path}")
    return text


def fetch_url(url: str) -> str:
    """抓取网页并提取正文。

    优先用 trafilatura 做正文提取（自动去掉导航、广告等噪声）；
    失败时给出友好提示，而不是抛一堆栈。
    """
    try:
        import trafilatura

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            )
        }
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        # trafilatura 提取正文，去掉评论与杂项
        text = trafilatura.extract(
            resp.text, include_comments=False, include_tables=False
        )
        if not text or not text.strip():
            raise ValueError(
                "未能从该网页提取到正文，可能是动态渲染页面或反爬限制。"
                "建议改为把文章保存成本地文本文件后再试。"
            )
        return text.strip()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"网页抓取失败（网络错误）：{e}") from e


def summarize(text: str) -> str:
    """调用 DeepSeek 生成结构化摘要 Markdown。"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError(
            "未读取到 DEEPSEEK_API_KEY，请把 .env.example 复制为 .env 并填入你的 key。"
        )

    client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)

    # 文章过长时截断，避免超出上下文（可改成分段摘要处理超长文）
    max_chars = 12000
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n（原文过长，已截断）"

    resp = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"请为下面这篇文章生成摘要：\n\n{text}"},
        ],
        temperature=0.3,  # 低温度让输出更稳定
        stream=False,
    )
    return resp.choices[0].message.content.strip()


def save_markdown(summary: str, source: str) -> Path:
    """把摘要写成带元信息的 Markdown 文件，返回文件路径。"""
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    # 用来源名 + 时间戳命名，便于区分多次运行
    stem = Path(source).stem if not source.startswith("http") else "webpage"
    stem = re.sub(r"[^\w一-鿿-]", "_", stem)[:30]
    out_path = OUTPUT_DIR / f"摘要-{stem}-{timestamp}.md"

    content = (
        f"> 来源：{source}\n"
        f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"> 由 DeepSeek（{DEEPSEEK_MODEL}）自动生成\n\n"
        f"{summary}\n"
    )
    out_path.write_text(content, encoding="utf-8")
    return out_path


def push_webhook(summary: str, source: str) -> None:
    """可选：把摘要推送到飞书 / 钉钉群机器人（text 消息）。"""
    webhook_url = os.getenv("WEBHOOK_URL", "").strip()
    if not webhook_url:
        return  # 未配置则跳过

    # 飞书自定义机器人与钉钉机器人都接受这种 text 结构
    payload = {
        "msg_type": "text",  # 飞书字段
        "msgtype": "text",  # 钉钉字段
        "content": {"text": f"【自动摘要】来源：{source}\n\n{summary}"},
        "text": {"content": f"【自动摘要】来源：{source}\n\n{summary}"},
    }
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        print(f"✅ 已推送到 webhook：{webhook_url[:40]}...")
    except requests.exceptions.RequestException as e:
        print(f"⚠️  webhook 推送失败（不影响本地摘要）：{e}")


def main() -> None:
    if len(sys.argv) < 2:
        print("用法：uv run python digest.py <文件路径 或 网页URL>")
        print("示例：uv run python digest.py samples/示例文章.md")
        sys.exit(1)

    source = sys.argv[1]
    print(f"📥 正在读取输入：{source}")
    try:
        text = read_input(source)
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"❌ 读取失败：{e}")
        sys.exit(1)

    print(f"📝 已获取正文（{len(text)} 字），正在调用 DeepSeek 生成摘要……")
    try:
        summary = summarize(text)
    except RuntimeError as e:
        print(f"❌ {e}")
        sys.exit(1)

    print("\n" + "=" * 50)
    print(summary)
    print("=" * 50 + "\n")

    out_path = save_markdown(summary, source)
    print(f"💾 摘要已保存：{out_path}")

    push_webhook(summary, source)


if __name__ == "__main__":
    main()
