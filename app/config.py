"""환경 변수 설정을 한곳에서 읽는다."""

import os

from dotenv import load_dotenv

load_dotenv()

# mock(개발·테스트) | claude | gemini | openai
AI_PROVIDER = os.getenv("AI_PROVIDER", "mock")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "")
AI_TIMEOUT = float(os.getenv("AI_TIMEOUT", "30"))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app/db/app.db")
