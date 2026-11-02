# 듣기 회차 추가하기

공식 모의고사 PDF·mp3 한 쌍으로 «듣기» 탭 회차 하나를 만든다. 설계는 `docs/superpowers/specs/2026-10-09-hsk-listening-tab-design.md`.

## 준비 (한 번만)

```sh
brew install whisper-cpp
mkdir -p ~/hsk-listening-work/models
curl -L -o ~/hsk-listening-work/models/ggml-small.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin
python3 -m venv ~/venv-store/hsk-listening && ~/venv-store/hsk-listening/bin/pip install pypinyin jieba
```

중간 파일과 모델은 Google Drive 밖 `~/hsk-listening-work/`에 둔다.

## 순서 (예: H31006)

```sh
PY=~/venv-store/hsk-listening/bin/python
W=~/hsk-listening-work
M=$W/models/ggml-small.bin

$PY tools/listening/paper.py H31006 --pdf H31006.pdf --work $W --public public/listening
$PY tools/listening/audio.py align  H31006 --mp3 H31006.mp3 --work $W --model $M
$PY tools/listening/audio.py build  H31006 --work $W --public public/listening
$PY tools/listening/audio.py verify H31006 --work $W --public public/listening --model $M
# 해설: $W/H31006/enrich.json 을 만든다 (병음·해석·단어·문장 구조, 형식은 설계서 참고)
$PY tools/listening/assemble.py H31001 H31002 H31003 H31004 H31005 H31006 --work $W --repo . --show-readings
```

PDF에 듣기 대본이 없으면 빈 대본을 만든 뒤, 공식 음원의 반복 낭독을 이용해 복구한다.

```sh
$PY tools/listening/paper.py H31006 --pdf H31006.pdf --work $W --public public/listening \
  --allow-missing-script --answers-json H31006-answers.json
$PY tools/listening/bootstrap.py H31006 --mp3 H31006.mp3 --work $W --model $M
$PY tools/listening/audio.py build H31006 --work $W --public public/listening
$PY tools/listening/audio.py verify H31006 --work $W --public public/listening --model $M
$PY tools/listening/refine.py H31006 --work $W
```

`answers-json`은 `{"1":"A", ..., "40":"C"}` 형식이다. `verify`가 실제로 더 길게 들은 문장을 표시하면 `refine.py`가 그 문항의 임시 Whisper 대본을 보완한다.

기존 화면 형식에 맞는 병음·한국어 해설 초안을 한꺼번에 만들 수 있다.

```sh
$PY tools/auto_enrich.py H31006 --listening-work $W --reading-work ~/hsk-reading-work --mode listening
```

- 핵심 단어는 문항당 최대 8개다. 해당 시험 급수에서 새로 추가되는 어휘를 먼저 담고, 남는 칸만 다른 핵심어로 채운다. 신규 어휘가 8개를 넘으면 문항에 먼저 나온 8개를 쓴다.
- 기존 병음·해석·문법을 유지하고 전체 회차의 핵심 단어만 다시 만들 때는 모든 회차를 넘기고 `--vocab-only --repo .`를 붙인다. 작업 폴더와 `public/listening`의 단어만 함께 갱신된다.
- `assemble.py`에는 **모든 회차**를 넘긴다. 회차 목록과 단어장의 «HSK3 듣기» 단원을 매번 새로 쓰기 때문이다.
- `assemble.py --check`는 검사만 하고 파일을 쓰지 않는다. H31006 이후 회차는 대본 손질 이력 때문에 `assemble.py`로 다시 만들 수 없으니, 단어만 고칠 때는 아래 `vocab_fixes.py --apply-listening`을 쓴다.
- **핵심 단어 보정 사전** `tools/vocab_fixes.json`: 자동 단어 중 한글 뜻이 없는 것(뜻 = 한자), 품사를 못 정한 것(«단어»), 두 단어가 붙거나 잘못 끊긴 토큰(比较忙, 铅笔画)은 여기에 병음·품사·뜻(`words`), 나누기(`split`·`parts`), 문항별 보정(`items`)으로 적는다. `auto_enrich.py`와 `assemble.py`가 이 사전을 거치고, `assemble.py` 검사는 **뜻에 한글이 없거나 품사가 «단어»인 단어를 막는다.** 원본 작업 폴더의 해설 파일은 고치지 않는다. 사전을 고친 뒤에는 `$PY tools/vocab_fixes.py --repo . --apply-listening`(듣기 공개 데이터·«HSK3 듣기» 단원)과 독해 `assemble.py`(모든 회차)를 차례로 돌린다. `$PY tools/vocab_fixes.py --repo .`는 공개 데이터에 남은 문제 개수만 보여 준다.
- 단어장 카드 id는 다시 만들어도 같은 단어면 그대로 둔다(오답노트가 id로 기록된다). 새 단어만 다음 번호를 받는다.
- `align`이나 `verify`에서 «확인 필요»로 걸린 문항은 원본에서 구간을 들어 보고 `$W/<회차>/overrides.json`에 `{"12": [시작초, 끝초]}`로 적은 뒤 `build`부터 다시 돌린다.
- `--show-readings`로 나오는 목록은 pypinyin과 음절이 다른 단어다. 다음자(还 huán, 长 cháng, 성씨 解 Xiè 등)는 맞는 경우가 많으니 문맥을 보고 고칠 것만 고친다.
