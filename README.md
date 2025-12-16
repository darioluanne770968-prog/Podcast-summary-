# 🎙️ Podcast Summary

一个强大的播客分析和总结工具，支持音频转录、内容分析、多格式导出。

## ✨ 功能特性

| 功能 | 描述 |
|------|------|
| 🗣️ **语音转文字** | 使用 Whisper 进行高精度转录，支持中英文等多语言 |
| 👥 **说话人识别** | 自动识别不同说话人（主持人 vs 嘉宾） |
| 📝 **内容摘要** | AI 生成结构化摘要，提取核心要点 |
| 🏷️ **关键词提取** | 识别播客中的核心话题和关键词 |
| 📑 **章节分割** | 按话题自动切分内容，生成时间戳目录 |
| 💬 **金句提取** | 提取播客中的精彩观点和金句 |
| 😊 **情感分析** | 分析讨论的情感倾向 |
| ❓ **问答生成** | 生成 Q&A 便于复习 |
| 🗺️ **思维导图** | 自动生成内容思维导图 |
| 📤 **多格式导出** | Markdown / JSON / Notion |

## 🚀 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/your-repo/podcast-summary.git
cd podcast-summary

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 或使用 pip install -e .
pip install -e .
```

### 配置

复制环境变量模板并填写 API 密钥：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# 必填：至少配置一个 LLM API Key
ANTHROPIC_API_KEY=your_anthropic_api_key
OPENAI_API_KEY=your_openai_api_key

# 可选：Notion 同步
NOTION_API_KEY=your_notion_api_key
NOTION_DATABASE_ID=your_database_id

# 可选：说话人识别（需要同意模型使用条款）
HF_TOKEN=your_huggingface_token
```

### 使用方式

#### 命令行 (CLI)

```bash
# 分析本地音频文件
podcast-cli analyze ./podcast.mp3

# 分析 YouTube 视频
podcast-cli analyze "https://youtube.com/watch?v=xxx"

# 分析播客 RSS 订阅
podcast-cli analyze "https://feeds.example.com/podcast.xml"

# 启用全部功能
podcast-cli analyze ./podcast.mp3 --full

# 指定输出目录和格式
podcast-cli analyze ./podcast.mp3 -o ./notes --json --mindmap

# 仅转录（不分析）
podcast-cli transcribe ./podcast.mp3

# 查看音频信息
podcast-cli info ./podcast.mp3

# 列出 RSS 订阅中的节目
podcast-cli list-episodes "https://feeds.example.com/podcast.xml"

# 检查配置
podcast-cli check
```

#### Web 界面

```bash
# 启动 Web 界面
streamlit run src/web_app.py

# 浏览器访问 http://localhost:8501
```

#### Python API

```python
from src.pipeline import PodcastAnalyzer, PipelineConfig

# 基础使用
config = PipelineConfig()
analyzer = PodcastAnalyzer(config)
result = analyzer.analyze_sync("./podcast.mp3")

print(result.summary.brief)  # 简短摘要
print(result.chapters)       # 章节列表
print(result.keywords)       # 关键词

# 完整配置
config = PipelineConfig(
    whisper_model="large-v3",
    enable_diarization=True,
    enable_sentiment=True,
    export_markdown=True,
    export_json=True,
    export_notion=True,
    output_dir=Path("./output"),
)
```

## 📁 项目结构

```
podcast-summary/
├── src/
│   ├── main.py             # CLI 入口
│   ├── web_app.py          # Web 界面
│   ├── pipeline.py         # 分析管道
│   ├── config.py           # 配置管理
│   │
│   ├── audio/              # 音频处理
│   │   ├── downloader.py   # 下载器
│   │   └── converter.py    # 格式转换
│   │
│   ├── transcription/      # 语音转文字
│   │   ├── whisper_engine.py  # Whisper 引擎
│   │   └── diarization.py     # 说话人识别
│   │
│   ├── analysis/           # LLM 分析
│   │   ├── llm_client.py   # LLM 客户端
│   │   ├── summarizer.py   # 摘要生成
│   │   ├── keywords.py     # 关键词提取
│   │   ├── chapters.py     # 章节分割
│   │   ├── quotes.py       # 金句提取
│   │   ├── sentiment.py    # 情感分析
│   │   └── qa_generator.py # 问答生成
│   │
│   ├── export/             # 导出
│   │   ├── markdown.py     # Markdown 导出
│   │   ├── json_export.py  # JSON 导出
│   │   ├── notion.py       # Notion 同步
│   │   └── mindmap.py      # 思维导图
│   │
│   └── utils/              # 工具函数
│
├── tests/                  # 测试
├── examples/               # 示例
├── requirements.txt        # 依赖
├── pyproject.toml          # 项目配置
└── README.md
```

## 📊 输出示例

### Markdown 笔记

```markdown
# 🎙️ [播客标题] - 分析笔记

## 📋 基本信息
- **时长**: 1:23:45
- **语言**: 中文

## 📝 内容摘要
本期播客主要讨论了...

### 核心要点
- 要点一
- 要点二
- 要点三

## 📑 章节目录
- [00:00] 开场介绍
- [05:23] 话题一：AI 发展趋势
- [25:10] 话题二：创业经验分享

## 🏷️ 关键词
`人工智能` `创业` `投资` `技术趋势`

## 💬 金句摘录
> "创业最重要的是找到真正的需求..." — 嘉宾 [32:15]

## ❓ 问答复习
Q: 本期讨论的AI发展三大趋势是什么？
A: 1. 多模态融合 2. Agent 自动化 3. ...
```

## 🔧 技术栈

- **语音识别**: faster-whisper / openai-whisper
- **说话人识别**: pyannote.audio
- **LLM**: Claude (Anthropic) / GPT (OpenAI)
- **CLI**: Click + Rich
- **Web**: Streamlit
- **音频处理**: pydub, yt-dlp

## 📝 支持的来源

| 来源 | 示例 |
|------|------|
| 本地文件 | `./podcast.mp3`, `./video.mp4` |
| YouTube | `https://youtube.com/watch?v=xxx` |
| 播客 RSS | `https://feeds.example.com/podcast.xml` |
| 小宇宙 | `https://www.xiaoyuzhoufm.com/episode/xxx` |
| 直接 URL | `https://example.com/audio.mp3` |

## ⚙️ 配置选项

| 环境变量 | 说明 | 必填 |
|---------|------|------|
| `ANTHROPIC_API_KEY` | Claude API 密钥 | 二选一 |
| `OPENAI_API_KEY` | OpenAI API 密钥 | 二选一 |
| `DEFAULT_LLM_PROVIDER` | 默认 LLM (claude/openai) | 否 |
| `WHISPER_MODEL` | Whisper 模型 | 否 |
| `NOTION_API_KEY` | Notion API 密钥 | 否 |
| `NOTION_DATABASE_ID` | Notion 数据库 ID | 否 |
| `HF_TOKEN` | HuggingFace Token | 否 |

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 License

MIT License
