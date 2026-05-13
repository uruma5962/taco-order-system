"""環境変数または .env ファイルから読み込むアプリ設定。"""
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_user: str = Field(default="admin", alias="APP_USER")
    app_pass: str = Field(default="admin", alias="APP_PASS")

    notifier_backend: Literal["log", "discord"] = Field(default="log", alias="NOTIFIER_BACKEND")
    discord_token: str = Field(default="", alias="DISCORD_TOKEN")
    kitchen_channel_id: int = Field(default=0, alias="KITCHEN_CHANNEL_ID")
    delivery_channel_id: int = Field(default=0, alias="DELIVERY_CHANNEL_ID")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
