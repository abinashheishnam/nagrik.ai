from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Praja.ai"
    DATABASE_URL: str = "mysql+pymysql://praja_user:Praja%40123@127.0.0.1:3306/praja_ai"

    JWT_SECRET: str = "CHANGE_ME_TO_SOMETHING_SECRET"
    JWT_ALGO: str = "HS256"
    ACCESS_TOKEN_MINUTES: int = 60 * 24

settings = Settings()
