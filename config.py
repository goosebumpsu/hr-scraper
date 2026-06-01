import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

# config.py 위치 기준으로 .env 탐색 → 실행 디렉토리에 무관하게 동작
_ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(_ENV_PATH, override=True)


@dataclass(frozen=True)
class SiteConfig:
    name: str
    base_url: str
    scraper_module: str


SITES: list[SiteConfig] = [
    SiteConfig(
        name="에이치닷",
        base_url="https://contents.h.place/article",
        scraper_module="scrapers.hdot",
    ),
    SiteConfig(
        name="그리팅",
        base_url="https://blog.greetinghr.com/tag/recruitment-article/",
        scraper_module="scrapers.greeting",
    ),
    SiteConfig(
        name="레몬베이스",
        base_url="https://lemonbase.com/blog/",
        scraper_module="scrapers.lemonbase",
    ),
]

# 상태 파일 경로
STATE_FILE = "data/state.json"
PROCESSED_FILE = "data/processed.json"

# 스크래퍼 설정
MAX_ARTICLES_PER_FETCH = 10
ARTICLE_MIN_DATE = date(2025, 1, 1)   # 이 날짜 이전 아티클은 수집하지 않음
REQUEST_TIMEOUT = 15          # seconds
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# Claude API 설정
def _require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise EnvironmentError(
            f"필수 환경변수 '{name}'가 설정되지 않았습니다. "
            ".env 파일 또는 GitHub Secrets를 확인하세요."
        )
    return val


ANTHROPIC_API_KEY: str = _require_env("ANTHROPIC_API_KEY")
CLAUDE_MODEL = "claude-sonnet-4-6"
SUMMARIZER_MAX_TOKENS = 4096
LLM_RETRY_COUNT = 1

# Notion 설정
NOTION_TOKEN: str = _require_env("NOTION_TOKEN")
NOTION_DATABASE_ID: str = _require_env("NOTION_DATABASE_ID")
NOTION_CATALOG_VALUE = "HR"

# 알림 설정 (Slack or Gmail, 둘 다 선택적)
SLACK_WEBHOOK_URL: str | None = os.environ.get("SLACK_WEBHOOK_URL")
GMAIL_USER: str | None = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD: str | None = os.environ.get("GMAIL_APP_PASSWORD")
