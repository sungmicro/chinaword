# HSK 독해 탭·내 단어장 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** chinaword 앱에 HSK 3급 공식 모의고사 독해(41~70번) 탭을 «문항 해설형» 해설과 함께 넣고, 해설의 단어·문장 구조를 «내 단어장»에 모아 단어장·랜덤 학습에서 다시 보게 한다.

**Architecture:** 시험지 PDF를 `pdftotext -raw`로 읽어 문항을 뽑는 파이썬 도구(`tools/reading/paper.py`), Claude가 쓴 해설과 합치며 기계 검사하는 도구(`tools/reading/assemble.py`)가 `public/reading/<회차>.json`을 만든다. 화면은 듣기 탭에서 공용 조각(`src/hskParts.jsx`, `src/practiceStore.js`)을 떼어 독해 탭(`src/Reading.jsx`)과 같이 쓰고, 내 단어장은 저장을 한 모듈(`src/myVocab.js`)에 가둔다.

**Tech Stack:** React 19 + Vite(정적 배포, Vercel), lucide-react, Node 26 내장 테스트 실행기(`node --test`), Python 3.9 + pypinyin(`~/venv-store/hsk-listening`), poppler `pdftotext`.

**Spec:** `docs/superpowers/specs/2026-10-12-hsk-reading-tab-design.md`

## Global Constraints

- 작업은 Drive 밖 worktree `~/worktrees/chinaword-hsk-reading`(브랜치 `claude/hsk-reading-tab`)에서 한다. Drive 원본(`~/Library/CloudStorage/GoogleDrive-ssungmichoi@gmail.com/내 드라이브/90)Claude/projects/chinaword`)은 `main`에 두고 거기서 `npm`을 돌리지 않는다.
- 셸 변수: `W=~/worktrees/chinaword-hsk-reading`, `PY=~/venv-store/hsk-listening/bin/python`, `WORK=~/hsk-reading-work`, `SCRATCH=/private/tmp/claude-501/-Users-sungmi-LLM-wiki/0affe58d-1163-48cf-a7f9-93037dbe1c69/scratchpad`.
- 파이썬은 3.9다. `X | None` 타입 표기, `match` 문을 쓰지 않는다.
- `dist/`는 git에 올라가 있다. 빌드 확인은 `npx vite build --outDir "$SCRATCH/dist-check" --emptyOutDir`로 저장소 밖에 하고 `dist/`를 커밋하지 않는다.
- node 테스트가 가져오는 모듈(`practiceStore.js`, `myVocab.js`)은 서로를 `.js` 확장자까지 붙여 import한다(node ESM). 다른 파일은 기존처럼 확장자 없이 쓴다.
- localStorage 키: 풀이 기록 `sungmi-vocab-reading-v1`, 화면 상태 `sungmi-vocab-reading-prefs-v1`, 내 단어장 `sungmi-vocab-mine-v1`, 랜덤 학습 «내 단어장만» `sungmi-vocab-study-mine-v1`.
- 단원 이름 `HSK3 독해`, 내 단어장 칩 이름 `내 단어장`, 단어장 id 접두 `HSK3R-`.
- 부분 안내 문구: 1 `서로 이어지는 문장 짝 찾기`, 2 `빈칸에 알맞은 단어 고르기`, 3 `짧은 글을 읽고 질문에 답하기`.
- 듣기 탭의 CSS 클래스 이름은 바꾸지 않는다. 독해 전용은 `read*`, 내 단어장 전용은 `mine*`.
- 병음 관례: 不·一 변조 표기(`bú shì`, `yí ge`), 경성 무표기, 원문 한자는 PDF 그대로.
- 커밋 메시지는 영어 한 줄 요약 + 빈 줄 + `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- `main` 병합·푸시는 성미님 확인 뒤에만 한다.

## Review Focus

1. **폰 폭 390px**: 탭 6개가 한 줄에 들어가고, 긴 지문(H31001 64번, H31004 70번)과 단어 보기 6개가 가로 스크롤 없이 줄바꿈된다 → Task 8 브라우저 단계.
2. **같은 단어를 여러 곳에서**: 독해에서 담은 단어가 듣기 해설·단어장 «내 단어장»에 바로 «담음»·목록으로 보인다 → Task 6 구독 테스트, Task 9 브라우저 단계.
3. **«내 단어장만» 켠 채 마지막 항목 빼기**: 토글이 꺼지고 전체 카드가 나오며 출제 칸이 빈 카드가 나오지 않는다 → Task 9 브라우저 단계.
4. **저장소가 막히거나 깨진 기기(사생활 보호 모드)**: 독해·내 단어장이 빈 상태로 동작하고 멈추지 않는다 → Task 5·6 단위 테스트.
5. **회차 데이터 받기 실패(오프라인·404)**: 오류 문구가 나오고, 다시 고르면 다시 받는다 → Task 5 `fetchCached` 테스트.

---

### Task 1: worktree 준비와 글자 처리 도우미 `hsktext.py`

**Files:**
- Create: `tools/reading/hsktext.py`
- Test: `tools/reading/test_hsktext.py`

**Interfaces:**
- Produces: `tidy(text) -> str`, `toneless(pinyin) -> str`, `join_words(words) -> str`, `check_words(words, source, where, problems, reading_diffs) -> None`, `words_to_pinyin(words) -> str` (모두 `tools/reading/hsktext.py`). `words`는 `[[한자, 병음], …]`.

듣기 도구(`tools/listening/`)는 완성된 일회성 스크립트라 건드리지 않는다. 같은 함수를 독해 쪽에 옮겨 오고, 듣기 해설 보강(다음 작업) 때 합친다.

- [ ] **Step 1: Drive 원본을 main으로 돌리고 worktree를 만든다**

```bash
DRIVE="$HOME/Library/CloudStorage/GoogleDrive-ssungmichoi@gmail.com/내 드라이브/90)Claude/projects/chinaword"
git -C "$DRIVE" status --short   # 비어 있어야 한다
git -C "$DRIVE" switch main
mkdir -p ~/worktrees
git -C "$DRIVE" worktree add ~/worktrees/chinaword-hsk-reading claude/hsk-reading-tab
cd ~/worktrees/chinaword-hsk-reading && npm ci
```

Expected: `npm ci`가 끝나고 `git branch --show-current`가 `claude/hsk-reading-tab`.

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`tools/reading/test_hsktext.py`:

```python
import unittest

from hsktext import check_words, join_words, tidy, toneless, words_to_pinyin


class TidyTest(unittest.TestCase):
    def test_removes_spaces_next_to_hanzi_and_punctuation(self):
        self.assertEqual(tidy('今天是 9 月 10 日，教师（ ） ！'), '今天是9月10日，教师（）！')

    def test_joins_numbers_with_units(self):
        self.assertEqual(tidy('写着 1.21 元，前面的 1 表示元'), '写着1.21元，前面的1表示元')

    def test_keeps_single_space_between_latin(self):
        self.assertEqual(tidy('A   8 点'), 'A 8点')


class TonelessTest(unittest.TestCase):
    def test_strips_tones_and_writes_u_umlaut_as_v(self):
        self.assertEqual(toneless('lǜsè'), 'lvse')
        self.assertEqual(toneless('Mǎnyì'), 'manyi')


class CheckWordsTest(unittest.TestCase):
    def test_reports_mismatch_with_source(self):
        problems, diffs = [], []
        check_words([['我', 'wǒ'], ['很', 'hěn']], '我很好', 'T', problems, diffs)
        self.assertEqual(len(problems), 1)
        self.assertIn('원문과 다름', problems[0])

    def test_reports_missing_pinyin_and_pinyin_on_punctuation(self):
        problems, diffs = [], []
        check_words([['满意', ''], ['。', 'x']], '满意。', 'T', problems, diffs)
        self.assertEqual(len(problems), 2)

    def test_lists_reading_differences_without_failing(self):
        problems, diffs = [], []
        check_words([['满意', 'mǎnyì'], ['还', 'huán']], '满意还', 'T', problems, diffs)
        self.assertEqual(problems, [])
        self.assertEqual(len(diffs), 1)


class WordsTest(unittest.TestCase):
    def test_join_words(self):
        self.assertEqual(join_words([['我', 'wǒ'], ['。', '']]), '我。')

    def test_words_to_pinyin_builds_sentence(self):
        words = [['我', 'wǒ'], ['对', 'duì'], ['这儿', 'zhèr'], ['很', 'hěn'], ['满意', 'mǎnyì'], ['。', '']]
        self.assertEqual(words_to_pinyin(words), 'Wǒ duì zhèr hěn mǎnyì.')


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 3: 실패를 확인한다**

Run: `cd $W && $PY -m unittest discover -s tools/reading -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'hsktext'`

- [ ] **Step 4: 구현한다**

`tools/reading/hsktext.py`:

```python
"""독해 도구가 같이 쓰는 글자 처리. tools/listening/의 같은 함수를 옮겨 왔다
(듣기 도구는 완성된 일회성 스크립트라 그대로 두고, 듣기 해설을 보강할 때 합친다)."""
import re
import unicodedata

from pypinyin import Style, lazy_pinyin

CJK = r'[一-鿿，。！？：；、“”‘’（）《》…—]'
DIGIT_READINGS = set('0123456789')
PUNCT_PINYIN = {'，': ',', '、': ',', '。': '.', '？': '?', '！': '!', '：': ':', '；': ';', '“': '"', '”': '"'}


def tidy(text):
    """pdftotext가 한자·문장부호 옆에 넣은 공백을 걷어낸다 ('才 5 点' → '才5点')."""
    text = re.sub(rf'(?<={CJK})\s+|\s+(?={CJK})', '', text.strip())
    return re.sub(r'\s{2,}', ' ', text)


def toneless(pinyin):
    text = re.sub('[üǖǘǚǜ]', 'v', pinyin.lower())  # 성조 부호를 지우기 전에 ü를 v로 (pypinyin 표기)
    text = unicodedata.normalize('NFD', text)
    text = ''.join(ch for ch in text if unicodedata.category(ch) != 'Mn')
    return re.sub(r'[^a-z]', '', text)


def join_words(words):
    return ''.join(token for token, _ in words)


def check_words(words, source, where, problems, reading_diffs):
    """한자를 이으면 원문과 같은지(problems), pypinyin과 음절이 다른지(reading_diffs) 본다."""
    joined = join_words(words)
    if joined != source:
        problems.append(f'{where}: 한자 이어 붙이기가 원문과 다름\n    원문 {source}\n    결과 {joined}')
    for token, pinyin in words:
        hanzi = re.sub(r'[^一-鿿]', '', token)
        if not hanzi:
            if pinyin and not set(token) & DIGIT_READINGS:
                problems.append(f'{where}: 문장부호 "{token}"에 병음 "{pinyin}"')
            continue
        if not pinyin:
            problems.append(f'{where}: "{token}" 병음 없음')
            continue
        if hanzi != token:
            continue  # 숫자·기호가 섞인 토큰은 읽기를 사람이 정했다
        expected = ''.join(lazy_pinyin(token, style=Style.NORMAL))
        accepted = {expected}
        if len(token) > 1 and token.endswith('儿') and expected.endswith('er'):
            accepted.add(expected[:-2] + 'r')  # 儿화: pypinyin은 'zheer', 해설은 'zhèr'
        if toneless(pinyin) not in accepted:
            reading_diffs.append(f'{where}: {token} {pinyin} (pypinyin: {"".join(lazy_pinyin(token, style=Style.TONE))})')


def words_to_pinyin(words):
    """[['你','nǐ'],['，','']] → 'Nǐ,' 처럼 단어장 예문 병음 한 줄로 만든다."""
    out = ''
    for token, pinyin in words:
        if pinyin:
            out += (' ' if out and not out.endswith('"') else '') + pinyin
        elif token in PUNCT_PINYIN:
            out += PUNCT_PINYIN[token]
    return out[:1].upper() + out[1:]
```

- [ ] **Step 5: 통과를 확인한다**

Run: `cd $W && $PY -m unittest discover -s tools/reading -v`
Expected: 9개 모두 OK

- [ ] **Step 6: 커밋한다**

```bash
cd $W && git add tools/reading/hsktext.py tools/reading/test_hsktext.py
git commit -m "Add text helpers for reading tools

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: 시험지에서 독해 문항 뽑기 `paper.py`

**Files:**
- Create: `tools/reading/paper.py`
- Test: `tools/reading/test_paper.py`

**Interfaces:**
- Consumes: `tidy` (Task 1)
- Produces: `raw_lines(pdf) -> list[str]`, `reading_section(lines) -> list[str]`, `parse_reading(section) -> {'groups': [...], 'items': [...]}`, `parse_answers(lines) -> {no: label}`, `check_paper(paper) -> list[str]`. 결과 파일 `$WORK/<회차>/paper.json`:

```json
{ "id": "H31001",
  "groups": [{ "id": "41-45", "part": 1, "options": [{ "label": "A", "text": "太好了！需要我帮忙吗？" }], "example": "E" }],
  "items": [
    { "no": 41, "part": 1, "group": "41-45", "lines": [{ "speaker": null, "text": "我的作业早就完成了。" }], "question": null, "options": null, "answer": "C" },
    { "no": 56, "part": 2, "group": "56-60", "lines": [{ "speaker": "A", "text": "请问，现在是十一点吗？" }, { "speaker": "B", "text": "现在十一点十五了，您的表慢了一（）。" }], "question": null, "options": null, "answer": "A" },
    { "no": 63, "part": 3, "group": null, "lines": [{ "speaker": null, "text": "我对这儿很满意，…" }], "question": "使他觉得满意的是：", "options": [{ "label": "A", "text": "没有花园" }], "answer": "C" } ] }
```

`-layout` 추출은 몇 문항에서 줄 순서가 꼬인다(H31002 67번·H31003 65번은 지문 첫 줄이 번호 위로, H31004 55·60번은 빈칸 괄호가 다른 줄로). `-raw`는 내용 순서대로 나오므로 이것을 쓴다. 대신 쪽 번호(`H31001 - 7`)가 줄 끝에 붙어 나와 지운다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tools/reading/test_paper.py`:

```python
import unittest
from pathlib import Path

from paper import check_paper, parse_answers, parse_reading, raw_lines, reading_section

PDF_DIR = Path.home() / 'hsk-listening-work' / 'src'
TEST_IDS = ['H31001', 'H31002', 'H31003', 'H31004', 'H31005']
H31001_ANSWERS = dict(zip(range(41, 71), 'CBADFBDEACFDCBAABEFCAACBBAABBC'))

FIXTURE = '''第 一 部 分
第 41-45 题
A 太好了！需要我帮忙吗？
B 今天把我饿坏了，还有什么吃的吗？
例如：你知道怎么去那儿吗？ （ B ）
41．我的作业早就完成了。 （ ）
第 二 部 分
第 56-60 题
A 刻 B 一直 C 节 D 爱好 E 被 F 打扫
例如：A：你有什么（ D ）？
B：我喜欢体育。
56．A：请问，现在是十一点吗？
B：现在十一点十五了，您的表慢了一（ ） 。
第 三 部 分
第 61-70 题
例如：您是来参加今天会议的吗？您来早了一点儿，现在才八点半。您先进来
坐吧。
★ 会议最可能几点开始？
A 8 点 B 8 点半 C 9 点 √
63．我对这儿很满意，虽然没有花园，但是离河边很近，
还有鸟。
★ 使他觉得满意的是：
A 没有花园 B 房间很大 C 离河很近'''.splitlines()


class ParseReadingFixtureTest(unittest.TestCase):
    def setUp(self):
        paper = parse_reading(FIXTURE)
        self.items = {item['no']: item for item in paper['items']}
        self.groups = {group['id']: group for group in paper['groups']}

    def test_only_items_are_collected(self):
        self.assertEqual(sorted(self.items), [41, 56, 63])
        self.assertEqual(sorted(self.groups), ['41-45', '56-60'])

    def test_part1_group_options_and_example(self):
        group = self.groups['41-45']
        self.assertEqual([o['label'] for o in group['options']], ['A', 'B'])
        self.assertEqual(group['options'][1]['text'], '今天把我饿坏了，还有什么吃的吗？')
        self.assertEqual(group['example'], 'B')

    def test_part1_item_drops_answer_brackets(self):
        self.assertEqual(self.items[41]['lines'], [{'speaker': None, 'text': '我的作业早就完成了。'}])
        self.assertEqual(self.items[41]['group'], '41-45')

    def test_part2_word_bank_and_dialogue_blank(self):
        group = self.groups['56-60']
        self.assertEqual([o['text'] for o in group['options']], ['刻', '一直', '节', '爱好', '被', '打扫'])
        self.assertEqual(group['example'], 'D')
        self.assertEqual(self.items[56]['lines'], [
            {'speaker': 'A', 'text': '请问，现在是十一点吗？'},
            {'speaker': 'B', 'text': '现在十一点十五了，您的表慢了一（）。'},
        ])

    def test_part3_skips_example_and_joins_passage(self):
        item = self.items[63]
        self.assertEqual(item['lines'], [{'speaker': None, 'text': '我对这儿很满意，虽然没有花园，但是离河边很近，还有鸟。'}])
        self.assertEqual(item['question'], '使他觉得满意的是：')
        self.assertEqual([o['text'] for o in item['options']], ['没有花园', '房间很大', '离河很近'])
        self.assertIsNone(item['group'])


@unittest.skipUnless((PDF_DIR / 'H31001.pdf').exists(), '시험지 PDF 없음 (~/hsk-listening-work/src)')
class RealPaperTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.papers = {}
        for test_id in TEST_IDS:
            lines = raw_lines(PDF_DIR / f'{test_id}.pdf')
            paper = parse_reading(reading_section(lines))
            answers = parse_answers(lines)
            for item in paper['items']:
                item['answer'] = answers.get(item['no'])
            cls.papers[test_id] = paper

    def item(self, test_id, no):
        return next(item for item in self.papers[test_id]['items'] if item['no'] == no)

    def test_all_papers_pass_checks(self):
        for test_id, paper in self.papers.items():
            with self.subTest(test_id):
                self.assertEqual(check_paper(paper), [])

    def test_h31001_answers_match_answer_key(self):
        got = {item['no']: item['answer'] for item in self.papers['H31001']['items']}
        self.assertEqual(got, H31001_ANSWERS)

    def test_blank_bracket_on_its_own_line_h31004_55(self):
        self.assertEqual(self.item('H31004', 55)['lines'], [{'speaker': None, 'text': '（）更好地解决问题，必须提高自己的水平。'}])

    def test_blank_at_start_of_b_line_h31004_60(self):
        self.assertEqual(self.item('H31004', 60)['lines'][1], {'speaker': 'B', 'text': '（）我只想听听那些老歌。'})

    def test_passage_first_line_above_number_h31002_67(self):
        text = self.item('H31002', 67)['lines'][0]['text']
        self.assertTrue(text.startswith('“再见”是一个很有意思的词语。“再见”表示'), text)

    def test_quote_spacing_h31003_65(self):
        text = self.item('H31003', 65)['lines'][0]['text']
        self.assertTrue(text.startswith('“6月的天，孩子的脸，说变就变。”刚才还是大晴天'), text)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd $W && $PY -m unittest discover -s tools/reading -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'paper'`

- [ ] **Step 3: 구현한다**

`tools/reading/paper.py`:

```python
#!/usr/bin/env python3
"""HSK 3급 시험지 PDF에서 독해 41~70번(묶음 보기·문항·정답)을 뽑는다.

사용: paper.py H31001 --pdf ~/hsk-listening-work/src/H31001.pdf --work ~/hsk-reading-work
결과: <work>/<회차>/paper.json

-layout 추출은 몇 문항에서 줄 순서가 꼬여서(지문 첫 줄이 번호 위로, 빈칸 괄호가 다른 줄로)
내용 순서대로 나오는 -raw를 쓴다. 대신 쪽 번호가 줄 끝에 붙어 나와 지운다.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

from hsktext import tidy

FOOTER = re.compile(r'\s*H3\d{4}\s*-\s*\d+\s*$')
PART = re.compile(r'^第\s*([一二三])\s*部\s*分$')
GROUP = re.compile(r'^第\s*(\d+)\s*-\s*(\d+)\s*题$')
ITEM = re.compile(r'^(\d{2})．\s*(.*)$')
OPTION_LINE = re.compile(r'^([A-F])\s+(.+)$')
BANK_WORD = re.compile(r'([A-F])\s+(\S+)')
EXAMPLE_LABEL = re.compile(r'（\s*([A-F])\s*）')
SPEAKER = re.compile(r'^([AB])：\s*(.*)$')
CHOICES = re.compile(r'^A\s+(.+?)\s+B\s+(.+?)\s+C\s+(.+?)\s*√?\s*$')
TRAILING_BRACKETS = re.compile(r'（）$')
PART_NUMBERS = {'一': 1, '二': 2, '三': 3}


def raw_lines(pdf):
    out = subprocess.run(['pdftotext', '-raw', str(pdf), '-'], capture_output=True, text=True, check=True).stdout
    return [FOOTER.sub('', line.replace('\f', '')).strip() for line in out.splitlines()]


def squash(line):
    return re.sub(r'\s', '', line)


def reading_section(lines):
    """시험지의 '二、阅读' 다음 줄부터 '三、书写' 앞까지 (빈 줄 제외)."""
    start = next(i for i, line in enumerate(lines) if squash(line) == '二、阅读')
    end = next(i for i in range(start + 1, len(lines)) if squash(lines[i]) == '三、书写')
    return [line for line in lines[start + 1:end] if line]


def add_text(item, line):
    """문항 번호 줄 뒤에 이어지는 글을 부분별 규칙으로 붙인다."""
    if item['part'] == 3:
        if line.startswith('★'):
            item['question'] = line.lstrip('★').strip()
        elif item['question'] is not None:
            choices = CHOICES.match(line)
            if choices and item['options'] is None:
                item['options'] = [{'label': label, 'text': text} for label, text in zip('ABC', choices.groups())]
            elif item['options'] is None:
                item['question'] += line  # 질문이 두 줄로 넘어간 경우
        elif item['lines']:
            item['lines'][0]['text'] += line
        else:
            item['lines'].append({'speaker': None, 'text': line})
        return

    speaker = SPEAKER.match(line) if item['part'] == 2 else None
    if speaker:
        item['lines'].append({'speaker': speaker.group(1), 'text': speaker.group(2)})
    elif item['lines']:
        item['lines'][-1]['text'] += line
    else:
        item['lines'].append({'speaker': None, 'text': line})


def finish(item):
    for line in item['lines']:
        text = tidy(line['text'])
        if item['part'] == 1:
            text = TRAILING_BRACKETS.sub('', text)  # 답 쓰는 칸 '（ ）'
        line['text'] = text
    if item['question']:
        item['question'] = tidy(item['question'])
    for option in item['options'] or []:
        option['text'] = tidy(option['text'])


def parse_reading(section):
    """독해 구간 줄들을 묶음(1·2부분 보기)과 문항으로 나눈다. 예시(例如)는 보기 이름만 남기고 버린다."""
    part, group, item, in_example = 0, None, None, False
    groups, items = [], []
    for line in section:
        heading = PART.match(line)
        if heading:
            part, group, item, in_example = PART_NUMBERS[heading.group(1)], None, None, False
            continue
        header = GROUP.match(line)
        if header:
            group = {'id': f'{header.group(1)}-{header.group(2)}', 'part': part, 'options': [], 'example': None}
            if part in (1, 2):
                groups.append(group)
            item, in_example = None, False
            continue
        if line.startswith('例如：'):
            in_example = True
            label = EXAMPLE_LABEL.search(line)
            if part in (1, 2) and label:
                group['example'] = label.group(1)
            continue
        start = ITEM.match(line)
        if start:
            in_example = False
            item = {
                'no': int(start.group(1)),
                'part': part,
                'group': group['id'] if part in (1, 2) else None,
                'lines': [],
                'question': None,
                'options': None,
            }
            items.append(item)
            line = start.group(2)
        elif in_example:
            continue
        elif item is None:
            option = OPTION_LINE.match(line)
            if part == 1 and option:
                group['options'].append({'label': option.group(1), 'text': option.group(2)})
            elif part == 2 and line.startswith('A '):
                group['options'] = [{'label': label, 'text': text} for label, text in BANK_WORD.findall(line)]
            continue
        if line:
            add_text(item, line)

    for item in items:
        finish(item)
    for group in groups:
        for option in group['options']:
            option['text'] = tidy(option['text'])
    return {'groups': groups, 'items': items}


def parse_answers(lines):
    """'卷答案' 아래 정답표에서 41~70번만."""
    start = next(i for i, line in enumerate(lines) if '卷答案' in line)
    pairs = re.findall(r'(\d{2})．\s*([A-F])', '\n'.join(lines[start:]))
    return {int(no): answer for no, answer in pairs if 41 <= int(no) <= 70}


def check_paper(paper):
    problems = []
    items = paper['items']
    groups = {group['id']: group for group in paper['groups']}
    numbers = [item['no'] for item in items]
    if numbers != list(range(41, 71)):
        problems.append(f'문항 번호가 41~70이 아님: {numbers}')

    for group_id, group in groups.items():
        labels = [option['label'] for option in group['options']]
        if len(labels) < 5 or labels != list('ABCDEF'[:len(labels)]):
            problems.append(f'{group_id} 묶음 보기 이상: {labels}')
        if group['part'] == 2 and len(labels) != 6:
            problems.append(f'{group_id} 단어 보기가 6개가 아님')
        answers = [item.get('answer') for item in items if item['group'] == group_id]
        if len(set(answers)) != len(answers):
            problems.append(f'{group_id} 정답이 겹침: {answers}')

    for item in items:
        where = f'{item["no"]}번'
        answer = item.get('answer')
        if not answer:
            problems.append(f'{where} 정답 없음')
            continue
        if not item['lines'] or not all(line['text'] for line in item['lines']):
            problems.append(f'{where} 문장 없음')
        if item['part'] in (1, 2):
            group = groups.get(item['group'])
            if not group:
                problems.append(f'{where} 묶음 없음')
                continue
            if answer not in [option['label'] for option in group['options']]:
                problems.append(f'{where} 정답 {answer}가 묶음 보기에 없음')
            if answer == group['example']:
                problems.append(f'{where} 정답이 예시 보기')
        if item['part'] == 2:
            blanks = sum(line['text'].count('（）') for line in item['lines'])
            if blanks != 1:
                problems.append(f'{where} 빈칸이 {blanks}개')
        if item['part'] == 3:
            if not item['question']:
                problems.append(f'{where} ★ 질문 없음')
            if [option['label'] for option in item['options'] or []] != ['A', 'B', 'C']:
                problems.append(f'{where} 보기가 A·B·C가 아님')
    return problems


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('test_id')
    parser.add_argument('--pdf', required=True)
    parser.add_argument('--work', required=True)
    args = parser.parse_args()

    lines = raw_lines(Path(args.pdf).expanduser())
    parsed = parse_reading(reading_section(lines))
    answers = parse_answers(lines)
    for item in parsed['items']:
        item['answer'] = answers.get(item['no'])
    paper = {'id': args.test_id, **parsed}
    problems = check_paper(paper)

    out_dir = Path(args.work).expanduser() / args.test_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'paper.json').write_text(json.dumps(paper, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{args.test_id}: 묶음 {len(paper["groups"])}개, 문항 {len(paper["items"])}개')
    for problem in problems:
        print('  ! ' + problem)
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd $W && $PY -m unittest discover -s tools/reading -v`
Expected: 모두 OK (RealPaperTest 6개 포함, skip 없음)

실패하면 해당 회차를 `pdftotext -raw ~/hsk-listening-work/src/<회차>.pdf - | awk '/二、阅/{c++} c==1 && /三、书/{exit} c==1'`로 보고 규칙을 고친다. 테스트 기대값을 바꾸지 않는다.

- [ ] **Step 5: 다섯 회차 paper.json을 만든다**

```bash
cd $W && for t in H31001 H31002 H31003 H31004 H31005; do
  $PY tools/reading/paper.py $t --pdf ~/hsk-listening-work/src/$t.pdf --work $WORK || break
done
```

Expected: 회차마다 `묶음 4개, 문항 30개`, `!` 줄 없음.

- [ ] **Step 6: 커밋한다**

```bash
cd $W && git add tools/reading/paper.py tools/reading/test_paper.py
git commit -m "Extract HSK3 reading items from mock test PDFs

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: 해설과 합치고 검사하는 `assemble.py`, 해설 쓰기 규칙 README

**Files:**
- Create: `tools/reading/assemble.py`
- Create: `tools/reading/README.md`
- Test: `tools/reading/test_assemble.py`

**Interfaces:**
- Consumes: `paper.json` (Task 2), `check_words`, `join_words`, `words_to_pinyin` (Task 1)
- Produces:
  - 해설 파일 `$WORK/<회차>/enrich-41-50.json`, `enrich-51-60.json`, `enrich-61-70.json` 형식(README에 정의). `load_enrich(base)`가 `enrich-*.json`을 모두 합친다.
  - `build_test(test_id, work, problems, reading_diffs) -> dict` — 앱이 읽는 회차 데이터:
    `{ id, title, parts: [{part, guide}], groups: [{id, part, options: [{label, words, ko}], example}], items: [{no, part, group, answer, lines: [{speaker, words, ko, blank?}], question: {words, ko}|null, options: [{label, words, ko}]|null, pair: 'item-first'|'option-first'|null, explain}] }`
    `explain = { basis: {quote, note}, distractors: [{label, note}], breakdown: [{chunks: [{text, role}], note}], vocab: [{hanzi, pinyin, partOfSpeech, meaningKo, usage, example: {zh, words, ko}}], grammar: [{pattern, meaningKo, note, example: {zh, words, ko}}] }`
  - `update_vocab(tests, repo) -> int` — `src/data/vocab.json`에 «HSK3 독해» 단원.
  - CLI: `assemble.py <회차…> --work $WORK --repo . [--check] [--show-readings]`. `--check`는 검사만 하고 아무 파일도 쓰지 않는다(여러 에이전트가 동시에 써도 안전).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tools/reading/test_assemble.py`:

```python
import copy
import json
import tempfile
import unittest
from pathlib import Path

from assemble import LESSON, build_test, update_vocab


def ex(words, ko):
    return {'zh': ''.join(token for token, _ in words), 'words': words, 'ko': ko}


EXAMPLE = ex([['这', 'zhè'], ['把', 'bǎ'], ['椅子', 'yǐzi'], ['很', 'hěn'], ['舒服', 'shūfu'], ['。', '']], '이 의자는 아주 편하다.')
GRAMMAR = {'pattern': '很不 + 형용사', 'meaningKo': '아주 ~하지 않다', 'note': '很 뒤에 不를 붙여 정도를 부정한다.', 'example': EXAMPLE}


def word(hanzi, pinyin, pos, ko):
    return {'hanzi': hanzi, 'pinyin': pinyin, 'partOfSpeech': pos, 'meaningKo': ko, 'usage': f'{hanzi} 용법', 'example': EXAMPLE}


PAPER = {
    'id': 'T1',
    'groups': [{'id': '51-55', 'part': 2, 'example': 'E', 'options': [
        {'label': label, 'text': text} for label, text in zip('ABCDEF', ['其实', '感冒', '附近', '舒服', '声音', '把'])]}],
    'items': [
        {'no': 51, 'part': 2, 'group': '51-55', 'answer': 'D', 'question': None, 'options': None,
         'lines': [{'speaker': None, 'text': '坐着很不（）。'}]},
        {'no': 61, 'part': 3, 'group': None, 'answer': 'A', 'question': '他觉得怎么样？',
         'lines': [{'speaker': None, 'text': '我对这儿很满意。房间很大。'}],
         'options': [{'label': 'A', 'text': '满意'}, {'label': 'B', 'text': '不满意'}, {'label': 'C', 'text': '很累'}]},
    ],
}

ENRICH_51_60 = {
    'groups': [{'id': '51-55', 'options': [
        {'label': label, 'words': [[text, pinyin]], 'ko': ko}
        for label, text, pinyin, ko in [
            ('A', '其实', 'qíshí', '사실은'), ('B', '感冒', 'gǎnmào', '감기'), ('C', '附近', 'fùjìn', '근처'),
            ('D', '舒服', 'shūfu', '편안하다'), ('E', '声音', 'shēngyīn', '소리'), ('F', '把', 'bǎ', '~을')]]}],
    'items': [{
        'no': 51, 'question': None, 'options': None, 'pair': None,
        'lines': [{'words': [['坐着', 'zuòzhe'], ['很', 'hěn'], ['不', 'bù'], ['舒服', 'shūfu'], ['。', '']],
                   'ko': '앉아 있으면 아주 불편하다.', 'blank': 3}],
        'explain': {
            'basis': {'quote': '很不舒服', 'note': '很不 뒤에는 형용사가 온다.'},
            'distractors': [{'label': 'B', 'note': '感冒는 형용사가 아니다.'}],
            'breakdown': [{'chunks': [{'text': '坐着', 'role': '부사어'}, {'text': '很不舒服', 'role': '술어'}],
                           'note': '앉아 있는 상태 + 불편하다'}],
            'vocab': [word('舒服', 'shūfu', '형용사', '편안하다'), word('坐', 'zuò', '동사', '앉다'), word('低', 'dī', '형용사', '낮다')],
            'grammar': [GRAMMAR],
        },
    }],
}

ENRICH_61_70 = {
    'items': [{
        'no': 61, 'pair': None,
        'lines': [
            {'words': [['我', 'wǒ'], ['对', 'duì'], ['这儿', 'zhèr'], ['很', 'hěn'], ['满意', 'mǎnyì'], ['。', '']], 'ko': '나는 여기가 아주 마음에 든다.'},
            {'words': [['房间', 'fángjiān'], ['很', 'hěn'], ['大', 'dà'], ['。', '']], 'ko': '방이 크다.'},
        ],
        'question': {'words': [['他', 'tā'], ['觉得', 'juéde'], ['怎么样', 'zěnmeyàng'], ['？', '']], 'ko': '그는 어떻게 느끼는가?'},
        'options': [
            {'label': 'A', 'words': [['满意', 'mǎnyì']], 'ko': '만족한다'},
            {'label': 'B', 'words': [['不', 'bù'], ['满意', 'mǎnyì']], 'ko': '만족하지 않는다'},
            {'label': 'C', 'words': [['很', 'hěn'], ['累', 'lèi']], 'ko': '피곤하다'},
        ],
        'explain': {
            'basis': {'quote': '我对这儿很满意', 'note': '첫 문장이 바로 답이다.'},
            'distractors': [{'label': 'B', 'note': '반대 내용'}, {'label': 'C', 'note': '지문에 없음'}],
            'breakdown': [{'chunks': [{'text': '我', 'role': '주어'}, {'text': '对这儿', 'role': '부사어'}, {'text': '很满意', 'role': '술어'}],
                           'note': '对 + 대상 + 满意'}],
            'vocab': [word('满意', 'mǎnyì', '형용사', '만족하다'), word('房间', 'fángjiān', '명사', '방'), word('对', 'duì', '개사', '~에 대해')],
            'grammar': [GRAMMAR],
        },
    }],
}


class AssembleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.work = Path(self.tmp.name)
        self.write(PAPER, ENRICH_51_60, ENRICH_61_70)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, paper, enrich_51, enrich_61):
        base = self.work / 'T1'
        base.mkdir(exist_ok=True)
        (base / 'paper.json').write_text(json.dumps(paper, ensure_ascii=False), encoding='utf-8')
        (base / 'enrich-51-60.json').write_text(json.dumps(enrich_51, ensure_ascii=False), encoding='utf-8')
        (base / 'enrich-61-70.json').write_text(json.dumps(enrich_61, ensure_ascii=False), encoding='utf-8')

    def build(self):
        problems, diffs = [], []
        test = build_test('T1', self.work, problems, diffs)
        return test, problems

    def test_valid_files_merge_without_problems(self):
        test, problems = self.build()
        self.assertEqual(problems, [])
        self.assertEqual([item['no'] for item in test['items']], [51, 61])
        self.assertEqual(test['groups'][0]['example'], 'E')
        self.assertEqual(test['items'][0]['lines'][0]['blank'], 3)
        self.assertEqual(test['items'][1]['question']['ko'], '그는 어떻게 느끼는가?')
        self.assertEqual(test['parts'][1], {'part': 2, 'guide': '빈칸에 알맞은 단어 고르기'})

    def test_blank_word_must_be_the_answer_word(self):
        broken = copy.deepcopy(ENRICH_51_60)
        broken['items'][0]['lines'][0]['words'][3] = ['附近', 'fùjìn']
        self.write(PAPER, broken, ENRICH_61_70)
        _, problems = self.build()
        self.assertTrue(any('빈칸 단어' in p for p in problems), problems)

    def test_passage_sentences_must_join_to_source(self):
        broken = copy.deepcopy(ENRICH_61_70)
        broken['items'][0]['lines'].pop()
        self.write(PAPER, ENRICH_51_60, broken)
        _, problems = self.build()
        self.assertTrue(any('지문' in p and '원문과 다름' in p for p in problems), problems)

    def test_distractor_cannot_be_the_answer(self):
        broken = copy.deepcopy(ENRICH_61_70)
        broken['items'][0]['explain']['distractors'][0]['label'] = 'A'
        self.write(PAPER, ENRICH_51_60, broken)
        _, problems = self.build()
        self.assertTrue(any('오답 이유' in p for p in problems), problems)

    def test_breakdown_must_come_from_the_item(self):
        broken = copy.deepcopy(ENRICH_51_60)
        broken['items'][0]['explain']['breakdown'][0]['chunks'][0]['text'] = '站着'
        self.write(PAPER, broken, ENRICH_61_70)
        _, problems = self.build()
        self.assertTrue(any('끊어 읽기' in p for p in problems), problems)

    def test_vocab_needs_an_example(self):
        broken = copy.deepcopy(ENRICH_61_70)
        del broken['items'][0]['explain']['vocab'][0]['example']
        self.write(PAPER, ENRICH_51_60, broken)
        _, problems = self.build()
        self.assertTrue(any('예문' in p for p in problems), problems)

    def test_update_vocab_skips_known_words_and_is_idempotent(self):
        test, problems = self.build()
        self.assertEqual(problems, [])
        repo = self.work / 'repo'
        (repo / 'src' / 'data').mkdir(parents=True)
        vocab_path = repo / 'src' / 'data' / 'vocab.json'
        vocab_path.write_text(json.dumps([{'id': 'K1', 'lesson': 'HSK3 추가 300', 'hanzi': '舒服'}], ensure_ascii=False), encoding='utf-8')

        added = update_vocab([test], repo)
        first = vocab_path.read_text(encoding='utf-8')
        self.assertEqual(added, 5)
        entries = {entry['hanzi']: entry for entry in json.loads(first) if entry.get('lesson') == LESSON}
        self.assertEqual(sorted(entries), sorted(['坐', '低', '满意', '房间', '对']))
        self.assertEqual(entries['坐']['exampleZh'], '坐着很不舒服。')  # 시험 문장(빈칸 채움)
        self.assertEqual(entries['低']['exampleZh'], '这把椅子很舒服。')  # 시험 문장에 없으면 해설 예문
        self.assertEqual(entries['坐']['source'], 'HSK3 공식 모의고사 T1 독해 51번')

        update_vocab([test], repo)
        self.assertEqual(vocab_path.read_text(encoding='utf-8'), first)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd $W && $PY -m unittest discover -s tools/reading -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'assemble'`

- [ ] **Step 3: 구현한다**

`tools/reading/assemble.py`:

```python
#!/usr/bin/env python3
"""paper.json(원문·정답) + enrich-*.json(병음·해석·해설)을 합쳐 앱이 읽는
public/reading/<회차>.json을 만들고, 독해 핵심 단어를 단어장(vocab.json)에 넣는다.

  assemble.py H31001 H31002 ... --work ~/hsk-reading-work --repo .
  assemble.py H31001 --work ~/hsk-reading-work --repo . --check   # 검사만, 파일을 쓰지 않음

쓰기 전에 해설을 기계적으로 검사한다. 단어 묶음의 한자를 이으면 원문과 같아야 하고(2부분은 빈칸 단어를
'（）'로 바꾼 결과), 해설 칸이 기준 개수대로 차 있어야 한다. pypinyin과 음절이 다른 단어는 목록으로만 보여준다.
"""
import argparse
import json
from pathlib import Path

from hsktext import check_words, join_words, words_to_pinyin

LESSON = 'HSK3 독해'
PART_GUIDES = {
    1: '서로 이어지는 문장 짝 찾기',
    2: '빈칸에 알맞은 단어 고르기',
    3: '짧은 글을 읽고 질문에 답하기',
}
ROLES = {'주어', '술어', '목적어', '관형어', '부사어', '보어', '접속사', '개사구'}
BLANK = '（）'


def load_enrich(base):
    groups, items = {}, {}
    for path in sorted(base.glob('enrich-*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        for group in data.get('groups', []):
            groups[group['id']] = group
        for item in data.get('items', []):
            items[item['no']] = item
    return groups, items


def check_annotated(annotated, source_text, where, problems, reading_diffs):
    check_words(annotated.get('words') or [], source_text, where, problems, reading_diffs)
    if not (annotated.get('ko') or '').strip():
        problems.append(f'{where}: 해석 없음')


def check_example(example, where, problems, reading_diffs):
    if not example or not example.get('zh') or not example.get('words') or not example.get('ko'):
        problems.append(f'{where}: 예문(zh·words·ko) 없음')
        return
    check_words(example['words'], example['zh'], where, problems, reading_diffs)


def build_groups(paper_groups, notes, test_id, problems, reading_diffs):
    groups = []
    for group in paper_groups:
        note = notes.get(group['id'])
        if not note:
            problems.append(f'{test_id} {group["id"]}: 묶음 해설 없음')
            continue
        annotated = {option['label']: option for option in note.get('options', [])}
        options = []
        for option in group['options']:
            where = f'{test_id} {group["id"]} 보기 {option["label"]}'
            entry = annotated.get(option['label']) or {}
            check_annotated(entry, option['text'], where, problems, reading_diffs)
            options.append({'label': option['label'], 'words': entry.get('words') or [], 'ko': entry.get('ko', '')})
        groups.append({'id': group['id'], 'part': group['part'], 'options': options, 'example': group['example']})
    return groups


def build_lines(source, note, paper_group, where, problems, reading_diffs):
    annotated = note.get('lines') or []
    if source['part'] == 3:
        passage = source['lines'][0]['text']
        joined = ''.join(join_words(line.get('words') or []) for line in annotated)
        if joined != passage:
            problems.append(f'{where} 지문: 문장을 이으면 원문과 다름\n    원문 {passage}\n    결과 {joined}')
        for index, line in enumerate(annotated):
            words = line.get('words') or []
            check_annotated(line, join_words(words), f'{where} 지문 {index + 1}문장', problems, reading_diffs)
        return [{'speaker': None, 'words': line.get('words') or [], 'ko': line.get('ko', '')} for line in annotated]

    if len(annotated) != len(source['lines']):
        problems.append(f'{where}: 줄 수가 다름 ({len(source["lines"])} vs {len(annotated)})')
        return []
    lines, blanks = [], 0
    for index, (line, entry) in enumerate(zip(source['lines'], annotated)):
        here = f'{where} {index + 1}줄'
        words = entry.get('words') or []
        blank = entry.get('blank')
        if blank is None:
            check_annotated(entry, line['text'], here, problems, reading_diffs)
        else:
            blanks += 1
            if not isinstance(blank, int) or not 0 <= blank < len(words):
                problems.append(f'{here}: blank 위치가 단어 범위 밖 ({blank})')
                continue
            gapped = [w if i != blank else [BLANK, ''] for i, w in enumerate(words)]
            check_annotated({'words': gapped, 'ko': entry.get('ko')}, line['text'], here, problems, reading_diffs)
            check_words([words[blank]], words[blank][0], f'{here} 빈칸 단어', problems, reading_diffs)
            answer_word = None
            if paper_group:
                answer_word = next((o['text'] for o in paper_group['options'] if o['label'] == source['answer']), None)
            if words[blank][0] != answer_word:
                problems.append(f'{here}: 빈칸 단어 {words[blank][0]}가 정답 보기 {answer_word}와 다름')
        item_line = {'speaker': line['speaker'], 'words': words, 'ko': entry.get('ko', '')}
        if blank is not None:
            item_line['blank'] = blank
        lines.append(item_line)
    if source['part'] == 2 and blanks != 1:
        problems.append(f'{where}: 빈칸 표시(blank)가 {blanks}개')
    if source['part'] == 1 and blanks:
        problems.append(f'{where}: 1부분에는 빈칸이 없음')
    return lines


def check_explain(explain, part, answer, labels, texts, where, problems, reading_diffs):
    """labels: 고를 수 있는 보기 이름(예시 제외), texts: 그 문항 화면에 나오는 문장들(빈칸 채움)."""
    if not explain:
        problems.append(f'{where}: 해설(explain) 없음')
        return

    basis = explain.get('basis') or {}
    if not basis.get('quote') or not basis.get('note'):
        problems.append(f'{where}: 정답 근거(quote·note) 비었음')
    elif not any(basis['quote'] in text for text in texts):
        problems.append(f'{where}: 정답 근거 인용이 문항 글에 없음: {basis["quote"]}')

    distractors = explain.get('distractors') or []
    named = [d.get('label') for d in distractors]
    if any(label not in labels or label == answer for label in named) or any(not d.get('note') for d in distractors):
        problems.append(f'{where}: 오답 이유의 보기 이름·설명이 이상함 {named}')
    if part == 3 and sorted(named) != sorted(label for label in labels if label != answer):
        problems.append(f'{where}: 3부분 오답 이유는 나머지 두 보기 모두 {named}')
    if part in (1, 2) and not 1 <= len(distractors) <= 2:
        problems.append(f'{where}: 1·2부분 오답 이유는 1~2개 ({len(distractors)}개)')

    breakdown = explain.get('breakdown') or []
    if not 1 <= len(breakdown) <= 2:
        problems.append(f'{where}: 끊어 읽기는 1~2문장 ({len(breakdown)}개)')
    for sentence in breakdown:
        chunks = sentence.get('chunks') or []
        text = ''.join(chunk.get('text', '') for chunk in chunks)
        if not chunks or not any(text in t for t in texts):
            problems.append(f'{where}: 끊어 읽기 문장이 문항 글에 없음: {text}')
        roles = [chunk.get('role') for chunk in chunks if chunk.get('role') not in ROLES]
        if roles:
            problems.append(f'{where}: 끊어 읽기 성분 이름이 목록 밖 {roles}')
        if not sentence.get('note'):
            problems.append(f'{where}: 끊어 읽기 요약(note) 없음')

    vocab = explain.get('vocab') or []
    if not 3 <= len(vocab) <= 6:
        problems.append(f'{where}: 단어는 3~6개 ({len(vocab)}개)')
    for entry in vocab:
        here = f'{where} 단어 {entry.get("hanzi")}'
        missing = [key for key in ('hanzi', 'pinyin', 'partOfSpeech', 'meaningKo', 'usage') if not entry.get(key)]
        if missing:
            problems.append(f'{here}: {missing} 없음')
        if entry.get('hanzi') and entry.get('pinyin'):
            check_words([[entry['hanzi'], entry['pinyin']]], entry['hanzi'], here, problems, reading_diffs)
        check_example(entry.get('example'), f'{here} 예문', problems, reading_diffs)

    grammar = explain.get('grammar') or []
    if not 1 <= len(grammar) <= 3:
        problems.append(f'{where}: 문법은 1~3개 ({len(grammar)}개)')
    for entry in grammar:
        here = f'{where} 문법 {entry.get("pattern")}'
        missing = [key for key in ('pattern', 'meaningKo', 'note') if not entry.get(key)]
        if missing:
            problems.append(f'{here}: {missing} 없음')
        check_example(entry.get('example'), f'{here} 예문', problems, reading_diffs)


def build_item(source, note, paper_group, group_options, where, problems, reading_diffs):
    part, answer = source['part'], source['answer']
    lines = build_lines(source, note, paper_group, where, problems, reading_diffs)

    question, options = None, None
    if part == 3:
        annotated_question = note.get('question') or {}
        check_annotated(annotated_question, source['question'], f'{where} ★', problems, reading_diffs)
        question = {'words': annotated_question.get('words') or [], 'ko': annotated_question.get('ko', '')}
        annotated = {option['label']: option for option in note.get('options') or []}
        options = []
        for option in source['options']:
            entry = annotated.get(option['label']) or {}
            check_annotated(entry, option['text'], f'{where} 보기 {option["label"]}', problems, reading_diffs)
            options.append({'label': option['label'], 'words': entry.get('words') or [], 'ko': entry.get('ko', '')})

    pair = note.get('pair')
    if part == 1 and pair not in ('item-first', 'option-first'):
        problems.append(f'{where}: pair는 item-first 또는 option-first ({pair})')
    if part != 1:
        pair = None

    visible = options if part == 3 else group_options
    texts = [join_words(line['words']) for line in lines]
    texts += [join_words(question['words'])] if question else []
    texts += [join_words(option['words']) for option in visible]
    example = paper_group['example'] if paper_group else None
    labels = [option['label'] for option in visible if option['label'] != example]
    check_explain(note.get('explain'), part, answer, labels, texts, where, problems, reading_diffs)

    return {
        'no': source['no'],
        'part': part,
        'group': source['group'],
        'answer': answer,
        'lines': lines,
        'question': question,
        'options': options,
        'pair': pair,
        'explain': note.get('explain'),
    }


def build_test(test_id, work, problems, reading_diffs):
    base = work / test_id
    paper = json.loads((base / 'paper.json').read_text(encoding='utf-8'))
    group_notes, item_notes = load_enrich(base)
    groups = build_groups(paper['groups'], group_notes, test_id, problems, reading_diffs)
    options_by_group = {group['id']: group['options'] for group in groups}
    paper_groups = {group['id']: group for group in paper['groups']}

    items = []
    for source in paper['items']:
        where = f'{test_id} {source["no"]}번'
        note = item_notes.get(source['no'])
        if not note:
            problems.append(f'{where}: 해설 없음')
            continue
        items.append(build_item(source, note, paper_groups.get(source['group']),
                                options_by_group.get(source['group'], []), where, problems, reading_diffs))

    return {
        'id': test_id,
        'title': f'HSK 3급 {test_id}',
        'parts': [{'part': part, 'guide': guide} for part, guide in PART_GUIDES.items()],
        'groups': groups,
        'items': items,
    }


def example_for(word, item, group_options):
    """단어가 나온 시험 문장(빈칸 채움·질문·보기)을 예문으로, 없으면 해설 예문을 쓴다."""
    sentences = list(item['lines'])
    if item['question']:
        sentences.append(item['question'])
    sentences += item['options'] or []
    sentences += group_options
    for sentence in sentences:
        text = join_words(sentence['words'])
        if word['hanzi'] in text:
            return text, words_to_pinyin(sentence['words']), sentence['ko']
    example = word['example']
    return example['zh'], words_to_pinyin(example['words']), example['ko']


def update_vocab(tests, repo):
    path = repo / 'src' / 'data' / 'vocab.json'
    vocab = json.loads(path.read_text(encoding='utf-8'))
    # 다시 돌려도 같은 결과가 나오게 지난번에 넣은 독해 단어는 지우고 새로 넣는다.
    vocab = [entry for entry in vocab if entry.get('lesson') != LESSON]
    known = {entry['hanzi'] for entry in vocab}
    added = []
    for test in tests:
        options_by_group = {group['id']: group['options'] for group in test['groups']}
        for item in test['items']:
            for word in item['explain']['vocab']:
                if word['hanzi'] in known:
                    continue
                known.add(word['hanzi'])
                zh, py, ko = example_for(word, item, options_by_group.get(item['group'], []))
                added.append({
                    'id': f'HSK3R-{len(added) + 1:03d}',
                    'level': 'HSK3',
                    'lesson': LESSON,
                    'category': f'{LESSON} {test["id"]}',
                    'itemType': '단어',
                    'hanzi': word['hanzi'],
                    'pinyin': word['pinyin'],
                    'meaningKo': word['meaningKo'],
                    'partOfSpeech': word.get('partOfSpeech', ''),
                    'exampleZh': zh,
                    'examplePinyin': py,
                    'exampleKo': ko,
                    'source': f'HSK3 공식 모의고사 {test["id"]} 독해 {item["no"]}번',
                    'tags': ['HSK3', '단어', LESSON, test['id']],
                })
    path.write_text(json.dumps(vocab + added, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return len(added)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('test_ids', nargs='+')
    parser.add_argument('--work', required=True)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--check', action='store_true', help='검사만 하고 파일을 쓰지 않는다')
    parser.add_argument('--show-readings', action='store_true', help='pypinyin과 음절이 다른 단어를 모두 보여준다')
    args = parser.parse_args()
    work, repo = Path(args.work).expanduser(), Path(args.repo)

    problems, reading_diffs, tests = [], [], []
    for test_id in args.test_ids:
        tests.append(build_test(test_id, work, problems, reading_diffs))

    print(f'pypinyin과 음절이 다른 단어 {len(reading_diffs)}개 (다음자·변조는 맞을 수 있음)')
    if args.show_readings:
        for diff in reading_diffs:
            print('  ? ' + diff)
    if problems:
        for problem in problems:
            print('  ! ' + problem)
        print(f'문제 {len(problems)}개. 파일을 쓰지 않았습니다.')
        return 1
    if args.check:
        print('검사 통과 (--check라 파일은 쓰지 않았습니다).')
        return 0

    public = repo / 'public' / 'reading'
    public.mkdir(parents=True, exist_ok=True)
    for test in tests:
        (public / f'{test["id"]}.json').write_text(json.dumps(test, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    index = [{'id': test['id'], 'title': test['title'], 'count': len(test['items'])} for test in tests]
    (repo / 'src' / 'data' / 'reading-index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    added = update_vocab(tests, repo)
    print(f'회차 {len(tests)}개를 썼고, 단어장에 «{LESSON}» 단어 {added}개를 넣었습니다.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd $W && $PY -m unittest discover -s tools/reading -v`
Expected: 모두 OK (assemble 7개 포함)

- [ ] **Step 5: README(해설 쓰기 규칙 포함)를 쓴다**

`tools/reading/README.md`:

````markdown
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
````

- [ ] **Step 6: 커밋한다**

```bash
cd $W && git add tools/reading/assemble.py tools/reading/test_assemble.py tools/reading/README.md
git commit -m "Assemble and validate HSK3 reading explanations

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: H31001 해설 쓰기·검수·조립 (첫 회차로 형식 검증)

**Files:**
- Create (저장소 밖): `$WORK/H31001/enrich-41-50.json`, `enrich-51-60.json`, `enrich-61-70.json`
- Create: `public/reading/H31001.json`, `src/data/reading-index.json`
- Modify: `src/data/vocab.json` (assemble.py가 «HSK3 독해» 단원 추가), `src/lessons.js:4`

**Interfaces:**
- Consumes: `paper.json`(Task 2), README «해설 쓰기»·`assemble.py --check`(Task 3)
- Produces: `public/reading/H31001.json` — Task 8·9 화면이 읽는 실제 데이터. `src/data/reading-index.json` = `[{ "id": "H31001", "title": "HSK 3급 H31001", "count": 30 }]`.

- [ ] **Step 1: 해설 쓰기 에이전트를 보낸다** (Agent 도구, general-purpose, 아래 프롬프트에서 `{ID}`=H31001)

```text
너는 HSK 3급 독해 해설을 쓰는 중국어 교사다. 회차 {ID}의 해설 파일 세 개를 만든다.
저장소: ~/worktrees/chinaword-hsk-reading (여기서 명령을 돌린다)

1. tools/reading/README.md의 «해설 쓰기» 절을 끝까지 읽는다. 형식과 기준을 그대로 따른다.
2. ~/hsk-reading-work/{ID}/paper.json을 읽는다. 원문 한자·정답은 이 파일이 기준이다.
3. ~/hsk-reading-work/{ID}/enrich-41-50.json, enrich-51-60.json, enrich-61-70.json을 차례로 쓴다.
   파일 하나를 쓸 때마다 바로 4번 검사를 돌려 그 부분의 «!» 문제를 먼저 없앤다.
4. 검사: ~/venv-store/hsk-listening/bin/python tools/reading/assemble.py {ID} --work ~/hsk-reading-work --repo . --check --show-readings
   «!» 문제를 모두 고친다(아직 안 쓴 부분의 «해설 없음»은 마지막 파일까지 쓴 뒤 사라진다).
   «?» 병음 차이는 문맥상 맞는지 보고 틀린 것만 고친다.
5. 저장소 파일(public/, src/, tools/)은 고치지 않는다. 다른 회차 폴더도 건드리지 않는다. --check 없이 assemble.py를 돌리지 않는다.

보고(한국어): 마지막 검사 출력의 요약 줄, 고친 «?» 항목, 판단이 애매했던 문항 번호와 이유.
```

- [ ] **Step 2: 검사가 통과하는지 직접 확인한다**

Run: `cd $W && $PY tools/reading/assemble.py H31001 --work $WORK --repo . --check --show-readings`
Expected: `검사 통과 (--check라 파일은 쓰지 않았습니다).` `?` 목록을 훑어 틀린 병음이 있으면 고친다.

- [ ] **Step 3: 검수 에이전트를 보낸다** (Agent 도구, general-purpose, `{ID}`=H31001)

```text
너는 HSK 3급 독해 해설을 검수하는 중국어 교사다. 회차 {ID}의 해설(~/hsk-reading-work/{ID}/enrich-*.json)을
원문·정답(~/hsk-reading-work/{ID}/paper.json)과 대조해 검수하고, 틀린 곳은 해설 파일을 직접 고친다.
기준: ~/worktrees/chinaword-hsk-reading/tools/reading/README.md «해설 쓰기».

문항마다 확인한다:
1. 정답 근거가 paper.json의 answer 보기를 가리키는가, quote가 원문 그대로인가
2. 오답 이유가 지문 내용과 맞는가 (지문에 있는 걸 «없음»이라 하지 않았나)
3. 끊어 읽기 성분 표시가 맞는가 (주어·술어·목적어·관형어·부사어·보어·접속사·개사구)
4. 병음: 다음자, 不·一 변조, 경성, 儿화
5. 한국어 해석이 정확하고 자연스러운가
6. 단어 품사·뜻·용법이 맞고, 예문이 자연스러운 HSK 3급 수준인가
7. 1부분 pair 순서가 대화로 자연스러운가

고친 뒤 저장소에서 검사가 통과해야 한다:
cd ~/worktrees/chinaword-hsk-reading && ~/venv-store/hsk-listening/bin/python tools/reading/assemble.py {ID} --work ~/hsk-reading-work --repo . --check
저장소 파일은 고치지 않는다. --check 없이 assemble.py를 돌리지 않는다.

보고(한국어): 고친 문항 번호와 무엇을 고쳤는지 문항당 한 줄. 고칠 것이 없었던 항목 수.
```

- [ ] **Step 4: 단원 순서에 «HSK3 독해»를 더한다**

`src/lessons.js:4`:

```js
export const LESSON_ORDER = ['HSK1 150', 'HSK2 추가 150', 'HSK2 공식문제', 'HSK3 추가 300', 'HSK3 듣기', 'HSK3 독해'];
```

- [ ] **Step 5: 조립해서 앱 데이터를 쓴다**

Run: `cd $W && $PY tools/reading/assemble.py H31001 --work $WORK --repo .`
Expected: `회차 1개를 썼고, 단어장에 «HSK3 독해» 단어 N개를 넣었습니다.`

확인:

```bash
cd $W && $PY -c "
import json; t=json.load(open('public/reading/H31001.json'))
print(len(t['items']), [g['id'] for g in t['groups']], t['items'][22]['explain']['basis'])"
git diff --stat src/data/vocab.json
```

Expected: `30 ['41-45', '46-50', '51-55', '56-60'] {...63번 근거...}`, vocab.json은 추가 줄만.

- [ ] **Step 6: 커밋한다**

```bash
cd $W && git add public/reading/H31001.json src/data/reading-index.json src/data/vocab.json src/lessons.js
git commit -m "Add H31001 reading items with explanations

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: 듣기·독해 공용 도우미 `practiceStore.js`

**Files:**
- Create: `src/practiceStore.js`
- Modify: `src/listeningTools.js:1-63` (공용 부분을 가져다 쓰게)
- Modify: `package.json` (scripts.test)
- Test: `src/practiceStore.test.js`

**Interfaces:**
- Produces (`src/practiceStore.js`): `UNKNOWN = '?'`, `readJson(key, fallback)`, `writeJson(key, value)`, `gradeOf(item, picked) -> 'right'|'wrong'|'unknown'|null`, `tally(items, picks) -> {right, wrong, unknown}`, `fetchCached(url, label) -> Promise<data>`.
- `src/listeningTools.js`는 지금 export 이름(`UNKNOWN, fetchTest, gradeOf, loadAnswers, loadPrefs, saveAnswers, savePrefs, tally, useClipPlayer`)을 그대로 유지한다. `Listening.jsx`는 이 Task에서 고치지 않는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`src/practiceStore.test.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { UNKNOWN, fetchCached, gradeOf, readJson, tally, writeJson } from './practiceStore.js';

function memoryStorage(initial = {}) {
  const data = { ...initial };
  return {
    getItem: (key) => (key in data ? data[key] : null),
    setItem: (key, value) => {
      data[key] = String(value);
    },
    data
  };
}

function useStorage(storage) {
  Object.defineProperty(globalThis, 'localStorage', { value: storage, configurable: true, writable: true });
}

test('gradeOf: 안 고름·모름·맞힘·틀림', () => {
  const item = { no: 1, answer: 'B' };
  assert.equal(gradeOf(item, undefined), null);
  assert.equal(gradeOf(item, UNKNOWN), 'unknown');
  assert.equal(gradeOf(item, 'B'), 'right');
  assert.equal(gradeOf(item, 'C'), 'wrong');
});

test('tally는 고른 문항만 센다', () => {
  const items = [{ no: 1, answer: 'A' }, { no: 2, answer: 'B' }, { no: 3, answer: 'C' }, { no: 4, answer: 'D' }];
  assert.deepEqual(tally(items, { 1: 'A', 2: 'C', 3: '?' }), { right: 1, wrong: 1, unknown: 1 });
});

test('readJson: 깨진 값·없는 키·저장소 없음이면 기본값', () => {
  useStorage(memoryStorage({ broken: '{not json', ok: '{"a":1}' }));
  assert.deepEqual(readJson('ok', {}), { a: 1 });
  assert.deepEqual(readJson('broken', { fallback: true }), { fallback: true });
  assert.deepEqual(readJson('missing', {}), {});
  useStorage(undefined);
  assert.deepEqual(readJson('anything', { a: 1 }), { a: 1 });
});

test('writeJson: 저장 실패를 삼킨다', () => {
  useStorage({ getItem: () => null, setItem: () => { throw new Error('full'); } });
  assert.doesNotThrow(() => writeJson('k', { a: 1 }));
  useStorage(undefined);
  assert.doesNotThrow(() => writeJson('k', { a: 1 }));
});

test('fetchCached: 같은 주소는 한 번만 받고, 실패하면 다음에 다시 받는다', async () => {
  let calls = 0;
  let fail = true;
  globalThis.fetch = async (url) => {
    calls += 1;
    if (fail) return { ok: false, status: 503 };
    return { ok: true, json: async () => ({ url }) };
  };
  await assert.rejects(fetchCached('/reading/T1.json', 'T1'), /T1 데이터를 불러오지 못했어요 \(503\)/);
  fail = false;
  const first = await fetchCached('/reading/T1.json', 'T1');
  const second = await fetchCached('/reading/T1.json', 'T1');
  assert.deepEqual(first, { url: '/reading/T1.json' });
  assert.equal(second, first);
  assert.equal(calls, 2);
});
```

`package.json`의 `scripts`에 한 줄 더한다:

```json
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test": "node --test src/*.test.js"
  },
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd $W && npm test`
Expected: FAIL — `Cannot find module '.../src/practiceStore.js'`

- [ ] **Step 3: 구현한다**

`src/practiceStore.js`:

```js
// 듣기·독해 탭이 같이 쓰는 도우미: 기기 저장, 채점, 회차 데이터 받아오기.
// node 테스트(src/*.test.js)가 바로 가져다 쓰므로 React를 쓰지 않습니다.

// '모르겠음'은 기록에 '?'로 남깁니다. 틀린 것과 따로 셉니다.
export const UNKNOWN = '?';

export function readJson(key, fallback) {
  try {
    const saved = localStorage.getItem(key);
    const parsed = saved ? JSON.parse(saved) : null;
    return parsed && typeof parsed === 'object' ? parsed : fallback;
  } catch {
    return fallback;
  }
}

export function writeJson(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // 저장 실패가 학습을 막을 이유는 없습니다.
  }
}

export function gradeOf(item, picked) {
  if (!picked) return null;
  if (picked === UNKNOWN) return 'unknown';
  return picked === item.answer ? 'right' : 'wrong';
}

export function tally(items, picks = {}) {
  return items.reduce(
    (acc, item) => {
      const grade = gradeOf(item, picks[item.no]);
      if (grade) acc[grade] += 1;
      return acc;
    },
    { right: 0, wrong: 0, unknown: 0 }
  );
}

const cache = new Map();

// 회차 데이터는 그 회차를 고를 때만 받아옵니다. 실패하면 캐시에서 지워 다음에 다시 받습니다.
export function fetchCached(url, label) {
  if (!cache.has(url)) {
    const request = fetch(url).then((response) => {
      if (!response.ok) throw new Error(`${label} 데이터를 불러오지 못했어요 (${response.status})`);
      return response.json();
    });
    request.catch(() => cache.delete(url));
    cache.set(url, request);
  }
  return cache.get(url);
}
```

`src/listeningTools.js`의 1~63줄(파일 머리부터 `fetchTest` 끝까지)을 아래로 바꾼다. `// 이어 붙인 음원에서 지금 시각이 몇 번 문항인지…`부터 끝까지는 그대로 둔다.

```js
// 듣기 탭 도우미: 풀이 기록, 문항 구간 재생. 독해와 같이 쓰는 부분은 practiceStore.js에 있습니다.
import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchCached, readJson, writeJson } from './practiceStore';

export { UNKNOWN, gradeOf, tally } from './practiceStore';

const ANSWER_KEY = 'sungmi-vocab-listening-v1';
const PREF_KEY = 'sungmi-vocab-listening-prefs-v1';

// { "H31001": { "23": "A", "24": "?" } }
export const loadAnswers = () => readJson(ANSWER_KEY, {});
export const saveAnswers = (answers) => writeJson(ANSWER_KEY, answers);
export const loadPrefs = () => readJson(PREF_KEY, {});
export const savePrefs = (prefs) => writeJson(PREF_KEY, prefs);

// 회차 데이터(대본·해설, 약 85KB)는 그 회차를 고를 때만 받아옵니다.
export const fetchTest = (id) => fetchCached(`/listening/${id}.json`, id);
```

- [ ] **Step 4: 통과와 빌드를 확인한다**

Run: `cd $W && npm test && npx vite build --outDir "$SCRATCH/dist-check" --emptyOutDir`
Expected: 테스트 5개 pass, 빌드 성공(경고만 허용)

- [ ] **Step 5: 커밋한다**

```bash
cd $W && git add src/practiceStore.js src/practiceStore.test.js src/listeningTools.js package.json
git commit -m "Share storage, grading and fetch helpers between practice tabs

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: 내 단어장 저장 모듈 `myVocab.js`

**Files:**
- Create: `src/myVocab.js`
- Test: `src/myVocab.test.js`

**Interfaces:**
- Consumes: `readJson`, `writeJson` (Task 5)
- Produces (`src/myVocab.js`):
  - 상수 `MINE_KEY = 'sungmi-vocab-mine-v1'`, `MINE_LESSON = '내 단어장'`
  - `wordsToPinyin(words) -> string`, `wordKey(hanzi)`, `patternKey(pattern)`
  - `wordEntry(word, source, now?) -> entry`, `patternEntry(grammar, source, now?) -> entry` — entry 모양은 설계서 «저장 형식» 그대로(`key, kind, hanzi, pinyin, meaningKo, partOfSpeech, note, exampleZh, examplePinyin, exampleKo, source, addedAt`)
  - `toggleEntry(items, entry)`, `removeKey(items, key)`, `mineToStudyItems(items) -> card[]` (card: `id: 'mine:'+key, itemType: '단어'|'패턴', lesson: MINE_LESSON, hanzi, pinyin, meaningKo, partOfSpeech, note, exampleZh, examplePinyin, exampleKo, source, mineKey`)
  - 저장소: `loadMine()`, `toggleMine(entry)`, `removeMine(key)`, `subscribeMine(listener) -> unsubscribe`, `resetMineForTest()`
  - 훅 `useMyVocab() -> { items, has(key), toggle(entry), remove(key) }`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`src/myVocab.test.js`:

```js
import { beforeEach, test } from 'node:test';
import assert from 'node:assert/strict';
import {
  MINE_KEY,
  MINE_LESSON,
  loadMine,
  mineToStudyItems,
  patternEntry,
  removeMine,
  resetMineForTest,
  subscribeMine,
  toggleEntry,
  toggleMine,
  wordEntry,
  wordsToPinyin
} from './myVocab.js';

const NOW = new Date('2026-10-12T05:00:00Z');
const READING_WORD = {
  hanzi: '满意', pinyin: 'mǎnyì', partOfSpeech: '형용사', meaningKo: '만족하다', usage: '对A很满意',
  example: { zh: '我很满意。', words: [['我', 'wǒ'], ['很', 'hěn'], ['满意', 'mǎnyì'], ['。', '']], ko: '나는 만족한다.' }
};
const LISTENING_WORD = { hanzi: '门口', pinyin: 'ménkǒu', meaningKo: '입구', partOfSpeech: '명사' };
const READING_GRAMMAR = {
  pattern: '虽然A，但是B', meaningKo: 'A이긴 하지만 B', note: '무게는 B에 있다.',
  example: { zh: '虽然贵，但是好。', words: [['虽然', 'suīrán'], ['贵', 'guì'], ['，', ''], ['但是', 'dànshì'], ['好', 'hǎo'], ['。', '']], ko: '비싸지만 좋다.' }
};
const LISTENING_GRAMMAR = { pattern: '동사 + 到 (결과보어)', note: '목표를 이루었음을 나타낸다.' };

function memoryStorage(initial = {}) {
  const data = { ...initial };
  return {
    getItem: (key) => (key in data ? data[key] : null),
    setItem: (key, value) => {
      data[key] = String(value);
    }
  };
}

function useStorage(storage) {
  Object.defineProperty(globalThis, 'localStorage', { value: storage, configurable: true, writable: true });
}

beforeEach(() => {
  useStorage(memoryStorage());
  resetMineForTest();
});

test('wordsToPinyin: 예문 병음 한 줄', () => {
  assert.equal(wordsToPinyin(READING_GRAMMAR.example.words), 'Suīrán guì, dànshì hǎo.');
  assert.equal(wordsToPinyin(undefined), '');
});

test('wordEntry: 독해 단어는 용법·예문까지 담는다', () => {
  assert.deepEqual(wordEntry(READING_WORD, 'H31001 독해 63번', NOW), {
    key: 'word:满意', kind: 'word', hanzi: '满意', pinyin: 'mǎnyì', meaningKo: '만족하다', partOfSpeech: '형용사',
    note: '对A很满意', exampleZh: '我很满意。', examplePinyin: 'Wǒ hěn mǎnyì.', exampleKo: '나는 만족한다.',
    source: 'H31001 독해 63번', addedAt: '2026-10-12T05:00:00.000Z'
  });
});

test('wordEntry: 듣기 단어는 용법·예문 칸이 빈다', () => {
  const entry = wordEntry(LISTENING_WORD, 'H31001 듣기 25번', NOW);
  assert.equal(entry.note, '');
  assert.equal(entry.exampleZh, '');
  assert.equal(entry.examplePinyin, '');
});

test('patternEntry: 짧은 뜻이 있으면 뜻 자리에, 없으면 설명 전체가 뜻', () => {
  const reading = patternEntry(READING_GRAMMAR, 'H31001 독해 63번', NOW);
  assert.equal(reading.key, 'pattern:虽然A，但是B');
  assert.equal(reading.kind, 'pattern');
  assert.equal(reading.meaningKo, 'A이긴 하지만 B');
  assert.equal(reading.note, '무게는 B에 있다.');
  assert.equal(reading.examplePinyin, 'Suīrán guì, dànshì hǎo.');
  const listening = patternEntry(LISTENING_GRAMMAR, 'H31001 듣기 25번', NOW);
  assert.equal(listening.meaningKo, '목표를 이루었음을 나타낸다.');
  assert.equal(listening.note, '');
});

test('toggleEntry: 같은 key는 하나만, 다시 누르면 뺀다, 새 항목이 앞', () => {
  let items = toggleEntry([], wordEntry(READING_WORD, 's1', NOW));
  items = toggleEntry(items, patternEntry(READING_GRAMMAR, 's2', NOW));
  assert.deepEqual(items.map((i) => i.key), ['pattern:虽然A，但是B', 'word:满意']);
  items = toggleEntry(items, wordEntry(READING_WORD, '다른 문항', NOW));
  assert.deepEqual(items.map((i) => i.key), ['pattern:虽然A，但是B']);
});

test('mineToStudyItems: 단어장·랜덤 학습 카드 모양', () => {
  const [card] = mineToStudyItems([patternEntry(READING_GRAMMAR, 'H31001 독해 63번', NOW)]);
  assert.equal(card.id, 'mine:pattern:虽然A，但是B');
  assert.equal(card.itemType, '패턴');
  assert.equal(card.lesson, MINE_LESSON);
  assert.equal(card.hanzi, '虽然A，但是B');
  assert.equal(card.pinyin, '');
  assert.equal(card.meaningKo, 'A이긴 하지만 B');
  assert.equal(card.mineKey, 'pattern:虽然A，但是B');
  assert.equal(card.source, 'H31001 독해 63번');
});

test('저장소: 담기·빼기가 기기에 남고 구독자에게 알린다', () => {
  let calls = 0;
  const off = subscribeMine(() => {
    calls += 1;
  });
  toggleMine(wordEntry(READING_WORD, 's', NOW));
  assert.equal(loadMine().length, 1);
  assert.equal(JSON.parse(localStorage.getItem(MINE_KEY)).items[0].key, 'word:满意');
  const snapshot = loadMine();
  assert.equal(loadMine(), snapshot); // 바뀌기 전에는 같은 배열 (useSyncExternalStore 조건)
  removeMine('word:满意');
  assert.equal(loadMine().length, 0);
  assert.equal(calls, 2);
  off();
});

test('저장소: 깨진 저장값은 버리고, 저장소가 없어도 빈 목록으로 동작', () => {
  useStorage(memoryStorage({ [MINE_KEY]: '{"items": [{"key": 1}, null, {"key": "word:好", "hanzi": "好"}]}' }));
  resetMineForTest();
  assert.deepEqual(loadMine().map((i) => i.key), ['word:好']);
  useStorage(undefined);
  resetMineForTest();
  assert.deepEqual(loadMine(), []);
  assert.doesNotThrow(() => toggleMine(wordEntry(READING_WORD, 's', NOW)));
  assert.equal(loadMine().length, 1);
});
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd $W && npm test`
Expected: FAIL — `Cannot find module '.../src/myVocab.js'`

- [ ] **Step 3: 구현한다**

`src/myVocab.js`:

```js
// 내 단어장: 해설에서 «＋ 담기»로 모은 단어·문장 구조.
// 화면은 이 파일만 거칩니다. 로그인을 붙일 때는 아래 '저장소' 부분만 서버 저장으로 바꾸고,
// 첫 로그인 때 기기에 있던 항목을 계정으로 올립니다.
import { useSyncExternalStore } from 'react';
import { readJson, writeJson } from './practiceStore.js';

export const MINE_KEY = 'sungmi-vocab-mine-v1';
export const MINE_LESSON = '내 단어장';

const PUNCT_PINYIN = { '，': ',', '、': ',', '。': '.', '？': '?', '！': '!', '：': ':', '；': ';', '“': '"', '”': '"' };

// [['你','nǐ'],['，','']] → 'Nǐ,' (tools/reading/hsktext.py words_to_pinyin과 같은 규칙)
export function wordsToPinyin(words) {
  let out = '';
  (words ?? []).forEach(([token, pinyin]) => {
    if (pinyin) out += (out && !out.endsWith('"') ? ' ' : '') + pinyin;
    else if (PUNCT_PINYIN[token]) out += PUNCT_PINYIN[token];
  });
  return out.charAt(0).toUpperCase() + out.slice(1);
}

export const wordKey = (hanzi) => `word:${hanzi}`;
export const patternKey = (pattern) => `pattern:${pattern}`;

// 해설의 단어 하나를 담는 순간 그대로 저장합니다. 독해 단어에는 용법·예문이 있고 듣기 단어에는 없습니다.
export function wordEntry(word, source, now = new Date()) {
  return {
    key: wordKey(word.hanzi),
    kind: 'word',
    hanzi: word.hanzi,
    pinyin: word.pinyin ?? '',
    meaningKo: word.meaningKo ?? '',
    partOfSpeech: word.partOfSpeech ?? '',
    note: word.usage ?? '',
    exampleZh: word.example?.zh ?? '',
    examplePinyin: wordsToPinyin(word.example?.words),
    exampleKo: word.example?.ko ?? '',
    source,
    addedAt: now.toISOString()
  };
}

// 문법(문장 구조) 하나. 듣기 문장 구조에는 짧은 뜻이 없어 설명 전체를 뜻 자리에 씁니다.
export function patternEntry(grammar, source, now = new Date()) {
  const short = grammar.meaningKo ?? '';
  return {
    key: patternKey(grammar.pattern),
    kind: 'pattern',
    hanzi: grammar.pattern,
    pinyin: '',
    meaningKo: short || grammar.note || '',
    partOfSpeech: '',
    note: short ? grammar.note ?? '' : '',
    exampleZh: grammar.example?.zh ?? '',
    examplePinyin: wordsToPinyin(grammar.example?.words),
    exampleKo: grammar.example?.ko ?? '',
    source,
    addedAt: now.toISOString()
  };
}

// 같은 단어·패턴은 하나로 칩니다. 있으면 빼고, 없으면 맨 앞에 넣습니다.
export function toggleEntry(items, entry) {
  return items.some((item) => item.key === entry.key)
    ? items.filter((item) => item.key !== entry.key)
    : [entry, ...items];
}

export function removeKey(items, key) {
  return items.filter((item) => item.key !== key);
}

// 단어장·랜덤 학습이 쓰는 카드 모양으로 바꿉니다 (최근에 담은 것이 앞).
export function mineToStudyItems(items) {
  return items.map((entry) => ({
    id: `mine:${entry.key}`,
    itemType: entry.kind === 'pattern' ? '패턴' : '단어',
    lesson: MINE_LESSON,
    hanzi: entry.hanzi,
    pinyin: entry.pinyin,
    meaningKo: entry.meaningKo,
    partOfSpeech: entry.partOfSpeech,
    note: entry.note,
    exampleZh: entry.exampleZh,
    examplePinyin: entry.examplePinyin,
    exampleKo: entry.exampleKo,
    source: entry.source,
    mineKey: entry.key
  }));
}

function sanitize(saved) {
  const items = Array.isArray(saved?.items) ? saved.items : [];
  return items.filter((entry) => entry && typeof entry.key === 'string' && typeof entry.hanzi === 'string');
}

// --- 저장소 (지금은 이 기기의 localStorage) ---
let current = null;
const listeners = new Set();

export function loadMine() {
  if (current === null) current = sanitize(readJson(MINE_KEY, {}));
  return current;
}

function commit(next) {
  current = next;
  writeJson(MINE_KEY, { version: 1, items: next });
  listeners.forEach((listener) => listener());
}

export function toggleMine(entry) {
  commit(toggleEntry(loadMine(), entry));
}

export function removeMine(key) {
  commit(removeKey(loadMine(), key));
}

export function subscribeMine(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function resetMineForTest() {
  current = null;
  listeners.clear();
}

// 독해·듣기 해설, 단어장, 랜덤 학습이 같은 목록을 봅니다.
export function useMyVocab() {
  const items = useSyncExternalStore(subscribeMine, loadMine, loadMine);
  return {
    items,
    has: (key) => items.some((item) => item.key === key),
    toggle: toggleMine,
    remove: removeMine
  };
}
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd $W && npm test`
Expected: practiceStore 5개 + myVocab 8개 pass

- [ ] **Step 5: 커밋한다**

```bash
cd $W && git add src/myVocab.js src/myVocab.test.js
git commit -m "Add my-vocab store for collected words and patterns

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: 공용 화면 조각 `hskParts.jsx`와 듣기 해설의 «＋ 담기»

**Files:**
- Create: `src/hskParts.jsx`
- Modify: `src/Listening.jsx:1-213` (공용 조각을 가져다 쓰게), `src/Listening.jsx` 본문의 `Verdict`·`Explanation` 사용처
- Modify: `src/styles.css` (`.listenGrammar p` 규칙 뒤에 담기 버튼 스타일)

**Interfaces:**
- Consumes: `UNKNOWN`, `gradeOf` (Task 5), `useMyVocab`, `wordEntry`, `patternEntry`, `wordKey`, `patternKey` (Task 6)
- Produces (`src/hskParts.jsx`):
  - `Ruby({ words, showPinyin = true, blank = null, fillBlank = false })` — `blank`가 있으면 그 단어를 «（　　）»로 가리거나(`fillBlank=false`) 강조(`true`)
  - `ChoiceButton({ value, picked, item, revealed, onPick, blocked = false, className, children })`
  - `Verdict({ item, picked, answerText })`
  - `ExplainVocab({ vocab, source })`, `ExplainGrammar({ grammar, source })` — 항목마다 담기 버튼. `source` 예: `'H31001 듣기 25번'`

- [ ] **Step 1: 공용 조각 파일을 만든다**

`src/hskParts.jsx`:

```jsx
import React from 'react';
import { Check, Plus, X } from 'lucide-react';
import { UNKNOWN, gradeOf } from './practiceStore';
import { patternEntry, patternKey, useMyVocab, wordEntry, wordKey } from './myVocab';

// 듣기·독해 탭이 같이 쓰는 화면 조각: 한자 아래 병음, 보기 버튼, 채점 문구,
// 해설의 단어·문장 구조 목록(항목마다 «＋ 담기»).

const OPENING_PUNCT = new Set(['“', '‘', '《', '（']);

// 문장부호가 혼자 다음 줄로 넘어가지 않게 앞 단어에 붙입니다 (여는 따옴표는 뒤 단어에).
// 세 번째 칸(mark)이 있는 단어는 빈칸 표시라 문장부호로 보지 않습니다.
function groupWords(words) {
  const units = [];
  let prefix = '';
  words.forEach(([hanzi, pinyin, mark]) => {
    if (!pinyin && !mark && OPENING_PUNCT.has(hanzi)) {
      prefix += hanzi;
    } else if (!pinyin && !mark && units.length && !prefix) {
      units[units.length - 1].suffix += hanzi;
    } else {
      units.push({ prefix, hanzi, pinyin, suffix: '', mark });
      prefix = '';
    }
  });
  if (prefix) units.push({ prefix, hanzi: '', pinyin: '', suffix: '' });
  return units;
}

// 한자 바로 아래에 병음을 붙여 단어 단위로 보여줍니다.
// blank: 빈칸 문제에서 정답 단어의 자리. 채우기 전에는 «（　　）»로 가리고, 채우면 강조합니다.
export function Ruby({ words, showPinyin = true, blank = null, fillBlank = false }) {
  const marked =
    blank === null
      ? words
      : words.map((word, index) => {
          if (index !== blank) return word;
          return fillBlank ? [word[0], word[1], 'filled'] : ['（　　）', '', 'gap'];
        });

  return (
    <span className="ruby">
      {groupWords(marked).map((unit, index) => (
        <span className={`rubyUnit${unit.mark ? ` ruby-${unit.mark}` : ''}`} key={index}>
          {unit.prefix ? <span className="rubyPunct">{unit.prefix}</span> : null}
          <span className="rubyWord">
            <span className="rubyHanzi">{unit.hanzi}</span>
            {showPinyin ? <span className="rubyPinyin">{unit.pinyin || ' '}</span> : null}
          </span>
          {unit.suffix ? <span className="rubyPunct">{unit.suffix}</span> : null}
        </span>
      ))}
    </span>
  );
}

// blocked: 예시에 쓰인 보기처럼 고를 수 없는 보기.
export function ChoiceButton({ value, picked, item, revealed, onPick, blocked = false, className = '', children }) {
  const answered = Boolean(picked);
  const isPicked = picked === value;
  const isAnswer = value === item.answer;
  const state =
    (answered || revealed) && isAnswer ? 'right' : isPicked && value === UNKNOWN ? 'unknown' : isPicked ? 'wrong' : '';

  return (
    <button
      type="button"
      className={`listenChoice ${className} ${state}${blocked ? ' blocked' : ''}`}
      onClick={() => onPick(value)}
      disabled={answered || blocked}
    >
      {children}
      {state === 'right' ? <Check size={16} /> : null}
      {state === 'wrong' ? <X size={16} /> : null}
    </button>
  );
}

export function Verdict({ item, picked, answerText }) {
  const grade = gradeOf(item, picked);
  if (!grade) return null;
  const text = {
    right: '정답이에요',
    wrong: `아쉬워요 · 정답은 ${answerText}`,
    unknown: `정답은 ${answerText}`
  }[grade];
  return <p className={`listenVerdict ${grade}`}>{text}</p>;
}

function MineButton({ saved, label, onToggle }) {
  return (
    <button
      type="button"
      className={`mineButton${saved ? ' saved' : ''}`}
      onClick={onToggle}
      aria-pressed={saved}
      aria-label={saved ? `${label} 내 단어장에서 빼기` : `${label} 내 단어장에 담기`}
    >
      {saved ? <Check size={13} /> : <Plus size={13} />}
      {saved ? '담음' : '담기'}
    </button>
  );
}

function Example({ example }) {
  return (
    <div className="readExample">
      <Ruby words={example.words} />
      <p className="listenKo">{example.ko}</p>
    </div>
  );
}

// 해설의 단어 목록. 독해 단어에는 용법(usage)·예문(example)이 더 있어 한 줄에 하나씩 넓게 보여줍니다.
export function ExplainVocab({ vocab, source }) {
  const mine = useMyVocab();
  const detailed = vocab.some((word) => word.usage || word.example);
  return (
    <ul className={`listenVocab${detailed ? ' readVocab' : ''}`}>
      {vocab.map((word) => (
        <li key={word.hanzi}>
          <strong>{word.hanzi}</strong>
          <span className="vocabPinyinText">{word.pinyin}</span>
          <span className="vocabMeaningText">{word.meaningKo}</span>
          {word.partOfSpeech ? <em>{word.partOfSpeech}</em> : null}
          <MineButton
            saved={mine.has(wordKey(word.hanzi))}
            label={word.hanzi}
            onToggle={() => mine.toggle(wordEntry(word, source))}
          />
          {word.usage ? <p className="readUsage">{word.usage}</p> : null}
          {word.example ? <Example example={word.example} /> : null}
        </li>
      ))}
    </ul>
  );
}

// 해설의 문장 구조(문법) 목록. 독해 문법에는 짧은 뜻(meaningKo)·예문이 더 있습니다.
export function ExplainGrammar({ grammar, source }) {
  const mine = useMyVocab();
  return (
    <ul className="listenGrammar">
      {grammar.map((note, index) => (
        <li key={index}>
          <div className="grammarHead">
            <strong>{note.pattern}</strong>
            {note.meaningKo ? <span className="grammarGloss">{note.meaningKo}</span> : null}
            <MineButton
              saved={mine.has(patternKey(note.pattern))}
              label={note.pattern}
              onToggle={() => mine.toggle(patternEntry(note, source))}
            />
          </div>
          <p>{note.note}</p>
          {note.example ? <Example example={note.example} /> : null}
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 2: 듣기 탭이 공용 조각을 쓰게 바꾼다**

`src/Listening.jsx` 머리(1~14줄)를 아래로 바꾼다:

```jsx
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, Eye, Headphones, Play, Repeat, RotateCcw, Square } from 'lucide-react';
import testIndex from './data/listening-index.json';
import { ChoiceButton, ExplainGrammar, ExplainVocab, Ruby, Verdict } from './hskParts';
import {
  UNKNOWN,
  fetchTest,
  loadAnswers,
  loadPrefs,
  saveAnswers,
  savePrefs,
  tally,
  useClipPlayer
} from './listeningTools';
```

같은 파일에서 다음 정의를 **지운다**: `const OPENING_PUNCT …`, `function groupWords …`, `function Ruby …`, `function ChoiceButton …`, `function Verdict …`. (`PART_CHIPS`, `SPEAKER_LABELS`, `TRUE_FALSE`, `answerLabel`, `Choices`는 남긴다.)

`function Explanation({ item })`를 아래로 바꾼다:

```jsx
function Explanation({ item, source }) {
  return (
    <section className="listenReveal">
      <h3>대본</h3>
      <ol className="listenScript">
        {item.script.map((line, index) => (
          <li key={index} className="listenLine">
            {line.speaker ? (
              <span className={`listenSpeaker ${line.speaker === '问' ? 'question' : ''}`}>
                {SPEAKER_LABELS[line.speaker] ?? line.speaker}
              </span>
            ) : null}
            <div className="listenLineBody">
              <Ruby words={line.words} />
              <p className="listenKo">{line.ko}</p>
            </div>
          </li>
        ))}
      </ol>

      <h3>핵심 단어</h3>
      <ExplainVocab vocab={item.vocab} source={source} />

      <h3>문장 구조</h3>
      <ExplainGrammar grammar={item.grammar} source={source} />
    </section>
  );
}
```

본문에서 두 사용처를 바꾼다:

```jsx
            <Verdict item={item} picked={picked} answerText={answerLabel(item)} />
```

```jsx
                <Explanation item={item} source={`${testId} 듣기 ${item.no}번`} />
```

- [ ] **Step 3: 담기 버튼 스타일을 더한다**

`src/styles.css`에서 `.listenGrammar p { … }` 규칙 바로 뒤(`.listenNav {` 앞)에 넣는다:

```css
/* 해설의 «＋ 담기» (내 단어장) */
.mineButton {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  min-height: 28px;
  padding: 0 10px;
  border: 1px solid var(--accent);
  border-radius: 999px;
  background: #fff;
  color: var(--accent-strong);
  font-size: 0.74rem;
  font-weight: 900;
}

.mineButton.saved {
  border-color: transparent;
  background: var(--accent-strong);
  color: #fff8ef;
}

.grammarHead {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px 8px;
}

.grammarGloss {
  color: var(--accent-strong);
  font-size: 0.84rem;
  font-weight: 850;
}
```

- [ ] **Step 4: 테스트·빌드를 확인한다**

Run: `cd $W && npm test && npx vite build --outDir "$SCRATCH/dist-check" --emptyOutDir`
Expected: 테스트 13개 pass, 빌드 성공

- [ ] **Step 5: 브라우저에서 듣기 탭을 확인한다**

```bash
cd $W && npx vite --port 5174 --strictPort   # Bash run_in_background
```

Chrome(mcp__claude-in-chrome) 새 탭으로 `http://localhost:5174` → «듣기» 탭:
- H31001 25번에서 «문제 듣기»가 재생·멈춤되고, 보기를 고르면 정답 표시와 대본·핵심 단어·문장 구조가 전과 같이 나온다.
- 핵심 단어 `书店` 옆 «담기»를 누르면 «담음»으로 바뀌고, javascript_tool로 `localStorage.getItem('sungmi-vocab-mine-v1')`에 `word:书店`이 있다. 다시 누르면 빠진다.
- 문장 구조 `동사 + 到 (결과보어)` «담기» → «담음».
- 콘솔 오류 없음(read_console_messages, pattern `error|Error`).

- [ ] **Step 6: 커밋한다**

```bash
cd $W && git add src/hskParts.jsx src/Listening.jsx src/styles.css
git commit -m "Share ruby, choices and explanation lists; add collect buttons

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: 독해 탭 `Reading.jsx`

**Files:**
- Create: `src/Reading.jsx`
- Modify: `src/main.jsx:7-9` (import), `src/main.jsx:27-33` (`VIEW_OPTIONS`), 본문 탭 분기와 `keyboardHint`
- Modify: `src/styles.css` (`.viewTabs` 6칸, 모바일 탭 글자, 독해 스타일)

**Interfaces:**
- Consumes: `public/reading/H31001.json`·`src/data/reading-index.json` (Task 4), `UNKNOWN`, `fetchCached`, `readJson`, `tally`, `writeJson` (Task 5), `ChoiceButton`, `ExplainGrammar`, `ExplainVocab`, `Ruby`, `Verdict` (Task 7)
- Produces: `export default function Reading()` — props 없음. 내 단어장 출처 문구 `'<회차> 독해 <번호>번'`.

- [ ] **Step 1: 독해 탭 화면을 만든다**

`src/Reading.jsx`:

```jsx
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, Eye, Languages, RotateCcw } from 'lucide-react';
import testIndex from './data/reading-index.json';
import { UNKNOWN, fetchCached, readJson, tally, writeJson } from './practiceStore';
import { ChoiceButton, ExplainGrammar, ExplainVocab, Ruby, Verdict } from './hskParts';

// HSK 공식 모의고사 독해. 문항마다 '읽기 → 고르기(또는 모르겠음) → 정답·해설'.
// 회차 데이터 public/reading/<회차>.json은 tools/reading/assemble.py가 만듭니다.

const ANSWER_KEY = 'sungmi-vocab-reading-v1';
const PREF_KEY = 'sungmi-vocab-reading-prefs-v1';
const PART_CHIPS = ['전체', 1, 2, 3];

const fetchTest = (id) => fetchCached(`/reading/${id}.json`, id);
const hanziOf = (words) => words.map(([hanzi]) => hanzi).join('');

// 1·2부분은 다섯 문항이 묶음 보기를 같이 쓰고, 3부분은 문항마다 A·B·C가 있습니다.
function choicesOf(test, item) {
  if (item.part === 3) return { options: item.options ?? [], example: null };
  const group = test.groups.find((entry) => entry.id === item.group);
  return { options: group?.options ?? [], example: group?.example ?? null };
}

function answerText(item, options) {
  if (item.part !== 2) return item.answer;
  const word = options.find((option) => option.label === item.answer);
  return word ? `${item.answer} ${hanziOf(word.words)}` : item.answer;
}

// 지문(3부분), 문항 문장(1부분), 빈칸 문장(2부분). 2부분은 답을 고르면 빈칸이 채워집니다.
function Lines({ item, showPinyin, revealed }) {
  return (
    <div className="readLines">
      {item.lines.map((line, index) => (
        <div className="readLine" key={index}>
          {line.speaker ? <span className="listenSpeaker">{line.speaker}</span> : null}
          <div className="listenLineBody">
            <Ruby
              words={line.words}
              showPinyin={showPinyin || revealed}
              blank={line.blank ?? null}
              fillBlank={revealed}
            />
            {revealed ? <p className="listenKo">{line.ko}</p> : null}
          </div>
        </div>
      ))}
    </div>
  );
}

function Question({ question, showPinyin, revealed }) {
  return (
    <div className="listenStatement">
      <span className="listenStar">★</span>
      <div>
        <Ruby words={question.words} showPinyin={showPinyin || revealed} />
        {revealed ? <p className="listenKo">{question.ko}</p> : null}
      </div>
    </div>
  );
}

function Choices({ item, options, example, picked, revealed, showPinyin, onPick }) {
  const shared = { item, picked, revealed, onPick };
  const wordBank = item.part === 2;
  const kind = wordBank ? 'readWord' : 'option';
  return (
    <div className={`listenChoices ${wordBank ? 'readBank' : 'listenOptions'}`}>
      {options.map((option) => {
        const isExample = option.label === example;
        return (
          <ChoiceButton key={option.label} value={option.label} className={kind} blocked={isExample} {...shared}>
            <span className="optionLabel">{option.label}</span>
            <span className="optionText">
              <Ruby words={option.words} showPinyin={showPinyin || revealed} />
              {revealed ? <span className="listenKo">{option.ko}</span> : null}
            </span>
            {isExample ? <span className="readExampleTag">예시</span> : null}
          </ChoiceButton>
        );
      })}
      <ChoiceButton value={UNKNOWN} className={`${kind} unknownChoice`} {...shared}>
        <span className="optionText">모르겠음</span>
      </ChoiceButton>
    </div>
  );
}

// 1부분: 짝지은 두 문장을 대화 순서대로 이어 보여줍니다.
function PairDialogue({ item, options }) {
  const partner = options.find((option) => option.label === item.answer);
  if (!partner) return null;
  const own = { key: 'item', tag: `${item.no}`, words: item.lines[0].words, ko: item.lines[0].ko };
  const other = { key: 'option', tag: partner.label, words: partner.words, ko: partner.ko };
  const order = item.pair === 'option-first' ? [other, own] : [own, other];
  return (
    <>
      <h3>이어 읽기</h3>
      <ol className="listenScript">
        {order.map((line) => (
          <li key={line.key} className="listenLine">
            <span className="listenSpeaker">{line.tag}</span>
            <div className="listenLineBody">
              <Ruby words={line.words} />
              <p className="listenKo">{line.ko}</p>
            </div>
          </li>
        ))}
      </ol>
    </>
  );
}

function Explanation({ item, options, source }) {
  const { basis, distractors, breakdown, vocab, grammar } = item.explain;
  const optionOf = (label) => options.find((option) => option.label === label);
  return (
    <section className="listenReveal">
      {item.part === 1 ? <PairDialogue item={item} options={options} /> : null}

      <h3>정답 근거</h3>
      <div className="readBasis">
        <p className="readQuote">{basis.quote}</p>
        <p>{basis.note}</p>
      </div>

      {distractors.length ? (
        <>
          <h3>오답 이유</h3>
          <ul className="readDistractors">
            {distractors.map((entry) => (
              <li key={entry.label}>
                <span className="optionLabel">{entry.label}</span>
                <div>
                  <p className="readDistractorText">{hanziOf(optionOf(entry.label)?.words ?? [])}</p>
                  <p>{entry.note}</p>
                </div>
              </li>
            ))}
          </ul>
        </>
      ) : null}

      <h3>끊어 읽기</h3>
      <ul className="readBreakdown">
        {breakdown.map((sentence, index) => (
          <li key={index}>
            <div className="readChunks">
              {sentence.chunks.map((chunk, chunkIndex) => (
                <span className="readChunk" key={chunkIndex}>
                  <span className="readChunkText">{chunk.text}</span>
                  <span className="readChunkRole">{chunk.role}</span>
                </span>
              ))}
            </div>
            <p>{sentence.note}</p>
          </li>
        ))}
      </ul>

      <h3>단어</h3>
      <ExplainVocab vocab={vocab} source={source} />

      <h3>문법</h3>
      <ExplainGrammar grammar={grammar} source={source} />
    </section>
  );
}

export default function Reading() {
  const initial = useMemo(() => readJson(PREF_KEY, {}), []);
  const [testId, setTestId] = useState(
    testIndex.some((entry) => entry.id === initial.testId) ? initial.testId : testIndex[0]?.id
  );
  const [part, setPart] = useState(PART_CHIPS.includes(initial.part) ? initial.part : '전체');
  const [positions, setPositions] = useState(
    initial.positions && typeof initial.positions === 'object' ? initial.positions : {}
  );
  const [showPinyin, setShowPinyin] = useState(initial.showPinyin === true);
  const [answers, setAnswers] = useState(() => readJson(ANSWER_KEY, {}));
  const [shown, setShown] = useState({}); // 고르지 않고 '해설 보기'로 펼친 문항
  const [test, setTest] = useState(null);
  const [error, setError] = useState('');
  const bodyRef = useRef(null);

  useEffect(() => {
    if (!testId) return undefined;
    let alive = true;
    setTest(null);
    setError('');
    fetchTest(testId)
      .then((data) => alive && setTest(data))
      .catch((err) => alive && setError(err.message));
    return () => {
      alive = false;
    };
  }, [testId]);

  useEffect(() => {
    writeJson(PREF_KEY, { testId, part, positions, showPinyin });
  }, [testId, part, positions, showPinyin]);

  const items = useMemo(
    () => (test ? test.items.filter((entry) => part === '전체' || entry.part === part) : []),
    [test, part]
  );
  const allItems = test?.items ?? [];
  const savedNo = positions[testId];
  const index = Math.max(0, items.findIndex((entry) => entry.no === savedNo));
  const item = items[index];

  useEffect(() => {
    bodyRef.current?.scrollTo?.({ top: 0 });
  }, [testId, item?.no]);

  const picks = answers[testId] ?? {};
  const picked = item ? picks[item.no] : undefined;
  const revealed = Boolean(item && (picked || shown[`${testId}-${item.no}`]));
  const counts = tally(allItems, picks);
  const { options, example } = item && test ? choicesOf(test, item) : { options: [], example: null };
  const guide = test?.parts.find((entry) => entry.part === item?.part)?.guide;

  function goTo(nextIndex) {
    const next = items[nextIndex];
    if (next) setPositions((prev) => ({ ...prev, [testId]: next.no }));
  }

  function changePart(nextPart) {
    setPart(nextPart);
    const first = test?.items.find((entry) => nextPart === '전체' || entry.part === nextPart);
    if (first) setPositions((prev) => ({ ...prev, [testId]: first.no }));
  }

  function pick(value) {
    const next = { ...answers, [testId]: { ...picks, [item.no]: value } };
    setAnswers(next);
    writeJson(ANSWER_KEY, next);
  }

  function retry() {
    const { [item.no]: _removed, ...rest } = picks;
    const next = { ...answers, [testId]: rest };
    setAnswers(next);
    writeJson(ANSWER_KEY, next);
    setShown((prev) => ({ ...prev, [`${testId}-${item.no}`]: false }));
  }

  return (
    <section className="listenPanel">
      <div className="listenControls">
        <div className="lessonChips listenTests" aria-label="회차 선택">
          {testIndex.map((entry) => (
            <button
              key={entry.id}
              type="button"
              className={`lessonChip ${testId === entry.id ? 'active' : ''}`}
              onClick={() => setTestId(entry.id)}
            >
              {entry.id}
            </button>
          ))}
        </div>
        <div className="listenToolbar">
          <div className="memoToggles" aria-label="부분 선택">
            {PART_CHIPS.map((chip) => (
              <button
                key={chip}
                type="button"
                className={`memoToggle ${part === chip ? 'active' : ''}`}
                onClick={() => changePart(chip)}
              >
                {chip === '전체' ? '전체' : `${chip}부분`}
              </button>
            ))}
          </div>
          <button
            type="button"
            className={`memoToggle readPinyinToggle ${showPinyin ? 'active' : ''}`}
            onClick={() => setShowPinyin((on) => !on)}
            aria-pressed={showPinyin}
          >
            <Languages size={14} /> 병음 보기
          </button>
        </div>
        <p className="listCount">
          {allItems.length
            ? `맞힘 ${counts.right} · 틀림 ${counts.wrong} · 모름 ${counts.unknown} · 안 푼 문제 ${
                allItems.length - counts.right - counts.wrong - counts.unknown
              }`
            : ' '}
        </p>
      </div>

      <div className="listenBody" ref={bodyRef}>
        {error ? <p className="listEmpty">{error}</p> : null}
        {!error && !item ? <p className="listEmpty">불러오는 중…</p> : null}
        {item ? (
          <article className="listenCard">
            <div className="quizProgress">
              <span>
                {item.no}번 · {item.part}부분
              </span>
              <span>{guide}</span>
            </div>

            <Lines item={item} showPinyin={showPinyin} revealed={revealed} />
            {item.question ? <Question question={item.question} showPinyin={showPinyin} revealed={revealed} /> : null}
            <Choices
              item={item}
              options={options}
              example={example}
              picked={picked}
              revealed={revealed}
              showPinyin={showPinyin}
              onPick={pick}
            />
            <Verdict item={item} picked={picked} answerText={answerText(item, options)} />

            {revealed ? (
              <>
                <Explanation item={item} options={options} source={`${testId} 독해 ${item.no}번`} />
                <button type="button" className="subButton listenRetry" onClick={retry}>
                  <RotateCcw size={15} /> 이 문제 다시 풀기
                </button>
              </>
            ) : (
              <button
                type="button"
                className="subButton listenShow"
                onClick={() => setShown((prev) => ({ ...prev, [`${testId}-${item.no}`]: true }))}
              >
                <Eye size={15} /> 고르지 않고 해설 보기
              </button>
            )}
          </article>
        ) : null}
      </div>

      <div className="listenNav">
        <button type="button" className="listenNavButton" onClick={() => goTo(index - 1)} disabled={index <= 0}>
          <ChevronLeft size={18} /> 이전
        </button>
        <span>{items.length ? `${index + 1} / ${items.length}` : ''}</span>
        <button
          type="button"
          className="listenNavButton"
          onClick={() => goTo(index + 1)}
          disabled={index >= items.length - 1}
        >
          다음 <ChevronRight size={18} />
        </button>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: 탭을 연결한다**

`src/main.jsx` import 줄(`import Listening from './Listening';` 아래)에 더한다:

```jsx
import Reading from './Reading';
```

`VIEW_OPTIONS`:

```jsx
const VIEW_OPTIONS = [
  { key: 'study', label: '랜덤 학습' },
  { key: 'list', label: '단어장' },
  { key: 'memo', label: '암기' },
  { key: 'quiz', label: '시험보기' },
  { key: 'listen', label: '듣기' },
  { key: 'read', label: '독해' }
];
```

본문 탭 분기에서 `view === 'listen' ? (<Listening />)` 다음에 독해를 넣는다:

```jsx
      ) : view === 'listen' ? (
        <Listening />
      ) : view === 'read' ? (
        <Reading />
      ) : (
        <ToneQuiz items={studyItems} canSpeak={hasChineseVoice} onSpeak={handleSpeak} />
      )}
```

`keyboardHint`의 `view === 'listen'` 분기 다음에 넣는다:

```jsx
              : view === 'listen'
                ? '문제 듣기는 멈춤을 누를 때까지 되풀이합니다 · 이어 듣기는 화면을 꺼도 계속 재생됩니다'
                : view === 'read'
                  ? '답을 고르면 정답 근거·끊어 읽기·단어·문법이 열립니다 · ＋ 담기로 내 단어장에 모아요'
                  : '한자를 보고 들으면서 성조가 맞는 병음을 고르세요'}
```

- [ ] **Step 3: 스타일을 더한다**

`src/styles.css` `.viewTabs`의 `grid-template-columns: repeat(5, 1fr);` → `repeat(6, 1fr);`

모바일 `.viewTab`(`@media (max-width: 680px)` 안)의 주석과 글자 크기:

```css
    /* 탭이 6개라 좁은 화면에서는 글자를 줄여야 한 줄에 들어갑니다. */
    font-size: clamp(0.62rem, 2.8vw, 0.82rem);
```

담기 버튼 스타일(Task 7) 뒤, `.listenNav {` 앞에 넣는다:

```css
/* 독해 탭 */
.readLines {
  display: grid;
  gap: 8px;
}

.readLine {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.readBank {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
}

.listenChoice.readWord {
  flex-direction: column;
  gap: 2px;
  min-width: 76px;
  padding: 8px 12px;
}

.listenChoice.readWord .optionLabel {
  width: 22px;
  height: 22px;
  font-size: 0.75rem;
}

.listenChoice.readWord .optionText {
  justify-items: center;
}

.listenChoice.blocked {
  opacity: 0.45;
  border-style: dashed;
  cursor: default;
}

.readExampleTag {
  margin-left: auto;
  padding: 2px 8px;
  border-radius: 999px;
  background: #f2e4d4;
  color: var(--accent-strong);
  font-size: 0.7rem;
  font-weight: 900;
}

.ruby-gap .rubyHanzi {
  color: var(--muted);
  letter-spacing: 0.1em;
}

.ruby-filled .rubyHanzi {
  padding: 0 4px;
  border-radius: 6px;
  background: #e8f5ec;
  color: #235535;
}

.readBasis,
.readBreakdown li,
.readDistractors li {
  padding: 10px 12px;
  border-radius: 14px;
  background: #fbf5ee;
}

.readBasis p,
.readBreakdown p,
.readDistractors p {
  margin: 0;
  font-size: 0.88rem;
  font-weight: 750;
  line-height: 1.55;
}

.readBasis .readQuote {
  margin: 0 0 6px;
  padding-left: 10px;
  border-left: 3px solid var(--accent);
  font-size: 1.05rem;
  font-weight: 900;
}

.readDistractors,
.readBreakdown {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.readDistractors li {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.readDistractors .readDistractorText {
  font-size: 1rem;
  font-weight: 900;
}

.readChunks {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 6px;
}

.readChunk {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 6px 8px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #fff;
}

.readChunkText {
  font-size: 1.1rem;
  font-weight: 900;
}

.readChunkRole {
  color: var(--accent);
  font-size: 0.7rem;
  font-weight: 900;
}

.listenVocab.readVocab {
  grid-template-columns: 1fr;
}

.readUsage {
  flex-basis: 100%;
  margin: 2px 0 0;
  color: var(--accent-strong);
  font-size: 0.84rem;
  font-weight: 800;
}

.readExample {
  flex-basis: 100%;
  margin-top: 4px;
  padding: 8px 10px;
  border-radius: 10px;
  background: #fff;
}

.readExample .rubyHanzi,
.readExample .rubyPunct {
  font-size: 1.02rem;
}
```

- [ ] **Step 4: 테스트·빌드를 확인한다**

Run: `cd $W && npm test && npx vite build --outDir "$SCRATCH/dist-check" --emptyOutDir`
Expected: 테스트 pass, 빌드 성공

- [ ] **Step 5: 브라우저에서 독해 탭을 확인한다** (dev 서버가 꺼졌으면 Task 7 Step 5처럼 다시 켠다)

데스크톱 폭과 `resize_window` 390×844 두 번 본다. «독해» 탭에서:
- 탭 6개가 한 줄, 글자가 잘리지 않는다(390px).
- 41번: 보기 A~F 중 E가 흐리고 «예시», 눌리지 않는다. «병음 보기»를 켜면 한자 아래 병음이 나오고, 새로고침 뒤에도 켜져 있다.
- 41번에서 틀린 보기를 고르면 «아쉬워요 · 정답은 C», 이어 읽기(두 문장 대화), 정답 근거·오답 이유·끊어 읽기·단어·문법이 나온다.
- 52번(2부분): 빈칸이 «（　　）», 단어 보기 6개가 줄바꿈되고, 답을 고르면 빈칸에 정답 단어가 초록으로 채워진다. «아쉬워요 · 정답은 D 舒服» 형태.
- 56번: A·B 화자 표시와 빈칸이 B줄에.
- 64번(긴 지문): 390px에서 가로 스크롤 없이 줄바꿈된다.
- «고르지 않고 해설 보기» → 해설이 열리고 «이 문제 다시 풀기»로 되돌아간다.
- 단어 «담기»를 누르면 «담음», 같은 한자가 다른 문항 해설에 나오면 거기서도 «담음».
- 집계 «맞힘·틀림·모름»이 고른 대로 바뀌고 새로고침 뒤에도 남는다.
- javascript_tool로 `localStorage.setItem('sungmi-vocab-reading-prefs-v1', '{"testId":"없음","part":9}')` 뒤 새로고침 → H31001 전체로 열린다.
- 콘솔 오류 없음.

- [ ] **Step 6: 커밋한다**

```bash
cd $W && git add src/Reading.jsx src/main.jsx src/styles.css
git commit -m "Add HSK3 reading tab with explanation-level answers

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: 단어장 «내 단어장» 칩과 랜덤 학습 «내 단어장만»

**Files:**
- Modify: `src/main.jsx` (`HiddenAnswer`, `VocabList`, `StudyCard`, `App`)
- Modify: `src/styles.css` (내 단어장 목록·카드 스타일)

**Interfaces:**
- Consumes: `MINE_LESSON`, `mineToStudyItems`, `useMyVocab` (Task 6)
- Produces: `VocabList({ items, mineItems, onRemoveMine, canSpeak, speakingText, onSpeak })`, `StudyCard({ …기존, mineToggle })`

- [ ] **Step 1: import와 담은 카드 상세를 더한다**

`src/main.jsx` 머리:

```jsx
import { Eye, Search, Shuffle, Sparkles, Volume2, X } from 'lucide-react';
import { MINE_LESSON, mineToStudyItems, useMyVocab } from './myVocab';
```

`function HiddenAnswer` 바로 위에 넣는다:

```jsx
// 내 단어장 카드는 담을 때 같이 저장한 용법·설명·예문·출처를 정답과 함께 보여줍니다.
function MineDetails({ card }) {
  if (!card.note && !card.exampleZh && !card.source) return null;
  return (
    <div className="mineDetails">
      {card.note ? <p className="mineNote">{card.note}</p> : null}
      {card.exampleZh ? (
        <div className="mineExample">
          <p className="mineExampleZh">{card.exampleZh}</p>
          {card.examplePinyin ? <p className="vocabPinyin">{card.examplePinyin}</p> : null}
          {card.exampleKo ? <p className="vocabMeaning">{card.exampleKo}</p> : null}
        </div>
      ) : null}
      {card.source ? <p className="mineSource">{card.source}</p> : null}
    </div>
  );
}
```

`HiddenAnswer`의 `answerRows.map(...)` 닫는 줄 바로 뒤, `</div>` 앞에 넣는다:

```jsx
      {card.mineKey ? <MineDetails card={card} /> : null}
```

- [ ] **Step 2: 단어장에 «내 단어장» 칩을 넣는다**

`function VocabList`를 아래처럼 바꾼다 (검색창·목록 마크업은 기존 그대로, 바뀐 곳만 표시):

```jsx
function VocabList({ items, mineItems, onRemoveMine, canSpeak, speakingText, onSpeak }) {
  const [query, setQuery] = useState('');
  const [lesson, setLesson] = useState('전체');

  const lessons = useMemo(() => buildLessonChips(items), [items]);
  // «내 단어장»은 단원이 아니라 내가 담은 목록이라 «전체» 바로 뒤에 따로 둡니다.
  const chips = useMemo(() => [lessons[0], MINE_LESSON, ...lessons.slice(1)], [lessons]);
  const showingMine = lesson === MINE_LESSON;

  const visibleItems = useMemo(() => {
    const needle = normalizeForSearch(query);
    const pool = showingMine ? mineItems : items;

    return pool.filter((item) => {
      if (!showingMine && !matchesLessonChip(item, lesson)) return false;
      if (!needle) return true;
      return (
        normalizeForSearch(item.hanzi).includes(needle) ||
        normalizeForSearch(item.pinyin).includes(needle) ||
        normalizeForSearch(item.meaningKo).includes(needle)
      );
    });
  }, [items, mineItems, showingMine, lesson, query]);
```

칩 목록 렌더링은 `lessons.map` → `chips.map`, 라벨을 바꾼다:

```jsx
          {chips.map((option) => (
            <button
              key={option}
              type="button"
              className={`lessonChip ${lesson === option ? 'active' : ''}`}
              onClick={() => setLesson(option)}
            >
              {option === MINE_LESSON ? `${MINE_LESSON} ${mineItems.length}` : option}
            </button>
          ))}
```

`vocabTexts` 안 `vocabMeaning` 줄 뒤에 더한다:

```jsx
                    {item.mineKey && item.note ? <p className="mineNote">{item.note}</p> : null}
                    {item.mineKey && item.exampleZh ? (
                      <p className="mineExampleZh">
                        {item.exampleZh} <span>{item.exampleKo}</span>
                      </p>
                    ) : null}
                    {item.mineKey && item.source ? <p className="mineSource">{item.source}</p> : null}
```

`return ( <li key={item.id}> … </li> );` 블록 전체를 아래로 바꾼다 (빼기 버튼 추가):

```jsx
              return (
                <li key={item.id} className={item.mineKey ? 'mineRow' : undefined}>
                  {speakable ? (
                    <button
                      type="button"
                      className={`vocabRow vocabRowSpeak ${speakingText === item.hanzi ? 'speaking' : ''}`}
                      onClick={() => onSpeak(item.hanzi)}
                      aria-label={`${item.hanzi} 발음 듣기`}
                    >
                      {body}
                    </button>
                  ) : (
                    <div className="vocabRow">{body}</div>
                  )}
                  {item.mineKey ? (
                    <button
                      type="button"
                      className="mineRemove"
                      onClick={() => onRemoveMine(item.mineKey)}
                      aria-label={`${item.hanzi} 내 단어장에서 빼기`}
                    >
                      <X size={14} /> 빼기
                    </button>
                  ) : null}
                </li>
              );
```

빈 목록 문구:

```jsx
          <p className="listEmpty">
            {showingMine && !mineItems.length ? '해설에서 ＋ 담기를 누르면 여기에 모여요.' : '검색 결과가 없어요.'}
          </p>
```

- [ ] **Step 3: 랜덤 학습에 «내 단어장만»을 넣는다**

`StudyCard` 시그니처에 `mineToggle`을 더하고 `cardMeta`를 바꾼다:

```jsx
function StudyCard({ card, promptType, revealed, onReveal, onNext, canSpeak, speaking, onSpeak, mineToggle }) {
```

```jsx
      <div className="cardMeta">
        <span>{card.itemType}</span>
        {mineToggle}
        <span>출제: {PROMPT_LABELS[promptType]}</span>
      </div>
```

`App`에서 `const studyItems = useMemo(...)` 바로 아래에 넣고, 기존 `currentIndex`·`promptType` 초기값을 `pool` 기준으로 바꾼다:

```jsx
  const mine = useMyVocab();
  const mineItems = useMemo(() => mineToStudyItems(mine.items), [mine.items]);
  const [mineOnly, setMineOnly] = useState(() => loadJson('sungmi-vocab-study-mine-v1', false) === true);
  // 담은 것이 없으면 «내 단어장만»은 켜지지 않습니다. 켜 둔 채 마지막 항목을 빼면 꺼집니다.
  const studyMine = mineOnly && mineItems.length > 0;
  const pool = studyMine ? mineItems : studyItems;
```

```jsx
  const [currentIndex, setCurrentIndex] = useState(() => randomIndex(pool.length));
  const [promptType, setPromptType] = useState(() => resolvePromptType(pool[currentIndex], promptMode));
```

> 주의: 기존 코드는 `promptMode` 상태가 `currentIndex`보다 먼저 선언되어 있다. 위 두 줄은 `promptMode` 선언 뒤에 둔다.

효과 두 개를 기존 `saveJson` 효과들 옆에 더한다:

```jsx
  useEffect(() => {
    if (mineOnly && !mineItems.length) setMineOnly(false);
  }, [mineOnly, mineItems.length]);

  useEffect(() => {
    saveJson('sungmi-vocab-study-mine-v1', mineOnly);
  }, [mineOnly]);
```

`const currentCard = studyItems[currentIndex] ?? studyItems[0];` → 아래로 바꾸고, 출제 칸이 빈 카드를 막는다:

```jsx
  const currentCard = pool[currentIndex] ?? pool[0];
  // 카드가 바뀌었는데(예: 내 단어장에서 뺌) 출제 칸이 비어 있으면 있는 칸으로 보여줍니다.
  const cardPrompts = availablePromptTypes(currentCard);
  const shownPrompt = cardPrompts.includes(promptType) ? promptType : cardPrompts[0] ?? 'hanzi';
```

`moveNext` 안의 `studyItems`를 `pool`로 바꾼다:

```jsx
  function moveNext() {
    const nextIndex = randomIndex(pool.length, currentIndex);
    const nextCard = pool[nextIndex];
    setCurrentIndex(nextIndex);
    setPromptType(resolvePromptType(nextCard, promptMode));
    setRevealed(false);
    setTodayCountState((prev) => {
      const normalized = prev.day === todayKey ? prev : { day: todayKey, count: 0 };
      return { ...normalized, count: normalized.count + 1 };
    });
  }
```

`moveNext` 아래에 토글 함수를 더한다:

```jsx
  function toggleMineOnly() {
    const next = !studyMine;
    const nextPool = next ? mineItems : studyItems;
    const nextIndex = randomIndex(nextPool.length);
    setMineOnly(next);
    setCurrentIndex(nextIndex);
    setPromptType(resolvePromptType(nextPool[nextIndex], promptMode));
    setRevealed(false);
  }
```

키보드 처리기의 `promptType !== 'meaningKo'`를 `shownPrompt !== 'meaningKo'`로 바꾼다.

렌더링에서 `StudyCard`와 `VocabList`를 바꾼다:

```jsx
        <StudyCard
          card={currentCard}
          promptType={shownPrompt}
          revealed={revealed}
          onReveal={() => setRevealed(true)}
          onNext={moveNext}
          canSpeak={canSpeak}
          speaking={Boolean(speakingText)}
          onSpeak={handleSpeak}
          mineToggle={
            <button
              type="button"
              className={`mineOnlyToggle${studyMine ? ' active' : ''}`}
              onClick={toggleMineOnly}
              disabled={!mineItems.length}
              aria-pressed={studyMine}
            >
              내 단어장만 {mineItems.length}
            </button>
          }
        />
```

```jsx
        <VocabList
          items={studyItems}
          mineItems={mineItems}
          onRemoveMine={mine.remove}
          canSpeak={hasChineseVoice}
          speakingText={speakingText}
          onSpeak={handleSpeak}
        />
```

- [ ] **Step 4: 스타일을 더한다**

`src/styles.css` 독해 스타일(Task 8) 뒤, `.listenNav {` 앞에 넣는다:

```css
/* 내 단어장 (단어장 칩·랜덤 학습) */
.mineRow {
  display: flex;
  align-items: stretch;
  gap: 6px;
}

.mineRow > .vocabRow {
  flex: 1;
  min-width: 0;
}

.mineRemove {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 0 12px;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.86);
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 900;
}

.mineNote,
.mineSource,
.mineExampleZh {
  margin: 2px 0 0;
  font-size: 0.8rem;
  font-weight: 800;
}

.mineNote {
  color: var(--accent-strong);
}

.mineSource {
  color: var(--muted);
  font-size: 0.72rem;
}

.mineExampleZh {
  font-size: 0.92rem;
  font-weight: 900;
}

.mineExampleZh span {
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 800;
}

.mineDetails {
  display: grid;
  gap: 4px;
  padding: 10px 12px;
  border-radius: 14px;
  background: #fbf5ee;
  text-align: left;
}

.mineDetails p {
  margin: 0;
}

.mineOnlyToggle {
  min-height: 28px;
  padding: 4px 10px;
  border: 1px solid var(--accent);
  border-radius: 999px;
  background: #fff;
  color: var(--accent-strong);
  font-size: 0.78rem;
  font-weight: 900;
}

.mineOnlyToggle.active {
  border-color: transparent;
  background: var(--accent-strong);
  color: #fff8ef;
}

.mineOnlyToggle:disabled {
  opacity: 0.45;
  cursor: default;
}
```

- [ ] **Step 5: 테스트·빌드를 확인한다**

Run: `cd $W && npm test && npx vite build --outDir "$SCRATCH/dist-check" --emptyOutDir`
Expected: 테스트 pass, 빌드 성공

- [ ] **Step 6: 브라우저에서 확인한다** (390px와 데스크톱)

javascript_tool로 `localStorage.removeItem('sungmi-vocab-mine-v1')` 후 새로고침해서 빈 상태부터:
- 랜덤 학습 «내 단어장만 0»이 흐리고 눌리지 않는다. 단어장 «내 단어장 0» 칩 → «해설에서 ＋ 담기를 누르면 여기에 모여요.»
- 독해 63번에서 단어 하나와 문법 `虽然A，但是B`(또는 그 문항의 문법 하나)를 담는다. 듣기 25번에서 `书店`을 담는다.
- 단어장 «내 단어장 3»: 최근 담은 순, 출처(«H31001 독해 63번»), 용법·예문, 패턴은 종류 «패턴»과 설명·예문. 검색이 이 목록 안에서 된다. «전체»에는 담은 항목이 따로 섞여 나오지 않는다.
- 랜덤 학습 «내 단어장만 3» 켜기 → 카드가 담은 것에서만 나온다. 정답을 열면 예문·출처가 보인다. 패턴 카드는 병음 출제가 나오지 않는다(«병음만» 모드에서도 한자로 나온다).
- 새로고침 뒤 토글이 켜진 채로 남는다.
- **Review Focus 3**: 토글을 켠 채 단어장에서 세 개를 모두 «빼기» → 랜덤 학습으로 돌아가면 토글이 꺼져 있고(«내 단어장만 0»), 일반 카드가 나오며 빈 출제 칸이 없다.
- **Review Focus 2**: 독해에서 담은 단어를 단어장에서 빼면 독해 해설로 돌아갔을 때 «담기»로 돌아와 있다.
- 성조 «시험보기» 범위 칩에 «내 단어장»이 없다.
- 콘솔 오류 없음.

- [ ] **Step 7: 커밋한다**

```bash
cd $W && git add src/main.jsx src/styles.css
git commit -m "Show collected words in vocab list and random study

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: H31002~H31005 해설 쓰기·검수와 전체 조립

**Files:**
- Create (저장소 밖): `$WORK/H3100{2..5}/enrich-41-50.json`, `enrich-51-60.json`, `enrich-61-70.json`
- Create: `public/reading/H31002.json` … `H31005.json`
- Modify: `src/data/reading-index.json`, `src/data/vocab.json`

**Interfaces:**
- Consumes: Task 4의 쓰기·검수 프롬프트(그대로, `{ID}`만 바꿈), `assemble.py`
- Produces: 다섯 회차 데이터와 단어장 «HSK3 독해» 단원 전체

- [ ] **Step 1: 해설 쓰기 에이전트 넷을 한 메시지로 동시에 보낸다** — Task 4 Step 1 프롬프트, `{ID}` = H31002, H31003, H31004, H31005. 서로 다른 회차 폴더만 쓰고 `--check`만 돌리므로 겹치지 않는다.

- [ ] **Step 2: 네 회차 검사를 직접 확인한다**

Run: `cd $W && for t in H31002 H31003 H31004 H31005; do $PY tools/reading/assemble.py $t --work $WORK --repo . --check --show-readings || echo "!! $t"; done`
Expected: 네 번 모두 `검사 통과`. `?` 목록을 훑어 틀린 병음을 고친다.

- [ ] **Step 3: 검수 에이전트 넷을 한 메시지로 동시에 보낸다** — Task 4 Step 3 프롬프트, `{ID}` = H31002~H31005. 각 보고(고친 문항 목록)를 모아 둔다.

- [ ] **Step 4: 다섯 회차를 한 번에 조립한다**

Run: `cd $W && $PY tools/reading/assemble.py H31001 H31002 H31003 H31004 H31005 --work $WORK --repo . --show-readings`
Expected: `회차 5개를 썼고, 단어장에 «HSK3 독해» 단어 N개를 넣었습니다.`

```bash
cd $W && cat src/data/reading-index.json && ls -la public/reading/ && git diff --stat
$PY -m unittest discover -s tools/reading && npm test
```

Expected: 목록 5개(count 30), JSON 5개(각 100~250KB), 테스트 모두 통과.

- [ ] **Step 5: 커밋한다**

```bash
cd $W && git add public/reading src/data/reading-index.json src/data/vocab.json
git commit -m "Add H31002-H31005 reading items with explanations

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: 마무리 확인과 넘겨주기

**Files:**
- Modify: `/Users/sungmi/LLM_wiki/90_Daily/97_Log/Log-26-10-12.md` (작업 로그, 13:32 항목)

- [ ] **Step 1: 전체 테스트·빌드**

Run: `cd $W && $PY -m unittest discover -s tools/reading && npm test && npx vite build --outDir "$SCRATCH/dist-check" --emptyOutDir && git status --short`
Expected: 모두 통과, `git status`에 `dist/`나 다른 변경 없음

- [ ] **Step 2: 브라우저 마지막 점검** (390px·데스크톱)

- 독해: 다섯 회차를 바꿔 가며 각 부분 첫 문항이 열린다. H31004 55번·60번(빈칸이 줄 처음), H31002 67번(지문 첫 줄), H31003 65번(따옴표)이 원문대로 보인다. H31004 70번 긴 지문이 390px에서 가로 스크롤 없이 보인다.
- 듣기: 문항 재생·되풀이·이어 듣기·대본·해설이 전과 같다.
- 단어장: «HSK3 독해» 칩이 «HSK3 듣기» 뒤에 있다. 성조 시험 범위에도 «HSK3 독해»가 있다.
- **Review Focus 5**: dev 서버에서 `public/reading/H31005.json`을 잠시 `H31005.json.bak`으로 바꾸고 새로고침 뒤 H31005를 고르면 오류 문구가 나오고 앱은 멈추지 않는다(Vercel에서는 «… 불러오지 못했어요 (404)», vite dev 서버는 없는 파일에 index.html을 돌려줘 JSON 해석 오류 문구일 수 있다). 이름을 되돌리고 다른 회차를 골랐다가 H31005를 다시 고르면 열린다.
- 콘솔 오류 없음.

- [ ] **Step 3: 작업 로그를 고친다**

`Log-26-10-12.md`를 다시 읽고 `### 13:32 🔵 — chinaword HSK3 독해 탭 추가 (claude)` 항목의 `- 상태:` 줄을 바꾸고 결과 줄을 더한다(다른 항목은 건드리지 않는다):

```markdown
- 상태: 완료(브랜치) — main 병합·배포는 성미님 확인 대기
- 결과: worktree `~/worktrees/chinaword-hsk-reading` 브랜치 `claude/hsk-reading-tab`. 독해 탭(H31001~H31005, 150문항, 정답 근거·오답 이유·끊어 읽기·단어·문법), 해설 «＋ 담기» → 단어장 «내 단어장» 칩·랜덤 학습 «내 단어장만»(이 기기 저장, `src/myVocab.js`에 저장 격리). 단어장 «HSK3 독해» N개. 도구 `tools/reading/`(paper·assemble·README), 테스트 파이썬 N개·node N개 통과
- 이어갈 일: 성미님이 브랜치 확인 → main 병합(Vercel 배포). 다음 작업: 듣기 해설 «문항 해설형», 로그인·사용자별 저장
```

- [ ] **Step 4: 성미님께 넘긴다**

superpowers:finishing-a-development-branch 스킬로 병합 방식을 고른다. `main` 병합·푸시는 성미님이 고른 뒤에만 한다. 병합 뒤에는 Drive 원본에서 `git pull`이 아니라 `git -C "$DRIVE" merge --ff-only claude/hsk-reading-tab`(같은 저장소의 브랜치)로 맞추고, `git worktree remove ~/worktrees/chinaword-hsk-reading`로 정리한다.
