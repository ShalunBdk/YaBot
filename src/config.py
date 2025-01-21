from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    YANDEX_BOT_TOKEN: str

    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASS: str
    DB_NAME: str

    REDIS_HOST: str
    REDIS_PORT: int

    AD_SERVER: str
    AD_USER: str
    AD_PASSWORD: str
    AD_BASE_DN: str
    AD_USER_FOR_PASS_CHANGE: str
    AD_PASSWORD_FOR_PASS_CHANGE: str

    API_TOKEN: str

    API_TOKEN_360: str
    ORG_ID: int

    @property
    def REDIS_URL(self):
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}"

    @property
    def DB_URL(self):
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
