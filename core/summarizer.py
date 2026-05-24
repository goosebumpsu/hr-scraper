# Phase 1: Claude Sonnet API 요약·구조화 로직
from __future__ import annotations

import json
import logging
import re
from typing import Optional

import anthropic
from pydantic import AliasChoices, BaseModel, Field, ValidationError

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, LLM_RETRY_COUNT, SUMMARIZER_MAX_TOKENS
from scrapers.base import Article

logger = logging.getLogger(__name__)

# ── Pydantic 모델 ──────────────────────────────────────────────────────────────

class Subsection(BaseModel):
    # Claude가 'heading' 또는 'subheading' 중 하나를 반환할 수 있으므로 둘 다 허용
    heading: str = Field(validation_alias=AliasChoices("heading", "subheading"))
    content: str


class Section(BaseModel):
    heading: str                   # ## 수준 대제목
    subsections: list[Subsection]  # 하위 항목 (없으면 빈 리스트)


class ArticleSummary(BaseModel):
    one_line_summary: str       # 1문장 핵심 요약
    insights: list[str]         # 핵심 인사이트 2~5개
    sections: list[Section]     # 구조화된 본문 섹션


# ── JSON Schema (output_config 용) ───────────────────────────────────────────

_SUMMARY_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "one_line_summary": {
            "type": "string",
            "description": "아티클 전체를 1문장으로 요약"
        },
        "insights": {
            "type": "array",
            "items": {"type": "string"},
            "description": "핵심 인사이트 2~5개 (각 항목은 1문장)"
        },
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "heading": {"type": "string", "description": "## 수준 대제목"},
                    "subsections": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "heading": {"type": "string", "description": "### 수준 소제목"},
                                "content": {"type": "string", "description": "소제목 아래 내용"}
                            },
                            "required": ["heading", "content"]
                        }
                    }
                },
                "required": ["heading", "subsections"]
            },
            "description": "본문을 논리 흐름에 따라 섹션으로 분리"
        }
    },
    "required": ["one_line_summary", "insights", "sections"]
}

# ── 시스템 프롬프트 (캐시 대상) ───────────────────────────────────────────────

_SYSTEM_PROMPT = """\
당신은 HR 전문 에디터입니다. 사용자가 제공하는 HR 아티클 본문을 읽고,
아래 JSON 스키마에 맞춰 한국어로 구조화된 요약 결과를 반환하세요.

## 작성 지침
- one_line_summary: 아티클의 핵심 메시지를 1문장으로 압축합니다.
- insights: 실무 담당자에게 가장 유용한 인사이트 2~5개를 도출합니다.
  각 인사이트는 "~이다 / ~해야 한다 / ~할 수 있다" 형태의 완전한 문장으로 작성합니다.
- sections: 아티클의 논리 흐름을 따라 2~5개의 섹션으로 나눕니다.
  각 섹션은 heading(대제목)과 subsections(소제목+내용) 목록을 포함합니다.
  subsections가 없는 섹션은 빈 배열([])을 사용합니다.
  content는 원문 정보를 유지하되 불필요한 중복은 제거하여 간결하게 작성합니다.

## 중요
- 반드시 JSON만 반환하세요. 마크다운 코드블록이나 추가 설명 없이 순수 JSON만 출력합니다.
- 모든 텍스트는 한국어로 작성하세요.
"""

# ── Summarizer ────────────────────────────────────────────────────────────────

class Summarizer:
    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def summarize(self, article: Article) -> Optional[ArticleSummary]:
        """아티클 본문을 Claude로 요약·구조화한다. 실패 시 None 반환."""
        user_content = (
            f"[제목] {article.title}\n\n"
            f"[출처] {article.source}\n\n"
            f"[본문]\n{article.body}"
        )

        for attempt in range(LLM_RETRY_COUNT + 1):
            try:
                response = self._client.messages.create(
                    model=CLAUDE_MODEL,
                    max_tokens=SUMMARIZER_MAX_TOKENS,
                    system=[
                        {
                            "type": "text",
                            "text": _SYSTEM_PROMPT,
                            "cache_control": {"type": "ephemeral"},  # 프롬프트 캐싱
                        }
                    ],
                    messages=[{"role": "user", "content": user_content}],
                )

                raw = response.content[0].text.strip()
                # Claude가 ```json ... ``` 코드블록으로 감쌀 때 JSON만 추출
                if raw.startswith("```"):
                    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
                    raw = re.sub(r"\n?```$", "", raw).strip()
                data = json.loads(raw)
                summary = ArticleSummary.model_validate(data)
                logger.info("요약 완료: %s", article.title[:40])
                return summary

            except ValidationError as e:
                logger.warning("Pydantic 검증 실패 (attempt %d): %s", attempt + 1, e)
            except json.JSONDecodeError as e:
                logger.warning("JSON 파싱 실패 (attempt %d): %s", attempt + 1, e)
            except anthropic.APIError as e:
                logger.warning("Claude API 오류 (attempt %d): %s", attempt + 1, e)

        logger.error("요약 실패 - 모든 시도 소진: %s", article.title[:40])
        return None
