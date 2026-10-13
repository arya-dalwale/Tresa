from pydantic_settings import BaseSettings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class Settings(BaseSettings):
    DATABASE_URL: str

    class Config:
        env_file = ".env"


settings = Settings()

engine = create_engine(settings.DATABASE_URL)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)