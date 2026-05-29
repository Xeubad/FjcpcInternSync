"""旧版一次性访问令牌持久化（auth_tokens.json）。"""

from __future__ import annotations

import json
import os
import secrets
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from filelock import FileLock


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            try:
                os.remove(tmp_name)
            except OSError:
                pass


class AccessTokenRepository:
    """线程安全读写 access_tokens.json。"""

    def __init__(self, file_path: Path, dev_access_token: str = "123"):
        self._path = file_path
        self._dev = dev_access_token
        self._lock = FileLock(str(file_path) + ".lock", timeout=30)

    def load_all(self) -> dict[str, Any]:
        with self._lock:
            if not self._path.exists():
                return {}
            try:
                return json.loads(self._path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {}

    def save_all(self, tokens: dict[str, Any]) -> None:
        with self._lock:
            _atomic_write_json(self._path, tokens)

    def validate_access(self, token: str, *, check_used: bool) -> tuple[bool, str | dict]:
        """登录校验：可要求未使用过。"""
        if token == self._dev:
            return True, {"enabled": True, "used": False, "dev": True}

        tokens = self.load_all()
        if token not in tokens:
            return False, "Token不存在"

        info = tokens[token]
        if not info.get("enabled", True):
            return False, "Token已被禁用"

        if check_used and info.get("used", False):
            return False, "Token已被使用"

        if info.get("expires_at"):
            expire_time = datetime.fromisoformat(info["expires_at"])
            if datetime.now() > expire_time:
                return False, "Token已过期"

        info["last_used"] = datetime.now().isoformat()
        tokens[token] = info
        self.save_all(tokens)
        return True, info

    def validate_session(self, token: str) -> tuple[bool, str | dict]:
        """已登录会话：不检查 used。"""
        if token == self._dev:
            return True, {"enabled": True, "used": False, "dev": True}

        tokens = self.load_all()
        if token not in tokens:
            return False, "Session Token不存在"

        info = tokens[token]
        if not info.get("enabled", True):
            return False, "Token已被禁用"

        if info.get("expires_at"):
            expire_time = datetime.fromisoformat(info["expires_at"])
            if datetime.now() > expire_time:
                return False, "Token已过期"

        return True, info

    def mark_used(self, token: str) -> None:
        if token == self._dev:
            return
        tokens = self.load_all()
        if token not in tokens:
            return
        tokens[token]["used"] = True
        tokens[token]["used_at"] = datetime.now().isoformat()
        self.save_all(tokens)

    def generate(self, admin_key: str, expected_admin_key: str, expire_days: int) -> tuple[str | None, str | None]:
        if admin_key != expected_admin_key:
            return None, "管理员密钥错误"
        raw = secrets.token_urlsafe(32)
        expire_time = datetime.now() + timedelta(days=expire_days)
        tokens = self.load_all()
        tokens[raw] = {
            "enabled": True,
            "used": False,
            "created_at": datetime.now().isoformat(),
            "expires_at": expire_time.isoformat(),
            "last_used": None,
            "used_at": None,
        }
        self.save_all(tokens)
        return raw, None

    def list_tokens_for_admin(self) -> list[dict[str, Any]]:
        """与旧版列表结构一致（管理员查看完整 token）。"""
        out: list[dict[str, Any]] = []
        for token, info in self.load_all().items():
            out.append(
                {
                    "token": token,
                    "enabled": info.get("enabled", True),
                    "used": info.get("used", False),
                    "created_at": info.get("created_at"),
                    "used_at": info.get("used_at"),
                    "last_used": info.get("last_used"),
                }
            )
        out.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        return out

    def revoke(self, token: str) -> bool:
        tokens = self.load_all()
        if token not in tokens:
            return False
        tokens[token]["enabled"] = False
        self.save_all(tokens)
        return True
