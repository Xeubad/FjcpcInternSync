from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，支持 .env 覆盖。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: str = "http://localhost:5173"
    # 供 /api/config 返回；留空则用请求推导的 base_url
    public_base_url: str = ""

    admin_username: str = "admin"
    admin_password: str = "admin123"
    user_username: str = "user"
    user_password: str = "user123"

    data_dir: str = "data"

    # 兼容旧字段：上传逻辑以 FJCPC_* 为准；未单独配置时可回退
    upstream_base_url: str = ""
    upstream_verify_tls: bool = False

    # FJCPC 上游（自 app_excel CONFIG 迁移，环境变量名如 FJCPC_API_URL）
    fjcpc_api_url: str = "https://dgsxapi.fjcpc.edu.cn/Reports/StudentOperator"
    fjcpc_api_host: str = "dgsxapi.fjcpc.edu.cn"
    fjcpc_api_cookie_template: str = (
        "PHPSESSID=d1ko4k5jj5cet643lokdqq05f2; "
        "fjczqxy_session=RqlGw90xKdlxRsJMeYyBkVmb6k8GB4XjEqEa03u; token={token}"
    )
    fjcpc_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0"
    )
    fjcpc_referer: str = "https://dgsx.fjcpc.edu.cn/"
    fjcpc_origin: str = "https://dgsx.fjcpc.edu.cn/"
    fjcpc_request_interval: float = 2.0
    fjcpc_request_timeout: float = 10.0
    fjcpc_auth_priority: str = "cookie_first"  # cookie_first | token_first
    fjcpc_verify_tls: bool = False
    # 留空则不读文件；填写相对路径时相对于启动 uvicorn 时的当前工作目录
    fjcpc_browser_cookies_path: str = ""
    # 留空则与读取路径相同逻辑，最终回退到 data/config/browser_cookies.json
    fjcpc_browser_cookies_write_path: str = ""
    fjcpc_dry_run: bool = False

    # 旧版一次性访问令牌（auth_tokens.json）
    access_tokens_file: str = ""
    admin_key: str = "fjcpc2025"
    dev_access_token: str = "123"
    token_expire_days: int = 7

    db_enabled: bool = False
    queue_enabled: bool = False

    # React 构建产物目录；留空则使用 FjcpcInternSync/frontend/dist（由后端托管 SPA）
    spa_static_dir: str = ""

    @property
    def data_path(self) -> Path:
        return Path(self.data_dir).resolve()

    @property
    def access_tokens_path(self) -> Path:
        raw = (self.access_tokens_file or "").strip()
        if raw:
            path = Path(raw)
            return path if path.is_absolute() else (Path.cwd() / path).resolve()
        return self.data_path / "config" / "access_tokens.json"

    @property
    def browser_cookies_read_path(self) -> Path:
        """读取浏览器 Cookie 的文件路径（与保存路径一致的回退逻辑）。"""
        raw = (self.fjcpc_browser_cookies_path or "").strip()
        if raw:
            path = Path(raw)
            return path if path.is_absolute() else (Path.cwd() / path).resolve()
        return self.data_path / "config" / "browser_cookies.json"

    @property
    def browser_cookies_save_path(self) -> Path:
        raw = (self.fjcpc_browser_cookies_write_path or "").strip()
        if raw:
            path = Path(raw)
            return path if path.is_absolute() else (Path.cwd() / path).resolve()
        readp = (self.fjcpc_browser_cookies_path or "").strip()
        if readp:
            path = Path(readp)
            return path if path.is_absolute() else (Path.cwd() / path).resolve()
        return self.data_path / "config" / "browser_cookies.json"

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def spa_dist_path(self) -> Path | None:
        """存在 index.html 时返回 frontend/dist，否则 None（仅 API 模式）。"""
        raw = (self.spa_static_dir or "").strip()
        if raw:
            path = Path(raw)
            resolved = path if path.is_absolute() else (Path.cwd() / path).resolve()
            if resolved.is_dir() and (resolved / "index.html").is_file():
                return resolved
            return None
        auto = Path(__file__).resolve().parents[3] / "frontend" / "dist"
        if auto.is_dir() and (auto / "index.html").is_file():
            return auto
        return None


settings = Settings()
