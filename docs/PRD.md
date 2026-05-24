# HR 아티클 자동 수집·정리 시스템 PRD
> **문서 버전**: v1.0 (확정)
> **작성일**: 2026-05-23
> **상태**: 확정 ✅
---
## 1. 프로젝트 개요
### 1.1 배경
HR 관련 인사이트를 얻기 위해 여러 HR 사이트를 수동으로 방문하여 새 아티클을 확인하고,
노션 데이터베이스에 페이지를 생성한 뒤 본문과 요약을 직접 정리하고 있다.
이 반복 작업은 시간 소모가 크고 누락이 발생할 가능성이 있다.
**기존 수동 워크플로우:**
1. 각 사이트 접속 → 아티클 확인 및 본문 확인
2. 노션 데이터베이스에 페이지 생성
3. 해당 페이지에 본문 내용 정리
4. DB '간단 요약' 속성에 요약 작성
### 1.2 목적
- 아티클 수집 → 노션 정리 과정을 자동화
- 본인의 시간을 "정보 수집·정리"가 아닌 "정보 활용"에 집중
- 신뢰할 수 있는 HR 정보 아카이브를 노션에 지속 축적
### 1.3 성공 기준
- 수동 작업 시간: 기존 대비 80% 이상 절감
- 신규 아티클 누락 0건 (2주 검증 기준)
- 시스템이 개입 없이 4주 이상 안정 운영
- 월 운영 비용: $5 이하 (Claude API 포함)
---
## 2. 사용자 및 사용 환경
### 2.1 사용자
- **타입**: 단일 사용자 (본인)
- **목적**: 개인 HR 인사이트 아카이빙
- **기술 수준**: 코드 수정 가능, GitHub 사용 가능
### 2.2 실행 환경
- **플랫폼**: GitHub Actions (cron 스케줄)
- **실행 주기**: 매주 월요일·목요일 오전 9시 KST (UTC 00:00)
- **코드 저장소**: GitHub Private Repository
### 2.3 결과 확인
- 본인 Notion 데이터베이스 (기존 DB 사용)
- Slack 또는 이메일 실행 결과 알림 (성공/실패 모두)
---
## 3. 기능 요구사항
### 3.1 스크랩 대상 사이트
| 우선순위 | 사이트 | URL |
|---|---|---|
| 1 | 에이치닷 | https://contents.h.place/article |
| 2 | 그리팅 | https://blog.greetinghr.com/tag/recruitment-article/ |
| 3 | 레몬베이스 | https://lemonbase.com/blog/?search= |
| 4 | 플렉스 (추후 추가) | https://flex.team/blog/category/axhub/ |
### 3.2 아티클 선택 로직 (핵심)
매 실행 시 **전체에서 1건**만 가져온다.
폭포식 탐색(Waterfall) 방식으로, 현재 순번 사이트부터 시작해 새 아티클이 나올 때까지 다음 사이트로 순차 탐색한다.
**동작 흐름:**
```
실행 시작
    ↓
현재 순번 사이트 탐색
    ↓ 새 아티클 있음
노션 저장 → 다음 사이트로 순번 이동 → 종료
    ↓ 새 아티클 없음
다음 순번 사이트 탐색
    ↓ 새 아티클 있음
노션 저장 → 다음 사이트로 순번 이동 → 종료
    ↓ 새 아티클 없음
그 다음 순번 사이트 탐색
    ↓ 모든 사이트 탐색 후에도 없음
"전체 사이트 새 아티클 없음" 알림 발송 → 종료
```
**동작 예시:**
| 실행일 | 시작 사이트 | 탐색 순서 | 결과 |
|---|---|---|---|
| 5/25 (월) | 에이치닷 | 에이치닷(없음) → 그리팅(있음) | 그리팅 저장, 다음 순번: 레몬베이스 |
| 5/28 (목) | 레몬베이스 | 레몬베이스(없음) → 에이치닷(있음) | 에이치닷 저장, 다음 순번: 그리팅 |
| 6/1 (월) | 그리팅 | 그리팅(있음) | 그리팅 저장, 다음 순번: 레몬베이스 |
| 6/4 (목) | 레몬베이스 | 레몬베이스(없음) → 에이치닷(없음) → 그리팅(없음) | "새 글 없음" 알림 |
**순번 이동 규칙:**
- 성공 시: 성공한 사이트의 **다음 사이트**로 순번 이동 (균등 탐색 보장)
- 전체 탐색 실패 시: 순번 변경 없음 (다음 실행에서 같은 사이트부터 재시도)
**순환 상태 저장:**
- 다음 실행 시작 사이트 인덱스를 `data/state.json`에 저장
- 처리 완료된 URL 목록을 `data/processed.json`에 저장
- 두 파일 모두 처리 후 레포에 자동 커밋
### 3.3 수집 데이터
각 아티클당 수집 항목:
| 항목 | 설명 |
|---|---|
| 제목 (Title) | 아티클 제목 |
| 원문 URL | 개별 아티클 페이지 링크 |
| 본문 (Body) | 아티클 전문 (HTML → 정제된 텍스트) |
| 작성일 | 원문 발행일 |
| 출처 | 사이트명 (에이치닷 / 그리팅 / 레몬베이스) |
| 태그 | 원문 태그 (있는 경우) 또는 LLM 자동 추출 |
### 3.4 요약 및 본문 정리 사양
**노션 DB 속성 '간단 요약':**
- 자동 생성 안 함 (본인이 직접 작성)
**슬랙/이메일 알림용 한 줄 요약:**
- 아티클 한 줄 요약 1문장 (알림 메시지에만 포함, 노션엔 저장 안 함)
**노션 페이지 본문 구조 (확정):**
```
[목차]
 └ Notion Table of Contents 블록 (페이지 내 제목2·3 자동 링크)
[🔗 아티클 전문]
 └ URL 북마크 블록 (원문 링크)
[💡 주요 인사이트]
 └ 불릿 3~5개 (Claude 추출)
[📝 아티클 정리]
 └ 제목2: 서론
     제목3: 소제목
     본문 단락
 └ 제목2: 본론
     제목3: 소제목1
     본문 단락
     제목3: 소제목2
     본문 단락
 └ 제목2: 결론
     본문 단락
```
**구현 방식:**
- Claude API가 아티클 본문을 분석하여 구조화된 JSON 반환
  ```json
  {
    "insights": ["인사이트1", "인사이트2", "인사이트3"],
    "one_line_summary": "알림용 한 줄 요약",
    "sections": [
      {
        "heading2": "서론",
        "subsections": [
          {"heading3": "소제목", "content": "내용..."}
        ]
      }
    ]
  }
  ```
- `notion_writer.py`가 JSON을 Notion API 블록 형식으로 변환하여 페이지 생성
- 아티클마다 소제목 개수·구조가 달라도 원문 구조를 그대로 반영 (동적 생성)
- 기존 노션 템플릿(제목2·3 뼈대)은 코드로 대체되므로 더 이상 사용 불필요
### 3.5 노션 DB 속성 매핑
기존 사용 중인 DB 구조 기반 (이미지 확인):
| 속성명 | 타입 | 입력 방식 | 설명 |
|---|---|---|---|
| 제목 | Title | 자동 | 아티클 제목 |
| 태그 | Multi-select | 자동 | 원문 태그 또는 LLM 추출 |
| URL | URL | 자동 | 원문 링크 |
| 간단요약 | Text | 수동 (본인 작성) | 자동 입력 안 함 |
| 작성일 | Date | 자동 | 원문 발행일 |
| 카탈로그 | Select | 자동 | 고정값 "HR" |
| 출처 | Text | 자동 | 에이치닷 / 그리팅 / 레몬베이스 |
### 3.6 노션 페이지 템플릿 호환
기존에 템플릿(목차/아티클 전문 URL/제목2·제목3 블록 자동 생성)이 설정되어 있는 상태.
**처리 방향:**
- 노션 API로 페이지 생성 시 템플릿은 자동 적용되지 않음 (API 한계)
- 대신 파이썬 코드에서 **동일한 블록 구조를 직접 생성**하도록 구현
- 목차(Table of Contents 블록), 소제목(Heading 2·3), 본문 단락(Paragraph) 블록을 코드로 구성
### 3.7 알림 사양 (Slack 또는 이메일)
**성공 시 알림 내용:**
```
✅ HR 아티클 수집 완료
📌 출처: 에이치닷
📄 제목: 데이터로 본, 채용 리드 타임이 길어지는 이유 TOP 5
🔗 URL: https://contents.h.place/article/...
💡 한 줄 요약: HR 담당자 89%가 채용 병목을 경험하며, 핵심 원인은 평가 기준과 운영 구조의 부재다.
📅 작성일: 2026-05-23
```
**새 아티클 없을 시 (전체 사이트 탐색 후):**
```
📭 전체 사이트 새 아티클 없음 (2026-05-25 기준)
탐색한 사이트: 에이치닷 → 그리팅 → 레몬베이스
```
**실패 시:**
```
❌ HR 스크래퍼 실행 실패
사이트: 그리팅
오류: ConnectionError - 사이트 응답 없음
GitHub Actions 로그: {링크}
```
### 3.8 에러 처리
| 상황 | 동작 |
|---|---|
| 스크래퍼 실패 (네트워크 등) | 실패 알림 발송 후 종료. 다음 실행 시 동일 사이트 재시도 (순환 인덱스 유지) |
| LLM 호출 실패 | 재시도 1회 후 실패 시 → 본문만 저장, 요약 없이 노션 저장 |
| 노션 저장 실패 | 실패 알림 발송, 처리된 URL 기록 안 함 (다음 실행에서 재시도) |
| 신규 아티클 없음 | "없음" 알림 발송, 정상 종료 |
---
## 4. 비기능 요구사항
### 4.1 안정성
- 단일 실행 실패가 다음 실행에 영향 없음
- 상태(순환 인덱스, 처리된 URL)가 레포에 커밋되어 유실 없음
### 4.2 비용
- GitHub Actions: 무료 (월 ~40분 사용, 한도 2,000분)
- Claude Sonnet 4.6 API: 월 약 $2~4 (주 2회 × 1건 기준)
- 총 월 운영 비용 목표: $5 이하
### 4.3 유지보수성
- 사이트별 어댑터 분리 (한 사이트 HTML 변경 시 해당 파일만 수정)
- 새 사이트 추가 시 어댑터 파일 1개 추가 + `config.py`에 등록만 하면 동작
- 시크릿(API 키, 노션 토큰)은 GitHub Secrets로 관리
### 4.4 관찰 가능성
- 매 실행 로그: GitHub Actions 탭에서 확인
- 처리 이력: `data/processed.json` (레포에 커밋)
- 알림으로 실행 결과 즉시 파악
---
## 5. 기술 스택
### 5.1 언어 및 런타임
- Python 3.11+
### 5.2 주요 라이브러리
| 용도 | 라이브러리 |
|---|---|
| HTTP 요청 | `requests` |
| HTML 파싱 | `beautifulsoup4`, `lxml` |
| JS 렌더링 (필요 시) | `playwright` |
| LLM 호출 | `anthropic` (Claude Sonnet 4.6) |
| 노션 API | `notion-client` |
| 환경변수 | `python-dotenv` (로컬 개발용) |
### 5.3 인프라
| 항목 | 선택 |
|---|---|
| 실행 환경 | GitHub Actions |
| 스케줄 | cron (`0 0 * * 1,4`, UTC) |
| 시크릿 관리 | GitHub Secrets |
| 상태 저장 | 레포 내 `data/` 폴더 (커밋) |
| 알림 | Slack Webhook 또는 Gmail SMTP |
---
## 6. 시스템 아키텍처
### 6.1 모듈 구성
```
hr-scraper/
├── docs/
│   └── PRD.md
├── scrapers/
│   ├── __init__.py
│   ├── base.py           # BaseScraper 인터페이스
│   ├── heydot.py         # 에이치닷 어댑터
│   ├── greeting.py       # 그리팅 어댑터
│   └── lemonbase.py      # 레몬베이스 어댑터
├── core/
│   ├── __init__.py
│   ├── scheduler.py      # 라운드로빈 사이트 선택
│   ├── summarizer.py     # Claude API 요약·정리
│   ├── notion_writer.py  # Notion 페이지 생성
│   └── notifier.py       # Slack/이메일 알림
├── data/
│   ├── state.json        # 현재 순환 인덱스 (다음 실행할 사이트)
│   └── processed.json    # 처리 완료된 URL 목록
├── .github/
│   └── workflows/
│       └── daily.yml     # GitHub Actions 스케줄
├── main.py               # 오케스트레이터
├── config.py             # 사이트 목록, 설정값
├── requirements.txt
└── README.md
```
### 6.2 데이터 흐름
```
[GitHub Actions cron: 월·목 09:00 KST]
          ↓
     [main.py 실행]
          ↓
[scheduler.py: state.json 읽어 이번 실행 사이트 결정]
          ↓
[해당 사이트 Scraper Adapter 실행]
          ↓
     신규 아티클 있음?
     ├── 없음 → [notifier.py: "없음" 알림] → 종료
     └── 있음 ↓
          ↓
[가장 최신 아티클 1건 선택]
          ↓
[summarizer.py: Claude Sonnet API 호출]
  - 본문 재구성 (서론/본론/결론 구조)
  - 주요 인사이트 3~5개 불릿 추출
  - 알림용 한 줄 요약 생성
          ↓
[notion_writer.py: 페이지 생성]
  - DB 속성 입력 (제목, URL, 작성일, 출처, 태그, 카탈로그)
  - 페이지 본문 블록 생성
    (인사이트 불릿 → 전문 링크 → 서론/본론/결론)
          ↓
[notifier.py: 성공 알림 발송]
  (출처, 제목, URL, 한 줄 요약, 작성일)
          ↓
[state.json 업데이트: 다음 사이트 인덱스]
[processed.json 업데이트: 처리된 URL 추가]
          ↓
[git commit & push: data/ 폴더]
```
### 6.3 어댑터 인터페이스
```python
from dataclasses import dataclass
from datetime import date
@dataclass
class Article:
    title: str
    url: str
    body: str            # 정제된 본문 텍스트
    published_date: date
    source: str          # "에이치닷" / "그리팅" / "레몬베이스"
    tags: list[str]      # 원문 태그 (없으면 빈 리스트)
class BaseScraper:
    source_name: str
    base_url: str
    def get_latest_articles(self) -> list[Article]:
        """목록 페이지에서 최신 아티클 메타 정보 추출 (최대 10건)"""
        ...
    def parse_article(self, url: str) -> Article:
        """개별 아티클 페이지에서 본문 추출"""
        ...
```
---
## 7. 범위 설정 (Scope)
### 7.1 In Scope (v1.0)
- ✅ 3개 사이트 자동 스크랩 (에이치닷, 그리팅, 레몬베이스)
- ✅ 라운드로빈 방식 실행당 1건 선택
- ✅ Claude Sonnet 4.6으로 본문 재구성 및 인사이트 추출
- ✅ 노션 DB 자동 저장 (기존 DB 속성 구조 준수)
- ✅ 노션 페이지 본문 블록 구조 자동 생성
- ✅ URL 기반 중복 제거
- ✅ GitHub Actions 주 2회 자동 실행
- ✅ Slack 또는 이메일 성공/실패/없음 알림
### 7.2 Out of Scope (v1.0 제외)
- ❌ 노션 DB '간단 요약' 자동 작성 (본인 직접 작성)
- ❌ 본문 내 이미지 자동 첨부
- ❌ 플렉스 사이트 (추후 추가)
- ❌ 웹 UI / 대시보드
- ❌ 다국어 번역
- ❌ 키워드 기반 필터링
### 7.3 Future Work
- 플렉스(AX 허브) 어댑터 추가
- 키워드 필터링 ("AI 채용", "OKR" 등 관심 주제 우선)
- 주간 다이제스트 (주 1회 요약 모음 발송)
- 새 사이트 추가 (사람인 HR 매거진 등)
---
## 8. 마일스톤
### Phase 1: MVP — 1개 사이트 end-to-end (목표: 1~2일)
- [ ] GitHub 레포 생성, 폴더 구조 셋업
- [ ] `BaseScraper` 인터페이스 작성
- [ ] **에이치닷** 어댑터 구현 (우선순위 1)
- [ ] `summarizer.py` 작성 (Claude API 연동)
- [ ] `notion_writer.py` 작성 (기존 DB 구조 기반)
- [ ] 로컬 수동 실행 → 노션에 1건 정상 저장 확인
### Phase 2: 사이트 확장 + 라운드로빈 (목표: 1일)
- [ ] 그리팅, 레몬베이스 어댑터 추가
- [ ] `scheduler.py` 라운드로빈 로직 구현
- [ ] `state.json` / `processed.json` 중복 체크 구현
### Phase 3: 자동화 (목표: 반나절)
- [ ] GitHub Actions `daily.yml` 작성
- [ ] GitHub Secrets 등록 (API 키, 노션 토큰)
- [ ] workflow_dispatch 수동 실행 테스트
- [ ] cron 활성화 및 실제 자동 실행 확인
### Phase 4: 알림 연동 (목표: 반나절)
- [ ] `notifier.py` 작성 (Slack Webhook 또는 이메일)
- [ ] 성공/실패/없음 케이스별 알림 포맷 확정
- [ ] 테스트 발송 확인
### Phase 5: 안정화 (2주 운영 후)
- [ ] 누락·오류 케이스 수정
- [ ] 플렉스 어댑터 추가 준비
- [ ] README 정리
---
## 9. 환경변수 목록
| 변수명 | 설명 | 보관 위치 |
|---|---|---|
| `ANTHROPIC_API_KEY` | Claude API 키 | GitHub Secrets |
| `NOTION_TOKEN` | Notion Integration Token | GitHub Secrets |
| `NOTION_DATABASE_ID` | 저장 대상 DB ID | GitHub Secrets |
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL | GitHub Secrets |
| (선택) `GMAIL_USER` | 이메일 발신 계정 | GitHub Secrets |
| (선택) `GMAIL_APP_PASSWORD` | Gmail 앱 비밀번호 | GitHub Secrets |
---
## 10. 참고 문서
- [Notion API Docs](https://developers.notion.com/)
- [Anthropic API Docs](https://docs.claude.com/)
- [GitHub Actions: Workflow syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [Slack Incoming Webhooks](https://api.slack.com/messaging/webhooks)
