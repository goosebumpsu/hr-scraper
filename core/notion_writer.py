# Phase 1: Notion 페이지 생성 로직
from __future__ import annotations

import logging
import textwrap
from typing import Any, Optional

from notion_client import Client

from config import NOTION_CATALOG_VALUE, NOTION_DATABASE_ID, NOTION_TOKEN
from core.summarizer import ArticleSummary
from scrapers.base import Article

logger = logging.getLogger(__name__)

_RT_MAX = 2000      # Notion rich_text 단일 요소 최대 글자수
_BLOCK_BATCH = 100  # Notion append_block_children 한 번에 최대 블록 수


# ── Rich Text / Block 헬퍼 ───────────────────────────────────────────────────

def _rt(text: str, bold: bool = False) -> list[dict]:
    """긴 텍스트를 2000자 단위로 쪼개 rich_text 리스트로 반환."""
    chunks = textwrap.wrap(text, _RT_MAX, break_long_words=True, break_on_hyphens=False)
    if not chunks:
        chunks = [""]
    result = []
    for chunk in chunks:
        annotations: dict[str, Any] = {}
        if bold:
            annotations["bold"] = True
        rt: dict[str, Any] = {"type": "text", "text": {"content": chunk}}
        if annotations:
            rt["annotations"] = annotations
        result.append(rt)
    return result


def _heading2(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {"rich_text": _rt(text[:_RT_MAX])},
    }


def _heading3(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_3",
        "heading_3": {"rich_text": _rt(text[:_RT_MAX])},
    }


def _paragraph(text: str) -> list[dict]:
    """긴 텍스트를 여러 paragraph 블록으로 쪼개 반환 (Notion 2000자 제한 대응)."""
    chunks = textwrap.wrap(text, _RT_MAX, break_long_words=True, break_on_hyphens=False)
    if not chunks:
        return [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": ""}}]}}]
    return [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]},
        }
        for chunk in chunks
    ]


def _bullet(text: str) -> dict:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": _rt(text[:_RT_MAX])},
    }


def _bookmark(url: str, caption: str = "") -> dict:
    block: dict[str, Any] = {
        "object": "block",
        "type": "bookmark",
        "bookmark": {"url": url},
    }
    if caption:
        block["bookmark"]["caption"] = _rt(caption[:_RT_MAX])
    return block


def _toc() -> dict:
    return {"object": "block", "type": "table_of_contents", "table_of_contents": {}}


def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


# ── Properties 빌더 ───────────────────────────────────────────────────────────

def _build_properties(article: Article, summary: Optional[ArticleSummary]) -> dict:
    """Notion DB 속성 딕셔너리 생성."""
    props: dict[str, Any] = {
        # 제목 (title 속성)
        "제목": {
            "title": [{"type": "text", "text": {"content": article.title[:_RT_MAX]}}]
        },
        # URL (url 속성)
        "URL": {"url": article.url},
        # 출처 (rich_text 속성)
        "출처": {"rich_text": [{"type": "text", "text": {"content": article.source}}]},
        # 카탈로그 (multi_select 속성)
        "카탈로그": {"multi_select": [{"name": NOTION_CATALOG_VALUE}]},
    }

    # 작성일 (date 속성) — parse_article 후에는 채워져 있음
    if article.published_date:
        props["작성일"] = {"date": {"start": article.published_date.isoformat()}}

    # 태그 (multi_select 속성)
    if article.tags:
        props["태그"] = {
            "multi_select": [{"name": tag[:100]} for tag in article.tags[:5]]
        }

    # 간단요약 — 수동 작성 방침이므로 비워둠 (PRD Out-of-scope)

    return props


# ── Blocks 빌더 ──────────────────────────────────────────────────────────────

def _build_blocks(article: Article, summary: Optional[ArticleSummary]) -> list[dict]:
    """페이지 본문 블록 목록 생성."""
    blocks: list[dict] = []

    if summary:
        # 목차
        blocks.append(_toc())
        blocks.append(_divider())

        # 아티클 전문 링크
        blocks.append(_heading2("🔗 아티클 전문"))
        blocks.append(_bookmark(article.url, article.title))
        blocks.append(_divider())

        # 핵심 인사이트
        blocks.append(_heading2("💡 핵심 인사이트"))
        for insight in summary.insights:
            blocks.append(_bullet(insight))
        blocks.append(_divider())

        # 아티클 정리 (섹션별)
        blocks.append(_heading2("📝 아티클 정리"))
        for section in summary.sections:
            blocks.append(_heading2(section.heading))
            for sub in section.subsections:
                blocks.append(_heading3(sub.heading))
                blocks.extend(_paragraph(sub.content))

    else:
        # 요약 실패 시 원문 본문을 그대로 삽입
        blocks.append(_heading2("🔗 아티클 전문"))
        blocks.append(_bookmark(article.url, article.title))
        blocks.append(_divider())
        blocks.append(_heading2("📄 원문 본문"))
        if article.body:
            # 원문을 2000자 단위 paragraph로 분할
            blocks.extend(_paragraph(article.body))
        else:
            blocks.extend(_paragraph("(본문 없음)"))

    return blocks


# ── NotionWriter ─────────────────────────────────────────────────────────────

class NotionWriter:
    def __init__(self) -> None:
        self._client = Client(auth=NOTION_TOKEN)

    def url_exists(self, url: str) -> bool:
        """Notion DB에 동일한 URL의 페이지가 이미 있으면 True."""
        import requests as _requests
        resp = _requests.post(
            f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query",
            headers={
                "Authorization": f"Bearer {NOTION_TOKEN}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json",
            },
            json={
                "filter": {"property": "URL", "url": {"equals": url}},
                "page_size": 1,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return len(resp.json().get("results", [])) > 0

    def create_page(
        self,
        article: Article,
        summary: Optional[ArticleSummary] = None,
    ) -> str:
        """Notion DB에 페이지를 생성하고 블록을 추가한다. page_id 반환."""
        properties = _build_properties(article, summary)
        blocks = _build_blocks(article, summary)

        # 1) 페이지 생성 (본문 블록 없이 먼저 생성)
        page = self._client.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties=properties,
        )
        page_id: str = page["id"]
        logger.info("Notion 페이지 생성: %s (id=%s)", article.title[:40], page_id)

        # 2) 블록을 100개씩 배치 append
        for i in range(0, len(blocks), _BLOCK_BATCH):
            batch = blocks[i : i + _BLOCK_BATCH]
            self._client.blocks.children.append(
                block_id=page_id,
                children=batch,
            )
            logger.debug("블록 배치 %d~%d 추가 완료", i, i + len(batch) - 1)

        logger.info("Notion 페이지 완성: %s", page_id)
        return page_id
