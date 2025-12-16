"""
播客分析工具 - 命令行界面

Usage:
    podcast-cli analyze <source> [options]
    podcast-cli transcribe <source> [options]
    podcast-cli info <source>
"""

import asyncio
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

from .config import get_settings, LLMProvider
from .utils import setup_logging, get_logger
from .pipeline import PodcastAnalyzer, PipelineConfig

console = Console()
logger = get_logger(__name__)


@click.group()
@click.option("--debug", is_flag=True, help="启用调试模式")
@click.version_option(version="1.0.0", prog_name="podcast-cli")
def cli(debug: bool):
    """🎙️ Podcast Summary - 播客分析和总结工具"""
    import logging
    setup_logging(level=logging.DEBUG if debug else logging.INFO)


@cli.command()
@click.argument("source")
@click.option("--title", "-t", help="播客标题")
@click.option("--output", "-o", default="./output", help="输出目录")
@click.option("--language", "-l", help="语言代码 (zh, en, auto)")
@click.option("--provider", "-p", type=click.Choice(["claude", "openai"]), help="LLM 提供商")
@click.option("--full", is_flag=True, help="启用全部分析功能")
@click.option("--diarization", is_flag=True, help="启用说话人识别")
@click.option("--json", "export_json", is_flag=True, help="同时导出 JSON")
@click.option("--notion", is_flag=True, help="同步到 Notion")
@click.option("--mindmap", is_flag=True, help="生成思维导图")
@click.option("--transcript", is_flag=True, help="包含完整转录文本")
@click.option("--whisper-model", default="large-v3", help="Whisper 模型")
def analyze(
    source: str,
    title: Optional[str],
    output: str,
    language: Optional[str],
    provider: Optional[str],
    full: bool,
    diarization: bool,
    export_json: bool,
    notion: bool,
    mindmap: bool,
    transcript: bool,
    whisper_model: str,
):
    """分析播客内容

    SOURCE 可以是：
    - 本地音频文件路径
    - YouTube 视频 URL
    - 播客 RSS 订阅 URL
    - 小宇宙播客链接
    - 直接音频文件 URL

    \b
    示例:
      podcast-cli analyze ./podcast.mp3
      podcast-cli analyze "https://youtube.com/watch?v=xxx"
      podcast-cli analyze "https://feeds.example.com/podcast.xml" --full
    """
    console.print(Panel.fit(
        "[bold blue]🎙️ Podcast Summary Tool[/bold blue]\n"
        "播客分析和总结工具",
        border_style="blue",
    ))

    # 配置
    config = PipelineConfig(
        output_dir=Path(output),
        whisper_model=whisper_model,
        language=language,
        enable_diarization=diarization or full,
        enable_summary=True,
        enable_keywords=True,
        enable_chapters=True,
        enable_quotes=True,
        enable_sentiment=full,
        enable_qa=True,
        export_markdown=True,
        export_json=export_json or full,
        export_notion=notion,
        export_mindmap=mindmap or full,
        include_transcript=transcript,
    )

    if provider:
        config.llm_provider = LLMProvider(provider)

    # 进度显示
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        stages = {
            "download": progress.add_task("[cyan]获取音频...", total=100),
            "transcription": progress.add_task("[yellow]转录中...", total=100),
            "diarization": progress.add_task("[magenta]说话人识别...", total=100, visible=config.enable_diarization),
            "analysis": progress.add_task("[green]分析内容...", total=100),
            "export": progress.add_task("[blue]导出结果...", total=100),
        }

        def progress_callback(stage: str, pct: float, message: str):
            if stage in stages:
                progress.update(stages[stage], completed=pct * 100, description=f"[cyan]{message}")

        try:
            analyzer = PodcastAnalyzer(config)
            result = analyzer.analyze_sync(source, title, progress_callback)

            # 显示结果摘要
            _display_result_summary(result)

        except Exception as e:
            console.print(f"[red]错误: {e}[/red]")
            raise click.Abort()


@cli.command()
@click.argument("source")
@click.option("--output", "-o", default="./output", help="输出目录")
@click.option("--language", "-l", help="语言代码")
@click.option("--model", "-m", default="large-v3", help="Whisper 模型")
@click.option("--srt", is_flag=True, help="导出 SRT 字幕")
def transcribe(
    source: str,
    output: str,
    language: Optional[str],
    model: str,
    srt: bool,
):
    """仅转录音频（不进行分析）

    \b
    示例:
      podcast-cli transcribe ./podcast.mp3
      podcast-cli transcribe ./video.mp4 --srt
    """
    from .audio import AudioDownloader
    from .transcription import WhisperTranscriber

    console.print("[cyan]开始转录...[/cyan]")

    with console.status("[bold green]处理中..."):
        # 获取音频
        downloader = AudioDownloader(Path(output))
        source_info = asyncio.run(downloader.download(source))

        # 转录
        transcriber = WhisperTranscriber(model_name=model)
        result = transcriber.transcribe(source_info.local_path, language=language)

    # 保存结果
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存文本
    txt_path = output_dir / f"{source_info.title or 'transcript'}.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(result.full_text_with_timestamps)

    console.print(f"[green]转录完成![/green]")
    console.print(f"- 语言: {result.language}")
    console.print(f"- 时长: {result.duration:.1f}s")
    console.print(f"- 片段数: {len(result.segments)}")
    console.print(f"- 文件: {txt_path}")

    # 导出 SRT
    if srt:
        srt_path = output_dir / f"{source_info.title or 'transcript'}.srt"
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(result.to_srt())
        console.print(f"- SRT: {srt_path}")


@cli.command()
@click.argument("source")
def info(source: str):
    """显示音频/来源信息

    \b
    示例:
      podcast-cli info ./podcast.mp3
      podcast-cli info "https://youtube.com/watch?v=xxx"
    """
    from .audio import AudioDownloader, AudioConverter

    downloader = AudioDownloader()

    with console.status("[bold green]获取信息..."):
        source_type = downloader.detect_source_type(source)
        source_info = asyncio.run(downloader.download(source))

        if source_info.local_path:
            converter = AudioConverter()
            audio_info = converter.get_audio_info(source_info.local_path)
        else:
            audio_info = {}

    # 显示信息表格
    table = Table(title="📋 音频信息", show_header=False)
    table.add_column("属性", style="cyan")
    table.add_column("值")

    table.add_row("来源类型", source_type.value)
    table.add_row("标题", source_info.title or "-")
    table.add_row("作者", source_info.author or "-")
    table.add_row("URL", source_info.url or "-")

    if audio_info:
        table.add_row("时长", audio_info.get("duration_formatted", "-"))
        table.add_row("采样率", f"{audio_info.get('sample_rate', '-')} Hz")
        table.add_row("声道", str(audio_info.get("channels", "-")))
        table.add_row("文件大小", f"{audio_info.get('file_size_mb', 0):.2f} MB")

    console.print(table)


@cli.command()
@click.argument("rss_url")
@click.option("--limit", "-n", default=10, help="显示条目数")
def list_episodes(rss_url: str, limit: int):
    """列出 RSS 订阅中的节目

    \b
    示例:
      podcast-cli list-episodes "https://feeds.example.com/podcast.xml"
    """
    from .audio import AudioDownloader

    downloader = AudioDownloader()

    with console.status("[bold green]获取订阅..."):
        episodes = downloader.list_rss_episodes(rss_url, limit)

    table = Table(title="📻 播客节目列表")
    table.add_column("#", style="cyan", width=4)
    table.add_column("标题", width=50)
    table.add_column("发布时间", width=20)

    for ep in episodes:
        table.add_row(
            str(ep["index"]),
            ep["title"][:50],
            ep["published"][:20] if ep["published"] else "-",
        )

    console.print(table)
    console.print(f"\n[dim]使用 --rss-index N 选项来分析特定节目[/dim]")


@cli.command()
def check():
    """检查配置和依赖"""
    settings = get_settings()

    table = Table(title="⚙️ 配置检查")
    table.add_column("项目", style="cyan")
    table.add_column("状态")
    table.add_column("详情")

    # 检查 API Keys
    anthropic_ok = bool(settings.anthropic_api_key)
    table.add_row(
        "Anthropic API",
        "✅" if anthropic_ok else "❌",
        "已配置" if anthropic_ok else "未配置 ANTHROPIC_API_KEY",
    )

    openai_ok = bool(settings.openai_api_key)
    table.add_row(
        "OpenAI API",
        "✅" if openai_ok else "❌",
        "已配置" if openai_ok else "未配置 OPENAI_API_KEY",
    )

    notion_ok = settings.validate_notion_config()
    table.add_row(
        "Notion",
        "✅" if notion_ok else "⚠️",
        "已配置" if notion_ok else "未配置（可选）",
    )

    hf_ok = bool(settings.hf_token)
    table.add_row(
        "HuggingFace Token",
        "✅" if hf_ok else "⚠️",
        "已配置" if hf_ok else "未配置（说话人识别需要）",
    )

    # 检查依赖
    try:
        import faster_whisper
        table.add_row("faster-whisper", "✅", "已安装")
    except ImportError:
        table.add_row("faster-whisper", "❌", "未安装")

    try:
        import torch
        cuda_available = torch.cuda.is_available()
        table.add_row(
            "PyTorch + CUDA",
            "✅" if cuda_available else "⚠️",
            f"CUDA {'可用' if cuda_available else '不可用（将使用 CPU）'}",
        )
    except ImportError:
        table.add_row("PyTorch", "❌", "未安装")

    console.print(table)


def _display_result_summary(result):
    """显示结果摘要"""
    console.print("\n")
    console.print(Panel.fit(
        f"[bold green]✅ 分析完成[/bold green]\n\n"
        f"📝 标题: {result.title}\n"
        f"⏱️ 时长: {result.metadata.get('duration_formatted', '-')}\n"
        f"🌐 语言: {result.metadata.get('language', '-')}",
        title="结果摘要",
        border_style="green",
    ))

    # 显示摘要
    if result.summary and hasattr(result.summary, "brief"):
        console.print(f"\n[bold]📋 简要摘要:[/bold]\n{result.summary.brief}")

    # 显示关键词
    if result.keywords:
        tags = [kw.word if hasattr(kw, "word") else kw for kw in result.keywords[:10]]
        console.print(f"\n[bold]🏷️ 关键词:[/bold] {', '.join(tags)}")

    # 显示章节
    if result.chapters:
        console.print(f"\n[bold]📑 章节 ({len(result.chapters)}):[/bold]")
        for ch in result.chapters[:5]:
            time = ch.start_formatted if hasattr(ch, "start_formatted") else ""
            title = ch.title if hasattr(ch, "title") else ch.get("title", "")
            console.print(f"  [{time}] {title}")
        if len(result.chapters) > 5:
            console.print(f"  ... 还有 {len(result.chapters) - 5} 个章节")

    console.print(f"\n[dim]详细结果已保存到输出目录[/dim]")


if __name__ == "__main__":
    cli()
