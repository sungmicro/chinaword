# 성미 중국어 카드 단어장 웹앱

Vercel Hobby 무료 플랜에 올려서 사용할 수 있는 개인용 중국어 단어 카드 웹앱입니다.

## 들어있는 기능

- 중국어 단어 카드 표시
- 카드 클릭 시 뜻과 예문 표시
- 한자, 병음, 뜻, 예문 검색
- HSK 급수 필터
- Lesson 필터
- 랜덤 보기
- `알아요` / `복습 필요` 표시
- 학습 표시 localStorage 저장
- 모바일 화면 대응

## 로컬에서 실행하기

```bash
npm install
npm run dev
```

브라우저에서 안내되는 주소를 열면 됩니다.

## Vercel에 배포하기

1. 이 폴더를 GitHub 저장소에 올립니다.
2. Vercel에 로그인합니다.
3. New Project를 누릅니다.
4. GitHub 저장소를 선택합니다.
5. Framework Preset이 Vite로 잡히는지 확인합니다.
6. Deploy를 누릅니다.

## 단어 추가 방법

`src/data/vocab.json` 파일에 아래 형식으로 단어를 추가합니다.

```json
{
  "id": 21,
  "level": "HSK1",
  "lesson": "Lesson 4",
  "category": "명사",
  "hanzi": "水",
  "pinyin": "shuǐ",
  "meaningKo": "물",
  "partOfSpeech": "명사",
  "exampleZh": "我喝水。",
  "examplePinyin": "Wǒ hē shuǐ.",
  "exampleKo": "저는 물을 마십니다.",
  "tags": ["일상", "음식"]
}
```

중요: `id`는 기존 단어와 겹치지 않게 숫자를 늘려주세요.

## 추천 운영 방식

처음에는 `vocab.json`에 단어를 넣어서 배포하고, 나중에 단어 수가 많아지면 Google Sheets 또는 Notion DB 연동 방식으로 확장하는 것을 추천합니다.
