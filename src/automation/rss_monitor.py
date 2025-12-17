"""
RSS 订阅监控模块

自动监控播客 RSS 订阅，发现新节目时自动处理
"""

import asyncio
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Callable, Any
import json

from ..utils import get_logger, ensure_dir

logger = get_logger(__name__)


@dataclass
class FeedItem:
    """RSS 订阅项"""
    id: str
    title: str
    url: str
    published: Optional[datetime] = None
    description: str = ""
    duration: Optional[int] = None
    podcast_name: str = ""


@dataclass
class FeedSubscription:
    """RSS 订阅"""
    id: str
    name: str
    feed_url: str
    enabled: bool = True
    auto_process: bool = True
    process_template: str = "default"
    last_checked: Optional[str] = None
    last_item_id: Optional[str] = None
    check_interval: int = 3600  # 秒
    filters: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "feed_url": self.feed_url,
            "enabled": self.enabled,
            "auto_process": self.auto_process,
            "process_template": self.process_template,
            "last_checked": self.last_checked,
            "last_item_id": self.last_item_id,
            "check_interval": self.check_interval,
            "filters": self.filters,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FeedSubscription":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class RSSMonitor:
    """RSS 监控器"""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path.home() / ".podcast_summary" / "rss"
        ensure_dir(self.storage_dir)
        self._subscriptions: Dict[str, FeedSubscription] = {}
        self._callbacks: List[Callable[[FeedSubscription, FeedItem], Any]] = []
        self._running = False
        self._load_subscriptions()

    def _load_subscriptions(self):
        """加载订阅配置"""
        config_file = self.storage_dir / "subscriptions.json"
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for sub_data in data:
                        sub = FeedSubscription.from_dict(sub_data)
                        self._subscriptions[sub.id] = sub
            except Exception as e:
                logger.error(f"加载订阅配置失败: {e}")

    def _save_subscriptions(self):
        """保存订阅配置"""
        config_file = self.storage_dir / "subscriptions.json"
        try:
            data = [sub.to_dict() for sub in self._subscriptions.values()]
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存订阅配置失败: {e}")

    def add_subscription(
        self,
        name: str,
        feed_url: str,
        auto_process: bool = True,
        check_interval: int = 3600,
    ) -> FeedSubscription:
        """添加订阅"""
        sub_id = hashlib.md5(feed_url.encode()).hexdigest()[:8]

        subscription = FeedSubscription(
            id=sub_id,
            name=name,
            feed_url=feed_url,
            auto_process=auto_process,
            check_interval=check_interval,
        )

        self._subscriptions[sub_id] = subscription
        self._save_subscriptions()
        logger.info(f"添加订阅: {name} ({feed_url})")
        return subscription

    def remove_subscription(self, sub_id: str) -> bool:
        """移除订阅"""
        if sub_id in self._subscriptions:
            del self._subscriptions[sub_id]
            self._save_subscriptions()
            logger.info(f"移除订阅: {sub_id}")
            return True
        return False

    def get_subscription(self, sub_id: str) -> Optional[FeedSubscription]:
        """获取订阅"""
        return self._subscriptions.get(sub_id)

    def list_subscriptions(self) -> List[FeedSubscription]:
        """列出所有订阅"""
        return list(self._subscriptions.values())

    def on_new_episode(self, callback: Callable[[FeedSubscription, FeedItem], Any]):
        """注册新节目回调"""
        self._callbacks.append(callback)

    async def _parse_feed(self, feed_url: str) -> List[FeedItem]:
        """解析 RSS 订阅"""
        try:
            import feedparser
        except ImportError:
            logger.error("请安装 feedparser: pip install feedparser")
            return []

        try:
            feed = feedparser.parse(feed_url)
            items = []

            for entry in feed.entries:
                # 获取音频 URL
                audio_url = None
                if hasattr(entry, "enclosures") and entry.enclosures:
                    for enc in entry.enclosures:
                        if enc.get("type", "").startswith("audio/"):
                            audio_url = enc.get("href")
                            break

                if not audio_url:
                    continue

                # 解析发布时间
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])

                # 解析时长
                duration = None
                if hasattr(entry, "itunes_duration"):
                    try:
                        parts = str(entry.itunes_duration).split(":")
                        if len(parts) == 3:
                            duration = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                        elif len(parts) == 2:
                            duration = int(parts[0]) * 60 + int(parts[1])
                        else:
                            duration = int(parts[0])
                    except:
                        pass

                item = FeedItem(
                    id=entry.get("id", hashlib.md5(audio_url.encode()).hexdigest()[:8]),
                    title=entry.get("title", "未知标题"),
                    url=audio_url,
                    published=published,
                    description=entry.get("summary", ""),
                    duration=duration,
                    podcast_name=feed.feed.get("title", ""),
                )
                items.append(item)

            return items

        except Exception as e:
            logger.error(f"解析 RSS 失败 [{feed_url}]: {e}")
            return []

    async def check_subscription(self, subscription: FeedSubscription) -> List[FeedItem]:
        """检查订阅更新"""
        if not subscription.enabled:
            return []

        items = await self._parse_feed(subscription.feed_url)
        new_items = []

        for item in items:
            # 检查是否是新节目
            if subscription.last_item_id and item.id == subscription.last_item_id:
                break
            new_items.append(item)

        # 更新状态
        if items:
            subscription.last_item_id = items[0].id
        subscription.last_checked = datetime.now().isoformat()
        self._save_subscriptions()

        # 应用过滤器
        filtered_items = self._apply_filters(new_items, subscription.filters)

        # 触发回调
        for item in filtered_items:
            for callback in self._callbacks:
                try:
                    result = callback(subscription, item)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.error(f"回调执行失败: {e}")

        return filtered_items

    def _apply_filters(
        self,
        items: List[FeedItem],
        filters: Dict[str, Any],
    ) -> List[FeedItem]:
        """应用过滤器"""
        if not filters:
            return items

        filtered = []
        for item in items:
            # 标题过滤
            if "title_contains" in filters:
                if filters["title_contains"].lower() not in item.title.lower():
                    continue

            if "title_excludes" in filters:
                if filters["title_excludes"].lower() in item.title.lower():
                    continue

            # 时长过滤
            if "min_duration" in filters and item.duration:
                if item.duration < filters["min_duration"]:
                    continue

            if "max_duration" in filters and item.duration:
                if item.duration > filters["max_duration"]:
                    continue

            filtered.append(item)

        return filtered

    async def check_all(self) -> Dict[str, List[FeedItem]]:
        """检查所有订阅"""
        results = {}
        for sub_id, subscription in self._subscriptions.items():
            new_items = await self.check_subscription(subscription)
            if new_items:
                results[sub_id] = new_items
                logger.info(f"发现新节目 [{subscription.name}]: {len(new_items)} 个")
        return results

    async def start_monitoring(self):
        """开始监控"""
        self._running = True
        logger.info("RSS 监控已启动")

        while self._running:
            try:
                await self.check_all()
            except Exception as e:
                logger.error(f"监控检查失败: {e}")

            # 计算下一次检查时间
            min_interval = min(
                (sub.check_interval for sub in self._subscriptions.values() if sub.enabled),
                default=3600
            )
            await asyncio.sleep(min_interval)

    def stop_monitoring(self):
        """停止监控"""
        self._running = False
        logger.info("RSS 监控已停止")

    def export_opml(self) -> str:
        """导出为 OPML 格式"""
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<opml version="2.0">',
            "  <head>",
            "    <title>Podcast Subscriptions</title>",
            f"    <dateCreated>{datetime.now().isoformat()}</dateCreated>",
            "  </head>",
            "  <body>",
        ]

        for sub in self._subscriptions.values():
            lines.append(
                f'    <outline text="{sub.name}" type="rss" xmlUrl="{sub.feed_url}"/>'
            )

        lines.extend([
            "  </body>",
            "</opml>",
        ])

        return "\n".join(lines)

    def import_opml(self, opml_content: str) -> int:
        """从 OPML 导入订阅"""
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(opml_content)
            count = 0

            for outline in root.findall(".//outline"):
                feed_url = outline.get("xmlUrl")
                if feed_url:
                    name = outline.get("text") or outline.get("title") or "未命名"
                    self.add_subscription(name, feed_url)
                    count += 1

            return count
        except Exception as e:
            logger.error(f"导入 OPML 失败: {e}")
            return 0
