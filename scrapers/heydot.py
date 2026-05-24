import json
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from config import MAX_ARTICLES_PER_FETCH, REQUEST_HEADERS, REQUEST_TIMEOUT
from scrapers.base import Article, BaseScraper


class HeydotScraper(BaseScraper):
    source_name = "에이치닷"
    base_url = "https://contents.h.place/article"

    def _get(self, url: str) -> requests.Response:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp

    def get_latest_articles(self) -> list[Article]:
        soup = BeautifulSoup(self._get(self.base_url).text, "lxml")

        items = soup.select("ul#blogList li.post-item")[:MAX_ARTICLES_PER_FETCH]
        articles = []
        for li in items:
            a_tag = li.find("a", href=True)
            if not a_tag:
                continue

            url = a_tag["href"]
            title = (li.get("data-title") or "").strip()
            if not title:
                el = li.select_one("p.item_title")
                title = el.get_text(strip=True) if el else ""

            category = (li.get("data-category") or "").strip()
            tags = [category] if category else []

            articles.append(Article(
                title=title,
                url=url,
                body="",
                source=self.source_name,
                tags=tags,
            ))

        return articles

    def parse_article(self, url: str) -> Article:
        soup = BeautifulSoup(self._get(url).text, "lxml")

        # 제목
        title_el = soup.select_one("h1.title")
        title = title_el.get_text(strip=True) if title_el else ""

        # 발행일 (JSON-LD)
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

        # 태그 (아티클 페이지의 category 영역)
        tag_el = soup.select_one("div.tag")
        tags = [tag_el.get_text(strip=True)] if tag_el else []

        # 본문
        body_el = soup.select_one("#hs_cos_wrapper_post_body")
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
