#!/usr/bin/env python3
"""듣기 대본 보정 (음성 인식 오류 바로잡기).

H31006 이후 회차의 대본은 시험지에 없어 공식 음원을 Whisper로 받아 적은 것이라(bootstrap.py) 인식 오류가 남아 있다
(可乐 ← 渴了, 跟班礼 ← 跟班里 등). 원본 작업 폴더(~/hsk-listening-work)는 고치지 않고, 이 보정 파일
(script_fixes.json)을 공개 데이터를 만들거나 보정하는 모든 경로에서 적용한다. 몇 번 돌려도 결과가 같다.

  - tools/vocab_fixes.py --apply-listening: 공개 듣기 데이터에 적용한 뒤 핵심 단어를 보정한다.
  - tools/listening/assemble.py: 회차를 조립한 뒤 적용한다.
  - tools/auto_enrich.py --vocab-only --repo: 공개 데이터의 단어를 바꿀 때 적용한다(보정한 문항은 보정 단어를 쓴다).

script_fixes.json 형식 — 키는 '<회차>/<번호>':
  {
    "reason": "근거(보기·정답·두 번 읽기·다시 들은 결과 등)",
    "script": {"2": {"from": "고치기 전 그 줄의 한자", "words": [["太","tài"], ...], "ko": "해석"}},
    "lineCount": 3,                                                    # 고치기 전 대본 줄 수(★·질문 줄 포함)
    "afterLines": ["…", "…"],                                         # 고친 뒤 대본 줄마다의 한자 문장(전체)
    "delete": {"1": "使?"},                                           # 대본이 아닌 줄을 지운다(그 번호의 줄이 이 문장일 때만)
    "statement": {"from": "…", "words": [...], "ko": "…"},          # 2부분 ★ 문장(대본 끝 ★ 줄도 함께)
    "vocab": [{"hanzi", "pinyin", "partOfSpeech", "meaningKo"}, ...],  # 있으면 그 문항 핵심 단어 전체를 바꾼다
    "grammar": [{"pattern", "note"}, ...]                              # 있으면 그 문항 문장 구조 전체를 바꾼다
  }
script·delete의 키는 1부터 세는 원래 대본 줄 번호다. 한 문항은 둘 중 한 상태여야 한다.
  - 고치기 전: 줄 수가 lineCount이고, 번호마다 그 줄이 from(삭제는 그 문장)과 같고, statement가 있으면
    ★ 문장과 대본의 ★ 줄이 둘 다 from과 같다 → 고친다. 고친 결과가 afterLines와 다르면 멈춘다.
  - 이미 고침: 대본 전체 줄이 afterLines와 같고, statement가 있으면 ★ 문장도 고친 문장이다 → 다시 써도 같다.
둘 다 아니면(원본이 바뀌었거나 일부만 고쳐진 상태) 그 문항은 하나도 바꾸지 않고 문제로 알린다. 문항마다 복사본에
적용하고 모든 검사를 통과할 때만 반영하므로, 실패한 문항은 대본·단어·문장 구조가 그대로다.
대본(script·delete·statement)을 고치는 항목은 lineCount와 afterLines가 꼭 있어야 한다.
"""
import copy
import json
import re
from pathlib import Path

FIXES_PATH = Path(__file__).with_name('script_fixes.json')
HANZI = re.compile(r'[一-鿿]')


def load_script_fixes(path=FIXES_PATH):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    return {key: value for key, value in data.items() if not key.startswith('_')}


def joined(words):
    return ''.join(token for token, _ in words)


def _line_problems(line, where):
    problems = []
    for token, pinyin in line['words']:
        if HANZI.search(token) and not pinyin:
            problems.append(f'{where}: "{token}" 병음 없음')
        if not HANZI.search(token) and pinyin and not re.search(r'\d', token):
            problems.append(f'{where}: 문장부호 "{token}"에 병음 "{pinyin}"')
    if not (line.get('ko') or '').strip():
        problems.append(f'{where}: 해석(ko) 없음')
    return problems


def _set(target, line):
    target['words'] = [list(pair) for pair in line['words']]
    target['ko'] = line['ko']


def _fix_lines(item, fix, where, problems):
    """대본 줄·★ 문장 보정과 줄 삭제. «고치기 전»이나 «이미 고침» 상태일 때만 바꾸고, 아니면 문제를 더한다."""
    lines = {int(no): line for no, line in fix.get('script', {}).items()}
    deletes = {int(no): text for no, text in fix.get('delete', {}).items()}
    statement_fix = fix.get('statement')
    if not lines and not deletes and statement_fix is None:
        return
    count, after_lines = fix.get('lineCount'), fix.get('afterLines')
    if not isinstance(count, int) or not isinstance(after_lines, list):
        problems.append(f'{where}: 대본을 고치는 보정에는 lineCount(고치기 전 줄 수)와 afterLines(고친 뒤 줄 문장)가 있어야 함')
        return
    if set(lines) & set(deletes):
        problems.append(f'{where}: 같은 줄을 고치면서 지울 수 없음')
        return
    for no, line in lines.items():
        problems.extend(_line_problems(line, f'{where} {no}줄'))
    if statement_fix is not None:
        problems.extend(_line_problems(statement_fix, f'{where} ★'))
    script = item['script']
    texts = [joined(line['words']) for line in script]
    stars = [index for index, line in enumerate(script) if line['speaker'] == '★']
    statement = item['choices'].get('statement')
    if statement_fix is not None and (statement is None or len(stars) != 1):
        problems.append(f'{where}: ★ 문장이 없는 문항')
        return
    if any(script[no - 1]['speaker'] == '★' for no in lines if 1 <= no <= len(script)):
        problems.append(f'{where}: ★ 문장은 statement로 고친다')
        return

    def text_at(no):
        return texts[no - 1] if 1 <= no <= len(texts) else None

    def statement_is(state):
        if statement_fix is None:
            return True
        want = statement_fix['from'] if state == 'before' else joined(statement_fix['words'])
        return joined(statement['words']) == want and texts[stars[0]] == want  # ★ 문장과 대본 끝 ★ 줄이 함께

    before = (len(texts) == count
              and all(text_at(no) == text for no, text in deletes.items())
              and all(text_at(no) == line['from'] for no, line in lines.items())
              and statement_is('before'))
    after = texts == after_lines and statement_is('after')  # 고친 뒤 대본 전체가 기록과 같아야 한다
    if before == after:  # 둘 다 아니거나(원본이 바뀜·일부만 고침), 둘 다 맞아 구분할 수 없음
        detail = ''.join(f'\n    {no}줄 지금 {text_at(no)} | from {line["from"]}' for no, line in lines.items())
        detail += ''.join(f'\n    {no}줄(삭제) 지금 {text_at(no)} | 지울 문장 {text}' for no, text in deletes.items())
        if statement_fix is not None:
            detail += f'\n    ★ 지금 {joined(statement["words"])} / 대본 ★ 줄 {texts[stars[0]]} | from {statement_fix["from"]}'
        problems.append(f'{where}: 대본이 고치기 전 상태도, 고친 상태도 아님(줄 수 {len(texts)}, lineCount {count}){detail}')
        return

    def shifted(no):
        return no if before else no - sum(1 for gone in deletes if gone < no)

    for no, line in lines.items():
        _set(script[shifted(no) - 1], line)
    if statement_fix is not None:
        _set(statement, statement_fix)
        _set(script[stars[0]], statement_fix)
    if before:
        item['script'] = [line for index, line in enumerate(script, 1) if index not in deletes]
        result = [joined(line['words']) for line in item['script']]
        if result != after_lines:  # 보정 파일 자체가 맞는지: 고친 결과가 기록한 afterLines와 같아야 한다
            problems.append(f'{where}: 고친 결과가 afterLines와 다름\n    결과 {result}\n    기록 {after_lines}')


def apply_script_fixes(test, problems, table=None, test_id=None):
    """test(공개 듣기 회차 dict)에 대본 보정을 적용한다. 반영한 문항 번호 목록을 돌려준다.

    문항마다 복사본에 적용하고, 그 문항에서 문제가 하나도 없을 때만 원래 문항을 바꾼다.
    test_id: test에 'id'가 없을 때 쓰는 회차 번호.
    """
    table = load_script_fixes() if table is None else table
    current_id = test.get('id', test_id)
    by_no = {item['no']: item for item in test['items']}
    fixed = []
    for key, fix in table.items():
        key_test, no = key.split('/')
        if key_test != current_id:
            continue
        where = f'{key_test} {no}번 대본 보정'
        item = by_no.get(int(no))
        if item is None:
            problems.append(f'{where}: 문항 없음')
            continue
        found = []
        work = copy.deepcopy(item)
        _fix_lines(work, fix, where, found)
        if 'vocab' in fix:
            work['vocab'] = [dict(word) for word in fix['vocab']]
        if 'grammar' in fix:
            work['grammar'] = [dict(entry) for entry in fix['grammar']]
        if found:
            problems.extend(found)  # 이 문항은 대본·단어·문장 구조 모두 그대로 둔다
            continue
        item.clear()
        item.update(work)
        fixed.append(int(no))
    return fixed
