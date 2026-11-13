#!/usr/bin/env python3
"""HSK 3.0 공식 시험 대강(chinesetest.cn 어휘 검색 API) 1~4급 2,000개 + 선택 5급 500개를 단어장(src/data/vocab.json)에 넣는다.

예전 HSK 단원(HSK 2.0 «HSK1 150»·«HSK2 추가 150»·«HSK2 공식문제»·«HSK3 추가 300», 2021 표준 «HSK4 (3.0)» 929개)을 빼고
이 목록으로 바꾼다. 교재(Lesson 1~8) 카드는 그대로 둔다. «HSK3 듣기»·«HSK3 독해»는 그 도구들의 규칙대로 다시 만든다
(대강과 겹치는 단어는 빠지고, 예전 HSK 단원에만 있던 시험 단어는 들어온다).

파일 (모두 tools/hsk_outline/)
  outline_raw.json     공식 API 2,500행(한자·병음·품사·급수) + Codex 1차본의 뜻(codexKo)·한국 한자 훈음(hanjaKo). `raw`가 만든다. 손으로 고치지 않는다.
  legacy_cards.json    git 67aad8a의 예전 HSK 단원·듣기·독해 카드 스냅숏(뜻 비교·예문 옮기기용). `legacy`가 git에서 뽑는다. 손으로 고치지 않는다.
  outline_select.json  넣을 것(add, 카드 하나 = 같은 급수 동형어를 합친 API 행)과 비교 정보. `select`가 raw·legacy·지금 교재 카드에서 만든다.
  meanings/outline-meanings-<묶음>.json  한국어 뜻·품사·훈음. `select`가 처음 한 번만 만들고(뜻은 Codex 뜻을 앱 형식으로 바꾼 초안),
                       사람/에이전트가 고친다. 다시 select해도 덮지 않는다.
  card_ids.json        카드 id 장부 {API id: 카드 id}. apply가 쓴다(같은 API 행은 늘 같은 id).

  build_outline.py raw --api <glossaryPage.json> --doc <Codex 1차본.md> --selected <5급 500.md>
  build_outline.py legacy --repo . [--rev 67aad8a]
  build_outline.py select --repo .
  build_outline.py check --repo .     # 뜻 파일·충돌 검사 + 임시 사본에서 듣기·독해 재생성까지 해 본다(저장소에 쓰지 않는다)
  build_outline.py apply --repo .     # 같은 계산 뒤 vocab.json·카드 id 장부·card_ids.json을 쓰고 내 단어장 갱신 색인을 다시 쓴다
  (check·apply는 듣기 도구가 pypinyin을 쓰므로 ~/venv-store/hsk-listening/bin/python으로 돌린다)

몇 번 돌려도 같다: apply는 예전 HSK 단원과 지난번 대강 단원을 지우고 맨 앞에 다시 넣은 뒤, 듣기·독해 단원을 그 도구들의
규칙(다른 단원에 없는 단어만)으로 다시 만든다 — 대강과 겹치는 듣기·독해 카드는 빠지고, 그 예문은 select가 새 카드로 옮긴다. 사라진 카드 id는
src/data/vocab-retired.json에 은퇴시킨다(tools/vocab_fixes.py와 같은 장부).
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from vocab_fixes import (ID_REGISTRY, OUTLINE_LESSONS, has_hangul, id_number, load_fixes, load_id_registry,  # noqa: E402
                         moved_to, registry_text, write_files_atomically)

RAW_PATH = HERE / 'outline_raw.json'
LEGACY_PATH = HERE / 'legacy_cards.json'
SELECT_PATH = HERE / 'outline_select.json'
IDS_PATH = HERE / 'card_ids.json'
MEANINGS_DIR = HERE / 'meanings'
MOVES_PATH = HERE.parent / 'mine_moves.json'
VOCAB_PATH = Path('src') / 'data' / 'vocab.json'

# 급수별 행 수(공식 1~4급 + 선택 5급).
LEVEL_COUNTS = {1: 300, 2: 200, 3: 500, 4: 1000, 5: 500}
# --- 이름(성미님 답에 따라 바꿀 수 있는 곳은 여기뿐) ---
LESSONS = dict(zip(range(1, 6), OUTLINE_LESSONS))
PREFIXES = {1: 'H1', 2: 'H2', 3: 'H3', 4: 'H4', 5: 'H5'}
SOURCE = 'HSK 3.0 공식 어휘(chinesetest.cn) · 뜻: AI 번역·검토'
# 빼는 예전 HSK 단원(성미님 결정 2026-11-13: «HSK2 공식문제» 문장 125개도 뺀다).
OLD_LESSONS = ('HSK1 150', 'HSK2 추가 150', 'HSK2 공식문제', 'HSK3 추가 300', 'HSK4 (3.0)')
# 시험에서 나온 단원. 다른 단원에 없는 단어만 담는다(tools/listening·reading assemble.py update_vocab). 대강 단원이 들어오면
# 겹치는 한자 카드는 빠지고(성미님 결정), 예전 HSK 단원에만 있던 단어는 새로 들어온다. apply가 두 도구를 이어서 돌린다.
REBUILT_LESSONS = ('HSK3 듣기', 'HSK3 독해')
# 새 카드에 옮길 예문을 찾는 순서(같은 한자·같은 읽기, 예문이 있는 카드). legacy_cards.json(67aad8a 스냅숏)에서 찾는다.
EXAMPLE_LESSONS = ('HSK3 추가 300', 'HSK3 듣기', 'HSK3 독해')
LEGACY_REV = '67aad8a'
# 듣기·독해 도구(assemble.py, vocab_fixes.py --apply-listening)는 자기 단원을 지우고 맨 뒤에 다시 붙인다.
# 대강 단원은 파일 맨 앞(예전 «HSK1 150» 자리)에 둔다: 그 도구들이 돌아도 순서가 안 바뀌고,
# «한자별 첫 단어 카드»(mine_refresh 기본 뜻)가 예전처럼 HSK 카드가 된다.
CHUNKS = [('L1', 1, None), ('L2', 2, None), ('L3', 3, None), ('L4a', 4, 0), ('L4b', 4, 1), ('L5', 5, None)]

SOURCES = [
    {'name': '중국교육부 교육고시원 중국어시험서비스망 HSK 어휘 검색 API(2026-11-12 Codex 수신)',
     'url': 'https://www.chinesetest.cn/api/hsk/outline/glossaryPage'},
    {'name': 'Codex 1차본 «HSK 3.0 1~4급과 선택 5급 500 병음순 단어장»(위키 00_Inbox, 2026-11-13) — 한국어 뜻·한국 한자 훈음',
     'note': '훈음 출처: libhangul hanja.txt(BSD 3-Clause)·OpenCC(Apache 2.0)·한국어문회 공개 학습자료 대조(원문서 «출처» 절)'},
    {'name': '성미님 지정 5급 500 «2026-11-12_HSK3.0_4급_독해보조_5급한자500.md»'},
]

ZH_LEVEL = {'一级': 1, '二级': 2, '三级': 3, '四级': 4, '五级': 5, '六级': 6, '七-九级': 7}
POS_ZH = {'名': '명사', '动': '동사', '形': '형용사', '副': '부사', '代': '대명사', '量': '양사', '连': '접속사',
          '数': '수사', '助': '조사', '介': '개사', '叹': '감탄사', '数量': '수량사', '后缀': '접미사', '前缀': '접두사'}
# Codex 1차본 «품사 보완»(공식 품사가 빈 23행): 구 → 표현, 명 → 명사.
DOC_POS = {'구': '표현', '명': '명사'}
# Codex 뜻의 품사 약어 → 앱 품사.
ABBR_POS = {'명': '명사', '동': '동사', '형': '형용사', '부': '부사', '대': '대명사', '수': '수사', '양': '양사',
            '개': '개사', '접': '접속사', '조': '조사', '감': '감탄사', '접두': '접두사', '접미': '접미사', '구': '표현'}
# 앱 뜻에서 둘째 품사부터 붙이는 약어(기존 카드 «변화하다 / (명) 변화»와 같다).
POS_ABBR = {'명사': '명', '동사': '동', '형용사': '형', '부사': '부', '대명사': '대', '수사': '수', '양사': '양',
            '개사': '개', '접속사': '접', '조사': '조', '감탄사': '감', '접두사': '접두', '접미사': '접미',
            '수량사': '수량', '표현': '표현'}
POS_ALLOWED = set(POS_ABBR)
# Q6·Q2(성미님 결정): 빠지는 «HSK3 추가 300»·듣기·독해 카드의 시험 예문을 같은 단어·같은 읽기의 새 카드로 옮긴다.
CARRY_EXAMPLES = True
MERGE_SAME_LEVEL_HOMOGRAPHS = True  # 질문 Q3: 花1·花2(2급), 生1·生2(4급)를 한 카드로
MAX_LEVEL = 5  # 이 급수까지 도입된 (괄호) 품사만 카드 품사에 넣는다
MEANING_MAX = 40
HANZI = re.compile(r'[一-鿿]')
WORD_TYPE = '단어'


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def dump(value):
    return json.dumps(value, ensure_ascii=False, indent=1) + '\n'


def dump_items(head, key, items):
    """머리 값은 들여쓰기, items는 한 줄에 하나(다시 만들 때 diff로 바뀐 행이 보이게)."""
    line = lambda value: json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    parts = [f' {line(k)}: {line(v)}' for k, v in head.items()]
    rows = ',\n'.join(f'  {line(item)}' for item in items)
    parts.append(f' {line(key)}: [\n{rows}\n ]')
    return '{\n' + ',\n'.join(parts) + '\n}\n'


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


TONE_MARKS = {'\u0304': '1', '\u0301': '2', '\u030c': '3', '\u0300': '4'}


def tone_key(pinyin, hanzi=''):
    """같은 단어인지 볼 때 쓰는 병음 열쇠(src/myVocab.js pinyinKey와 같은 규칙이어야 한다).
    첫 읽기만(shéi/shuí → shéi), 성조 뗀 소문자 글자(ü는 v) + 첫 성조 숫자(성조 부호가 없으면 0).
    둘째 음절부터의 경성 표기 차이(xuésheng·xuéshēng)는 같은 단어로, 첫 성조가 다르면(hǎo·hào, guò·guo) 다른 단어로 본다.
    一·不로 시작하면 변조(yí·yì, bú)와 상관없이 본래 성조(1, 4)로 친다."""
    text = unicodedata.normalize('NFD', str(pinyin or '').split('/')[0].lower())
    digit = next((TONE_MARKS[ch] for ch in text if ch in TONE_MARKS), '0')
    if hanzi.startswith('一'):
        digit = '1'
    elif hanzi.startswith('不'):
        digit = '4'
    letters = re.sub(r'[^a-z]', '', re.sub('u\u0308', 'v', text).replace('ü', 'v'))
    return letters + digit


# --- raw ---

def first_level(level_name):
    return ZH_LEVEL[re.match(r'^([^（]+)', level_name).group(1)]


def pos_groups(cixing, level_name):
    """'名、（动）' + '四级（五级）' → [('명사', 4), ('동사', 5)]. 괄호 품사는 괄호 급수에 처음 나온다."""
    if not cixing:
        return []
    base = first_level(level_name)
    later = [ZH_LEVEL[x] for x in re.findall(r'（([^）]*)）', level_name)]
    out, paren = [], 0
    for part in re.findall(r'（[^）]*）|[^、（）]+', cixing):
        if part.startswith('（'):
            level = later[paren]
            paren += 1
            names = part[1:-1].split('、')
        else:
            level, names = base, [part]
        for name in names:
            out.append((POS_ZH[name], level))
    if paren != len(later):
        raise SystemExit(f'괄호 품사와 괄호 급수 수가 다르다: {cixing} {level_name}')
    return out


def parse_doc(text):
    rows = []
    for line in text.split('\n'):
        match = re.match(r'^\| (.+?) 〔([1-5])〕 \| (.*?) \| (.*) \|$', line)
        if match:
            main, *rest = match.group(4).split('<br>')
            rows.append({'head': match.group(1), 'level': int(match.group(2)), 'pinyin': match.group(3),
                         'codexKo': main.strip(), 'hanjaLine': rest[0].strip() if rest else ''})
    fills = {}
    section = text.split('## 🤖 품사 보완', 1)[1].split('\n## ', 1)[0]
    for match in re.finditer(r'^- (\S+) \(id=(\d+)\): (\S+) - ', section, re.M):
        fills[match.group(2)] = {'head': match.group(1), 'pos': match.group(3)}
    return rows, fills


def parse_selected(text):
    body = text.split('---', 2)[2]
    return body.split()


def hanja_ko(line):
    """'愛 사랑 애 · 護 도울 호'는 그대로. 글자마다 훈음이 없으면('啊 —') 빈 값."""
    if not line:
        return ''
    parts = line.split(' · ')
    if all(part.endswith('—') for part in parts):
        return ''
    return line


def build_raw(api_path, doc_path, selected_path):
    api = [r for r in load_json(api_path)['data']['records'] if r['type'] == 1]
    doc_text = Path(doc_path).read_text(encoding='utf-8')
    rows, fills = parse_doc(doc_text)
    selected = parse_selected(Path(selected_path).read_text(encoding='utf-8'))
    problems = []
    by_key = {}
    for record in api:
        by_key.setdefault((record['word'], first_level(record['levelName']), record['pinyin']), []).append(record)
    items, used = [], set()
    for row in rows:
        found = by_key.get((row['head'], row['level'], row['pinyin']), [])
        if len(found) != 1:
            problems.append(f'API와 맞지 않는 행: {row["head"]} {row["level"]} {row["pinyin"]} ({len(found)}개)')
            continue
        record = found[0]
        if record['id'] in used:
            problems.append(f'API 행이 두 번 쓰였다: {record["id"]}')
        used.add(record['id'])
        groups = pos_groups(record.get('cixing', ''), record['levelName'])
        fill = fills.get(record['id'])
        if not groups:
            if not fill:
                problems.append(f'품사 없음·보완 없음: {record["id"]} {record["word"]}')
                continue
            groups = [(DOC_POS[fill['pos']], first_level(record['levelName']))]
        hanzi = re.sub(r'\d+$', '', record['word'])
        items.append({
            'apiId': record['id'],
            'sort': record['sort'],
            'level': row['level'],
            'head': record['word'],
            'hanzi': hanzi,
            'pinyin': record['pinyin'],
            'cixing': record.get('cixing', ''),
            'levelName': record['levelName'],
            'pos': [[name, level] for name, level in groups],
            'posFilled': bool(fill),
            'selected5': row['level'] == 5,
            'codexKo': row['codexKo'],
            'hanjaKo': hanja_ko(row['hanjaLine']),
        })
    counts = {level: sum(1 for item in items if item['level'] == level) for level in LEVEL_COUNTS}
    if counts != LEVEL_COUNTS:
        problems.append(f'급수별 행 수가 다르다: {counts}')
    api_low = {r['id'] for r in api if first_level(r['levelName']) <= 4}
    if api_low - used:
        problems.append(f'1~4급 API 행 중 1차본에 없는 것: {sorted(api_low - used)}')
    level5 = [item['hanzi'] for item in items if item['level'] == 5]
    if len(selected) != 500 or len(set(selected)) != 500:
        problems.append(f'지정 5급 목록은 서로 다른 500개여야 한다: {len(selected)}개, 서로 다른 것 {len(set(selected))}개')
    if sorted(level5) != sorted(selected):
        problems.append(f'1차본 5급 ≠ 지정 목록: 빠짐 {sorted(set(selected) - set(level5))}, 더함 {sorted(set(level5) - set(selected))}')
    if problems:
        raise SystemExit('\n'.join('  ! ' + p for p in problems))
    items.sort(key=lambda item: (item['level'], item['sort']))
    return {
        '_about': 'HSK 3.0 공식 시험 대강 1~4급 2,000행 + 지정 5급 500행. tools/hsk_outline/build_outline.py raw가 만든다. 손으로 고치지 않는다. '
                  'apiId·sort·head(끝 숫자는 공식 동형어 표식)·pinyin·cixing·levelName은 API 원문, level은 첫 도입 급수, '
                  'pos는 [앱 품사, 도입 급수](괄호 품사는 괄호 급수), posFilled는 공식 품사가 비어 Codex 1차본 «품사 보완»으로 채운 행, '
                  'codexKo는 Codex 1차본 한글 뜻 원문, hanjaKo는 4·5급 한국 한자 자형·대표 훈음(전부 «—»이면 빈 값).',
        'sources': SOURCES,
        'inputs': {'api': {'file': Path(api_path).name, 'sha256': sha256(api_path), 'records': len(api)},
                   'doc': {'file': Path(doc_path).name, 'sha256': sha256(doc_path)},
                   'selected': {'file': Path(selected_path).name, 'sha256': sha256(selected_path)}},
        'counts': {str(k): v for k, v in counts.items()},
        'items': items,
    }


# --- legacy ---

def build_legacy(repo, rev):
    text = subprocess.run(['git', '-C', str(repo), 'show', f'{rev}:{VOCAB_PATH.as_posix()}'],
                          check=True, capture_output=True, text=True).stdout
    lessons = OLD_LESSONS + REBUILT_LESSONS
    cards = [card for card in json.loads(text) if card.get('lesson') in lessons]
    return {'_about': f'git {rev}의 src/data/vocab.json 중 {", ".join(lessons)} 카드 스냅숏. build_outline.py legacy가 만든다. '
                      '손으로 고치지 않는다. 뜻 비교(select의 app)와 새 카드에 옮길 예문(EXAMPLE_LESSONS)에 쓴다 — 듣기·독해 카드는 apply 뒤 '
                      '겹치는 것이 빠지므로, 지금 vocab.json이 아니라 이 스냅숏을 써야 select가 apply 전후로 같다.',
            'rev': rev, 'count': len(cards), 'cards': cards}


# --- select ---

def card_pos(item):
    names = [name for name, level in item['pos'] if level <= MAX_LEVEL]
    return list(dict.fromkeys(names))


def convert_meaning(codex, pos_order):
    """Codex 뜻 «(동) A; (명) B»를 앱 형식 «A / (명) B»로. 같은 품사 안의 ;는 ,로.
    (돌려줌: 초안 문자열, 문제 표시 목록) — 표시가 있으면 뜻 담당이 손본다."""
    flags = []
    segments = [s.strip() for s in codex.split('; ') if s.strip()]
    parsed = []  # [(품사 또는 None, 글)]
    pending = []  # 합친 약어(동·명)에서 아직 글을 받지 못한 품사들
    current, combined = None, False
    for seg in segments:
        match = re.match(r'^\(([^()]*)\) (.+)$', seg)
        tags = match.group(1).split('·') if match else None
        if tags and all(tag in ABBR_POS for tag in tags):
            names = [ABBR_POS[tag] for tag in tags]
            if names == ['수사', '양사'] and '수량사' in pos_order:  # (수·양) 조금 = 수량사 한 품사
                names = ['수량사']
            if pending:
                flags.append('합친 품사 약어(예: 동·명)의 품사 수가 뜻 조각 수보다 많다: 어느 뜻이 어느 품사인지 확인')
            current, pending = names[0], names[1:]
            combined = len(names) > 1
            parsed.append((current, match.group(2)))
            continue
        if match and not (tags and all(tag in ABBR_POS for tag in tags)):
            flags.append(f'괄호 안이 품사가 아님: ({match.group(1)})')
        if pending:
            current = pending.pop(0)
        elif combined and not match:
            flags.append('합친 품사 약어 뒤 뜻 조각이 품사 수보다 많다: 남는 조각을 마지막 품사에 붙였다(배정 확인)')
            combined = False
        parsed.append((current, seg))
    if pending:
        flags.append('합친 품사 약어(예: 동·명)의 품사 수가 뜻 조각 수보다 많다: 어느 뜻이 어느 품사인지 확인')
    if parsed and parsed[0][0] is None:
        flags.append('첫 뜻에 품사 표시가 없음')
    groups = {}
    for name, text in parsed:
        groups.setdefault(name or pos_order[0], []).append(text)
    extra = [name for name in groups if name not in pos_order]
    if extra:
        flags.append(f'뜻의 품사 {extra}가 공식 품사 {pos_order}에 없음')
    missing = [name for name in pos_order if name not in groups and name != '표현']
    if missing:
        flags.append(f'공식 품사 {missing}의 뜻이 없음')
    order = [name for name in pos_order if name in groups] + extra
    parts = []
    for index, name in enumerate(order):
        text = ', '.join(dict.fromkeys(groups[name]))
        parts.append(text if index == 0 else f'({POS_ABBR.get(name, name)}) {text}')
    draft = ' / '.join(parts)
    if len(draft) > MEANING_MAX:
        flags.append(f'{MEANING_MAX}자 초과({len(draft)}자): 줄인다')
    if HANZI.search(draft):
        flags.append('뜻에 한자가 있음')
    return draft, flags


def app_cards(repo):
    """비교용 앱 «단어» 카드: 스냅숏(예전 HSK·듣기·독해) + 지금 교재 등 나머지 단원. apply 전후로 같다."""
    vocab = load_json(Path(repo) / VOCAB_PATH)
    skip = set(OLD_LESSONS) | set(REBUILT_LESSONS) | set(LESSONS.values())
    cards = load_json(LEGACY_PATH)['cards'] + [c for c in vocab if c.get('lesson') not in skip]
    return [c for c in cards if c.get('itemType') == WORD_TYPE]


def merged_items(raw):
    """같은 급수·같은 한자·같은 병음의 공식 동형어(花1·花2, 生1·生2)를 한 카드로 합친다(MERGE_SAME_LEVEL_HOMOGRAPHS).
    내 단어장 열쇠가 (한자, 병음)이라 같은 단원에 두 카드가 있으면 갱신이 한쪽 뜻으로 덮기 때문이다."""
    groups, order = {}, []
    for item in raw['items']:
        pair = (item['level'], item['hanzi'], item['pinyin']) if MERGE_SAME_LEVEL_HOMOGRAPHS else item['apiId']
        if pair not in groups:
            groups[pair] = []
            order.append(pair)
        groups[pair].append(item)
    out = []
    for pair in order:
        items = groups[pair]
        first = items[0]
        out.append({**first,
                    'officialIds': [i['apiId'] for i in items],
                    'head': '+'.join(i['head'] for i in items),
                    'pos': [p for i in items for p in i['pos']],
                    'codexKo': '; '.join(i['codexKo'] for i in items),
                    'hanjaKo': ' / '.join(dict.fromkeys(i['hanjaKo'] for i in items if i['hanjaKo']))})
    return out


def example_from(card):
    """예문이 나온 시험 문항(«H31001 듣기 31번»). 못 찾으면 빈 값."""
    match = re.search(r'H\d+ (?:듣기|독해) \d+번', card.get('source', ''))
    return match.group(0) if match else ''


def select(raw, cards):
    by_hanzi, legacy_examples = {}, {}
    for card in cards:
        by_hanzi.setdefault(card['hanzi'], []).append(card)
        if card.get('lesson') in EXAMPLE_LESSONS and card.get('exampleZh'):
            legacy_examples.setdefault(card['hanzi'], []).append(card)
    for found in legacy_examples.values():
        found.sort(key=lambda card: EXAMPLE_LESSONS.index(card['lesson']))
    add = []
    for item in merged_items(raw):
        pos = card_pos(item)
        draft, flags = convert_meaning(item['codexKo'], pos)
        same, other = [], []
        for card in by_hanzi.get(item['hanzi'], []):
            ref = {'id': card['id'], 'lesson': card['lesson'], 'pinyin': card['pinyin'],
                   'meaningKo': card['meaningKo'], 'partOfSpeech': card.get('partOfSpeech', '')}
            (same if tone_key(card['pinyin'], item['hanzi']) == tone_key(item['pinyin'], item['hanzi']) else other).append(ref)
        example = next(([c['exampleZh'], c['examplePinyin'], c['exampleKo'], example_from(c)] for c in legacy_examples.get(item['hanzi'], [])
                        if CARRY_EXAMPLES and tone_key(c['pinyin'], item['hanzi']) == tone_key(item['pinyin'], item['hanzi'])), None)
        add.append({
            'key': item['apiId'], 'officialIds': item['officialIds'], 'level': item['level'],
            'lesson': LESSONS[item['level']], 'head': item['head'], 'hanzi': item['hanzi'], 'pinyin': item['pinyin'],
            'posKo': '/'.join(pos), 'codexKo': item['codexKo'], 'draftKo': draft, 'flags': flags,
            'sameAsApp': next((a['lesson'] for a in same if a['meaningKo'] == draft), ''),
            'hanjaKo': item['hanjaKo'], 'example': example, 'app': same, 'appOtherReadings': other,
        })
    return {'add': add}


def chunk_rows(add):
    files = {}
    for name, level, half in CHUNKS:
        rows = [e for e in add if e['level'] == level]
        if half is not None:
            size = -(-len(rows) // 2)
            rows = rows[half * size:(half + 1) * size]
        files[MEANINGS_DIR / f'outline-meanings-{name}.json'] = [
            {'key': e['key'], 'head': e['head'], 'hanzi': e['hanzi'], 'pinyin': e['pinyin'], 'partOfSpeech': e['posKo'],
             'meaningKo': e['draftKo'], 'hanjaKo': e['hanjaKo'], 'codexKo': e['codexKo'], 'flags': e['flags'],
             'sameAsApp': e['sameAsApp'],
             'app': [f'{a["lesson"]} {a["pinyin"]} [{a["partOfSpeech"]}] {a["meaningKo"]}' for a in e['app']]}
            for e in rows]
    return files


# --- check / apply ---

def load_meanings():
    meanings = {}
    for path in sorted(MEANINGS_DIR.glob('outline-meanings-*.json')):
        for row in load_json(path):
            if row['key'] in meanings:
                raise SystemExit(f'뜻 파일에 같은 key가 둘: {row["key"]} ({path.name})')
            meanings[row['key']] = {**row, '_file': path.name}
    return meanings


def meaning_problems(add, meanings):
    problems = []
    keys = {entry['key'] for entry in add}
    for key in sorted(set(meanings) - keys):
        problems.append(f'{key}: 넣을 목록에 없는 key')
    for entry in add:
        row = meanings.get(entry['key'])
        here = f'{entry["key"]} {entry["head"]}'
        if row is None:
            problems.append(f'{here}: 뜻 파일에 없음')
            continue
        if (row['head'], row['hanzi'], row['pinyin']) != (entry['head'], entry['hanzi'], entry['pinyin']):
            problems.append(f'{here}: 한자·병음을 바꾸면 안 된다 ({row["head"]} {row["pinyin"]})')
        meaning = row.get('meaningKo') or ''
        if not has_hangul(meaning):
            problems.append(f'{here}: meaningKo에 한글이 없음 ({meaning!r})')
        elif len(meaning) > MEANING_MAX:
            problems.append(f'{here}: meaningKo가 {MEANING_MAX}자를 넘음 ({len(meaning)}자)')
        if meaning != meaning.strip() or ';' in meaning or '<' in meaning or HANZI.search(meaning):
            problems.append(f'{here}: meaningKo 형식(앞뒤 공백·«;»·태그·한자) ({meaning!r})')
        part = row.get('partOfSpeech') or ''
        if not part or any(p not in POS_ALLOWED for p in part.split('/')):
            problems.append(f'{here}: partOfSpeech {part!r} (허용: {"·".join(sorted(POS_ALLOWED))}, 여럿은 /로)')
        elif part != entry['posKo']:
            problems.append(f'{here}: partOfSpeech는 공식 품사 {entry["posKo"]!r}를 그대로 둔다 ({part!r})')
        if (row.get('hanjaKo') or '') != entry['hanjaKo']:
            problems.append(f'{here}: hanjaKo는 1차본 값을 그대로 둔다(고칠 때는 이 검사와 함께 계획을 바꾼다)')
    return problems


def conflict_problems(repo, add):
    """다른 도구 표와 부딪히는 단어. 남으면 mine_refresh 색인·테스트가 깨진다."""
    problems = []
    hanzi = {entry['hanzi'] for entry in add}
    fixes = load_fixes()
    moves = load_json(MOVES_PATH)
    for token in sorted(hanzi & set(fixes.get('split', {}))):
        problems.append(f'{token}: tools/vocab_fixes.json split에 있다(그 문항만 나누는 items로 옮긴다)')
    for token in sorted(hanzi & set(moves.get('split', {}))):
        problems.append(f'{token}: tools/mine_moves.json split에 있다')
    for token in sorted(hanzi & {k for k in moves.get('words', {}) if '#' not in k}):
        problems.append(f'{token}: tools/mine_moves.json words에 있다(지금 데이터에 들어오면 그 표에서 뺀다)')
    return problems


def registry_problems(registry, vocab):
    """은퇴 장부 movedTo 검사(tools/test_vocab_fixes.py와 같은 규칙). 모든 은퇴 카드: movedTo = moved_to(한자, 지금 한자).
    듣기·독해 은퇴 카드(HSK3L·HSK3R) 중 같은 한자가 더는 없는 것은 tools/vocab_fixes.json movedTo에 사람이 정한 값이 있어야 한다."""
    fixes = load_fixes()
    table = fixes.get('movedTo', {})
    alive = {card['hanzi'] for card in vocab}
    problems = []
    for entry_id, value in sorted(registry['retired'].items()):
        expected = moved_to(value['hanzi'], alive, fixes)
        if value['movedTo'] != expected:
            problems.append(f'은퇴 카드 {entry_id} {value["hanzi"]}: 장부 movedTo {value["movedTo"]!r} ≠ 규칙 {expected!r}')
        if (entry_id.startswith(('HSK3L-', 'HSK3R-')) and value['hanzi'] not in alive
                and table.get(value['hanzi'], 'MISSING') != value['movedTo']):
            problems.append(f'은퇴 카드 {entry_id} {value["hanzi"]}: apply하면 movedTo가 {value["movedTo"]!r}가 된다 → '
                            f'tools/vocab_fixes.json movedTo의 {value["hanzi"]}를 {json.dumps(value["movedTo"], ensure_ascii=False)}로 고친다')
    return problems


def load_module(name, path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rebuild_exam_lessons(repo):
    """듣기·독해 단원을 공개 데이터로 다시 만든다(vocab_fixes.py --apply-listening과 같은 길 + 독해 update_vocab).
    pypinyin이 필요하다(~/venv-store/hsk-listening/bin/python). (듣기 카드 수, 독해 카드 수)를 돌려준다."""
    import vocab_fixes
    tools = HERE.parent
    _, listened = vocab_fixes.apply_listening(repo)
    sys.path.insert(0, str(tools / 'reading'))
    reading = load_module('reading_assemble', tools / 'reading' / 'assemble.py')
    index = load_json(Path(repo) / 'src' / 'data' / 'reading-index.json')
    tests = [load_json(Path(repo) / 'public' / 'reading' / f'{entry["id"]}.json') for entry in index
             if (Path(repo) / 'public' / 'reading' / f'{entry["id"]}.json').exists()]
    read = reading.update_vocab(tests, Path(repo))
    return listened, read


def simulate(repo, final, registry):
    """임시 사본에서 대강 카드를 넣은 vocab.json으로 듣기·독해 단원을 다시 만들어 본다. 공개 데이터·문장 병음 표가
    바뀌면 멈춘다. (최종 vocab, 최종 장부, (듣기, 독해) 카드 수)를 돌려준다. 저장소는 건드리지 않는다."""
    import shutil
    import tempfile
    import sentence_split
    repo = Path(repo)
    splits_before = sentence_split.SPLITS_PATH.read_bytes() if sentence_split.SPLITS_PATH.exists() else None
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        shutil.copytree(repo / 'src' / 'data', tmp / 'src' / 'data')
        for kind in ('listening', 'reading'):
            (tmp / 'public' / kind).mkdir(parents=True)
            for path in (repo / 'public' / kind).glob('H*.json'):
                shutil.copy2(path, tmp / 'public' / kind / path.name)
        write_files_atomically({tmp / VOCAB_PATH: json.dumps(final, ensure_ascii=False, indent=2) + '\n',
                                tmp / ID_REGISTRY: registry_text(registry)})
        counts = rebuild_exam_lessons(tmp)
        for kind in ('listening', 'reading'):
            for path in (repo / 'public' / kind).glob('H*.json'):
                if path.read_bytes() != (tmp / 'public' / kind / path.name).read_bytes():
                    raise SystemExit(f'듣기·독해를 다시 만들면 공개 데이터가 바뀐다: {path} — 멈춘다')
        after = sentence_split.SPLITS_PATH.read_bytes() if sentence_split.SPLITS_PATH.exists() else None
        if after != splits_before:
            raise SystemExit('듣기를 다시 만들며 tools/sentence_splits.json이 바뀌었다 — git diff로 보고 멈춘다')
        return load_json(tmp / VOCAB_PATH), load_json(tmp / ID_REGISTRY), counts


def build_cards(selection, meanings):
    cards = []
    for entry in selection['add']:
        row = meanings[entry['key']]
        card = {
            'id': None,
            'level': f'HSK{entry["level"]}',
            'lesson': entry['lesson'],
            'category': f'{entry["lesson"]} 단어',
            'itemType': WORD_TYPE,
            'hanzi': entry['hanzi'],
            'pinyin': entry['pinyin'].replace('’', "'"),
            'meaningKo': row['meaningKo'],
            'partOfSpeech': row['partOfSpeech'],
            'exampleZh': (entry['example'] or ['', '', ''])[0],
            'examplePinyin': (entry['example'] or ['', '', ''])[1],
            'exampleKo': (entry['example'] or ['', '', ''])[2],
            'source': SOURCE + (f' · 예문: {entry["example"][3]}' if entry['example'] and entry['example'][3] else ''),
            'tags': [f'HSK{entry["level"]}', WORD_TYPE, entry['lesson']],
        }
        if row.get('hanjaKo'):
            card['hanjaKo'] = row['hanjaKo']
        cards.append((entry['key'], entry['level'], card))
    return cards


def plan_vocab(repo, selection, meanings):
    """새 vocab.json(전체)·장부·card_ids. 파일은 쓰지 않는다."""
    vocab = load_json(Path(repo) / VOCAB_PATH)
    remove = set(OLD_LESSONS) | set(LESSONS.values())
    removed = [card for card in vocab if card.get('lesson') in remove]
    others = [card for card in vocab if card.get('lesson') not in remove]
    registry = load_id_registry(repo)
    ids = load_json(IDS_PATH) if IDS_PATH.exists() else {}
    ids = {k: v for k, v in ids.items() if not k.startswith('_')}
    last = dict(registry['lastNo'])
    for prefix in PREFIXES.values():
        used = [id_number(i) for i in ids.values() if i.startswith(prefix + '-')]
        used += [id_number(i) for i in registry['retired'] if i.startswith(prefix + '-')]
        last[prefix] = max(used + [last.get(prefix, 0)])
    cards, new_ids = [], {}
    for key, level, card in build_cards(selection, meanings):
        prefix = PREFIXES[level]
        if key in ids and ids[key].startswith(prefix + '-'):
            card['id'] = ids[key]
        else:
            last[prefix] += 1
            card['id'] = f'{prefix}-{last[prefix]:03d}'
        new_ids[key] = card['id']
        cards.append(card)
    final = cards + others
    all_ids = [card['id'] for card in final]
    if len(all_ids) != len(set(all_ids)):
        raise SystemExit('vocab.json에 같은 id가 둘 이상 있다')
    alive_ids, alive_hanzi = set(all_ids), {card['hanzi'] for card in final}
    retired = {key: dict(value) for key, value in registry['retired'].items()}
    for card in removed:
        if card['id'] not in alive_ids:
            retired[card['id']] = {'hanzi': card['hanzi']}
    for old_key, old_id in ids.items():  # 지난번 대강 카드 중 이번에 빠진 것
        if old_id not in alive_ids and old_id not in retired:
            retired[old_id] = {'hanzi': next((c['hanzi'] for c in removed if c['id'] == old_id), '')}
    for value in retired.values():  # CardIds.plan과 같은 규칙
        value['movedTo'] = moved_to(value['hanzi'], alive_hanzi)
    if alive_ids & set(retired):
        raise SystemExit(f'은퇴한 id를 다시 썼다: {sorted(alive_ids & set(retired))[:10]}')
    registry = {**registry, 'lastNo': last, 'retired': retired}
    return final, registry, cards, new_ids


def ids_text(new_ids):
    body = {'_about': 'HSK 3.0 대강 카드 id 장부 {API id: 카드 id}. build_outline.py apply가 쓴다. 손으로 고치지 않는다.'}
    body.update(sorted(new_ids.items(), key=lambda kv: int(kv[0])))
    return dump(body)


def main(argv=None):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    raw_cmd = sub.add_parser('raw')
    raw_cmd.add_argument('--api', required=True)
    raw_cmd.add_argument('--doc', required=True)
    raw_cmd.add_argument('--selected', required=True)
    legacy_cmd = sub.add_parser('legacy')
    legacy_cmd.add_argument('--repo', required=True)
    legacy_cmd.add_argument('--rev', default=LEGACY_REV)
    for name in ('select', 'check', 'apply'):
        sub.add_parser(name).add_argument('--repo', required=True)
    args = parser.parse_args(argv)

    if args.command == 'raw':
        raw = build_raw(args.api, args.doc, args.selected)
        write_files_atomically({RAW_PATH: dump_items({k: v for k, v in raw.items() if k != 'items'}, 'items', raw['items'])})
        print(f'{RAW_PATH.name}: {len(raw["items"])}행 {raw["counts"]}')
        return 0
    repo = Path(args.repo)
    if args.command == 'legacy':
        legacy = build_legacy(repo, args.rev)
        write_files_atomically({LEGACY_PATH: dump_items({k: v for k, v in legacy.items() if k != 'cards'}, 'cards', legacy['cards'])})
        print(f'{LEGACY_PATH.name}: {legacy["count"]}개 ({args.rev})')
        return 0
    if args.command == 'select':
        selection = select(load_json(RAW_PATH), app_cards(repo))
        flagged = sum(1 for e in selection['add'] if e['flags'])
        files = {SELECT_PATH: dump_items({'_about': '넣을 것(add)과 비교 정보(app: 같은 한자·같은 읽기의 앱 카드, appOtherReadings: 다른 읽기). '
                                              'draftKo는 Codex 뜻을 앱 형식으로 기계 변환한 초안, flags는 손볼 곳. '
                                              'build_outline.py select가 만든다. 손으로 고치지 않는다.',
                                          'addCount': len(selection['add']), 'flaggedCount': flagged}, 'add', selection['add'])}
        chunks = chunk_rows(selection['add'])
        made = [path for path in chunks if not path.exists()]
        if made and len(made) != len(chunks):
            raise SystemExit('뜻 파일이 일부만 있다. 고친 뜻을 덮지 않도록 멈춘다.')
        if made:
            files.update({path: dump(rows) for path, rows in chunks.items()})
        write_files_atomically(files)
        print(f'넣을 것 {len(selection["add"])}개(손볼 표시 {flagged}개)'
              + (f', 뜻 파일 {len(made)}개를 만들었다' if made else ' (뜻 파일은 이미 있어 그대로 둠)'))
        return 0

    selection = load_json(SELECT_PATH)
    fresh = select(load_json(RAW_PATH), app_cards(repo))
    if [e['key'] for e in fresh['add']] != [e['key'] for e in selection['add']]:
        print('outline_select.json이 지금 데이터와 다르다 → build_outline.py select --repo . 를 다시 돌린다')
        return 1
    problems = meaning_problems(selection['add'], load_meanings()) + conflict_problems(repo, selection['add'])
    for problem in problems:
        print('  ! ' + problem)
    if problems:
        print(f'문제 {len(problems)}개. 파일을 쓰지 않았습니다.')
        return 1
    final, registry, cards, new_ids = plan_vocab(repo, selection, load_meanings())
    final, registry, (listened, read) = simulate(repo, final, registry)
    problems = registry_problems(registry, final)
    for problem in problems:
        print('  ! ' + problem)
    if problems:
        print(f'문제 {len(problems)}개. 파일을 쓰지 않았습니다.')
        return 1
    summary = (f'대강 카드 {len(cards)}개, 듣기 {listened}개, 독해 {read}개, vocab.json {len(final)}개')
    if args.command == 'check':
        print(f'문제 없음. apply하면 {summary}가 된다.')
        return 0
    write_files_atomically({
        repo / VOCAB_PATH: json.dumps(final, ensure_ascii=False, indent=2) + '\n',
        repo / ID_REGISTRY: registry_text(registry),
        IDS_PATH: ids_text(new_ids),
    })
    print(f'넣었습니다: {summary}.')
    import mine_refresh  # tools/mine_refresh.py
    return 0 if mine_refresh.refresh_after_write(repo) else 1

if __name__ == '__main__':
    raise SystemExit(main())
