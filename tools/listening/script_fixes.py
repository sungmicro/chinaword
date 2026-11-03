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
    "delete": {"1": "使?"},                                           # 대본이 아닌 줄을 지운다(그 문장과 같은 줄)
    "statement": {"from": "…", "words": [...], "ko": "…"},          # 2부분 ★ 문장(대본 끝 ★ 줄도 함께)
    "vocab": [{"hanzi", "pinyin", "partOfSpeech", "meaningKo"}, ...],  # 있으면 그 문항 핵심 단어 전체를 바꾼다
    "grammar": [{"pattern", "note"}, ...]                              # 있으면 그 문항 문장 구조 전체를 바꾼다
  }
script의 키는 1부터 세는 원래 대본 줄 번호(사람이 읽는 표시)이고, 고칠 줄은 문장으로 찾는다: from과 같은 줄,
이미 고쳤으면 고친 문장과 같은 줄. 둘 다 없으면 고치지 않고 문제로 알린다(원본이 바뀐 것이므로 사람이 다시 본다).
"""
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


def _replace(target, line, where, problems):
    """target(words·ko가 있는 dict)을 line으로 바꾼다. 지금 문장이 from도 고친 문장도 아니면 바꾸지 않는다."""
    current, fixed = joined(target['words']), joined(line['words'])
    if current not in (line['from'], fixed):
        problems.append(f'{where}: 대본이 보정 파일의 from과 다름\n    지금 {current}\n    from {line["from"]}')
        return False
    found = _line_problems(line, where)
    if found:
        problems.extend(found)
        return False
    target['words'] = [list(pair) for pair in line['words']]
    target['ko'] = line['ko']
    return True


def apply_script_fixes(test, problems, table=None, test_id=None):
    """test(공개 듣기 회차 dict)에 대본 보정을 적용한다. 고친 문항 번호 목록을 돌려준다.
    test_id: test에 'id'가 없을 때 쓰는 회차 번호."""
    table = load_script_fixes() if table is None else table
    current_id = test.get('id', test_id)
    by_no = {item['no']: item for item in test['items']}
    fixed = []
    for key, fix in table.items():
        test_id, no = key.split('/')
        if test_id != current_id:
            continue
        where = f'{test_id} {no}번 대본 보정'
        item = by_no.get(int(no))
        if item is None:
            problems.append(f'{where}: 문항 없음')
            continue
        for line_no, line in fix.get('script', {}).items():
            # 줄 번호는 원래 대본 기준이다. 지운 줄이 있으면 번호가 밀리므로 문장(from 또는 고친 문장)으로 찾는다.
            target_text = joined(line['words'])
            found = [l for l in item['script'] if l['speaker'] != '★' and joined(l['words']) in (line['from'], target_text)]
            if not found:
                problems.append(f'{where} {line_no}줄: 대본에 from도 고친 문장도 없음\n    from {line["from"]}')
                continue
            _replace(found[0], line, f'{where} {line_no}줄', problems)
        for line_no, text in fix.get('delete', {}).items():
            # 대본이 아닌 줄(문항 번호를 읽은 소리 등)을 지운다. 이미 지웠으면 그대로 둔다.
            item['script'] = [l for l in item['script'] if joined(l['words']) != text]
        if 'statement' in fix:
            statement = item['choices'].get('statement')
            star = [line for line in item['script'] if line['speaker'] == '★']
            if statement is None or len(star) != 1:
                problems.append(f'{where}: ★ 문장이 없는 문항')
            elif _replace(statement, fix['statement'], f'{where} ★', problems):
                star[0]['words'], star[0]['ko'] = [list(p) for p in statement['words']], statement['ko']
        if 'vocab' in fix:
            item['vocab'] = [dict(word) for word in fix['vocab']]
        if 'grammar' in fix:
            item['grammar'] = [dict(entry) for entry in fix['grammar']]
        fixed.append(int(no))
    return fixed
