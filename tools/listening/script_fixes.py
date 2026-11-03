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
    "delete": {"1": "使?"},                                           # 대본이 아닌 줄을 지운다(그 번호의 줄이 이 문장일 때만)
    "statement": {"from": "…", "words": [...], "ko": "…"},          # 2부분 ★ 문장(대본 끝 ★ 줄도 함께)
    "vocab": [{"hanzi", "pinyin", "partOfSpeech", "meaningKo"}, ...],  # 있으면 그 문항 핵심 단어 전체를 바꾼다
    "grammar": [{"pattern", "note"}, ...]                              # 있으면 그 문항 문장 구조 전체를 바꾼다
  }
script·delete의 키는 1부터 세는 원래 대본 줄 번호다. 한 문항은 둘 중 한 상태여야 한다.
  - 고치기 전: 줄 수가 lineCount이고, 번호마다 그 줄이 from(삭제는 그 문장)과 같다 → 고친다.
  - 이미 고침: 줄 수가 lineCount − 지운 줄 수이고, 지운 줄만큼 당긴 번호의 줄이 고친 문장과 같다 → 다시 써도 같다.
둘 다 아니면(원본이 바뀌었거나 일부만 고쳐진 상태) 그 문항은 하나도 바꾸지 않고 문제로 알린다. 문항마다 복사본에
적용하고 모든 검사를 통과할 때만 반영하므로, 실패한 문항은 대본·단어·문장 구조가 그대로다.
lineCount는 delete가 있으면 꼭 적는다(없으면 줄 수를 검사하지 않는다).
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


def _fix_script(item, fix, where, problems):
    """대본 줄 보정·삭제. 고치기 전이거나 이미 고친 상태일 때만 바꾸고, 아니면 문제를 더한다."""
    lines = {int(no): line for no, line in fix.get('script', {}).items()}
    deletes = {int(no): text for no, text in fix.get('delete', {}).items()}
    count = fix.get('lineCount')
    if not lines and not deletes:
        return
    if deletes and count is None:
        problems.append(f'{where}: delete가 있으면 lineCount(고치기 전 줄 수)를 적어야 함')
        return
    if set(lines) & set(deletes):
        problems.append(f'{where}: 같은 줄을 고치면서 지울 수 없음')
        return
    script = item['script']
    texts = [joined(line['words']) for line in script]
    for no, line in lines.items():
        problems.extend(_line_problems(line, f'{where} {no}줄'))

    def text_at(no):
        return texts[no - 1] if 1 <= no <= len(texts) else None

    def shifted(no):
        return no - sum(1 for gone in deletes if gone < no)

    before = ((count is None or len(texts) == count)
              and all(text_at(no) == text for no, text in deletes.items())
              and all(text_at(no) == line['from'] for no, line in lines.items()))
    after = ((count is None or len(texts) == count - len(deletes))
             and all(text_at(shifted(no)) == joined(line['words']) for no, line in lines.items()))
    if before == after:  # 둘 다 아니거나(원본이 바뀜·일부만 고침), 둘 다 맞아 구분할 수 없음
        detail = ''.join(f'\n    {no}줄 지금 {text_at(no)} | from {line["from"]}' for no, line in lines.items())
        detail += ''.join(f'\n    {no}줄(삭제) 지금 {text_at(no)} | 지울 문장 {text}' for no, text in deletes.items())
        problems.append(f'{where}: 대본이 고치기 전 상태도, 고친 상태도 아님(줄 수 {len(texts)}, lineCount {count}){detail}')
        return
    for no, line in lines.items():
        target = script[(no if before else shifted(no)) - 1]
        if target['speaker'] == '★':
            problems.append(f'{where} {no}줄: ★ 문장은 statement로 고친다')
            return
        _set(target, line)
    if before:
        item['script'] = [line for index, line in enumerate(script, 1) if index not in deletes]


def _fix_statement(item, fix, where, problems):
    line = fix.get('statement')
    if line is None:
        return
    statement = item['choices'].get('statement')
    star = [entry for entry in item['script'] if entry['speaker'] == '★']
    if statement is None or len(star) != 1:
        problems.append(f'{where}: ★ 문장이 없는 문항')
        return
    if joined(statement['words']) not in (line['from'], joined(line['words'])):
        problems.append(f'{where} ★: 고치기 전 문장도 고친 문장도 아님\n    지금 {joined(statement["words"])}\n    from {line["from"]}')
        return
    problems.extend(_line_problems(line, f'{where} ★'))
    _set(statement, line)
    _set(star[0], line)


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
        _fix_script(work, fix, where, found)
        _fix_statement(work, fix, where, found)
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
