# 다이어리 속지 카드 (7.5 × 10 cm)

내 주요 정보를 다이어리에 끼워 쓸 수 있도록 만든 인쇄용 카드입니다.
`cards/data.json` 의 값만 고치면 PNG가 다시 만들어집니다.

## 결과물

| 파일 | 내용 |
| --- | --- |
| `out/01-profile.png` | 나의 정보 — 이름 · 생년월일 · 혈액형 · 연락처 · 소속 |
| `out/02-emergency.png` | 비상 연락 — 긴급 연락처 · 병원 · 보험 · 알레르기 |
| `out/03-year-goals.png` | 한해 목표 체크리스트 |
| `out/04-quarter-goals.png` | 분기 목표 Q1–Q4 |
| `out/print-a4.png` | 위 4장을 A4 한 장에 배치 + 재단 표시 |

- 카드 1장 = **886 × 1181 px (7.5 × 10 cm @ 300dpi)**
- A4 시트 = 2480 × 3508 px
- 왼쪽 9.5 mm 는 바인더 펀치 여백이라 글자가 들어가지 않습니다.

## 만드는 법

```bash
npm install          # 처음 한 번 (playwright-core)
npm run cards        # 카드 PNG + A4 시트 생성
```

옵션

```bash
node cards/render.mjs --no-sheet   # 카드 PNG만
node cards/render.mjs --no-trim    # 가장자리 재단선 없이
```

한글 폰트(Noto Sans KR)가 없으면 처음 실행할 때 자동으로 내려받아 설치합니다.

## 내용 고치기

`cards/data.json` 에서 `value` / `text` 를 채우면 인쇄된 글자로 나오고,
`""` 로 비워두면 **손으로 적는 점선 칸**으로 나옵니다.

```json
{ "label": "휴대폰", "value": "010-0000-0000" }
{ "label": "주소",   "value": "", "span": 2 }        // span: 기입선 줄 수
{ "text": "HSK 3급 합격" }                            // 체크리스트 항목
```

카드 형식은 세 가지입니다.

- `fields` — 라벨 + 기입선 (정보 카드)
- `checklist` — 체크박스 + 기입선 (한해 목표)
- `quarters` — Q1–Q4 4분면 (분기 목표)

`accent` 는 `ink`(남색) 또는 `red`(진한 빨강)입니다.

### 실제 개인정보를 넣을 때

`cards/data.local.json` 을 만들면 그 파일이 우선 사용되고, `.gitignore` 에 있어
저장소에 올라가지 않습니다.

```bash
cp cards/data.json cards/data.local.json   # 여기에 진짜 정보를 채우기
npm run cards
```

주민등록번호 · 카드번호 · 여권번호처럼 잃어버렸을 때 곧바로 문제가 되는 정보는
카드에 적지 않는 편이 안전합니다.

## 인쇄 · 바인딩

1. `out/print-a4.png` 를 **100% (배율 맞춤 끄기)** 로 A4에 인쇄합니다.
2. 모서리 재단 표시를 따라 7.5 × 10 cm 로 자릅니다.
3. 왼쪽 여백에 다이어리와 같은 위치로 펀칭해서 끼웁니다.

낱장 PNG(`01-profile.png` 등)는 사진 인화(엽서 크기)나 태블릿 배경으로 쓰기 좋습니다.
120 g/m² 이상 용지에 인쇄하면 다이어리에서 잘 버팁니다.
