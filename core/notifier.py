# Phase 4: Slack Webhook 알림
from __future__ import annotations

import logging
from typing import Optional

import requests

from config import SLACK_WEBHOOK_URL
from core.summarizer import ArticleSummary
from scrapers.base import Article

logger = logging.getLogger(__name__)


def _post(payload: dict) -> None:
    """Slack Webhook으로 메시지를 전송한다. 실패해도 예외를 올리지 않는다."""
    if not SLACK_WEBHOOK_URL:
        logger.debug("SLACK_WEBHOOK_URL 미설정 - 알림 건너뜀")
        return
    try:
        resp = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        logger.warning("Slack 알림 전송 실패 (무시): %s", e)


def notify_success(
    article: Article,
    summary: Optional[ArticleSummary],
    page_id: str,
) -> None:
    """아티클 저장 성공 알림."""
    notion_url = f"https://www.notion.so/{page_id.replace('-', '')}"
    one_line = summary.one_line_summary if summary else "(요약 없음 - 원문 저장)"

    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "HR 아티클 저장 완료",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*제목*\n{article.title}"},
                    {"type": "mrkdwn", "text": f"*출처*\n{article.source}"},
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*한줄 요약*\n{one_line}"},
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Notion에서 보기"},
                        "url": notion_url,
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "원문 보기"},
                        "url": article.url,
                    },
                ],
            },
        ]
    }
    _post(payload)
    logger.info("Slack 알림 전송 완료")


def notify_error(site_name: str, error: str) -> None:
    """에러 발생 알림."""
    payload = {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":warning: *HR 스크래퍼 오류* [{site_name}]\n```{error[:300]}```",
                },
            }
        ]
    }
    _post(payload)
