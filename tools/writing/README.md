# HSK3 쓰기 데이터

`python3 tools/writing/generate.py --source ~/hsk-listening-work/src`로
`public/writing/hsk3-all.json`을 재생성합니다. Python 표준 라이브러리와 Poppler의
`pdftotext`가 필요합니다. 원본 PDF는 읽기만 합니다.

19회차의 71~80번을 지정된 순서로 이어 붙여 어순 95개·한자 95개를 보존합니다.
중복 문항을 제거하지 않습니다. 화면은 회차 대신 연속 번호를 사용하며, 내부 데이터는
원래 시험/문항 ID, 파일 SHA256, PDF 쪽수(1부터), 정답표 위치를 보존합니다.

`H31007 정답.pdf`는 텍스트가 없는 이미지 PDF이므로 2쪽을 직접 렌더해 판독한
공식 답을 `overrides.json`에 기록했습니다. 이 파일에는 원본 해시와 쪽수도 있습니다.
72번은 사용자 결정에 따라 문제지의 `姓名`을 사용하고, 정답표의 `名字`와 다른 점은
답 공개 후 안내합니다. 77번의 공식 복수 답 `元/圆`은 둘 다 보존합니다.
나머지 정답은 원본 PDF에서 직접 추출하며 복수 답도 모두 유지합니다.

검증:

```sh
python3 -m unittest discover -s tools/writing -p 'test_*.py'
npm test
npm run build
```

생성 시 190개·95/95·고유 ID·연속 번호·회차별 71~80번·복수 답·중복을 검사합니다.
어순은 모든 공식 답이 문제지 토큰의 순열과 일치해야 통과합니다.
원본 PDF가 있는 환경의 테스트는 출력 전체를 다시 생성해 비교하고 쪽수 범위를 확인합니다.
