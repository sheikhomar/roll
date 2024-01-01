from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    ACCOUNT_NAME: str = Field(env="ACCOUNT_NAME")
    LOGIN: str = Field(env="LOGIN")
    PASSWORD: str = Field(env="PASSWORD")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
