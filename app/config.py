import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    database_url: str
    REDIS_URL: str
    class Config:
        env_file = "../.env"
        extra = "ignore"

settings = Settings()