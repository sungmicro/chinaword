# 독해 회차 추가하기

공식 모의고사 PDF 하나로 «독해» 탭 회차 하나(41~70번)를 만든다. 설계는 `docs/superpowers/specs/2026-10-12-hsk-reading-tab-design.md`.

## 준비

듣기 도구와 같은 파이썬 환경(`~/venv-store/hsk-listening`, pypinyin)과 poppler(`pdftotext`)를 쓴다. 중간 파일은 Google Drive 밖 `~/hsk-reading-work/<회차>/`에 둔다.

## 순서 (예: H31006)

```sh
PY=~/venv-store/hsk-listening/bin/python
$PY tools/reading/paper.py H31006 --pdf ~/hsk-listening-work/src/H31006.pdf --work ~/hsk-reading-work
# 해설: ~/hsk-reading-work/H31006/enrich-41-50.json, enrich-51-60.json, enrich-61-70.json (아래 «해설 쓰기»)
$PY tools/reading/assemble.py H31006 --work ~/hsk-reading-work --repo . --check --show-readings
$PY tools/reading/assemble.py H31001 H31002 H31003 H31004 H31005 H31006 --work ~/hsk-reading-work --repo .
$PY -m unittest discover -s tools/reading -v
```

- `assemble.py`로 실제로 쓸 때는 **모든 회차**를 넘긴다. 회차 목록과 단어장 «HSK3 독해» 단원을 매번 새로 쓰기 때문이다.
- `--check`는 검사만 하고 파일을 쓰지 않는다. 해설을 쓰는 동안에는 이것만 돌린다.
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
        "breakdown": [{ "chunks": [{ "text": "我", "role": "주어" }], "note": "구조 요약 한 줄" }],
        "vocab": [{ "hanzi": "满意", "pinyin": "mǎnyì", "partOfSpeech": "형용사", "meaningKo": "만족하다",
                    "usage": "对A很满意 / 对A不满意",
                    "example": { "zh": "我对这个房间很满意。", "words": [["我","wǒ"],["对","duì"],["这个","zhège"],["房间","fángjiān"],["很","hěn"],["满意","mǎnyì"],["。",""]], "ko": "나는 이 방이 아주 마음에 든다." } }],
        "grammar": [{ "pattern": "虽然A，但是B", "meaningKo": "A이긴 하지만 B", "note": "말하는 사람의 무게는 B에 있다.",
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
- **끊어 읽기(breakdown)**: 문항당 1~2문장(정답 근거 문장 우선). `chunks`를 이으면 화면에 나오는 문장(지문·질문·보기·짝 문장, 2부분은 빈칸 채운 문장)의 일부와 같아야 한다. `role`은 `주어` `술어` `목적어` `관형어` `부사어` `보어` `접속사` `개사구` 중에서. `note`는 구조 요약 한 줄(예: `对 + 대상 + 满意 = '~에 만족하다'`).
- **단어(vocab)**: 문항당 3~6개, HSK 3급 수준 위주(HSK1 기초어는 뺀다). `usage`는 자주 쓰는 짝·호응, `example`은 **새로 지은** 짧은 예문(HSK 3급 수준).
- **문법(grammar)**: 문항당 1~3개, 접속사·구문 패턴 위주(虽然…但是…, 把자문, 被자문, 比 비교문, 결과보어, 방향보어, 一…就…, 越来越, 除了…还… 등). `meaningKo`는 짧은 뜻(내 단어장 카드 뜻 자리), `note`는 설명, `example`은 새 예문.
- 해설은 한국어로, 짧은 문장으로 쓴다.
