#!/usr/bin/env python3
"""듣기·독해 핵심 단어 보정과 검사.

auto_enrich는 사전에서 한글 뜻을 못 찾은 토큰을 예전에 «뜻 = 한자»로, 품사를 못 정한 토큰을 «단어»로 채웠고,
jieba가 두 단어를 붙이거나(比较忙) 잘못 끊은(铅笔画) 토큰도 그대로 담았다. 원본 작업 폴더(~/hsk-*-work)는
고치지 않고, 이 보정 사전(vocab_fixes.json)을 조립 단계에서 적용한다.

  - tools/reading/assemble.py: 해설 단어를 조립할 때 fix_vocab을 거치고, vocab_problems로 검사한다.
  - tools/listening/assemble.py: 같은 방식.
  - tools/auto_enrich.py: 새로 만드는 단어에도 fix_vocab을 거치고, 한글 뜻이 없으면 한자로 채우지 않는다.

듣기 공개 데이터는 H31006 이후 회차를 assemble.py로 다시 만들 수 없어(대본 손질 이력), 아래 명령으로
public/listening/*.json의 단어와 단어장 «HSK3 듣기» 단원만 보정한다. 몇 번 돌려도 결과가 같다.

  vocab_fixes.py --repo . --apply-listening   # 듣기 공개 데이터·단어장 보정
  vocab_fixes.py --repo .                     # 듣기·독해 공개 데이터에 남은 문제 개수만 보기
"""
import argparse
import json
import re
import sys
from pathlib import Path

FIXES_PATH = Path(__file__).with_name('vocab_fixes.json')
HANGUL = re.compile('[가-힣]')
VOCAB_KEYS = ('hanzi', 'pinyin', 'partOfSpeech', 'meaningKo')
VOCAB_LIMIT = 8
BANNED_PART = '단어'
READING_LESSON = 'HSK3 독해'


def has_hangul(text):
    return bool(HANGUL.search(text or ''))


def load_fixes(path=FIXES_PATH):
    return json.loads(Path(path).read_text(encoding='utf-8'))


_FIXES = None


def fixes():
    global _FIXES
    if _FIXES is None:
        _FIXES = load_fixes()
    return _FIXES


def _part(part_id, table):
    """split·items가 가리키는 단어. '多#남짓'처럼 # 뒤는 같은 한자의 다른 뜻 구분이다."""
    fields = table['parts'].get(part_id) or table['words'].get(part_id)
    if fields is None:
        raise KeyError(f'vocab_fixes.json: parts·words에 없는 단어 {part_id}')
    return {'hanzi': part_id.split('#', 1)[0], **{key: fields[key] for key in VOCAB_KEYS[1:]}}


def fix_vocab(vocab, where=None, table=None):
    """핵심 단어 목록에 보정 사전을 적용한다. where: 'reading/H31006/52' 같은 문항 주소.

    같은 한자는 하나만 남긴다(앞의 것). 나눠서 8개를 넘으면 나눠 생긴 단어를 뒤에서부터 뺀다
    (원래 고른 단어는 남긴다).
    """
    table = table or fixes()
    local = table.get('items', {}).get(where or '', {})
    out, seen = [], set()
    for entry in vocab or []:
        hanzi = entry.get('hanzi', '')
        if hanzi in local:
            replaced, derived = [_part(part, table) for part in local[hanzi]], True
        elif hanzi in table['split']:
            replaced, derived = [_part(part, table) for part in table['split'][hanzi]], True
        elif hanzi in table['words']:
            replaced, derived = [{**entry, **{key: table['words'][hanzi][key] for key in VOCAB_KEYS[1:]}}], False
        else:
            replaced, derived = [entry], False
        for word in replaced:
            if word['hanzi'] in seen:
                continue
            seen.add(word['hanzi'])
            out.append((word, derived))
    while len(out) > VOCAB_LIMIT:
        index = max((i for i, (_, derived) in enumerate(out) if derived), default=len(out) - 1)
        out.pop(index)
    return [word for word, _ in out]


def vocab_problems(entry, where):
    """뜻에 한글이 있어야 하고, 품사 «단어»는 쓰지 않는다."""
    problems = []
    here = f'{where} 단어 {entry.get("hanzi")}'
    if not has_hangul(entry.get('meaningKo')):
        problems.append(f'{here}: 뜻(meaningKo)에 한글이 없음 ({entry.get("meaningKo")!r}) → tools/vocab_fixes.json에 보정을 더한다')
    if entry.get('partOfSpeech') == BANNED_PART:
        problems.append(f'{here}: 품사 «{BANNED_PART}»는 쓰지 않음 → tools/vocab_fixes.json에 보정을 더한다')
    return problems


def count_problems(repo):
    """공개 데이터에서 뜻에 한글이 없는 항목, 품사가 «단어»인 항목을 센다."""
    result = {}
    for kind in ('reading', 'listening'):
        no_hangul = banned = 0
        items = set()
        for path in sorted((Path(repo) / 'public' / kind).glob('H*.json')):
            data = json.loads(path.read_text(encoding='utf-8'))
            for item in data['items']:
                vocab = item['explain']['vocab'] if kind == 'reading' else item['vocab']
                for word in vocab:
                    bad = False
                    if not has_hangul(word.get('meaningKo')):
                        no_hangul += 1
                        bad = True
                    if word.get('partOfSpeech') == BANNED_PART:
                        banned += 1
                        bad = True
                    if bad:
                        items.add((data['id'], item['no']))
        result[kind] = {'meaningKo에 한글 없음': no_hangul, "partOfSpeech=='단어'": banned, '문항': len(items)}
    return result


def apply_listening(repo):
    """public/listening/*.json의 단어를 보정하고, 단어장 «HSK3 듣기» 단원을 assemble.py와 같은 규칙으로 다시 넣는다."""
    sys.path.insert(0, str(Path(__file__).parent / 'listening'))
    from assemble import update_vocab  # tools/listening/assemble.py

    tests = []
    for path in sorted((Path(repo) / 'public' / 'listening').glob('H*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        for item in data['items']:
            item['vocab'] = fix_vocab(item['vocab'], f'listening/{data["id"]}/{item["no"]}')
        path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        tests.append(data)
    index = json.loads((Path(repo) / 'src' / 'data' / 'listening-index.json').read_text(encoding='utf-8'))
    order = {entry['id']: position for position, entry in enumerate(index)}
    tests.sort(key=lambda test: order.get(test['id'], len(order)))
    # assemble.py와 똑같이 다시 넣는다(다른 단원에 있는 단어는 빼고 «HSK3 듣기» 단원을 뒤에 붙인다).
    # 파일 안 순서는 원래대로 듣기 → 독해로 둔다. 독해 단원은 이어서 tools/reading/assemble.py가 다시 만든다.
    added = update_vocab(tests, Path(repo))
    path = Path(repo) / 'src' / 'data' / 'vocab.json'
    vocab = json.loads(path.read_text(encoding='utf-8'))
    vocab = [e for e in vocab if e.get('lesson') != READING_LESSON] + [e for e in vocab if e.get('lesson') == READING_LESSON]
    path.write_text(json.dumps(vocab, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return len(tests), added


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', required=True)
    parser.add_argument('--apply-listening', action='store_true', help='듣기 공개 데이터와 단어장 «HSK3 듣기» 단원을 보정한다')
    args = parser.parse_args()
    if args.apply_listening:
        tests, added = apply_listening(args.repo)
        print(f'듣기 회차 {tests}개의 단어를 보정했고, 단어장에 «HSK3 듣기» 단어 {added}개를 다시 넣었습니다.')
    for kind, counts in count_problems(args.repo).items():
        print(kind, json.dumps(counts, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
