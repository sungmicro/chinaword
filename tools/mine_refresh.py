#!/usr/bin/env python3
"""내 단어장 갱신 색인(src/data/mine-refresh.json) 만들기·검사.

내 단어장(src/myVocab.js, localStorage)은 «＋ 담기»·«모르겠어»를 누른 순간의 한자·병음·뜻·품사를 저장한다.
그래서 해설 데이터를 고친 뒤에도(뜻 = 한자, 붙은 토큰 比较忙, 이름+호칭 李先生, 대본 오인식 散 …) 예전에 담은
항목에는 옛 내용이 남는다. 앱은 내 단어장을 불러올 때 이 색인으로 단어 항목을 지금 데이터에 맞춘다
(src/mineRefresh.js). 이 파일은 공개 데이터에서 만들어지므로, 데이터를 고칠 때 함께 다시 만들면 갱신이 따라온다.

색인 (앱이 이미 번들에 넣는 src/data/vocab.json과 함께 쓴다. 독해·듣기 회차 JSON은 받지 않는다)
  senses: [[병음, 뜻, 품사], ...]   아래 base·at이 가리키는 뜻
  base:   {한자: 뜻 번호}           vocab.json에 «단어» 카드가 없는 한자의 기본 뜻(해설에서 가장 많이 쓰인 뜻)
  at:     {문항 주소: {한자: 뜻 번호}}   그 문항 해설의 뜻이 기본 뜻(vocab.json 첫 «단어» 카드, 없으면 base)과 다를 때만
  split:  {예전 토큰: [한자, ...]}    tools/vocab_fixes.json split(나눈 묶음, 빈 목록은 뺀 토큰)
          + tools/mine_moves.json split(해설에는 이미 없는 예전 붙은 토큰)
  moved:  {문항 주소: {예전 단어: [한자, ...]}}  vocab_fixes.json items(그 문항만 나누거나 뺀 것)와
          tools/mine_moves.json moved(대본 오인식 단어 → 고친 단어)를 합친 것. 같은 키면 mine_moves가 이긴다.
          mine_moves에서 뜻을 정한 바꿀 단어(角#자오)는 그 문항의 at에 그 뜻으로 들어간다.
  pinyin: {토큰: {붙은 병음: 나눈 병음}}  tools/sentence_splits.json(문장에서 나눈 토큰). 내 단어장 예문 병음을 고친다.
  base에는 tools/mine_moves.json words(지금 데이터에 없는 예전 단어의 뜻)도 들어간다.
문항 주소: reading/<회차>/<번호>, listening/<회차>/<번호>, writing/<회차>/<번호> (vocab_fixes items와 같은 형식).

  mine_refresh.py --repo .           # 색인을 다시 쓴다
  mine_refresh.py --repo . --check   # 색인이 지금 데이터와 같은지만 본다(다르면 1)

tools/vocab_fixes.py --apply-listening, tools/listening/assemble.py, tools/reading/assemble.py,
tools/auto_enrich.py --vocab-only --repo, tools/writing/generate.py가 공개 데이터를 쓴 뒤 이 색인도 다시 쓴다.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sentence_split import load_splits  # noqa: E402
from vocab_fixes import has_hangul, load_fixes, write_files_atomically  # noqa: E402

INDEX_PATH = Path('src') / 'data' / 'mine-refresh.json'
MOVES_PATH = Path(__file__).with_name('mine_moves.json')
WORD_TYPE = '단어'
ABOUT = ('내 단어장 갱신 색인. tools/mine_refresh.py가 공개 해설 데이터(public/reading·listening·writing), '
         'src/data/vocab.json, tools/vocab_fixes.json(split·items), tools/mine_moves.json, tools/sentence_splits.json에서 만든다. 손으로 고치지 않는다. '
         '앱(src/mineRefresh.js)이 내 단어장을 불러올 때 단어 항목을 지금 데이터의 병음·뜻·품사로 바꾸고, 나뉜 묶음은 조각으로, '
         '예문 병음의 붙은 토큰(bǐjiàománg)은 나눈 병음으로 바꾼다.')


def strip_sense(part_id):
    """'多#많다' → '多' (# 뒤는 vocab_fixes.json에서 같은 한자의 다른 뜻 구분)."""
    return part_id.split('#', 1)[0]


def sense_of(word):
    return (word.get('pinyin') or '', word.get('meaningKo') or '', word.get('partOfSpeech') or '')


def load_questions(repo):
    """{문항 주소: [해설 단어, ...]} — 앱이 «＋ 담기»의 출처로 적는 문항과 같은 단위."""
    repo = Path(repo)
    questions = {}
    for kind in ('reading', 'listening'):
        for path in sorted((repo / 'public' / kind).glob('H*.json')):
            data = json.loads(path.read_text(encoding='utf-8'))
            for item in data['items']:
                vocab = item['explain']['vocab'] if kind == 'reading' else item['vocab']
                questions[f'{kind}/{data["id"]}/{item["no"]}'] = vocab
    writing = repo / 'public' / 'writing' / 'hsk3-all.json'
    if writing.exists():
        for item in json.loads(writing.read_text(encoding='utf-8'))['items']:
            vocab = (item.get('study') or {}).get('vocab')
            if vocab:
                questions[f'writing/{item["exam"]}/{item["no"]}'] = vocab
    return questions


def vocab_base(vocab):
    """한자마다 vocab.json의 첫 «단어» 카드 뜻. 앱(src/mineRefresh.js)과 같은 규칙이어야 한다."""
    base = {}
    for card in vocab:
        if card.get('itemType') == WORD_TYPE and card['hanzi'] not in base:
            base[card['hanzi']] = sense_of(card)
    return base


def merged_moves(fixes, moves):
    """vocab_fixes items 중 다른 단어로 바꾸거나 뺀 것 + mine_moves. 같은 한자의 뜻만 바꾼 것(谢 → 谢#성씨)은 at이 맡는다."""
    out = {}
    for address, table in fixes.get('items', {}).items():
        for hanzi, parts in table.items():
            targets = [strip_sense(part) for part in parts]
            if targets != [hanzi]:
                out.setdefault(address, {})[hanzi] = targets
    for address, table in moves.get('moved', {}).items():
        for hanzi, targets in table.items():
            out.setdefault(address, {})[hanzi] = list(targets)  # '角#자오'처럼 뜻을 정한 것은 build_index가 at으로 옮긴다
    return {address: dict(sorted(table.items())) for address, table in sorted(out.items())}


class IndexProblems(Exception):
    def __init__(self, problems):
        super().__init__(f'색인 문제 {len(problems)}개')
        self.problems = problems


def build_index(repo, fixes=None, moves=None):
    repo = Path(repo)
    fixes = fixes if fixes is not None else load_fixes()
    moves = moves if moves is not None else json.loads(MOVES_PATH.read_text(encoding='utf-8'))
    vocab = json.loads((repo / 'src' / 'data' / 'vocab.json').read_text(encoding='utf-8'))
    questions = load_questions(repo)
    problems = []

    from_vocab = vocab_base(vocab)
    counts = {}
    for address in questions:
        for word in questions[address]:
            counts.setdefault(word['hanzi'], Counter())[sense_of(word)] += 1

    senses, numbers = [], {}

    def number(sense):
        if sense not in numbers:
            numbers[sense] = len(senses)
            senses.append(list(sense))
        return numbers[sense]

    # 기본 뜻: vocab.json에 없는 한자만 색인에 둔다(가장 많이 쓰인 뜻, 같으면 먼저 나온 뜻).
    base = {}
    for hanzi in sorted(counts):
        if hanzi not in from_vocab:
            base[hanzi] = number(counts[hanzi].most_common(1)[0][0])

    # 사람이 정한 예전 단어(tools/mine_moves.json words): 지금 데이터에 없는 한자만 기본 뜻으로 둔다.
    tagged = {}
    for key, fields in moves.get('words', {}).items():
        sense = sense_of(fields)
        if '#' in key:
            tagged[key] = sense
        elif key in from_vocab or key in base:
            problems.append(f'mine_moves words {key}: 지금 데이터에 이미 있음(표에서 뺀다)')
        else:
            base[key] = number(sense)
    base = dict(sorted(base.items()))

    def default(hanzi):
        return from_vocab.get(hanzi) or (tuple(senses[base[hanzi]]) if hanzi in base else None)

    at = {}
    for address, words in questions.items():
        for word in words:
            sense = sense_of(word)
            if sense != default(word['hanzi']):
                at.setdefault(address, {})[word['hanzi']] = number(sense)

    split = {token: [strip_sense(part) for part in parts] for token, parts in fixes.get('split', {}).items()}
    for token, parts in moves.get('split', {}).items():
        if token in split:
            problems.append(f'mine_moves split {token}: vocab_fixes.json split에도 있음')
        split[token] = [strip_sense(part) for part in parts]
    split = dict(sorted(split.items()))
    moved = merged_moves(fixes, moves)
    # 뜻을 정한 바꿀 단어(角#자오)는 그 문항에서만 그 뜻으로 보이게 at에 넣는다(다시 돌려도 같은 뜻).
    for address, table in moved.items():
        for hanzi, targets in table.items():
            for target in targets:
                if '#' not in target:
                    continue
                if target not in tagged:
                    problems.append(f'moved {address} {hanzi} → {target}: mine_moves words에 뜻이 없음')
                    continue
                plain = strip_sense(target)
                if plain in {word['hanzi'] for word in questions.get(address, [])}:
                    problems.append(f'moved {address} {hanzi} → {target}: 그 문항 해설에 {plain}이 이미 있음(# 없이 쓴다)')
                    continue
                at.setdefault(address, {})[plain] = number(tagged[target])
            table[hanzi] = [strip_sense(target) for target in targets]

    # --- 검사 ---
    for index, (pinyin, meaning, _) in enumerate(senses):
        if not pinyin.strip() or not has_hangul(meaning):
            problems.append(f'뜻 {index}: 병음이 비었거나 뜻에 한글이 없음 ({pinyin!r}, {meaning!r})')
    for card in vocab:
        if card.get('itemType') == WORD_TYPE and not has_hangul(card.get('meaningKo')):
            problems.append(f'vocab.json {card.get("id")} {card["hanzi"]}: 뜻에 한글이 없음')
    present = {address: {word['hanzi'] for word in words} for address, words in questions.items()}
    for token, targets in split.items():
        if token in from_vocab:
            problems.append(f'split {token}: vocab.json에 «단어» 카드가 있음')
        for address, hanzi in present.items():
            if token in hanzi:
                problems.append(f'split {token}: {address} 해설에 아직 있음(나눈 묶음은 해설에 없어야 한다)')
        for target in targets:
            if target in split:
                problems.append(f'split {token} → {target}: 조각이 다시 split에 있음(두 번 돌리면 결과가 달라진다)')
            if default(target) is None:
                problems.append(f'split {token} → {target}: 조각의 뜻을 찾을 수 없음(해설·vocab.json에 없음)')
    for address, table in moved.items():
        if address not in questions:
            problems.append(f'moved {address}: 그런 문항이 없음')
            continue
        for hanzi, targets in table.items():
            if hanzi in present[address]:
                problems.append(f'moved {address} {hanzi}: 그 문항 해설에 아직 있음')
            for target in targets:
                if target in table or target in split:
                    problems.append(f'moved {address} {hanzi} → {target}: 바꾼 단어가 다시 옮길 대상임')
                if target not in present[address] and default(target) is None and target not in at.get(address, {}):
                    problems.append(f'moved {address} {hanzi} → {target}: 바꾼 단어의 뜻을 찾을 수 없음')
    if problems:
        raise IndexProblems(problems)

    return {
        '_about': ABOUT,
        'senses': senses,
        'base': base,
        'at': {address: dict(sorted(table.items())) for address, table in sorted(at.items())},
        'split': split,
        'moved': moved,
        'pinyin': load_splits(),
    }


def index_text(index):
    """한 줄에 한 항목(문항 하나·뜻 하나)씩. 다시 만들 때 diff로 무엇이 바뀌었는지 보이게 한다."""
    def line(value):
        return json.dumps(value, ensure_ascii=False, separators=(',', ':'))

    def block(name, mapping, last=False):
        rows = [f'  {line(key)}:{line(value)}' for key, value in mapping.items()]
        return f' {line(name)}:{{\n' + ',\n'.join(rows) + ('\n }' if rows else '}') + ('' if last else ',')

    parts = ['{', f' "_about":{line(index["_about"])},', ' "senses":[']
    parts.append(',\n'.join(f'  {line(sense)}' for sense in index['senses']))
    parts.append(' ],')
    parts.append(block('base', index['base']))
    parts.append(block('at', index['at']))
    parts.append(block('split', index['split']))
    parts.append(block('moved', index['moved']))
    parts.append(block('pinyin', index['pinyin'], last=True))
    parts.append('}')
    return '\n'.join(parts) + '\n'


def write_mine_refresh(repo):
    """색인을 다시 만들어 쓴다. 바뀐 것이 없으면 쓰지 않는다. 문제가 있으면 IndexProblems."""
    path = Path(repo) / INDEX_PATH
    text = index_text(build_index(repo))
    if path.exists() and path.read_text(encoding='utf-8') == text:
        return False
    write_files_atomically({path: text})
    return True


def check_mine_refresh(repo):
    path = Path(repo) / INDEX_PATH
    return path.exists() and path.read_text(encoding='utf-8') == index_text(build_index(repo))


def refresh_after_write(repo):
    """공개 데이터를 쓴 도구가 마지막에 부른다. 문제가 있으면 색인은 그대로 두고 알리기만 한다(False).

    듣기(vocab_fixes --apply-listening)와 독해(reading/assemble.py)를 차례로 돌리는 중간에는 다른 쪽 데이터가
    아직 옛 보정 상태라 문제가 날 수 있다. 마지막 단계에서 통과하면 된다. 남은 문제는 npm test
    (src/mineRefresh.test.js)와 tools/test_mine_refresh.py가 막는다.
    """
    try:
        changed = write_mine_refresh(repo)
    except IndexProblems as error:
        for problem in error.problems:
            print('  ! ' + problem)
        print(f'내 단어장 갱신 색인({INDEX_PATH})은 그대로 두었습니다. 다른 데이터도 다시 만든 뒤에도 남으면 '
              'tools/mine_moves.json·vocab_fixes.json을 고치고 tools/mine_refresh.py --repo .를 돌리세요.')
        return False
    print(f'내 단어장 갱신 색인({INDEX_PATH})을 {"다시 썼습니다" if changed else "확인했습니다(바뀐 것 없음)"}.')
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', required=True)
    parser.add_argument('--check', action='store_true', help='색인이 지금 데이터와 같은지만 본다')
    args = parser.parse_args()
    if args.check:
        try:
            same = check_mine_refresh(args.repo)
        except IndexProblems as error:
            for problem in error.problems:
                print('  ! ' + problem)
            return 1
        print('색인이 지금 데이터와 같습니다.' if same else f'색인({INDEX_PATH})이 지금 데이터와 다릅니다. --check 없이 다시 돌리세요.')
        return 0 if same else 1
    return 0 if refresh_after_write(args.repo) else 1


if __name__ == '__main__':
    raise SystemExit(main())
