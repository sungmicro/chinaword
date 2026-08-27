# CLAUDE.md

## 이 저장소

`chinaword` — 중국어 랜덤 카드(모바일 암기장) 웹앱. Vite + React, Vercel 배포.

- `src/` — 앱 소스. `src/data/vocab.json`이 단어 데이터(HSK 1·2급 + 교재).
- `dist/` — 빌드 산출물.
- 개발: `npm run dev` / 빌드: `npm run build`

## 위키 = 구글 드라이브 (Notion 아님)

성미님의 위키는 **구글 드라이브의 `LLM_wiki` 폴더**다. Obsidian 볼트를 Drive에 동기화한 구조이며,
파일은 전부 `.md`다. **Notion은 사용하지 않는다. 위키 관련 요청에서 Notion을 검색하지 말 것.**

- 루트 폴더 ID: `1scFrMA0LIv4fQcO9_irCluJMLMh_6vOv`
  (https://drive.google.com/drive/folders/1scFrMA0LIv4fQcO9_irCluJMLMh_6vOv)
- 접근 도구: `mcp__Google_Drive__*` (`search_files`로 `parentId = '<폴더ID>'` 조회 → `read_file_content` → `create_file`)

### 폴더 구조

| 폴더 | 용도 |
|---|---|
| `00_Inbox` | 미분류 유입 |
| `01_Home` | 홈 |
| `02_Hub_신체자본` ~ `08_Hub_사회자본` | 개인 7자본 허브 |
| `09_Daily` | 일일 기록 |
| **`10_Work_미생물랩`** | **회사(업무용) 허브** — 개인 7자본과 분리 |
| `90_Templates`, `98_Attachments`, `99_Archive` | 템플릿·첨부·보관 |

### 업무용 허브 `10_Work_미생물랩` (folder ID `1yfyy3h7qBmLJAJcZqqHLNyZNTFs_RGGw`)

| 하위 | ID | 용도 |
|---|---|---|
| `00_Raw` | `1f4OhU05_7meDNKUz1H3Z4h2GFp_ZPa0W` | **인제스트** — 원본(녹취록·사진·원문) |
| `02_지식` | `1H2yyxbLWe-gRRkJRmUHVfkS9Miusnoup` | **지식** — 원본을 증류한 정리본 |
| `03_Projects` / `04_Newsletter` / `05_엔티티` | — | 프로젝트·뉴스레터·엔티티 |
| `00_허브 홈.md` | `1MicjC05ZYz6vutldU6h-uLmJpJzTwP2g` | 허브 인덱스 |

**"인제스트에서 자료 지식으로"** = 원본을 `00_Raw`에 넣고, 이를 증류한 노트를 `02_지식`에 만든다는 뜻.

### 노트 작성 규칙

- YAML frontmatter 필수: `type`(knowledge/raw/work_hub), `status`, `hub`, `source`, `created`, `updated`,
  `review`, `sensitivity`, `topics`, `tags`. 업무 문서는 `sensitivity: confidential`.
- 본문 첫 줄에 `> 상위: [[10_Work_미생물랩/00_허브 홈|미생물랩 허브 홈]]` — **고아 페이지 금지.**
- 링크는 Obsidian 위키링크 `[[경로|표시명]]`.
- 문서 끝에 `## 관련 문서`(원본 링크 포함)와 `## 변경 이력`.
- 새 지식 노트를 만들면 `00_허브 홈.md`의 `## 지식` 목록에 한 줄 추가한다.
  (Drive MCP의 `update_file`은 제목·위치만 바꾸므로 본문 수정은 사용자가 직접 하거나 별도 방법 필요)
- 회사 자료는 업무 허브 안에서만 다루고, 개인 7자본에는 전이 가능한 방법론만 링크한다.
