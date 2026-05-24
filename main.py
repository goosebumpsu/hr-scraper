"""
HR 아티클 스크래퍼 오케스트레이터 (Phase 1)
실행당 1건 수집 - 라운드로빈 Waterfall 방식
"""
from __future__ import annotations

import importlib
import json
import logging
import sys
from pathlib import Path

from config import PROCESSED_FILE, SITES, STATE_FILE
from core.notion_writer import NotionWriter
from core.summarizer import Summarizer
from scrapers.base import BaseScraper

# ── 로거 설정 ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
# Windows 터미널 인코딩 문제 방지
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
logger = logging.getLogger("main")


# ── 상태 파일 I/O ─────────────────────────────────────────────────────────────

def _load_state() -> dict:
    path = Path(STATE_FILE)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"current_index": 0}


def _save_state(state: dict) -> None:
    Path(STATE_FILE).write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _load_processed() -> set[str]:
    path = Path(PROCESSED_FILE)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        return set(data.get("urls", []))
    return set()


def _save_processed(urls: set[str]) -> None:
    Path(PROCESSED_FILE).write_text(
        json.dumps({"urls": sorted(urls)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ── 스크래퍼 동적 로딩 ────────────────────────────────────────────────────────

def _load_scraper(module_path: str) -> BaseScraper:
    module = importlib.import_module(module_path)
    # 모듈 내 BaseScraper 서브클래스를 자동 탐색
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if (
            isinstance(attr, type)
            and issubclass(attr, BaseScraper)
            and attr is not BaseScraper
        ):
            return attr()
    raise ImportError(f"BaseScraper 서브클래스를 찾을 수 없음: {module_path}")


# ── 메인 플로우 ───────────────────────────────────────────────────────────────

def run() -> None:
    state = _load_state()
    processed = _load_processed()

    current_index: int = state.get("current_index", 0) % len(SITES)
    site = SITES[current_index]
    logger.info("▶ 수집 대상: %s (index=%d)", site.name, current_index)

    # 1) 스크래퍼 로드 및 목록 수집
    try:
        scraper = _load_scraper(site.scraper_module)
        articles = scraper.get_latest_articles()
    except Exception as e:
        logger.error("목록 수집 실패 [%s]: %s", site.name, e)
        # 다음 사이트로 넘기지 않고 종료 (이번 실행 실패로 처리)
        sys.exit(1)

    # 2) 처리되지 않은 첫 번째 아티클 선택
    target = None
    for article in articles:
        if article.url not in processed:
            target = article
            break

    if target is None:
        logger.info("새 아티클 없음 - 다음 사이트로 순서 이동")
        state["current_index"] = (current_index + 1) % len(SITES)
        _save_state(state)
        return

    logger.info("선택된 아티클: %s", target.title[:60])

    # 3) 개별 아티클 본문 파싱
    try:
        target = scraper.parse_article(target.url)
    except Exception as e:
        logger.error("아티클 파싱 실패: %s", e)
        # 파싱 실패 URL도 processed에 등록해 무한 재시도 방지
        processed.add(target.url)
        _save_processed(processed)
        state["current_index"] = (current_index + 1) % len(SITES)
        _save_state(state)
        sys.exit(1)

    # 4) Claude 요약
    summarizer = Summarizer()
    summary = summarizer.summarize(target)
    if summary is None:
        logger.warning("요약 실패 - 본문 원문으로 Notion 저장 진행")

    # 5) Notion 저장
    try:
        writer = NotionWriter()
        page_id = writer.create_page(target, summary)
        logger.info("Notion 저장 완료: %s", page_id)
    except Exception as e:
        logger.error("Notion 저장 실패: %s", e)
        sys.exit(1)

    # 6) 상태 업데이트
    processed.add(target.url)
    _save_processed(processed)
    state["current_index"] = (current_index + 1) % len(SITES)
    _save_state(state)
    logger.info("상태 저장 완료 - 다음 실행 대상: %s", SITES[state["current_index"]].name)


if __name__ == "__main__":
    run()
