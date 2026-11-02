# 독해 회차 추가하기

공식 모의고사 PDF 하나로 «독해» 탭 회차 하나(41~70번)를 만든다. 설계는 `docs/superpowers/specs/2026-10-12-hsk-reading-tab-design.md`.

## 준비

듣기 도구와 같은 파이썬 환경(`~/venv-store/hsk-listening`, pypinyin·jieba)과 poppler(`pdftotext`)를 쓴다. 중간 파일은 Google Drive 밖 `~/hsk-reading-work/<회차>/`에 둔다.

## 순서 (예: H31006)

```sh
PY=~/venv-store/hsk-listening/bin/python
$PY tools/reading/paper.py H31006 --pdf ~/hsk-listening-work/src/H31006.pdf --work ~/hsk-reading-work
# 해설: ~/hsk-reading-work/H31006/enrich-41-50.json, enrich-51-60.json, enrich-61-70.json (아래 «해설 쓰기»)
$PY tools/reading/assemble.py H31006 --work ~/hsk-reading-work --repo . --check --show-readings
$PY tools/reading/assemble.py H31001 H31002 H31003 H31004 H31005 H31006 --work ~/hsk-reading-work --repo .
$PY -m unittest discover -s tools/reading -v
```

정답이 별도 파일이면 `paper.py`에 `--answers-json H31006-answers.json`을 준다. 파일은 `{"41":"A", ..., "70":"C"}` 형식이다. 기존 화면 형식의 병음·한국어 해설 초안은 다음처럼 만들 수 있다.

```sh
$PY tools/auto_enrich.py H31006 --listening-work ~/hsk-listening-work --reading-work ~/hsk-reading-work --mode reading
```

- 핵심 단어는 문항당 최대 8개다. 해당 시험 급수에서 새로 추가되는 어휘를 먼저 담고, 남는 칸만 다른 핵심어로 채운다. 신규 어휘가 8개를 넘으면 문항에 먼저 나온 8개를 쓴다. 1·2부분은 문항과 정답 문장을, 3부분은 지문·질문·세 보기를 기준으로 고른다.
- 기존 병음·해석·문법을 유지하고 전체 회차의 핵심 단어만 다시 만들 때는 모든 회차를 넘기고 `--vocab-only --repo .`를 붙인다. 작업 폴더와 `public/reading`의 단어만 함께 갱신된다.
- `assemble.py`로 실제로 쓸 때는 **모든 회차**를 넘긴다. 회차 목록과 단어장 «HSK3 독해» 단원을 매번 새로 쓰기 때문이다.
- `--check`는 검사만 하고 파일을 쓰지 않는다. 해설을 쓰는 동안에는 이것만 돌린다.
- **핵심 단어 보정 사전** `tools/vocab_fixes.json`: 자동 단어 중 한글 뜻이 없는 것(뜻 = 한자), 품사를 못 정한 것(«단어»), 두 단어가 붙거나 잘못 끊긴 토큰(比较忙, 铅笔画)은 여기에 병음·품사·뜻(`words`), 나누기(`split`·`parts`), 문항별 보정(`items`)으로 적는다. `auto_enrich.py`와 `assemble.py`가 이 사전을 거치고, `assemble.py` 검사는 **뜻에 한글이 없거나 품사가 «단어»인 단어를 막는다.** 원본 작업 폴더의 해설 파일은 고치지 않는다. 사전을 고친 뒤에는 `$PY tools/vocab_fixes.py --repo . --apply-listening`(듣기 공개 데이터·«HSK3 듣기» 단원)과 독해 `assemble.py`(모든 회차)를 차례로 돌린다. `$PY tools/vocab_fixes.py --repo .`는 공개 데이터에 남은 문제 개수만 보여 준다.
- 단어장 카드 id는 다시 만들어도 같은 단어면 그대로 둔다(오답노트가 id로 기록된다). 새 단어만 다음 번호를 받는다.
- `--show-readings` 목록은 pypinyin과 음절이 다른 단어다. 다음자(还 hái/huán, 长 cháng/zhǎng, 得 de/děi 등)와 不·一 변조는 맞는 경우가 많으니 문맥을 보고 틀린 것만 고친다.

## 해설 쓰기

`paper.json`의 원문·정답을 보고 부분마다 파일 하나씩 쓴다. 원문 한자는 `paper.json` 그대로 쓰고 추정해서 바꾸지 않는다.

### 파일 형식

```json
{
  "groups": [
    { "id": "41-45", "options": [{ "label": "A", "words": [["太","tài"],["好","hǎo"],["了","le"],["！",""]], "ko": "잘됐다!" }] }
  ],
  "items": [
    {
      "no": 41,
      "lines": [{ "words": [["我","wǒ"],["的","de"],["作业","zuòyè"]], "ko": "…" }],
      "question": null,
      "options": null,
      "pair": "item-first",
      "explain": {
        "basis": { "quote": "원문 구절 그대로", "note": "왜 답인지 1~3문장" },
        "distractors": [{ "label": "A", "note": "한 줄" }],
        "vocab": [{ "hanzi": "满意", "pinyin": "mǎnyì", "partOfSpeech": "형용사", "meaningKo": "만족하다" }],
        "grammar": [{ "pattern": "虽然A，但是B", "note": "‘A이긴 하지만 B’. 말하는 사람의 무게는 B에 있다. \"虽然没有花园，但是离河边很近\".",
                      "example": { "zh": "虽然很贵，但是很好吃。", "words": [["虽然","suīrán"],["很","hěn"],["贵","guì"],["，",""],["但是","dànshì"],["很","hěn"],["好吃","hǎochī"],["。",""]], "ko": "비싸긴 하지만 맛있다." } }]
      }
    }
  ]
}
```

- 파일마다 그 부분의 묶음 보기를 `groups`에 넣는다: `enrich-41-50.json`은 `41-45`·`46-50`, `enrich-51-60.json`은 `51-55`·`56-60`, `enrich-61-70.json`은 `groups` 없음. 2부분 단어 보기의 `ko`는 짧은 뜻(예: `"근처"`).
- `words`: 단어 단위 `[한자, 병음]`. 문장부호는 `["，", ""]`. 숫자가 섞인 토큰은 읽기를 병음으로(`["9月","jiǔ yuè"]`, `["100","yìbǎi"]`). 한자를 이으면 원문과 **정확히** 같아야 한다(문장부호·숫자 포함).
- **1부분**: `lines`는 문항 문장 한 줄. `pair`는 짝지은 대화에서 문항 문장이 먼저면 `"item-first"`, 정답 보기 문장이 먼저면 `"option-first"`. `question`·`options`는 `null`.
- **2부분**: `lines`는 `paper.json`의 줄 수와 같게(대화면 A·B 두 줄, 화자는 쓰지 않는다). 빈칸 자리에는 **정답 단어**를 넣고 그 줄에 `"blank": 단어 인덱스`를 단다. `pair`·`question`·`options`는 `null`.
- **3부분**: `lines`는 지문을 문장 단위(。！？ 뒤, 닫는 따옴표는 앞 문장에)로 나눈 것. 모두 이으면 지문 원문과 같아야 한다. `question`은 ★ 질문(★ 빼고), `options`는 A·B·C. `pair`는 `null`.
- 병음: 不·一 변조를 표기한다(`bú shì`, `yí ge`, `yìqǐ`). 경성은 성조 없이(`de`, `le`, `ma`, `zi`). 儿화는 붙여 쓴다(`zhèr`, `yíhuìr`). 단어 안은 붙여 쓰고 첫 글자도 소문자.
- `ko`: 자연스러운 한국어 해석.

### 해설 기준

- **정답 근거(basis)**: `quote`는 답을 가리키는 원문 구절을 **한 문장 안에서** 그대로 옮긴다(2부분은 빈칸에 정답을 채운 문장에서). `note`는 그 구절이 왜 답이 되는지 단서(접속사의 무게, 질문·대답 짝, 지시어, 빈칸 자리의 품사, 호응 등)를 1~3문장으로.
- **오답 이유(distractors)**: 3부분은 나머지 두 보기를 **모두**, 1·2부분은 헷갈리기 쉬운 보기 1~2개를 한 줄씩. 예시 보기는 쓰지 않는다. «지문에 없음», «반대 내용», «빈칸 자리는 형용사인데 동사»처럼 이유가 드러나게.
- **단어(vocab)**와 **문법(grammar)**은 «듣기» 탭과 같은 형식·기준으로 쓴다(`tools/listening/README.md`, 설계 `docs/superpowers/specs/2026-10-09-hsk-listening-tab-design.md` «해설 기준»). 화면도 듣기와 같은 목록(`ExplainVocab`·`ExplainGrammar`)으로 나온다.
- **단어(vocab)**: 문항당 3~8개. 해당 시험 급수에서 새로 추가되는 어휘를 본문 등장 순서로 먼저 담고, 남는 칸을 다른 핵심어로 채운다. 칸은 `hanzi`·`pinyin`·`partOfSpeech`·`meaningKo` 넷뿐이다. 용법(`usage`)·예문(`example`)은 쓰지 않는다. 단어장 «HSK3 독해» 카드 예문은 `assemble.py`가 그 단어가 나온 시험 문장에서 따온다.
- **문법(grammar)**: 문항당 1~3개, 접속사·구문 패턴 위주(虽然…但是…, 把자문, 被자문, 比 비교문, 결과보어, 방향보어, 一…就…, 越来越, 除了…还… 등). 필수 칸은 `pattern`·`note` 둘이다. 짧은 뜻이 있으면 `note` 앞에 `‘뜻’.`으로 쓰고, 이 문항의 문장을 따옴표로 인용해 어떻게 쓰였는지 보인다(듣기 문장 구조와 같은 방식).
- **문법 예문(grammar `example`)은 선택**이다. 쓰면 `{ "zh", "words", "ko" }` 셋을 모두 채우고, 지문에 없는 **새로 지은** 짧은 문장(해당 급수 수준)이어야 한다. 있으면 화면의 문장 구조 카드 안에 설명 아래로 나온다. 정답 근거 인용과 같거나 문항 글(지문·질문·보기)에 그대로 있는 문장은 지문 반복으로 보고 `assemble.py`가 버린다(H31006 이후 `auto_enrich`가 넣던 예문이 이 경우다). 지금 예문이 남는 회차는 사람이 해설을 쓴 H31001~H31005다.
- 끊어 읽기(`breakdown`)는 쓰지 않는다. 예전 해설 파일에 남은 `breakdown`·단어 `usage`·단어 `example`·문법 `meaningKo`는 `assemble.py`가 공개 데이터에 넣지 않는다(문법 `meaningKo`는 `note` 앞에 `‘뜻’.`으로 옮긴다).
- 해설은 한국어로, 짧은 문장으로 쓴다.
