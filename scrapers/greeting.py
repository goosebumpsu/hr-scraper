import json
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from config import MAX_ARTICLES_PER_FETCH, REQUEST_HEADERS, REQUEST_TIMEOUT
from scrapers.base import Article, BaseScraper

_BASE = "https://blog.greetinghr.com"


class GreetingScraper(BaseScraper):
    source_name = "그리팅"
    base_url = f"{_BASE}/tag/recruitment-article/"

    def _get(self, url: str) -> requests.Response:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        resp.encoding = "utf-8"
        resp.raise_for_status()
        return resp

    def get_latest_articles(self) -> list[Article]:
        soup = BeautifulSoup(self._get(self.base_url).text, "lxml")

        items = soup.select("article.post-card")[:MAX_ARTICLES_PER_FETCH]
        articles = []
        for item in items:
            # URL: 상대경로 → 절대경로
            a_tag = item.select_one("a[href]")
            if not a_tag:
                continue
            href = a_tag["href"]
            url = href if href.startswith("http") else f"{_BASE}{href}"

            # 제목
            title_el = item.select_one("h2, h3, .post-card-title")
            title = title_el.get_text(strip=True) if title_el else ""

            articles.append(Article(
                title=title,
                url=url,
                body="",
                source=self.source_name,
            ))

        return articles

    def parse_article(self, url: str) -> Article:
        soup = BeautifulSoup(self._get(url).text, "lxml")

        # 제목
        h1 = soup.select_one("h1")
        title = h1.get_text(strip=True) if h1 else ""

        # 발행일 (JSON-LD 우선, fallback: time 태그)
        published_date = None
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if "datePublished" in data:
                    published_date = datetime.fromisoformat(
                        data["datePublished"].replace("Z", "+00:00")
                    ).date()
                    break
            except Exception:
                pass
        if published_date is None:
            time_el = soup.select_one("time[datetime]")
            if time_el:
                try:
                    published_date = datetime.fromisoformat(
                        time_el["datetime"]
                    ).date()
                except Exception:
                    pass

        # 태그 (없으면 빈 리스트)
        tag_els = soup.select(".post-tags a, .post-full-tags a")
        tags = [t.get_text(strip=True) for t in tag_els if t.get_text(strip=True)]

        # 본문
        body_el = soup.select_one("div.post-content")
        body = ""
        if body_el:
            for tag in body_el.find_all(["script", "style", "noscript"]):
                tag.decompose()
            body = body_el.get_text(separator="\n", strip=True)
            body = re.sub(r"\n{3,}", "\n\n", body)

        return Article(
            title=title,
            url=url,
            body=body,
            source=self.source_name,
            published_date=published_date,
            tags=tags,
        )
