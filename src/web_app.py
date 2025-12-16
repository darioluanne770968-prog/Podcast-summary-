"""
播客分析工具 - Web 界面 (Streamlit)

运行方式:
    streamlit run src/web_app.py
"""

import asyncio
import tempfile
from pathlib import Path

import streamlit as st

# 页面配置
st.set_page_config(
    page_title="🎙️ Podcast Summary",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_session_state():
    """初始化 session state"""
    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None
    if "processing" not in st.session_state:
        st.session_state.processing = False


def main():
    """主函数"""
    init_session_state()

    # 标题
    st.title("🎙️ Podcast Summary")
    st.markdown("**播客分析和总结工具** - 自动转录、内容摘要、关键词提取、章节分割")

    # 侧边栏配置
    with st.sidebar:
        st.header("⚙️ 配置")

        # LLM 选择
        llm_provider = st.selectbox(
            "LLM 提供商",
            ["claude", "openai"],
            help="选择用于内容分析的 AI 模型",
        )

        # Whisper 模型
        whisper_model = st.selectbox(
            "Whisper 模型",
            ["large-v3", "large-v2", "medium", "small", "base", "tiny"],
            help="更大的模型精度更高，但速度更慢",
        )

        # 语言设置
        language = st.selectbox(
            "语言",
            ["auto", "zh", "en", "ja", "ko"],
            format_func=lambda x: {
                "auto": "自动检测",
                "zh": "中文",
                "en": "英文",
                "ja": "日语",
                "ko": "韩语",
            }.get(x, x),
        )

        st.divider()

        # 功能开关
        st.subheader("📊 分析功能")
        enable_summary = st.checkbox("内容摘要", value=True)
        enable_keywords = st.checkbox("关键词提取", value=True)
        enable_chapters = st.checkbox("章节分割", value=True)
        enable_quotes = st.checkbox("金句提取", value=True)
        enable_sentiment = st.checkbox("情感分析", value=False)
        enable_qa = st.checkbox("问答生成", value=True)
        enable_diarization = st.checkbox("说话人识别", value=False, help="需要 HuggingFace Token")

        st.divider()

        # 导出选项
        st.subheader("📤 导出选项")
        export_json = st.checkbox("导出 JSON", value=False)
        export_mindmap = st.checkbox("生成思维导图", value=False)
        include_transcript = st.checkbox("包含完整转录", value=False)

    # 主内容区
    tab1, tab2, tab3 = st.tabs(["📥 上传分析", "🔗 URL 分析", "📄 结果查看"])

    with tab1:
        st.subheader("上传音频文件")
        uploaded_file = st.file_uploader(
            "选择音频文件",
            type=["mp3", "wav", "m4a", "flac", "ogg", "mp4", "webm"],
            help="支持的格式: MP3, WAV, M4A, FLAC, OGG, MP4, WebM",
        )

        if uploaded_file:
            st.audio(uploaded_file)

            title = st.text_input("播客标题（可选）", value=uploaded_file.name)

            if st.button("🚀 开始分析", key="analyze_upload", type="primary"):
                _run_analysis(
                    uploaded_file,
                    title,
                    whisper_model,
                    language if language != "auto" else None,
                    llm_provider,
                    enable_summary,
                    enable_keywords,
                    enable_chapters,
                    enable_quotes,
                    enable_sentiment,
                    enable_qa,
                    enable_diarization,
                    export_json,
                    export_mindmap,
                    include_transcript,
                )

    with tab2:
        st.subheader("从 URL 分析")
        st.markdown("""
        支持的来源：
        - 🎬 YouTube 视频
        - 📻 播客 RSS 订阅
        - 🎧 小宇宙播客
        - 🔗 直接音频链接
        """)

        url = st.text_input(
            "输入 URL",
            placeholder="https://youtube.com/watch?v=xxx",
        )

        title_url = st.text_input("播客标题（可选）", key="title_url")

        if st.button("🚀 开始分析", key="analyze_url", type="primary"):
            if not url:
                st.error("请输入 URL")
            else:
                _run_analysis(
                    url,
                    title_url,
                    whisper_model,
                    language if language != "auto" else None,
                    llm_provider,
                    enable_summary,
                    enable_keywords,
                    enable_chapters,
                    enable_quotes,
                    enable_sentiment,
                    enable_qa,
                    enable_diarization,
                    export_json,
                    export_mindmap,
                    include_transcript,
                )

    with tab3:
        st.subheader("分析结果")

        if st.session_state.analysis_result:
            _display_results(st.session_state.analysis_result)
        else:
            st.info("👆 请先上传文件或输入 URL 进行分析")


def _run_analysis(
    source,
    title,
    whisper_model,
    language,
    llm_provider,
    enable_summary,
    enable_keywords,
    enable_chapters,
    enable_quotes,
    enable_sentiment,
    enable_qa,
    enable_diarization,
    export_json,
    export_mindmap,
    include_transcript,
):
    """运行分析"""
    from .config import LLMProvider
    from .pipeline import PodcastAnalyzer, PipelineConfig

    # 创建临时目录
    output_dir = Path(tempfile.mkdtemp())

    # 如果是上传的文件，保存到临时目录
    if hasattr(source, "read"):
        temp_path = output_dir / source.name
        with open(temp_path, "wb") as f:
            f.write(source.read())
        source = str(temp_path)

    # 配置
    config = PipelineConfig(
        output_dir=output_dir,
        whisper_model=whisper_model,
        language=language,
        llm_provider=LLMProvider(llm_provider),
        enable_summary=enable_summary,
        enable_keywords=enable_keywords,
        enable_chapters=enable_chapters,
        enable_quotes=enable_quotes,
        enable_sentiment=enable_sentiment,
        enable_qa=enable_qa,
        enable_diarization=enable_diarization,
        export_markdown=True,
        export_json=export_json,
        export_mindmap=export_mindmap,
        include_transcript=include_transcript,
    )

    # 进度条
    progress_bar = st.progress(0, text="准备中...")
    status_text = st.empty()

    stages_progress = {
        "download": 0.1,
        "transcription": 0.4,
        "diarization": 0.5,
        "analysis": 0.9,
        "export": 1.0,
    }

    def progress_callback(stage: str, pct: float, message: str):
        base = stages_progress.get(stage, 0)
        progress_bar.progress(min(base, 1.0), text=message)
        status_text.text(message)

    try:
        analyzer = PodcastAnalyzer(config)

        with st.spinner("正在分析..."):
            result = analyzer.analyze_sync(source, title, progress_callback)

        st.session_state.analysis_result = result
        progress_bar.progress(1.0, text="✅ 分析完成!")
        st.success("分析完成！请查看「结果查看」标签页")
        st.rerun()

    except Exception as e:
        st.error(f"分析失败: {e}")
        progress_bar.empty()
        status_text.empty()


def _display_results(result):
    """显示分析结果"""
    # 基本信息
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("标题", result.title[:30] + "..." if len(result.title) > 30 else result.title)
    with col2:
        if result.duration:
            mins = int(result.duration // 60)
            secs = int(result.duration % 60)
            st.metric("时长", f"{mins}:{secs:02d}")
    with col3:
        lang = result.metadata.get("language", "未知")
        st.metric("语言", lang)

    st.divider()

    # 使用 expander 组织内容
    if result.summary:
        with st.expander("📝 内容摘要", expanded=True):
            if hasattr(result.summary, "brief"):
                st.markdown(f"**一句话概括**: {result.summary.brief}")
                st.markdown("---")

            if hasattr(result.summary, "detailed"):
                st.markdown(result.summary.detailed)

            if hasattr(result.summary, "key_points") and result.summary.key_points:
                st.markdown("### 核心要点")
                for point in result.summary.key_points:
                    st.markdown(f"- {point}")

            if hasattr(result.summary, "takeaways") and result.summary.takeaways:
                st.markdown("### 💡 收获与启发")
                for takeaway in result.summary.takeaways:
                    st.markdown(f"- {takeaway}")

    if result.chapters:
        with st.expander("📑 章节目录", expanded=True):
            for chapter in result.chapters:
                time = chapter.start_formatted if hasattr(chapter, "start_formatted") else ""
                title = chapter.title if hasattr(chapter, "title") else chapter.get("title", "")
                summary = getattr(chapter, "summary", None) or chapter.get("summary", "")

                st.markdown(f"**[{time}]** {title}")
                if summary:
                    st.markdown(f"<small>{summary}</small>", unsafe_allow_html=True)

    if result.keywords:
        with st.expander("🏷️ 关键词", expanded=True):
            tags = []
            for kw in result.keywords:
                if hasattr(kw, "word"):
                    tags.append(kw.word)
                elif isinstance(kw, str):
                    tags.append(kw)
                else:
                    tags.append(kw.get("word", ""))

            st.markdown(" ".join([f"`{tag}`" for tag in tags]))

    if result.quotes:
        with st.expander("💬 金句摘录", expanded=True):
            for quote in result.quotes:
                if hasattr(quote, "text"):
                    text = quote.text
                    speaker = getattr(quote, "speaker", None)
                    time = getattr(quote, "timestamp_formatted", "")
                else:
                    text = quote.get("text", "")
                    speaker = quote.get("speaker")
                    time = quote.get("timestamp_formatted", "")

                speaker_part = f" — {speaker}" if speaker else ""
                time_part = f" [{time}]" if time else ""
                st.markdown(f"> \"{text}\"{speaker_part}{time_part}")

    if result.sentiment:
        with st.expander("😊 情感分析"):
            if hasattr(result.sentiment, "tone"):
                st.markdown(f"**整体基调**: {result.sentiment.tone}")

            if hasattr(result.sentiment, "emotions") and result.sentiment.emotions:
                import pandas as pd
                emotions_df = pd.DataFrame([
                    {"情感": k, "占比": v}
                    for k, v in result.sentiment.emotions.items()
                ])
                st.bar_chart(emotions_df.set_index("情感"))

    if result.qa_pairs:
        with st.expander("❓ 问答复习"):
            for i, qa in enumerate(result.qa_pairs, 1):
                if hasattr(qa, "question"):
                    question = qa.question
                    answer = qa.answer
                else:
                    question = qa.get("question", "")
                    answer = qa.get("answer", "")

                with st.container():
                    st.markdown(f"**Q{i}: {question}**")
                    st.markdown(f"A: {answer}")
                    st.divider()

    if result.speaker_stats:
        with st.expander("👥 说话人统计"):
            for speaker, stats in result.speaker_stats.items():
                duration = stats.get("total_duration_formatted", "")
                percentage = stats.get("percentage", 0)
                st.markdown(f"- **{speaker}**: {duration} ({percentage:.1f}%)")

    # 转录文本
    if result.transcript_with_timestamps:
        with st.expander("📜 完整转录"):
            st.text_area(
                "转录文本",
                result.transcript_with_timestamps,
                height=400,
            )

    # 下载按钮
    st.divider()
    st.subheader("📥 下载")

    col1, col2 = st.columns(2)
    with col1:
        # 生成 Markdown
        from .export import MarkdownExporter
        from io import StringIO

        md_content = _generate_markdown(result)
        st.download_button(
            "📄 下载 Markdown",
            md_content,
            file_name=f"{result.title[:30]}.md",
            mime="text/markdown",
        )

    with col2:
        # 生成 JSON
        import json
        json_content = _generate_json(result)
        st.download_button(
            "📋 下载 JSON",
            json_content,
            file_name=f"{result.title[:30]}.json",
            mime="application/json",
        )


def _generate_markdown(result) -> str:
    """生成 Markdown 内容"""
    lines = [f"# 🎙️ {result.title}\n"]

    if result.summary:
        lines.append("## 📝 内容摘要\n")
        if hasattr(result.summary, "brief"):
            lines.append(f"**概述**: {result.summary.brief}\n")
        if hasattr(result.summary, "detailed"):
            lines.append(result.summary.detailed + "\n")

    if result.chapters:
        lines.append("## 📑 章节目录\n")
        for ch in result.chapters:
            time = ch.start_formatted if hasattr(ch, "start_formatted") else ""
            title = ch.title if hasattr(ch, "title") else ch.get("title", "")
            lines.append(f"- [{time}] {title}")
        lines.append("")

    if result.keywords:
        lines.append("## 🏷️ 关键词\n")
        tags = [kw.word if hasattr(kw, "word") else kw for kw in result.keywords]
        lines.append(" ".join([f"`{tag}`" for tag in tags]) + "\n")

    if result.quotes:
        lines.append("## 💬 金句摘录\n")
        for quote in result.quotes:
            text = quote.text if hasattr(quote, "text") else quote.get("text", "")
            lines.append(f"> \"{text}\"\n")

    return "\n".join(lines)


def _generate_json(result) -> str:
    """生成 JSON 内容"""
    import json

    data = {
        "title": result.title,
        "duration": result.duration,
        "metadata": result.metadata,
    }

    if result.summary and hasattr(result.summary, "to_dict"):
        data["summary"] = result.summary.to_dict()

    if result.chapters:
        data["chapters"] = [
            ch.to_dict() if hasattr(ch, "to_dict") else ch
            for ch in result.chapters
        ]

    if result.keywords:
        data["keywords"] = [
            kw.to_dict() if hasattr(kw, "to_dict") else kw
            for kw in result.keywords
        ]

    if result.quotes:
        data["quotes"] = [
            q.to_dict() if hasattr(q, "to_dict") else q
            for q in result.quotes
        ]

    return json.dumps(data, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
