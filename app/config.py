"""配置管理"""
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from sqlalchemy.engine import URL
from typing import List
import os


class Settings(BaseSettings):
    """应用配置"""

    # 应用基础
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    API_TITLE: str = "Elderly Care Cloud API"
    API_VERSION: str = "0.1.0"

    # 数据库
    POSTGRES_USER: str = "elderly_admin"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "elderly_care"
    DATABASE_URL: str = ""

    # FastAPI
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4

    # 安全 ✅ 修复: 强制从环境变量加载，无默认值
    SECRET_KEY: str = Field(..., description="Must be set from environment or .env file")
    API_KEY: str = Field(..., description="Must be set from environment or .env file")
    # ✅ 修复: CORS 白名单，不再允许 "*"
    # 生产环境：https://safehome-frontend.vercel.app
    # 本地开发：http://localhost:3000
    ALLOW_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:3007",
            "http://localhost:3008",
            "http://localhost:3009",
            "http://localhost:3010",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3007",
            "http://127.0.0.1:3008",
            "http://127.0.0.1:3009",
            "http://127.0.0.1:3010",
            "https://safehome-frontend.vercel.app",
            "https://safehome.linkrytech.com",
            "https://www.linkrytech.com",
        ],
        description="Allowed CORS origins - updated for production (localhost for development)"
    )

    # 前端 URL（用于邮件链接等）
    FRONTEND_BASE_URL: str = Field(
        default="https://safehome.linkrytech.com",
        description="Frontend base URL for email links"
    )
    FRONTEND_URL: str = Field(
        default="https://safehome-frontend.vercel.app",
        description="Legacy frontend URL for email links"
    )

    # Home Assistant
    HOME_ASSISTANT_WEBHOOK_ID: str = "elderly_care_webhook"
    HOME_ASSISTANT_WEBHOOK_SECRET: str = ""

    # 告警配置
    ALERT_EMAIL_ENABLED: bool = False
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_APP_PASSWORD: str = ""
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "SafeHome <your_email@gmail.com>"
    MAILGUN_API_KEY: str = ""
    MAILGUN_DOMAIN: str = ""
    MAILGUN_FROM: str = ""
    INTERNAL_NOTIFICATION_EMAIL: str = ""

    DINGDING_WEBHOOK_URL: str = ""
    WECHAT_WEBHOOK_URL: str = ""

    # 规则阈值
    INACTIVITY_THRESHOLD_MINUTES: int = 240
    BATHROOM_TIMEOUT_MINUTES: int = 30
    WAKE_TIME_VARIANCE_HOURS: int = 2
    NIGHT_ACTIVITY_THRESHOLD: int = 5
    ROOM_ACTIVITY_DEVIATION_PERCENT: int = 50

    # 数据保留
    EVENT_RETENTION_DAYS: int = 180

    # 监控
    ENABLE_PROMETHEUS: bool = True
    ENABLE_SENTRY: bool = False
    SENTRY_DSN: str = ""

    # 测试
    TESTING: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def get_database_url(self) -> str:
        """获取数据库 URL"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return URL.create(
            drivername="postgresql+psycopg2",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DB,
        )

    @field_validator('ALLOW_ORIGINS')
    @classmethod
    def validate_origins(cls, v, info):
        """✅ 验证 CORS 配置"""
        if not v:
            raise ValueError("ALLOW_ORIGINS cannot be empty")
        if "*" in v:
            raise ValueError("ALLOW_ORIGINS cannot contain wildcard '*' - use explicit domains")
        return v


# 全局配置实例
try:
    settings = Settings()
except Exception as e:
    print(f"⚠️  Configuration error: {e}")
    print("💡 Make sure to set SECRET_KEY and API_KEY in your .env file or environment variables")
    raise
