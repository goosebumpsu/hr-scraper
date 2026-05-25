import json
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from config import ARTICLE_MIN_DATE, MAX_ARTICLES_PER_FETCH, REQUEST_HEADERS, REQUEST_TIMEOUT
from scrapers.base import Article, BaseScraper

_BASE = "https://lemonbase.com"
_INCLUDE_TAGS = {"아티클", "뉴스레터"}


class LemonbaseScraper(BaseScraper):
    source_name = "레몬베이스"
    base_url = f"{_BASE}/blog/"

    def _get(self, url: str) -> requests.Response:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        resp.encoding = "utf-8"
        resp.raise_for_status()
        return resp

    def _next_data(self, url: str) -> dict:
        """페이지의 __NEXT_DATA__ JSON을 파싱해 반환."""
        soup = BeautifulSoup(self._get(url).text, "lxml")
        el = soup.find("script", id="__NEXT_DATA__")
        if not el or not el.string:
            raise ValueError(f"__NEXT_DATA__ 없음: {url}")
        return json.loads(el.string)

    def get_latest_articles(self) -> list[Article]:
        data = self._next_data(self.base_url)
        posts: list[dict] = data.get("props", {}).get("pageProps", {}).get("posts", [])

        # '아티클' 또는 '뉴스레터' 태그이면서 ARTICLE_MIN_DATE 이후 발행된 포스트만 추출
        filtered = []
        for p in posts:
            has_tag = any(t.get("name") in _INCLUDE_TAGS for t in p.get("tags", []))
            if not has_tag:
                continue
            try:
                pub_date = datetime.fromisoformat(p.get("published_at", "")).date()
            except Exception:
                pub_date = None
            if pub_date and pub_date < ARTICLE_MIN_DATE:
                continue
            filtered.append(p)

        articles = []
        for post in filtered[:MAX_ARTICLES_PER_FETCH]:
            slug = post.get("slug", "")
            url = f"{_BASE}/blog/{slug}"
            title = post.get("title", "").strip()
            tags = [t["name"] for t in post.get("tags", []) if t.get("name")]

            articles.append(Article(
                title=title,
                url=url,
                body="",
                source=self.source_name,
                tags=tags,
            ))

        return articles

    def parse_article(self, url: str) -> Article:
        data = self._next_data(url)
        post: dict = data.get("props", {}).get("pageProps", {}).get("post", {})

        title = post.get("title", "").strip()

        # 발행일
        published_date = None
        raw_date = post.get("published_at", "")
        if raw_date:
            try:
                published_date = datetime.fromisoformat(raw_date).date()
            except Exception:
                pass

        # 태그
        tags = [t["name"] for t in post.get("tags", []) if t.get("name")]

        # 본문: html 필드를 텍스트로 변환
        html_body = post.get("html", "")
        body = ""
        if html_body:
            body_soup = BeautifulSoup(html_body, "lxml")
            for tag in body_soup.find_all(["script", "style", "noscript"]):
                tag.decompose()
            body = body_soup.get_text(separator="\n", strip=True)
            body = re.sub(r"\n{3,}", "\n\n", body)

        return Article(
            title=title,
            url=url,
            body=body,
            source=self.source_name,
            published_date=published_date,
            tags=tags,
        )
