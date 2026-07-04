# 중국어 랜덤 카드 단어장 웹앱

Vercel Hobby 무료 플랜에 올려서 사용할 수 있는 개인용 중국어 랜덤 카드 웹앱입니다.

## 들어있는 기능

- 한자/중국어, 한어병음, 한글 뜻 중 하나가 랜덤으로 먼저 표시
- `정답 보기` 버튼을 누르면 나머지 정보 표시
- `다음 랜덤 카드` 버튼으로 무한 랜덤 반복
- 단어, 표현, 문법 항목과 예문 문장을 함께 랜덤 출제
- HSK/Lesson/유형/학습상태 필터
- 검색 기능
- `알아요` / `복습 필요` 표시
- Space 또는 Enter 키로 정답 보기/다음 카드 진행

## 단어 데이터 수정 위치

`src/data/vocab.json`

기본 데이터 형식:

```json
{
  "id": 1,
  "level": "HSK1",
  "lesson": "Lesson 1",
  "category": "인사",
  "hanzi": "你好",
  "pinyin": "nǐ hǎo",
  "meaningKo": "안녕하세요",
  "partOfSpeech": "표현",
  "exampleZh": "你好，我是韩国人。",
  "examplePinyin": "Nǐ hǎo, wǒ shì Hánguó rén.",
  "exampleKo": "안녕하세요, 저는 한국 사람입니다.",
  "tags": ["인사", "기초"]
}
```

예문이 있는 항목은 앱에서 자동으로 별도 `문장` 카드로도 출제됩니다.

## Vercel 설정

- Framework Preset: Vite
- Build Command: `npm run build`
- Output Directory: `dist`
- Install Command: `npm install`

`package-lock.json`은 포함하지 않았습니다.
