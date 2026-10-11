# 듣기 회차 추가하기

공식 모의고사 PDF·mp3 한 쌍으로 «듣기» 탭 회차 하나를 만든다. 설계는 `docs/superpowers/specs/2026-10-09-hsk-listening-tab-design.md`.

## 준비 (한 번만)

```sh
brew install whisper-cpp
mkdir -p ~/hsk-listening-work/models
curl -L -o ~/hsk-listening-work/models/ggml-small.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin
python3 -m venv ~/venv-store/hsk-listening && ~/venv-store/hsk-listening/bin/pip install pypinyin
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

- `assemble.py`에는 **모든 회차**를 넘긴다. 회차 목록과 단어장의 «HSK3 듣기» 단원을 매번 새로 쓰기 때문이다.
- `align`이나 `verify`에서 «확인 필요»로 걸린 문항은 원본에서 구간을 들어 보고 `$W/<회차>/overrides.json`에 `{"12": [시작초, 끝초]}`로 적은 뒤 `build`부터 다시 돌린다.
- `--show-readings`로 나오는 목록은 pypinyin과 음절이 다른 단어다. 다음자(还 huán, 长 cháng, 성씨 解 Xiè 등)는 맞는 경우가 많으니 문맥을 보고 고칠 것만 고친다.
