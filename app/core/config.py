"""תצורת האפליקציה - נטענת מ-.env דרך pydantic-settings."""
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App ---
    app_env: Literal["development", "production"] = "development"
    log_level: str = "INFO"
    timezone: str = "Asia/Jerusalem"

    # --- DB ---
    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'trading.db'}"

    # --- API ---
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # --- Security (חובה לפני פרסום!) ---
    public_mode: bool = False  # True = הסתרת endpoints רגישים; admin token דרוש ל-write
    admin_api_key: str = ""    # X-Admin-Key header להפעלת סריקות וכו'
    rate_limit_per_minute: int = 60
    cors_origins: str = "*"    # "https://yourdomain.com,https://*.yourdomain.com"

    # --- Auth / JWT ---
    jwt_secret: str = "change-me-in-production-please-use-secrets-token-urlsafe-32"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24 * 30  # token חי 30 יום
    allow_signup: bool = True        # אפשר לכבות פתיחת חשבונות זמנית
    require_email_verification: bool = False  # אם True - חייב לאמת מייל לפני שימוש מלא

    # --- Email (Resend / SMTP / no-op) ---
    resend_api_key: str = ""         # Resend free tier: 100 emails/day. https://resend.com
    email_from: str = "noreply@tradingpro.app"
    email_from_name: str = "TradingPro"
    public_base_url: str = "https://rafinardea777-byte.github.io/trading-system"

    # --- Stripe (billing) ---
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id_pro: str = ""
    stripe_price_id_vip: str = ""

    # --- App branding ---
    app_name: str = "TradingPro"
    company_name: str = "TradingPro"
    contact_email: str = "admin@tradingpro.app"

    # --- Scheduling ---
    enable_scheduler: bool = True
    news_scan_interval_hours: int = 24
    market_scan_interval_minutes: int = 60

    # --- Telegram ---
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    enable_telegram_alerts: bool = False

    # --- News / X ---
    x_bearer_token: str = ""

    # --- OpenAI ---
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # --- Market scanner ---
    scan_min_price: float = 1.0
    scan_max_price: float = 500.0
    scan_min_volume: int = 500_000
    volume_spike_ratio: float = 1.5
    rsi_period: int = 14
    rsi_min: float = 45
    rsi_max: float = 75
    ma_fast: int = 20
    ma_slow: int = 50

    # --- Risk ---
    position_size_usd: float = 5000
    max_open_positions: int = 5
    stop_loss_pct: float = 0.04
    target_1_pct: float = 0.08
    target_2_pct: float = 0.20

    # --- Mode ---
    trading_mode: Literal["paper", "live"] = "paper"

    # --- Paths (derived) ---
    @property
    def base_dir(self) -> Path:
        return BASE_DIR

    @property
    def data_dir(self) -> Path:
        d = BASE_DIR / "data"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def reports_dir(self) -> Path:
        d = self.data_dir / "reports"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def use_openai(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def use_x_api(self) -> bool:
        return bool(self.x_bearer_token)


settings = Settings()


def _validate_settings() -> None:
    """בדיקות נחיתה בעלייה - מונע הרצה ב-public_mode עם הגדרות מסוכנות."""
    weak_secrets = {
        "change-me-in-production-please-use-secrets-token-urlsafe-32",
        "",
        "secret",
        "change-me",
    }
    if settings.public_mode:
        if settings.jwt_secret in weak_secrets or len(settings.jwt_secret) < 32:
            import sys
            sys.stderr.write(
                "FATAL: JWT_SECRET is weak/default in public_mode.\n"
                "Generate strong secret: python -c \"import secrets; print(secrets.token_urlsafe(48))\"\n"
            )
            raise RuntimeError("JWT_SECRET too weak for public_mode")
        if not settings.admin_api_key:
            import sys
            sys.stderr.write("WARN: public_mode=True but ADMIN_API_KEY is empty.\n")


_validate_settings()
