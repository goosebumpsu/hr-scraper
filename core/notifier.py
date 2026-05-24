# Phase 4: Slack Webhook 알림
from __future__ import annotations

import logging
from typing import Optional

import requests

from config import SLACK_WEBHOOK_URL
from core.summarizer import ArticleSummary
from scrapers.base import Article

logger = logging.getLogger(__name__)


def _post(payload: dict) -> bool:
    """Slack Webhook으로 메시지를 전송한다. 성공 여부를 반환하고 예외는 올리지 않는다."""
    if not SLACK_WEBHOOK_URL or SLACK_WEBHOOK_URL.endswith("..."):
        logger.debug("SLACK_WEBHOOK_URL 미설정 - 알림 건너뜀")
        return False
    try:
        resp = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.warning("Slack 알림 전송 실패 (무시): %s", e)
        return False


_SOURCE_EMOJI = {
    "에이치닷": "🏢",
    "그리팅": "👋",
    "레몬베이스": "🍋",
}


def notify_success(
    article: Article,
    summary: Optional[ArticleSummary],
    page_id: str,
) -> None:
    """아티클 저장 성공 알림."""
    notion_url = f"https://www.notion.so/{page_id.replace('-', '')}"
    one_line = summary.one_line_summary if summary else "(요약 없음 - 원문 저장)"
    source_emoji = _SOURCE_EMOJI.get(article.source, "📄")

    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "✅ HR 아티클 저장 완료",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"🌟 *제목*\n{article.title}"},
                    {"type": "mrkdwn", "text": f"❓ *출처*\n{article.source}"},
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"💡 *한줄 요약*\n{one_line}"},
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📝 Notion에서 보기", "emoji": True},
                        "url": notion_url,
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🔗 원문 보기", "emoji": True},
                        "url": article.url,
                    },
                ],
            },
        ]
    }
    if _post(payload):
        logger.info("Slack 알림 전송 완료")
    else:
        logger.debug("Slack 알림 건너뜀 (URL 미설정)")


def notify_error(site_name: str, error: str) -> None:
    """에러 발생 알림."""
    payload = {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🚨 *HR 스크래퍼 오류* [{site_name}]\n```{error[:300]}```",
                },
            }
        ]
    }
    _post(payload)
