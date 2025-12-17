# 🎙️ Podcast Summary

一个全功能的播客分析和总结工具，支持音频转录、智能分析、多媒体生成、自动化工作流。

## ✨ 功能特性

### 核心功能

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

### 高级音频处理

| 功能 | 描述 |
|------|------|
| 🔇 **智能降噪** | 多种降噪算法（频谱门限、RNNoise、DeepFilterNet） |
| 🎵 **音源分离** | 分离人声与背景音乐（Demucs/Spleeter） |
| 📺 **广告检测** | 自动识别并移除广告片段 |
| 🎚️ **音频增强** | 一键优化音频质量 |

### 智能分析

| 功能 | 描述 |
|------|------|
| ✅ **事实核查** | 验证播客中提到的事实和数据 |
| 🕸️ **知识图谱** | 构建内容知识图谱，支持导出 Neo4j |
| 🏷️ **实体识别** | 识别人物、组织、地点、产品等 |
| 💭 **观点分析** | 比较不同嘉宾的观点差异 |
| 📚 **引用检测** | 识别书籍、研究、名人名言引用 |
| 📋 **行动项提取** | 提取可执行的建议和行动项 |

### 多媒体生成

| 功能 | 描述 |
|------|------|
| 🎬 **短视频片段** | 自动生成带字幕的精彩片段 |
| 🖼️ **封面生成** | 生成播客封面图和分享卡片 |
| 🔊 **语音摘要** | TTS 生成音频版摘要 |
| 📱 **社交帖子** | 自动生成多平台社交媒体帖子 |
| 📊 **信息图表** | 生成数据可视化图表 |

### 个性化与协作

| 功能 | 描述 |
|------|------|
| 👤 **用户画像** | 学习用户偏好，个性化推荐 |
| 📋 **分析模板** | 内置多种模板，支持自定义 |
| ⭐ **收藏管理** | 收藏金句、片段、播客 |

### 自动化工作流

| 功能 | 描述 |
|------|------|
| 📡 **RSS 监控** | 自动监控订阅，新节目自动处理 |
| 📦 **批量处理** | 支持批量分析多个播客 |
| 🔔 **多渠道通知** | Slack/Email/Webhook/Telegram 通知 |
| ⏰ **定时任务** | 支持 Cron 调度 |

### 高级搜索

| 功能 | 描述 |
|------|------|
| 🔍 **语义搜索** | 基于嵌入向量的语义搜索 |
| 📚 **知识库** | 跨播客知识库管理 |
| 💾 **向量数据库** | 支持 ChromaDB/Pinecone |

### 多格式导出

| 格式 | 描述 |
|------|------|
| 📝 **Markdown** | 标准 Markdown 笔记 |
| 📊 **JSON** | 结构化 JSON 数据 |
| 📔 **Notion** | 同步到 Notion 数据库 |
| 🗺️ **思维导图** | Mermaid/Markmap 格式 |
| 🔮 **Obsidian** | Obsidian 笔记（支持双向链接） |
| 📽️ **PPT** | 自动生成演示文稿 |
| 📧 **Newsletter** | 生成邮件 Newsletter |

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

# 可选：说话人识别
HF_TOKEN=your_huggingface_token
```

### 使用方式

#### 命令行 (CLI)

```bash
# 分析本地音频文件
podcast-cli analyze ./podcast.mp3

# 分析 YouTube 视频
podcast-cli analyze "https://youtube.com/watch?v=xxx"

# 使用深度分析模板
podcast-cli analyze ./podcast.mp3 --template deep

# 批量处理
podcast-cli batch ./podcasts/ --template quick

# RSS 订阅监控
podcast-cli subscribe "https://feeds.example.com/podcast.xml"
podcast-cli monitor --interval 3600
```

#### Web 界面

```bash
# 启动 Web 界面
streamlit run src/web_app.py

# 浏览器访问 http://localhost:8501
```

#### API 服务

```bash
# 启动 API 服务
uvicorn src.api.app:app --host 0.0.0.0 --port 8000

# API 文档 http://localhost:8000/docs
```

#### Docker 部署

```bash
# 使用 Docker Compose 启动所有服务
docker-compose up -d

# 仅启动 API
docker-compose up -d api

# 启动完整服务（包含向量数据库）
docker-compose --profile full up -d
```

#### Python API

```python
from src.pipeline import PodcastPipeline

# 基础分析
pipeline = PodcastPipeline()
result = pipeline.process("./podcast.mp3")

print(result["summary"])
print(result["chapters"])
print(result["keywords"])

# 使用模板
result = pipeline.process("./podcast.mp3", template="deep")

# 高级功能
from src.advanced_analysis import FactChecker, KnowledgeGraphBuilder
from src.media_generation import VideoClipper, TTSSummaryGenerator
from src.search import KnowledgeBase

# 事实核查
checker = FactChecker()
facts = checker.check_facts(result["transcript"])

# 知识图谱
graph_builder = KnowledgeGraphBuilder()
graph = graph_builder.build_from_analysis(result)

# 生成短视频
clipper = VideoClipper()
clips = clipper.extract_highlights(audio_path, result["quotes"])

# 语义搜索
kb = KnowledgeBase()
kb.add_entry(...)
results = kb.search("AI 发展趋势")
```

## 📁 项目结构

```
podcast-summary/
├── src/
│   ├── main.py                 # CLI 入口
│   ├── web_app.py              # Web 界面
│   ├── pipeline.py             # 分析管道
│   ├── config.py               # 配置管理
│   │
│   ├── audio/                  # 音频处理
│   ├── transcription/          # 语音转文字
│   ├── analysis/               # 基础分析
│   │
│   ├── advanced_audio/         # 高级音频处理
│   │   ├── noise_reduction.py  # 降噪
│   │   ├── source_separation.py # 音源分离
│   │   ├── ad_detection.py     # 广告检测
│   │   └── audio_enhancer.py   # 音频增强
│   │
│   ├── advanced_analysis/      # 智能分析
│   │   ├── fact_checker.py     # 事实核查
│   │   ├── knowledge_graph.py  # 知识图谱
│   │   ├── entity_recognition.py # 实体识别
│   │   ├── opinion_analysis.py # 观点分析
│   │   ├── citation_detector.py # 引用检测
│   │   └── action_extractor.py # 行动项提取
│   │
│   ├── media_generation/       # 多媒体生成
│   │   ├── video_clipper.py    # 视频剪辑
│   │   ├── cover_generator.py  # 封面生成
│   │   ├── tts_summary.py      # 语音摘要
│   │   ├── social_posts.py     # 社交帖子
│   │   └── infographic.py      # 信息图表
│   │
│   ├── personalization/        # 个性化
│   │   ├── user_profile.py     # 用户画像
│   │   ├── templates.py        # 分析模板
│   │   └── collections.py      # 收藏管理
│   │
│   ├── automation/             # 自动化
│   │   ├── rss_monitor.py      # RSS 监控
│   │   ├── batch_processor.py  # 批量处理
│   │   ├── notifications.py    # 通知系统
│   │   └── scheduler.py        # 任务调度
│   │
│   ├── search/                 # 搜索
│   │   ├── semantic_search.py  # 语义搜索
│   │   ├── vector_store.py     # 向量存储
│   │   └── knowledge_base.py   # 知识库
│   │
│   ├── export/                 # 导出
│   │   ├── markdown.py
│   │   ├── json_export.py
│   │   ├── notion.py
│   │   ├── mindmap.py
│   │   └── advanced/
│   │       ├── obsidian.py     # Obsidian
│   │       ├── ppt_generator.py # PPT
│   │       └── newsletter.py   # Newsletter
│   │
│   ├── api/                    # API 服务
│   │   ├── app.py              # FastAPI 应用
│   │   ├── routes.py           # 路由定义
│   │   └── tasks.py            # 任务队列
│   │
│   └── utils/                  # 工具函数
│
├── Dockerfile                  # Docker 配置
├── docker-compose.yml          # Docker Compose
├── requirements.txt            # 依赖
├── pyproject.toml              # 项目配置
└── README.md
```

## 🔧 技术栈

- **语音识别**: faster-whisper / openai-whisper
- **说话人识别**: pyannote.audio
- **LLM**: Claude (Anthropic) / GPT (OpenAI)
- **向量搜索**: OpenAI Embeddings / Sentence Transformers
- **向量数据库**: ChromaDB / Pinecone
- **音频处理**: pydub, librosa, noisereduce
- **TTS**: Edge TTS / gTTS / OpenAI TTS
- **CLI**: Click + Rich
- **Web**: Streamlit
- **API**: FastAPI + Uvicorn
- **容器**: Docker + Docker Compose

## 📊 分析模板

| 模板 | 描述 | 输出 |
|------|------|------|
| `default` | 标准分析 | 摘要、章节、关键词、金句、问答 |
| `quick` | 快速摘要 | 简要摘要、关键词 |
| `deep` | 深度分析 | 全部功能 + 情感分析 + 实体识别 |
| `study` | 学习笔记 | 知识点、问答、行动项 |
| `content_creator` | 内容创作 | 金句、标题建议、社交帖子 |

## 🔌 API 端点

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/v1/analyze` | 提交分析任务 |
| POST | `/api/v1/analyze/upload` | 上传音频分析 |
| GET | `/api/v1/tasks/{id}` | 获取任务状态 |
| POST | `/api/v1/batch` | 批量分析 |
| POST | `/api/v1/search` | 知识库搜索 |
| GET | `/api/v1/templates` | 获取模板列表 |
| GET | `/api/v1/subscriptions` | RSS 订阅列表 |

## ⚙️ 环境变量

| 变量 | 说明 | 必填 |
|------|------|------|
| `ANTHROPIC_API_KEY` | Claude API 密钥 | 二选一 |
| `OPENAI_API_KEY` | OpenAI API 密钥 | 二选一 |
| `LLM_PROVIDER` | 默认 LLM (claude/openai) | 否 |
| `WHISPER_MODEL` | Whisper 模型 | 否 |
| `NOTION_API_KEY` | Notion API 密钥 | 否 |
| `NOTION_DATABASE_ID` | Notion 数据库 ID | 否 |
| `HF_TOKEN` | HuggingFace Token | 否 |
| `REDIS_URL` | Redis 连接地址 | 否 |

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 License

MIT License
