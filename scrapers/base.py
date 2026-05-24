from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Article:
    title: str
    url: str
    body: str               # HTML에서 정제된 본문 텍스트
    source: str             # "에이치닷" / "그리팅" / "레몬베이스"
    published_date: Optional[date] = None   # 목록 단계에서는 None, parse_article 후 채워짐
    tags: list[str] = field(default_factory=list)


class BaseScraper(ABC):
    source_name: str        # 서브클래스에서 클래스 변수로 선언
    base_url: str

    @abstractmethod
    def get_latest_articles(self) -> list[Article]:
        """목록 페이지에서 최신 아티클 메타 정보를 추출한다 (최대 10건).

        본문(body)은 빈 문자열로 두고 url만 채워도 된다.
        parse_article()에서 본문을 채우는 방식으로 구현할 것.
        """

    @abstractmethod
    def parse_article(self, url: str) -> Article:
        """개별 아티클 페이지에서 본문을 포함한 완전한 Article을 반환한다."""
