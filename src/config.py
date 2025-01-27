from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    YANDEX_BOT_TOKEN: str

    AD_SERVER: str
    AD_USER: str
    AD_PASSWORD: str
    AD_BASE_DN: str
    AD_USER_FOR_PASS_CHANGE: str
    AD_PASSWORD_FOR_PASS_CHANGE: str

    API_TOKEN_360: str
    ORG_ID: int

    model_config = SettingsConfigDict(env_file="/local/.env", extra="ignore")


settings = Settings()
