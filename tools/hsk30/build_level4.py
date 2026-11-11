#!/usr/bin/env python3
"""HSK 3.0(2021 《国际中文教育中文水平等级标准》) 4급 새 단어를 단어장(src/data/vocab.json)에 넣는다.

앱의 HSK1·HSK2·HSK3 단원은 예전 HSK 2.0 기준이다. 이 도구는 HSK 3.0 4급 목록(4급에서 새로 나오는 1000개)만
«HSK4 (3.0)» 단원으로 넣는다. 한자가 이미 단어장에 있는 단어는 넣지 않는다(아래 POLYPHONES는 예외).

파일 (모두 tools/hsk30/)
  level4_raw.json      공식 목록 4급 1000행(한자·병음·품사). `raw`가 공개 저장소 CSV에서 만든다. 손으로 고치지 않는다.
  level4_select.json   넣을 것(add)과 뺀 것(skipped, 이유). `select`가 raw와 지금 vocab.json에서 만든다.
  meanings/level4-meanings-N.json   한국어 뜻. `select`가 빈 칸(meaningKo "")으로 처음 한 번만 만들고, 사람/에이전트가 채운다.

  build_level4.py raw --csv <hsk30.csv> --elk <wordlist.txt>   # 공식 목록 4급 추출(두 출처 대조)
  build_level4.py select --repo .                               # 넣을 것 고르기 + 뜻 빈 칸 파일 만들기
  build_level4.py check --repo .                                # 뜻 파일·충돌 검사만(파일을 쓰지 않는다)
  build_level4.py apply --repo .                                # vocab.json·카드 id 장부를 쓰고 내 단어장 갱신 색인을 다시 쓴다

몇 번 돌려도 같다: apply는 지난번 «HSK4 (3.0)» 카드를 지우고 다시 넣으며, 같은 (한자, 병음)은 같은 id를 다시 쓴다.
사라진 카드 id는 src/data/vocab-retired.json에 은퇴시킨다(tools/vocab_fixes.py와 같은 장부).
"""
import argparse
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from vocab_fixes import (ID_REGISTRY, has_hangul, id_number, load_fixes, load_id_registry,  # noqa: E402
                         moved_to, registry_text, write_files_atomically)

RAW_PATH = HERE / 'level4_raw.json'
SELECT_PATH = HERE / 'level4_select.json'
MEANINGS_DIR = HERE / 'meanings'
MOVES_PATH = HERE.parent / 'mine_moves.json'
VOCAB_PATH = Path('src') / 'data' / 'vocab.json'

LEVEL = 'HSK4'
LESSON = 'HSK4 (3.0)'
CATEGORY = 'HSK4 (3.0) 단어'
PREFIX = 'HSK4'
SOURCE = 'HSK 3.0 4급 공식 목록 · 뜻: AI 번역'
TAGS = ['HSK4', '단어', CATEGORY]
CHUNKS = 4
# 이 단원 뒤에 다른 도구(듣기·독해 assemble.py, vocab_fixes.py --apply-listening)가 자기 단원을 다시 붙인다.
# 그 앞에 넣어 두면 그 도구들이 돌아도 파일 안 순서가 바뀌지 않는다.
INSERT_BEFORE = ('HSK3 듣기', 'HSK3 독해')
REBUILT_LESSONS = ('HSK3 듣기', 'HSK3 독해')

SOURCES = [
    {'name': 'ivankra/hsk30 hsk30.csv (공식 PDF + chinesetest.cn 병음·품사)',
     'url': 'https://github.com/ivankra/hsk30/blob/master/hsk30.csv',
     'commit': '4ff9e3915ce87baaecd7ebe263085573a4ea3192'},
    {'name': 'elkmovie/hsk30 wordlist.txt (공식 PDF OCR, 한자만) — 4급 1000행 대조',
     'url': 'https://github.com/elkmovie/hsk30/blob/main/wordlist.txt',
     'commit': '7f3d4fdcfcb6e826001df062747c943d1fa8160e'},
    {'name': '원문: 教育部 《国际中文教育中文水平等级标准》(2021)',
     'url': 'http://www.moe.gov.cn/jyb_xwfb/gzdt_gzdt/s5987/202103/t20210329_523304.html'},
]

# 한자는 이미 단어장에 있지만 4급에서 다른 읽기·다른 단어로 나오는 것. (한자, 병음) — 따로 카드를 만든다.
# 打 dá(다스, 양사)는 넣지 않는다: «HSK3 듣기»에 打 카드가 있어, 듣기 단원을 다시 만들면(update_vocab의 known)
# 그 카드가 빠지고 id가 은퇴된다.
POLYPHONES = {('啊', 'ā'), ('得', 'děi'), ('地方', 'dìfāng'), ('好', 'hào'), ('哪', 'na'), ('着', 'zháo'), ('种', 'zhòng')}
# 단어장에 같은 단어가 병음 표기만 달리 있다(shànggèyuè ↔ shàng ge yuè).
SAME_WORD = {'上个月', '下个月'}
# 넣지 않는 단어와 이유.
EXCLUDE = {
    '多年': 'tools/vocab_fixes.json split가 多年을 多·年으로 나눈다(나눈 묶음은 «단어» 카드가 될 수 없다: mine_refresh 색인 규칙)',
}

POS_KO = {'N': '명사', 'V': '동사', 'Adj': '형용사', 'Adv': '부사', 'Conj': '접속사', 'M': '양사', 'Pron': '대명사',
          'Prep': '개사', 'Aux': '조사', 'Intj': '감탄사', 'Num': '수사'}
POS_ALLOWED = set(POS_KO.values()) | {'조동사', '고유명사', '수량사', '표현', '패턴'}
HANZI = re.compile(r'[一-鿿]')
MEANING_MAX = 40
WORD_TYPE, PATTERN_TYPE = '단어', '패턴'


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def dump(value):
    return json.dumps(value, ensure_ascii=False, indent=1) + '\n'


def norm_pinyin(text):
    return re.sub(r"[\s'’·∥\-]", '', unicodedata.normalize('NFC', text or '')).lower()


# --- raw ---

def clean_pinyin(web, pdf):
    """사이트 병음(一·不 변조 표기, ∥ 이합사, · 경성 가능)에서 ∥·를 뺀다. 앱 병음도 一·不 변조를 적는다."""
    text = (web or pdf).replace('∥', '').replace('·', '')
    return unicodedata.normalize('NFC', text.strip())


def build_raw(csv_path, elk_path):
    rows = [row for row in csv.DictReader(open(csv_path, encoding='utf-8')) if row['Level'] == '4']
    lines = Path(elk_path).read_text(encoding='utf-8').split('\n')
    section, elk = None, []
    for line in lines:
        if line.endswith('词汇表'):
            section = line
            continue
        match = re.match(r'^(\d+) (.+)$', line)
        if match and section == '四级词汇表':
            elk.append(match.group(2).replace('｜', '|'))
    if len(rows) != 1000 or len(elk) != 1000:
        raise SystemExit(f'4급은 1000행이어야 한다: csv {len(rows)}, elk {len(elk)}')
    for row, ocr in zip(rows, elk):
        if row['OCR'].replace('｜', '|') != ocr:
            raise SystemExit(f'두 출처가 다르다: {row["ID"]} {row["OCR"]} ↔ {ocr}')
    items = []
    for number, row in enumerate(rows, 1):
        if '|' in row['Simplified']:
            raise SystemExit(f'변이형이 있는 행은 따로 다뤄야 한다: {row["ID"]} {row["Simplified"]}')
        items.append({
            'no': number,
            'officialId': row['ID'],
            'hanzi': row['Simplified'],
            'pinyin': clean_pinyin(row['WebPinyin'], row['Pinyin']),
            'pinyinPdf': row['Pinyin'],
            'pos': row['POS'],
            'ocr': row['OCR'],
        })
    return {
        '_about': 'HSK 3.0(2021) 4급 새 단어 1000행. tools/hsk30/build_level4.py raw가 만든다. 손으로 고치지 않는다. '
                  'pinyin은 chinesetest.cn 표기에서 ∥·를 뺀 것(一·不 변조 포함), pinyinPdf는 변조 없는 표기, '
                  'pos는 영문 약어(N V Adj Adv Conj M Pron Prep Aux Intj Num, 빈 값은 이합사·구), '
                  'ocr은 공식 PDF 표기(같은 한자의 다른 품사는 批（动）처럼 괄호로 적힌다).',
        'sources': SOURCES,
        'count': len(items),
        'items': items,
    }


# --- select ---

def pos_ko(code):
    if not code:
        return ''
    return '/'.join(POS_KO[part] for part in code.split('/'))


def existing_cards(vocab):
    return [card for card in vocab if card.get('lesson') != LESSON]


def select(raw, vocab):
    """raw 1000행 → {'add': [...], 'skipped': [...]}. 같은 (한자, 병음)은 한 카드로 합친다(批 동사·양사)."""
    others = existing_cards(vocab)
    app = {}
    for card in others:
        app.setdefault(card['hanzi'], set()).add(card['pinyin'])
    add, skipped, by_key = [], [], {}
    for item in raw['items']:
        hanzi, pinyin = item['hanzi'], item['pinyin']
        reason = None
        if hanzi in EXCLUDE:
            reason = 'exclude: ' + EXCLUDE[hanzi]
        elif hanzi in app and (hanzi, pinyin) not in POLYPHONES:
            if hanzi in SAME_WORD or norm_pinyin(pinyin) in {norm_pinyin(p) for p in app[hanzi]}:
                reason = 'same: 같은 단어가 이미 있음'
            else:
                reason = 'reading: 같은 한자의 다른 읽기(넣지 않음)'
        if reason:
            skipped.append({'officialId': item['officialId'], 'hanzi': hanzi, 'pinyin': pinyin, 'pos': item['pos'],
                            'ocr': item['ocr'], 'app': sorted(app.get(hanzi, [])), 'reason': reason})
            continue
        pair = (hanzi, pinyin)
        if pair in by_key:  # 같은 단어의 다른 품사 행(批（动）·批（量）)
            entry = by_key[pair]
            entry['officialIds'].append(item['officialId'])
            entry['pos'] = '/'.join(dict.fromkeys(entry['pos'].split('/') + item['pos'].split('/')))
            entry['ocr'].append(item['ocr'])
            continue
        entry = {'key': item['officialId'], 'officialIds': [item['officialId']], 'hanzi': hanzi, 'pinyin': pinyin,
                 'pos': item['pos'], 'ocr': [item['ocr']],
                 'itemType': PATTERN_TYPE if not HANZI.fullmatch(hanzi[0]) else WORD_TYPE,
                 'existing': sorted(app.get(hanzi, []))}
        by_key[pair] = entry
        add.append(entry)
    for entry in add:
        entry['posKo'] = PATTERN_TYPE if entry['itemType'] == PATTERN_TYPE else pos_ko(entry['pos'])
        entry['note'] = writer_note(entry)
    return {'add': add, 'skipped': skipped}


def writer_note(entry):
    notes = []
    marked = [ocr for ocr in entry['ocr'] if '（' in ocr]
    if marked:
        notes.append(f'공식 목록 표기 {"·".join(marked)}: 괄호 안 품사의 뜻을 먼저 쓴다')
    if entry['existing']:
        notes.append(f'앱에 같은 한자의 다른 읽기({", ".join(entry["existing"])}) 카드가 있다. 이 카드는 {entry["pinyin"]} 읽기의 뜻만 쓴다')
    if not entry['pos']:
        notes.append('품사가 비어 있다(이합사·구): partOfSpeech를 채운다')
    return ' / '.join(notes)


def chunk_files(add):
    size = -(-len(add) // CHUNKS)
    files = {}
    for index in range(CHUNKS):
        part = add[index * size:(index + 1) * size]
        files[MEANINGS_DIR / f'level4-meanings-{index + 1}.json'] = [
            {'key': e['key'], 'hanzi': e['hanzi'], 'pinyin': e['pinyin'], 'partOfSpeech': e['posKo'],
             'meaningKo': '', 'note': e['note']} for e in part]
    return files


# --- check / apply ---

def load_meanings():
    meanings = {}
    for path in sorted(MEANINGS_DIR.glob('level4-meanings-*.json')):
        for row in load_json(path):
            if row['key'] in meanings:
                raise SystemExit(f'뜻 파일에 같은 key가 둘: {row["key"]} ({path.name})')
            meanings[row['key']] = {**row, '_file': path.name}
    return meanings


def meaning_problems(add, meanings):
    problems = []
    keys = {entry['key'] for entry in add}
    for key in sorted(set(meanings) - keys):
        problems.append(f'{key}: 넣을 목록에 없는 key(뜻 파일에서 뺀다)')
    for entry in add:
        row = meanings.get(entry['key'])
        here = f'{entry["key"]} {entry["hanzi"]}'
        if row is None:
            problems.append(f'{here}: 뜻 파일에 없음')
            continue
        if (row['hanzi'], row['pinyin']) != (entry['hanzi'], entry['pinyin']):
            problems.append(f'{here}: 한자·병음을 바꾸면 안 된다 ({row["hanzi"]} {row["pinyin"]})')
        meaning = (row.get('meaningKo') or '').strip()
        if not has_hangul(meaning):
            problems.append(f'{here}: meaningKo에 한글이 없음 ({meaning!r})')
        elif len(meaning) > MEANING_MAX:
            problems.append(f'{here}: meaningKo가 {MEANING_MAX}자를 넘음 ({len(meaning)}자)')
        if meaning != (row.get('meaningKo') or ''):
            problems.append(f'{here}: meaningKo 앞뒤 공백')
        part = row.get('partOfSpeech') or ''
        if not part or any(p not in POS_ALLOWED for p in part.split('/')):
            problems.append(f'{here}: partOfSpeech {part!r} (허용: {"·".join(sorted(POS_ALLOWED))}, 여럿은 /로)')
        if entry['posKo'] and part != entry['posKo']:
            problems.append(f'{here}: partOfSpeech는 공식 품사 {entry["posKo"]!r}를 그대로 둔다 ({part!r})')
    return problems


def conflict_problems(repo, add):
    """다른 도구 표와 부딪히는 단어. 이것이 남으면 mine_refresh 색인·테스트가 깨진다."""
    problems = []
    vocab = load_json(Path(repo) / VOCAB_PATH)
    hanzi = {entry['hanzi'] for entry in add}
    fixes = load_fixes()
    moves = load_json(MOVES_PATH)
    for token in sorted(hanzi & set(fixes.get('split', {}))):
        problems.append(f'{token}: tools/vocab_fixes.json split에 있다(넣지 않거나 split를 고친다)')
    for token in sorted(hanzi & set(moves.get('split', {}))):
        problems.append(f'{token}: tools/mine_moves.json split에 있다')
    for token in sorted(hanzi & set(moves.get('words', {}))):
        problems.append(f'{token}: tools/mine_moves.json words에 있다(지금 데이터에 들어오면 그 표에서 뺀다)')
    rebuilt = {card['hanzi'] for card in vocab if card.get('lesson') in REBUILT_LESSONS}
    for token in sorted(hanzi & rebuilt):
        problems.append(f'{token}: «HSK3 듣기·독해»에 있는 한자(그 단원을 다시 만들면 그 카드가 빠진다)')
    table = fixes.get('movedTo', {})
    registry = load_id_registry(repo)
    alive = {card['hanzi'] for card in existing_cards(vocab)} | hanzi
    for entry_id, value in registry['retired'].items():
        target = moved_to(value['hanzi'], alive, fixes)
        if table.get(value['hanzi']) != target:
            problems.append(f'은퇴 카드 {entry_id} {value["hanzi"]}: 넣고 나면 movedTo가 {target!r}가 된다 → '
                            f'tools/vocab_fixes.json movedTo의 {value["hanzi"]}를 {target!r}로 고친다')
    return problems


def build_cards(selection, meanings):
    """넣을 카드(id는 assign_ids가 정한다)."""
    cards = []
    for entry in selection['add']:
        row = meanings[entry['key']]
        cards.append({
            'id': None,
            'level': LEVEL,
            'lesson': LESSON,
            'category': CATEGORY,
            'itemType': entry['itemType'],
            'hanzi': entry['hanzi'],
            'pinyin': entry['pinyin'],
            'meaningKo': row['meaningKo'],
            'partOfSpeech': row['partOfSpeech'],
            'exampleZh': '',
            'examplePinyin': '',
            'exampleKo': '',
            'source': SOURCE,
            'tags': list(TAGS),
        })
    return cards


def assign_ids(cards, previous, registry):
    """previous: 지난번 이 단원 카드 {(한자, 병음): id}. 새 카드는 은퇴 번호까지 포함한 최댓값 다음 번호."""
    used = [id_number(i) for i in previous.values()]
    used += [id_number(i) for i in registry['retired'] if i.startswith(PREFIX + '-')]
    last = max(used + [registry['lastNo'].get(PREFIX, 0)])
    for card in cards:
        pair = (card['hanzi'], card['pinyin'])
        if pair in previous:
            card['id'] = previous[pair]
        else:
            last += 1
            card['id'] = f'{PREFIX}-{last:03d}'
    return last


def plan_vocab(repo, selection, meanings):
    """새 vocab.json(전체)과 장부. 파일은 쓰지 않는다."""
    vocab = load_json(Path(repo) / VOCAB_PATH)
    previous = {(card['hanzi'], card['pinyin']): card['id'] for card in vocab if card.get('lesson') == LESSON}
    others = existing_cards(vocab)
    registry = load_id_registry(repo)
    cards = build_cards(selection, meanings)
    last = assign_ids(cards, previous, registry)
    at = next((i for i, card in enumerate(others) if card.get('lesson') in INSERT_BEFORE), len(others))
    final = others[:at] + cards + others[at:]
    ids = [card['id'] for card in final]
    if len(ids) != len(set(ids)):
        raise SystemExit('vocab.json에 같은 id가 둘 이상 있다')
    alive_ids, alive_hanzi = set(ids), {card['hanzi'] for card in final}
    retired = {key: dict(value) for key, value in registry['retired'].items()}
    for (hanzi, _), entry_id in previous.items():
        if entry_id not in alive_ids:
            retired[entry_id] = {'hanzi': hanzi}
    for value in retired.values():  # CardIds.plan과 같은 규칙
        value['movedTo'] = moved_to(value['hanzi'], alive_hanzi)
    if alive_ids & set(retired):
        raise SystemExit(f'은퇴한 id를 다시 썼다: {sorted(alive_ids & set(retired))}')
    registry = {**registry, 'lastNo': {**registry['lastNo'], PREFIX: last}, 'retired': retired}
    return final, registry, cards


def main(argv=None):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    raw_cmd = sub.add_parser('raw')
    raw_cmd.add_argument('--csv', required=True)
    raw_cmd.add_argument('--elk', required=True)
    for name in ('select', 'check', 'apply'):
        sub.add_parser(name).add_argument('--repo', required=True)
    args = parser.parse_args(argv)

    if args.command == 'raw':
        raw = build_raw(args.csv, args.elk)
        write_files_atomically({RAW_PATH: dump(raw)})
        print(f'{RAW_PATH.name}: {raw["count"]}행')
        return 0

    repo = Path(args.repo)
    if args.command == 'select':
        selection = select(load_json(RAW_PATH), load_json(repo / VOCAB_PATH))
        files = {SELECT_PATH: dump({'_about': '넣을 것(add)과 뺀 것(skipped). build_level4.py select가 만든다. 손으로 고치지 않는다.',
                                    'addCount': len(selection['add']), 'skippedCount': len(selection['skipped']),
                                    **selection})}
        made = [path for path in chunk_files(selection['add']) if not path.exists()]
        if made and len(made) != CHUNKS:
            raise SystemExit('뜻 파일이 일부만 있다. 채운 뜻을 덮지 않도록 멈춘다.')
        if made:
            files.update({path: dump(rows) for path, rows in chunk_files(selection['add']).items()})
        write_files_atomically(files)
        print(f'넣을 것 {len(selection["add"])}개, 뺀 것 {len(selection["skipped"])}개'
              + (f', 뜻 빈 칸 파일 {len(made)}개를 만들었다' if made else ' (뜻 파일은 이미 있어 그대로 둠)'))
        return 0

    selection = load_json(SELECT_PATH)
    fresh = select(load_json(RAW_PATH), load_json(repo / VOCAB_PATH))
    if [e['key'] for e in fresh['add']] != [e['key'] for e in selection['add']]:
        print('level4_select.json이 지금 데이터와 다르다 → build_level4.py select --repo . 를 다시 돌린다')
        return 1
    problems = meaning_problems(selection['add'], load_meanings()) + conflict_problems(repo, selection['add'])
    for problem in problems:
        print('  ! ' + problem)
    if problems:
        print(f'문제 {len(problems)}개. 파일을 쓰지 않았습니다.')
        return 1
    final, registry, cards = plan_vocab(repo, selection, load_meanings())
    if args.command == 'check':
        print(f'문제 없음. apply하면 «{LESSON}» 카드 {len(cards)}개, vocab.json {len(final)}개가 된다.')
        return 0
    write_files_atomically({
        repo / VOCAB_PATH: json.dumps(final, ensure_ascii=False, indent=2) + '\n',
        repo / ID_REGISTRY: registry_text(registry),
    })
    print(f'«{LESSON}» 카드 {len(cards)}개를 넣었습니다(vocab.json {len(final)}개).')
    import mine_refresh  # tools/mine_refresh.py
    return 0 if mine_refresh.refresh_after_write(repo) else 1


if __name__ == '__main__':
    raise SystemExit(main())
