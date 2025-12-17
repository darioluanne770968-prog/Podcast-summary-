"""
通知系统模块

支持多种通知渠道：Slack、Email、Webhook 等
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum
import json

from ..utils import get_logger, ensure_dir

logger = get_logger(__name__)


class NotificationType(str, Enum):
    """通知类型"""
    NEW_EPISODE = "new_episode"
    PROCESS_COMPLETE = "process_complete"
    PROCESS_FAILED = "process_failed"
    BATCH_COMPLETE = "batch_complete"
    SYSTEM_ERROR = "system_error"


class NotificationChannel(str, Enum):
    """通知渠道"""
    SLACK = "slack"
    EMAIL = "email"
    WEBHOOK = "webhook"
    DESKTOP = "desktop"
    TELEGRAM = "telegram"


@dataclass
class NotificationConfig:
    """通知配置"""
    channel: NotificationChannel
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    notification_types: List[NotificationType] = field(
        default_factory=lambda: list(NotificationType)
    )


@dataclass
class Notification:
    """通知消息"""
    id: str
    type: NotificationType
    title: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    sent: bool = False
    channels_sent: List[str] = field(default_factory=list)


class NotificationManager:
    """通知管理器"""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path.home() / ".podcast_summary" / "notifications"
        ensure_dir(self.storage_dir)
        self._channels: Dict[str, NotificationConfig] = {}
        self._history: List[Notification] = []
        self._load_config()

    def _load_config(self):
        """加载配置"""
        config_file = self.storage_dir / "config.json"
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for name, config_data in data.get("channels", {}).items():
                        self._channels[name] = NotificationConfig(
                            channel=NotificationChannel(config_data["channel"]),
                            enabled=config_data.get("enabled", True),
                            config=config_data.get("config", {}),
                            notification_types=[
                                NotificationType(t) for t in config_data.get("notification_types", [])
                            ] or list(NotificationType),
                        )
            except Exception as e:
                logger.error(f"加载通知配置失败: {e}")

    def _save_config(self):
        """保存配置"""
        config_file = self.storage_dir / "config.json"
        try:
            data = {
                "channels": {
                    name: {
                        "channel": config.channel.value,
                        "enabled": config.enabled,
                        "config": config.config,
                        "notification_types": [t.value for t in config.notification_types],
                    }
                    for name, config in self._channels.items()
                }
            }
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存通知配置失败: {e}")

    def add_channel(
        self,
        name: str,
        channel: NotificationChannel,
        config: Dict[str, Any],
        notification_types: Optional[List[NotificationType]] = None,
    ):
        """添加通知渠道"""
        self._channels[name] = NotificationConfig(
            channel=channel,
            config=config,
            notification_types=notification_types or list(NotificationType),
        )
        self._save_config()
        logger.info(f"添加通知渠道: {name} ({channel.value})")

    def remove_channel(self, name: str) -> bool:
        """移除通知渠道"""
        if name in self._channels:
            del self._channels[name]
            self._save_config()
            return True
        return False

    def configure_slack(
        self,
        webhook_url: str,
        channel: str = "#podcast-updates",
        name: str = "slack",
    ):
        """配置 Slack 通知"""
        self.add_channel(
            name=name,
            channel=NotificationChannel.SLACK,
            config={
                "webhook_url": webhook_url,
                "channel": channel,
            },
        )

    def configure_email(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_addr: str,
        to_addrs: List[str],
        name: str = "email",
    ):
        """配置邮件通知"""
        self.add_channel(
            name=name,
            channel=NotificationChannel.EMAIL,
            config={
                "smtp_host": smtp_host,
                "smtp_port": smtp_port,
                "username": username,
                "password": password,
                "from_addr": from_addr,
                "to_addrs": to_addrs,
            },
        )

    def configure_webhook(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        name: str = "webhook",
    ):
        """配置 Webhook 通知"""
        self.add_channel(
            name=name,
            channel=NotificationChannel.WEBHOOK,
            config={
                "url": url,
                "headers": headers or {},
            },
        )

    def configure_telegram(
        self,
        bot_token: str,
        chat_id: str,
        name: str = "telegram",
    ):
        """配置 Telegram 通知"""
        self.add_channel(
            name=name,
            channel=NotificationChannel.TELEGRAM,
            config={
                "bot_token": bot_token,
                "chat_id": chat_id,
            },
        )

    async def send(
        self,
        notification_type: NotificationType,
        title: str,
        message: str,
        data: Optional[Dict] = None,
    ) -> Notification:
        """发送通知"""
        import uuid
        notification = Notification(
            id=str(uuid.uuid4())[:8],
            type=notification_type,
            title=title,
            message=message,
            data=data or {},
        )

        for name, config in self._channels.items():
            if not config.enabled:
                continue
            if notification_type not in config.notification_types:
                continue

            try:
                await self._send_to_channel(notification, config)
                notification.channels_sent.append(name)
            except Exception as e:
                logger.error(f"发送通知失败 [{name}]: {e}")

        notification.sent = len(notification.channels_sent) > 0
        self._history.append(notification)

        # 保留最近 1000 条记录
        if len(self._history) > 1000:
            self._history = self._history[-1000:]

        return notification

    async def _send_to_channel(
        self,
        notification: Notification,
        config: NotificationConfig,
    ):
        """发送到指定渠道"""
        if config.channel == NotificationChannel.SLACK:
            await self._send_slack(notification, config.config)
        elif config.channel == NotificationChannel.EMAIL:
            await self._send_email(notification, config.config)
        elif config.channel == NotificationChannel.WEBHOOK:
            await self._send_webhook(notification, config.config)
        elif config.channel == NotificationChannel.TELEGRAM:
            await self._send_telegram(notification, config.config)
        elif config.channel == NotificationChannel.DESKTOP:
            await self._send_desktop(notification, config.config)

    async def _send_slack(self, notification: Notification, config: Dict):
        """发送 Slack 通知"""
        try:
            import aiohttp
        except ImportError:
            logger.error("请安装 aiohttp: pip install aiohttp")
            return

        webhook_url = config.get("webhook_url")
        if not webhook_url:
            return

        # 构建 Slack 消息
        emoji_map = {
            NotificationType.NEW_EPISODE: ":headphones:",
            NotificationType.PROCESS_COMPLETE: ":white_check_mark:",
            NotificationType.PROCESS_FAILED: ":x:",
            NotificationType.BATCH_COMPLETE: ":package:",
            NotificationType.SYSTEM_ERROR: ":warning:",
        }

        payload = {
            "channel": config.get("channel", "#podcast-updates"),
            "username": "Podcast Summary Bot",
            "icon_emoji": emoji_map.get(notification.type, ":robot_face:"),
            "attachments": [
                {
                    "color": "#36a64f" if "complete" in notification.type.value else "#ff0000",
                    "title": notification.title,
                    "text": notification.message,
                    "footer": "Podcast Summary Tool",
                    "ts": datetime.now().timestamp(),
                }
            ],
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as resp:
                if resp.status != 200:
                    raise Exception(f"Slack API 错误: {resp.status}")

        logger.info(f"Slack 通知已发送: {notification.title}")

    async def _send_email(self, notification: Notification, config: Dict):
        """发送邮件通知"""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart()
        msg["From"] = config["from_addr"]
        msg["To"] = ", ".join(config["to_addrs"])
        msg["Subject"] = f"[播客摘要] {notification.title}"

        # 构建邮件正文
        body = f"""
        <html>
        <body>
        <h2>{notification.title}</h2>
        <p>{notification.message}</p>
        <hr>
        <small>此邮件由 Podcast Summary Tool 自动发送</small>
        </body>
        </html>
        """
        msg.attach(MIMEText(body, "html"))

        # 发送邮件
        def send():
            with smtplib.SMTP(config["smtp_host"], config["smtp_port"]) as server:
                server.starttls()
                server.login(config["username"], config["password"])
                server.send_message(msg)

        await asyncio.get_event_loop().run_in_executor(None, send)
        logger.info(f"邮件通知已发送: {notification.title}")

    async def _send_webhook(self, notification: Notification, config: Dict):
        """发送 Webhook 通知"""
        try:
            import aiohttp
        except ImportError:
            logger.error("请安装 aiohttp: pip install aiohttp")
            return

        url = config.get("url")
        if not url:
            return

        payload = {
            "id": notification.id,
            "type": notification.type.value,
            "title": notification.title,
            "message": notification.message,
            "data": notification.data,
            "timestamp": notification.created_at,
        }

        headers = config.get("headers", {})
        headers["Content-Type"] = "application/json"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status not in [200, 201, 204]:
                    raise Exception(f"Webhook 错误: {resp.status}")

        logger.info(f"Webhook 通知已发送: {notification.title}")

    async def _send_telegram(self, notification: Notification, config: Dict):
        """发送 Telegram 通知"""
        try:
            import aiohttp
        except ImportError:
            logger.error("请安装 aiohttp: pip install aiohttp")
            return

        bot_token = config.get("bot_token")
        chat_id = config.get("chat_id")
        if not bot_token or not chat_id:
            return

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": f"*{notification.title}*\n\n{notification.message}",
            "parse_mode": "Markdown",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    raise Exception(f"Telegram API 错误: {resp.status}")

        logger.info(f"Telegram 通知已发送: {notification.title}")

    async def _send_desktop(self, notification: Notification, config: Dict):
        """发送桌面通知"""
        try:
            import platform
            system = platform.system()

            if system == "Darwin":  # macOS
                import subprocess
                subprocess.run([
                    "osascript", "-e",
                    f'display notification "{notification.message}" with title "{notification.title}"'
                ])
            elif system == "Linux":
                import subprocess
                subprocess.run([
                    "notify-send",
                    notification.title,
                    notification.message,
                ])
            elif system == "Windows":
                try:
                    from win10toast import ToastNotifier
                    toaster = ToastNotifier()
                    toaster.show_toast(
                        notification.title,
                        notification.message,
                        duration=5,
                    )
                except ImportError:
                    logger.warning("Windows 桌面通知需要安装 win10toast")

            logger.info(f"桌面通知已发送: {notification.title}")
        except Exception as e:
            logger.error(f"发送桌面通知失败: {e}")

    # 便捷方法
    async def notify_new_episode(
        self,
        podcast_name: str,
        episode_title: str,
        url: str,
    ):
        """通知新节目"""
        await self.send(
            NotificationType.NEW_EPISODE,
            f"新节目: {podcast_name}",
            f"《{episode_title}》已发布",
            {"podcast": podcast_name, "title": episode_title, "url": url},
        )

    async def notify_process_complete(
        self,
        title: str,
        summary: str,
        output_path: str,
    ):
        """通知处理完成"""
        await self.send(
            NotificationType.PROCESS_COMPLETE,
            f"处理完成: {title}",
            f"摘要: {summary[:200]}...",
            {"title": title, "output": output_path},
        )

    async def notify_process_failed(
        self,
        title: str,
        error: str,
    ):
        """通知处理失败"""
        await self.send(
            NotificationType.PROCESS_FAILED,
            f"处理失败: {title}",
            f"错误: {error}",
            {"title": title, "error": error},
        )

    async def notify_batch_complete(
        self,
        job_name: str,
        total: int,
        success: int,
        failed: int,
    ):
        """通知批量任务完成"""
        await self.send(
            NotificationType.BATCH_COMPLETE,
            f"批量任务完成: {job_name}",
            f"总计: {total}, 成功: {success}, 失败: {failed}",
            {"job": job_name, "total": total, "success": success, "failed": failed},
        )

    def get_history(
        self,
        notification_type: Optional[NotificationType] = None,
        limit: int = 50,
    ) -> List[Notification]:
        """获取通知历史"""
        history = self._history
        if notification_type:
            history = [n for n in history if n.type == notification_type]
        return list(reversed(history))[:limit]
