"""启动时维护：访问令牌备份、日志与备份目录清理（对齐旧版 app_excel 行为）。"""

import logging
import shutil
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

LOG_RETENTION_DAYS = 7
MAX_AUTH_TOKEN_BACKUPS = 10


def backup_access_tokens_file(token_file: Path, data_root: Path) -> None:
    """若令牌文件存在则复制到 data_root/backups/。"""
    if not token_file.exists():
        return
    backup_dir = data_root / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = backup_dir / f"auth_tokens_{timestamp}.json"
    try:
        shutil.copy2(token_file, dest)
        logger.info("访问令牌已备份: %s", dest)
    except OSError as exc:
        logger.error("备份访问令牌失败: %s", exc)
        return

    backups = sorted(backup_dir.glob("auth_tokens_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in backups[MAX_AUTH_TOKEN_BACKUPS:]:
        try:
            old.unlink()
            logger.info("删除过期令牌备份: %s", old.name)
        except OSError as exc:
            logger.warning("删除备份失败 %s: %s", old, exc)


def cleanup_data_logs_and_backups(data_root: Path) -> None:
    """清理 data/logs 下过旧日志；data/backups 下过多 auth_tokens 备份。"""
    now = datetime.now()
    logs_dir = data_root / "logs"
    backups_dir = data_root / "backups"

    if logs_dir.exists():
        for log_file in logs_dir.glob("*.log"):
            try:
                file_age = datetime.fromtimestamp(log_file.stat().st_mtime)
                if (now - file_age).days > LOG_RETENTION_DAYS:
                    log_file.unlink()
                    logger.info("已删除过期日志: %s", log_file.name)
            except OSError as exc:
                logger.warning("清理日志跳过 %s: %s", log_file, exc)

    if backups_dir.exists():
        backups = sorted(
            backups_dir.glob("auth_tokens_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old in backups[MAX_AUTH_TOKEN_BACKUPS:]:
            try:
                old.unlink()
                logger.info("已删除旧令牌备份: %s", old.name)
            except OSError as exc:
                logger.warning("删除备份失败 %s: %s", old, exc)
