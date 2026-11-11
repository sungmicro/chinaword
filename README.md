# 중국어 랜덤 카드 - 모바일 암기장 업데이트

이 업데이트는 기존 `vocab.json` 데이터는 그대로 두고 화면 구조만 바꿉니다.

## 변경 내용

- 모바일에서 카드 글자 크기를 크게 조정
- 한자만 / 병음만 / 뜻만 / 랜덤 출제 모드 버튼 추가
- 헤더와 카드 영역을 컴팩트하게 재배치
- 모바일 화면에서 페이지 전체가 아래로 스크롤되지 않도록 100svh 고정 레이아웃 적용
- 긴 문장이나 긴 뜻은 자동으로 작은 글자 크기로 표시
- 필터, 검색, 복습 버튼은 계속 제거 상태 유지

## 업로드 방법

GitHub `chinaword` 저장소에서 `Add file → Upload files`를 누른 뒤 이 폴더 안의 아래 항목을 업로드하세요.

```text
src
README.md
```

커밋 메시지 예시:

```text
Make mobile compact quiz layout
```

업로드 후 Vercel이 자동으로 재배포합니다.

## 유지되는 데이터

이번 ZIP에는 `src/data/vocab.json`이 포함되어 있지 않습니다. 기존 HSK 1급/2급 및 교재 단어장 데이터는 유지됩니다.

## 내 단어장 갱신

- 내 단어장(기기 저장)은 담을 때의 병음·뜻을 저장하므로, 앱이 불러올 때 `src/data/mine-refresh.json` 색인으로 단어 항목을 지금 데이터에 맞춘다(나뉜 묶음 比较忙 → 比较·忙, 대본 오인식 散 → 伞, 모름 횟수·출처·메모 유지, 문장·패턴은 그대로). 색인은 `tools/mine_refresh.py`가 공개 데이터·`tools/vocab_fixes.json`·`tools/mine_moves.json`에서 만들고 듣기·독해·쓰기 데이터를 쓰는 도구들이 마지막에 다시 쓰므로, 데이터를 고치면 갱신도 따라온다(오래되면 `npm test`가 실패한다 → `python3 tools/mine_refresh.py --repo .`).
- 문장(대본·지문·보기) words의 붙은 토큰(比较忙 bǐjiàománg)은 `tools/sentence_split.py`가 나눈다. 데이터를 다시 만들면 듣기·독해 `assemble.py`와 `vocab_fixes.py --apply-listening`이 함께 나누고, 공개 데이터와 `vocab.json` 예문 병음만 고칠 때는 `python3 tools/vocab_fixes.py --repo . --apply-sentences`. 고친 병음은 `tools/sentence_splits.json`에 쌓여 내 단어장 예문 병음도 같은 표로 바뀐다.

## HSK 3.0 4급 단어 (HSK4 그룹)

- 앱의 HSK1·HSK2·HSK3 단원은 HSK 2.0 기준이고, «HSK4 (3.0)» 단원은 HSK 3.0(2021) 4급 새 단어다. 한자가 이미 단어장에 있는 단어는 넣지 않았다(같은 한자의 다른 읽기 7개는 따로 카드).
- 목록·병음·품사: `tools/hsk30/level4_raw.json`(출처는 파일 안 `sources`). 뜻은 AI 번역(`tools/hsk30/meanings/`)이고 다른 에이전트가 검토했다.
- 뜻을 고치면 `tools/hsk30/meanings/*.json`을 고친 뒤 `python3 tools/hsk30/build_level4.py check --repo .` → `apply --repo .`. vocab.json을 손으로 고치지 않는다(카드 id 장부·내 단어장 갱신 색인도 apply가 함께 쓴다).
