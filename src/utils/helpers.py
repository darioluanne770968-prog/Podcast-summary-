"""
辅助工具函数
"""

import hashlib
import re
import unicodedata
from pathlib import Path
from typing import Union


def format_timestamp(seconds: float) -> str:
    """
    将秒数转换为时间戳格式 (HH:MM:SS 或 MM:SS)

    Args:
        seconds: 秒数

    Returns:
        格式化的时间戳字符串
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def parse_timestamp(timestamp: str) -> float:
    """
    将时间戳字符串解析为秒数

    Args:
        timestamp: 时间戳字符串 (HH:MM:SS 或 MM:SS)

    Returns:
        秒数
    """
    parts = timestamp.split(":")
    if len(parts) == 3:
        hours, minutes, seconds = map(float, parts)
        return hours * 3600 + minutes * 60 + seconds
    elif len(parts) == 2:
        minutes, seconds = map(float, parts)
        return minutes * 60 + seconds
    else:
        return float(parts[0])


def ensure_dir(path: Union[str, Path]) -> Path:
    """
    确保目录存在，如果不存在则创建

    Args:
        path: 目录路径

    Returns:
        Path 对象
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_file_hash(file_path: Union[str, Path], algorithm: str = "md5") -> str:
    """
    计算文件的哈希值

    Args:
        file_path: 文件路径
        algorithm: 哈希算法 (md5, sha256 等)

    Returns:
        哈希值字符串
    """
    hash_func = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_func.update(chunk)
    return hash_func.hexdigest()


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    清理文件名，移除非法字符

    Args:
        filename: 原始文件名
        max_length: 最大长度

    Returns:
        清理后的文件名
    """
    # 规范化 Unicode
    filename = unicodedata.normalize("NFKC", filename)

    # 移除非法字符
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", filename)

    # 移除首尾空格和点
    filename = filename.strip(" .")

    # 限制长度
    if len(filename) > max_length:
        filename = filename[:max_length]

    # 如果文件名为空，使用默认名
    if not filename:
        filename = "untitled"

    return filename


def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """
    截断文本到指定长度

    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 截断后缀

    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def count_tokens_estimate(text: str) -> int:
    """
    估算文本的 token 数量（粗略估计）

    Args:
        text: 文本

    Returns:
        估计的 token 数量
    """
    # 粗略估计：中文每个字约 1.5 token，英文每 4 个字符约 1 token
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    other_chars = len(text) - chinese_chars
    return int(chinese_chars * 1.5 + other_chars / 4)
