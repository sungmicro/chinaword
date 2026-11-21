#!/usr/bin/env python3
"""HSK 3.0 공식 샘플(3급·4급)의 공개 데이터를 조립하고 검사한다.

조립(작업 폴더의 중간 산출물 → public/hsk30, src/data/hsk30-index.json):
  assemble30.py --repo . [--work ~/hsk30-work]
    paper.json(문항·보기·정답) + timings.json(문항별 start/end) + script.json(대본 원문)
    + {listening,reading,writing}-enrich.json(해설) → public/hsk30/S30-x-{listening,reading,writing}.json
  작업 폴더는 저장소 밖(Drive 아님)이라 경로를 인자로 받는다. 기본값은 ~/hsk30-work.

검사(저장소의 공개 데이터만 본다. 작업 폴더가 없어도 된다):
  assemble30.py --repo . --check [--work ~/hsk30-work]
    --work를 주면 조립 때와 같이 원본(paper·script) 대조까지 한다.

쓰는 파일은 public/hsk30/S30-*-{listening,reading,writing}.json과 src/data/hsk30-index.json뿐이다.
vocab.json, listening-index.json, reading-index.json, 기존 public 파일은 쓰지 않는다.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vocab_fixes import has_hangul  # noqa: E402
from mine_refresh import refresh_after_write  # noqa: E402

TESTS = {
    'S30-3': {'level': 3, 'title': 'HSK 3.0 3급 샘플', 'counts': {'listening': 30, 'reading': 30, 'writing': 10}},
    'S30-4': {'level': 4, 'title': 'HSK 3.0 4급 샘플', 'counts': {'listening': 32, 'reading': 32, 'writing': 6}},
}
AREAS = ('listening', 'reading', 'writing')
PUBLIC = Path('public') / 'hsk30'
INDEX_PATH = Path('src') / 'data' / 'hsk30-index.json'
CJK = re.compile(r'[一-鿿]')
PUNCT_ONLY = re.compile(r'^[\s，。！？：；、“”‘’（）《》…—,.?!:;()\[\]"\'·%]+$')
SPACE = re.compile(r'\s+')

LISTENING_GUIDES = {
    'S30-3': {
        1: '듣고 알맞은 사진 고르기 (사진 6장·5장 중 하나, 실제 시험에서는 두 번 들려줍니다)',
        2: '대화를 듣고 질문에 답하기 (보기 3개, 실제 시험에서는 두 번 들려줍니다)',
        3: '단락을 듣고 질문에 답하기 (보기 3개, 29~30번은 같은 글, 실제 시험에서는 두 번 들려줍니다). 묶음 문항은 문항마다 지문을 다시 들려줍니다(이어 듣기 때 지문이 반복돼요).',
    },
    'S30-4': {
        1: '대화를 듣고 질문에 답하기 (보기 4개, 한 번만 들려줍니다)',
        2: '단락을 듣고 질문에 답하기 (보기 4개, 20~21·22~23·24~25·26~27·28~29·30~32번은 같은 글, 한 번만 들려줍니다). 묶음 문항은 문항마다 지문을 다시 들려줍니다(이어 듣기 때 지문이 반복돼요).',
    },
}
READING_GUIDES = {
    'match': '서로 이어지는 문장 짝 찾기 (보기 6개 중 하나)',
    'wordbank': '빈칸에 알맞은 단어 고르기',
    'passage': '짧은 글을 읽고 질문에 답하기',
    'cloze': '빈칸에 알맞은 문장 고르기',
}
WRITING_GUIDES = {
    'S30-3': {1: '병음을 보고 빈칸에 알맞은 한자 쓰기', 2: '사진을 보고 제시어로 문장 쓰기'},
    'S30-4': {1: '사진을 보고 제시어로 문장 쓰기', 2: '80자 이상 짧은 글 쓰기'},
}


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def dump_compact(data):
    return json.dumps(data, ensure_ascii=False, separators=(',', ':'))


def squash(text):
    return SPACE.sub('', text or '')


def joined(words):
    return ''.join(word[0] for word in words)


def group_nos(group_id):
    first, _, last = str(group_id).partition('-')
    return list(range(int(first), int(last or first) + 1))


# ---------------------------------------------------------------- 조립

def assemble_listening(sid, paper, timings, script, enrich):
    lis = paper['listening']
    times = {t['no']: t for t in timings}
    lines = {i['no']: i['lines'] for i in script['items']}
    items = []
    for src in lis['items']:
        no = src['no']
        extra = enrich['items'][str(no)]
        choices = dict(src['choices'])
        if choices.get('type') == 'text':
            by_label = extra['choices']
            choices = {'type': 'text', 'options': [
                {'label': o['label'], 'words': by_label[o['label']]['words'], 'ko': by_label[o['label']]['ko']}
                for o in src['choices']['options']]}
        elif not choices.get('example'):
            choices.pop('example', None)
        item = {'no': no, 'part': src['part']}
        if src.get('group'):
            item['group'] = src['group']
        item.update({'start': times[no]['start'], 'end': times[no]['end'], 'choices': choices,
                     'answer': src['answer'], 'script': extra['script'], 'vocab': extra['vocab'],
                     'grammar': extra['grammar']})
        items.append(item)
    parts = [{'part': p['part'], 'guide': LISTENING_GUIDES[sid][p['part']]} for p in lis['parts']]
    return {'id': sid, 'title': TESTS[sid]['title'], 'audio': f'{sid}.mp3', 'parts': parts, 'items': items}


def assemble_reading(sid, paper, enrich):
    rd = paper['reading']
    groups = []
    for src in list(rd['groups']) + list(rd['cloze']):
        merged = enrich['groups'][src['id']]
        group = {'id': src['id'], 'part': src['part'], 'options': merged['options'], 'example': src.get('example')}
        if merged.get('trap'):
            group['trap'] = merged['trap']
        groups.append(group)
    groups.sort(key=lambda g: (g['part'], group_nos(g['id'])[0]))
    items = []
    for src in rd['items']:
        no = src['no']
        extra = enrich['items'][str(no)]
        item = {'no': no, 'part': src['part'], 'group': src.get('group'), 'answer': src['answer'],
                'lines': extra['lines'], 'question': extra['question'], 'options': extra['options'],
                'pair': extra['pair'], 'explain': extra['explain']}
        if src.get('passageGroup'):
            item['passageGroup'] = src['passageGroup']
        items.append(item)
    kinds = {p['part']: p['kind'] for p in rd['parts']}
    parts = [{'part': p['part'], 'guide': READING_GUIDES[p['kind']], 'kind': p['kind']} for p in rd['parts']]
    if sid == 'S30-4':
        for part in parts:
            if part['kind'] == 'passage':
                part['guide'] = '글을 읽고 질문에 답하기'
    passage_groups = sorted({i['passageGroup'] for i in items if i.get('passageGroup')}, key=lambda g: group_nos(g)[0])
    if passage_groups:
        note = '·'.join(g.replace('-', '~') for g in passage_groups) + '번은 같은 글'
        for part in parts:
            if part['kind'] == 'passage':
                part['guide'] += f' ({note})'
    assert set(kinds) == {p['part'] for p in parts}
    return {'id': sid, 'title': TESTS[sid]['title'], 'parts': parts, 'groups': groups, 'items': items}


def assemble_writing(sid, paper, enrich):
    items = []
    for src in paper['writing']['items']:
        extra = enrich['items'][str(src['no'])]
        kind = src['kind']
        if kind == 'hanzi':
            item = {k: src[k] for k in ('id', 'exam', 'no', 'part', 'kind', 'sentence', 'pinyin', 'answers')}
            item['explain'] = extra['explain']
        elif kind == 'picture':
            item = {k: src[k] for k in ('id', 'exam', 'no', 'part', 'kind', 'word')}
            item['wordPinyin'] = extra['wordPinyin']
            item['image'] = src['image']
            item['answers'] = src['answers']
            item['explain'] = extra['explain']
        else:
            item = {k: src[k] for k in ('id', 'exam', 'no', 'part', 'kind')}
            item.update({'prompt': extra['prompt'], 'minChars': src['minChars'], 'model': extra['model'],
                         'aiWritten': extra['aiWritten'], 'explain': extra['explain']})
        items.append(item)
    parts = sorted({i['part'] for i in items})
    return {'parts': [{'part': p, 'guide': WRITING_GUIDES[sid][p]} for p in parts], 'items': items}


def build_index():
    entries = []
    for sid, meta in TESTS.items():
        entry = {'id': sid, 'level': meta['level'], 'title': meta['title']}
        for area in AREAS:
            entry[area] = {'file': f'{sid}-{area}.json', 'count': meta['counts'][area]}
        entries.append(entry)
    return entries


def load_work(work, sid):
    base = Path(work).expanduser() / sid
    data = {name: read_json(base / f'{name}.json') for name in ('paper', 'timings', 'script')}
    for area in AREAS:
        data[area] = read_json(base / f'{area}-enrich.json')
    return data


# ---------------------------------------------------------------- 검사

class Report:
    def __init__(self):
        self.errors = []

    def add(self, where, message):
        self.errors.append(f'{where}: {message}')


def check_words(words, where, report, source=None, allow_slot=False):
    """words = [[한자, 병음(, 표식)], ...]. 한자·숫자 토큰에는 병음이 있어야 하고, 이으면 원문과 같아야 한다."""
    if not isinstance(words, list) or not words:
        report.add(where, 'words가 비었음')
        return
    for word in words:
        if not (isinstance(word, list) and len(word) in (2, 3) and all(isinstance(x, str) for x in word)):
            report.add(where, f'words 항목 모양이 이상함 {word!r}')
            continue
        token, pinyin = word[0], word[1]
        is_slot = len(word) == 3 and word[2].startswith('slot:')
        if is_slot:
            if not allow_slot:
                report.add(where, f'빈칸 토큰 {token}이 있으면 안 되는 곳')
            continue
        if (CJK.search(token) or re.search(r'\d', token)) and not pinyin.strip():
            report.add(where, f'병음 없음 {token!r}')
        if PUNCT_ONLY.match(token) and pinyin:
            report.add(where, f'부호에 병음 {word!r}')
    if source is not None and squash(joined(words)) != squash(source):
        report.add(where, f'words를 이으면 원문과 다름: {joined(words)!r} != {source!r}')


def check_vocab(vocab, where, report, minimum=1):
    if not isinstance(vocab, list) or not (minimum <= len(vocab) <= 8):
        report.add(where, f'단어 {len(vocab) if isinstance(vocab, list) else vocab!r}개(허용 {minimum}~8)')
        return
    for entry in vocab:
        for field in ('hanzi', 'pinyin', 'partOfSpeech', 'meaningKo'):
            if not str(entry.get(field, '')).strip():
                report.add(where, f'단어 {entry.get("hanzi")} {field} 비었음')
        if not has_hangul(entry.get('meaningKo')):
            report.add(where, f'단어 {entry.get("hanzi")} 뜻에 한글이 없음 {entry.get("meaningKo")!r}')
        if entry.get('partOfSpeech') == '단어':
            report.add(where, f'단어 {entry.get("hanzi")} 품사가 «단어»')


def check_grammar(grammar, where, report, minimum=1):
    if not isinstance(grammar, list) or not (minimum <= len(grammar) <= 3):
        report.add(where, f'문법 {len(grammar) if isinstance(grammar, list) else grammar!r}개(허용 {minimum}~3)')
        return
    for entry in grammar:
        if not str(entry.get('pattern', '')).strip() or not has_hangul(entry.get('note')):
            report.add(where, f'문법 항목에 pattern이 없거나 설명에 한글이 없음 {entry!r}')


def check_ko(text, where, report):
    if not has_hangul(text):
        report.add(where, f'한국어 뜻에 한글이 없음 {text!r}')


def check_listening(sid, data, public, report, paper=None, script=None):
    meta = TESTS[sid]
    where = f'{sid} 듣기'
    items = data['items']
    if len(items) != meta['counts']['listening'] or [i['no'] for i in items] != list(range(1, meta['counts']['listening'] + 1)):
        report.add(where, f'문항 수·번호가 맞지 않음({len(items)})')
    if data.get('audio') != f'{sid}.mp3' or not (public / data['audio']).exists():
        report.add(where, f'음원 {data.get("audio")} 없음')
    part_set = {p['part'] for p in data['parts']}
    for p in data['parts']:
        if not has_hangul(p.get('guide')):
            report.add(where, f'부분 {p["part"]} 안내에 한글이 없음')
    last_end = 0
    paper_items = {i['no']: i for i in paper['listening']['items']} if paper else {}
    lines = {i['no']: i['lines'] for i in script['items']} if script else {}
    for item in items:
        no = item['no']
        at = f'{where} {no}번'
        if item['part'] not in part_set:
            report.add(at, f'부분 {item["part"]}이 parts에 없음')
        if not (isinstance(item['start'], (int, float)) and isinstance(item['end'], (int, float)) and 0 <= item['start'] < item['end']):
            report.add(at, f'start/end가 이상함 {item["start"]}~{item["end"]}')
        elif item['start'] < last_end - 1e-6:
            report.add(at, '앞 문항과 구간이 겹침')
        else:
            last_end = item['end']
        choices = item['choices']
        if choices['type'] == 'picture':
            labels = choices['labels']
            if item['answer'] not in labels:
                report.add(at, f'정답 {item["answer"]}이 사진 라벨에 없음')
            if choices.get('example') is not None and choices['example'] not in labels:
                report.add(at, '예시 라벨이 사진 라벨에 없음')
            if not (public / choices['image']).exists():
                report.add(at, f'사진 {choices["image"]} 없음')
            if sid == 'S30-3' and item['part'] == 1 and no <= 5 and choices.get('example') != 'D':
                report.add(at, '3급 1~5번 예시는 D')
        elif choices['type'] == 'text':
            labels = [o['label'] for o in choices['options']]
            want = 3 if sid == 'S30-3' else 4
            if labels != list('ABCD'[:want]):
                report.add(at, f'보기 라벨 {labels}')
            if item['answer'] not in labels:
                report.add(at, f'정답 {item["answer"]}이 보기에 없음')
            for opt in choices['options']:
                src = None
                if paper:
                    src = next((o['text'] for o in paper_items[no]['choices']['options'] if o['label'] == opt['label']), None)
                check_words(opt['words'], f'{at} 보기 {opt["label"]}', report, src)
                check_ko(opt['ko'], f'{at} 보기 {opt["label"]} ko', report)
        else:
            report.add(at, f'알 수 없는 보기 형식 {choices["type"]}')
        if paper and item['answer'] != paper_items[no]['answer']:
            report.add(at, f'정답이 시험지와 다름 {item["answer"]} != {paper_items[no]["answer"]}')
        if paper and item.get('group') != (paper_items[no].get('group') or None):
            report.add(at, f'묶음이 시험지와 다름 {item.get("group")}')
        if item.get('group') and not re.fullmatch(r'\d+-\d+', item['group']):
            report.add(at, f'묶음 표기 {item["group"]} (하이픈)')
        if not item['script']:
            report.add(at, '대본이 비었음')
        if script and len(item['script']) != len(lines[no]):
            report.add(at, f'대본 줄 수가 script.json과 다름 {len(item["script"])} != {len(lines[no])}')
        for k, line in enumerate(item['script']):
            src = lines[no][k]['text'] if script and k < len(lines[no]) else None
            check_words(line['words'], f'{at} 대본 {k}', report, src)
            check_ko(line.get('ko'), f'{at} 대본 {k} ko', report)
            if script and k < len(lines[no]) and line.get('speaker') != lines[no][k]['speaker']:
                report.add(at, f'대본 {k} 화자가 script.json과 다름')
        check_vocab(item['vocab'], at, report)
        check_grammar(item['grammar'], at, report)
    grouped = {}
    for item in items:
        if item.get('group'):
            grouped.setdefault(item['group'], []).append(item['no'])
    for gid, nos in grouped.items():
        if nos != group_nos(gid):
            report.add(where, f'묶음 {gid}의 문항 {nos}')


def check_reading(sid, data, report, paper=None):
    meta = TESTS[sid]
    where = f'{sid} 독해'
    items = data['items']
    if len(items) != meta['counts']['reading']:
        report.add(where, f'문항 수 {len(items)}')
    kinds = {}
    for p in data['parts']:
        if p.get('kind') not in READING_GUIDES:
            report.add(where, f'부분 {p["part"]} kind 없음·이상함')
        kinds[p['part']] = p.get('kind')
        if not has_hangul(p.get('guide')):
            report.add(where, f'부분 {p["part"]} 안내에 한글이 없음')
    groups = {g['id']: g for g in data['groups']}
    paper_items = {i['no']: i for i in paper['reading']['items']} if paper else {}
    paper_groups = {g['id']: g for g in (paper['reading']['groups'] + paper['reading']['cloze'])} if paper else {}
    if paper and set(groups) != set(paper_groups):
        report.add(where, f'묶음 id가 시험지와 다름 {sorted(groups)}')
    for gid, group in groups.items():
        at = f'{where} 묶음 {gid}'
        labels = [o['label'] for o in group['options']]
        if len(labels) != len(set(labels)):
            report.add(at, f'보기 라벨 중복 {labels}')
        for opt in group['options']:
            src = None
            if paper and gid in paper_groups:
                src = next((o['text'] for o in paper_groups[gid]['options'] if o['label'] == opt['label']), None)
            check_words(opt['words'], f'{at} 보기 {opt["label"]}', report, src)
            check_ko(opt['ko'], f'{at} 보기 {opt["label"]} ko', report)
        trap = group.get('trap')
        if trap and trap['label'] not in labels:
            report.add(at, 'trap 라벨이 보기에 없음')
    answers_in_group = {}
    for item in items:
        no = item['no']
        at = f'{where} {no}번'
        kind = kinds.get(item['part'])
        if paper and item['answer'] != paper_items[no]['answer']:
            report.add(at, f'정답이 시험지와 다름 {item["answer"]} != {paper_items[no]["answer"]}')
        if kind == 'passage':
            options = item.get('options') or []
            if not options:
                report.add(at, '지문형인데 options가 없음')
            labels = [o['label'] for o in options]
            if item['answer'] not in labels:
                report.add(at, f'정답 {item["answer"]}이 보기에 없음')
            if not item.get('question'):
                report.add(at, 'question 없음')
            else:
                src = paper_items[no]['question'] if paper else None
                check_words(item['question']['words'], f'{at} 질문', report, src)
                check_ko(item['question']['ko'], f'{at} 질문 ko', report)
            for opt in options:
                src = None
                if paper:
                    src = next((o['text'] for o in paper_items[no]['options'] if o['label'] == opt['label']), None)
                check_words(opt['words'], f'{at} 보기 {opt["label"]}', report, src)
                check_ko(opt['ko'], f'{at} 보기 {opt["label"]} ko', report)
        else:
            gid = item.get('group')
            if gid not in groups:
                report.add(at, f'group {gid}이 groups에 없음')
                continue
            if no not in group_nos(gid):
                report.add(at, f'번호가 묶음 {gid} 범위 밖')
            labels = [o['label'] for o in groups[gid]['options']]
            if item['answer'] not in labels:
                report.add(at, f'정답 {item["answer"]}이 묶음 {gid} 보기에 없음')
            if kind == 'cloze':
                if gid not in ('58-60', '61-64') and sid == 'S30-4':
                    report.add(at, f'cloze 묶음 {gid}')
                slots = {w[2] for line in item['lines'] for w in line['words'] if len(w) == 3}
                want = {f'slot:{n}' for n in group_nos(gid)}
                if slots != want:
                    report.add(at, f'빈칸 토큰 {sorted(slots)}이 {sorted(want)}와 다름')
            answers_in_group.setdefault(gid, []).append(item['answer'])
        for k, line in enumerate(item['lines']):
            src = None
            if paper and kind in ('match', 'passage', 'cloze') and len(paper_items[no]['lines']) == 1 and len(item['lines']) == 1:
                src = paper_items[no]['lines'][0]['text']
            if paper and kind == 'wordbank' and len(item['lines']) == len(paper_items[no]['lines']):
                text = paper_items[no]['lines'][k]['text']
                if '（）' in text:
                    ans = next(o['text'] for o in paper_groups[item['group']]['options'] if o['label'] == item['answer'])
                    src = text.replace('（）', ans)
            if kind == 'passage' and paper and len(item['lines']) > 1:
                src = None
            check_words(line['words'], f'{at} 줄 {k}', report, src, allow_slot=(kind == 'cloze'))
            check_ko(line.get('ko'), f'{at} 줄 {k} ko', report)
        if paper and kind == 'passage' and len(item['lines']) > 1:
            whole = ''.join(joined(line['words']) for line in item['lines'])
            if squash(whole) != squash(paper_items[no]['lines'][0]['text']):
                report.add(at, '문장별 words를 이으면 지문과 다름')
        if paper and kind == 'cloze':
            whole = ''.join(joined(line['words']) for line in item['lines'])
            if squash(whole) != squash(paper_items[no]['lines'][0]['text']):
                report.add(at, '빈칸 글 words를 이으면 시험지와 다름')
        if kind == 'wordbank' and not any('blank' in line for line in item['lines']):
            report.add(at, 'wordbank 문항에 blank 줄이 없음')
        ex = item.get('explain')
        if not ex:
            report.add(at, 'explain 없음')
            continue
        basis = ex.get('basis') or {}
        if not str(basis.get('quote', '')).strip() or not has_hangul(basis.get('note')):
            report.add(at, 'explain.basis(quote·note)가 비었거나 한글이 없음')
        if not isinstance(ex.get('distractors'), list):
            report.add(at, 'explain.distractors 없음')
        else:
            for d in ex['distractors']:
                if not has_hangul(d.get('note')):
                    report.add(at, f'오답 해설에 한글이 없음 {d!r}')
        check_vocab(ex.get('vocab'), at, report)
        check_grammar(ex.get('grammar'), at, report)
    if sid == 'S30-4':
        for gid in ('33-37', '38-42'):
            if gid in groups and not groups[gid].get('trap'):
                report.add(f'{where} 묶음 {gid}', 'trap(남는 보기) 설명이 없음')
    # 단어 빈칸 묶음의 정답은 서로 달라야 한다(한 보기는 한 문항에만).
    for gid, answers in answers_in_group.items():
        if kinds.get(groups[gid]['part']) in ('match', 'wordbank') and len(answers) != len(set(answers)):
            report.add(f'{where} 묶음 {gid}', f'정답이 겹침 {answers}')


def check_writing(sid, data, public, report, paper=None):
    meta = TESTS[sid]
    where = f'{sid} 쓰기'
    items = data['items']
    if len(items) != meta['counts']['writing']:
        report.add(where, f'문항 수 {len(items)}')
    paper_items = {i['no']: i for i in paper['writing']['items']} if paper else {}
    for p in data.get('parts', []):
        if not has_hangul(p.get('guide')):
            report.add(where, f'부분 {p["part"]} 안내에 한글이 없음')
    for item in items:
        no, kind = item['no'], item['kind']
        at = f'{where} {no}번'
        if item['id'] != f'{sid}-{no}' or item['exam'] != sid or not isinstance(item['part'], int):
            report.add(at, 'id·exam·part가 이상함')
        ex = item.get('explain')
        if not ex:
            report.add(at, 'explain 없음')
            continue
        if kind == 'hanzi':
            if item['sentence'].count('___') != 1:
                report.add(at, '빈칸(___)이 정확히 하나가 아님')
            if len(item['answers']) != 1 or not item.get('pinyin'):
                report.add(at, '정답·병음 이상')
            full = item['sentence'].replace('___', item['answers'][0]) if item['answers'] else ''
            check_words(ex['words'], f'{at} 해설 문장', report, full)
            check_ko(ex['ko'], f'{at} 해설 ko', report)
            check_vocab(ex.get('vocab'), at, report)
        elif kind == 'picture':
            if not (public / item['image']).exists():
                report.add(at, f'사진 {item["image"]} 없음')
            if not item.get('word') or not item.get('wordPinyin'):
                report.add(at, '제시어·병음 없음')
            if len(ex['answers']) != len(item['answers']):
                report.add(at, '참고답안 수와 해설 수가 다름')
            for k, (ans, sentence) in enumerate(zip(ex['answers'], item['answers'])):
                check_words(ans['words'], f'{at} 참고답안 {k}', report, sentence)
                check_ko(ans['ko'], f'{at} 참고답안 {k} ko', report)
            if item['word'] not in ''.join(item['answers']):
                report.add(at, '참고답안에 제시어가 없음')
            check_vocab(ex.get('vocab'), at, report)
            check_grammar(ex.get('grammar'), at, report)
        elif kind == 'essay':
            if sid != 'S30-4' or no != 70:
                report.add(at, '짧은 글은 4급 70번만')
            check_words(item['prompt']['words'], f'{at} 글감', report)
            check_ko(item['prompt']['ko'], f'{at} 글감 ko', report)
            if item['minChars'] != 80 or item.get('aiWritten') is not True:
                report.add(at, 'minChars 80·aiWritten true여야 함')
            lines = item['model']['lines']
            for k, line in enumerate(lines):
                check_words(line['words'], f'{at} 예시 글 {k}', report)
                check_ko(line['ko'], f'{at} 예시 글 {k} ko', report)
            size = len(CJK.findall(''.join(joined(line['words']) for line in lines)))  # 한자 수(부호 제외)
            if not 80 <= size <= 100:
                report.add(at, f'예시 글 글자 수 {size}(80~100)')
            check_vocab(ex.get('vocab'), at, report)
            check_grammar(ex.get('grammar'), at, report)
        else:
            report.add(at, f'알 수 없는 kind {kind}')
        if paper:
            src = paper_items[no]
            if item['part'] != src['part'] or item['kind'] != src['kind']:
                report.add(at, '부분·kind가 시험지와 다름')
            if kind in ('hanzi', 'picture') and (item['answers'] != src['answers']):
                report.add(at, '정답이 시험지와 다름')
            if kind == 'hanzi' and (item['sentence'] != src['sentence'] or item['pinyin'] != src['pinyin']):
                report.add(at, '문장·병음이 시험지와 다름')
            if kind == 'picture' and (item['word'] != src['word'] or item['image'] != src['image']):
                report.add(at, '제시어·사진이 시험지와 다름')
            if kind == 'essay' and squash(joined(item['prompt']['words'])) != squash(src['prompt']):
                report.add(at, '글감이 시험지와 다름')


def check_index(repo, report):
    path = repo / INDEX_PATH
    if not path.exists():
        report.add('index', f'{INDEX_PATH} 없음')
        return
    if read_json(path) != build_index():
        report.add('index', f'{INDEX_PATH}가 계약과 다름(id·level·파일 이름·문항 수)')


def check_all(repo, work=None):
    repo = Path(repo)
    public = repo / PUBLIC
    report = Report()
    check_index(repo, report)
    for sid in TESTS:
        data = {}
        for area in AREAS:
            path = public / f'{sid}-{area}.json'
            if not path.exists():
                report.add(sid, f'{path} 없음')
                continue
            data[area] = read_json(path)
        source = load_work(work, sid) if work and (Path(work).expanduser() / sid / 'paper.json').exists() else None
        paper = source['paper'] if source else None
        if 'listening' in data:
            check_listening(sid, data['listening'], public, report, paper, source['script'] if source else None)
        if 'reading' in data:
            check_reading(sid, data['reading'], report, paper)
        if 'writing' in data:
            check_writing(sid, data['writing'], public, report, paper)
    return report


# ---------------------------------------------------------------- 실행

def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(text, encoding='utf-8')
    tmp.replace(path)


def run_assemble(repo, work):
    repo = Path(repo)
    outputs = {}
    for sid in TESTS:
        src = load_work(work, sid)
        paper = src['paper']
        outputs[f'{sid}-listening.json'] = assemble_listening(sid, paper, src['timings'], src['script'], src['listening'])
        outputs[f'{sid}-reading.json'] = assemble_reading(sid, paper, src['reading'])
        outputs[f'{sid}-writing.json'] = assemble_writing(sid, paper, src['writing'])
    # 먼저 임시 위치에 검사하고 통과했을 때만 쓴다(검사 실패 시 기존 파일을 건드리지 않는다).
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp)
        (stage / PUBLIC).mkdir(parents=True)
        for name, data in outputs.items():
            (stage / PUBLIC / name).write_text(dump_compact(data), encoding='utf-8')
        # 이미지·음원은 저장소 것을 보게 한다.
        for asset in (repo / PUBLIC).glob('*'):
            if asset.suffix in ('.jpg', '.mp3'):
                (stage / PUBLIC / asset.name).symlink_to(asset.resolve())
        (stage / INDEX_PATH).parent.mkdir(parents=True)
        (stage / INDEX_PATH).write_text(json.dumps(build_index(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        report = check_all(stage, work)
    if report.errors:
        return report
    for name, data in outputs.items():
        write_text(repo / PUBLIC / name, dump_compact(data))
    write_text(repo / INDEX_PATH, json.dumps(build_index(), ensure_ascii=False, indent=2) + '\n')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--repo', default='.', help='저장소 뿌리(기본 .)')
    parser.add_argument('--work', default=None, help='중간 산출물 폴더(조립 기본 ~/hsk30-work, --check는 주었을 때만 원본 대조)')
    parser.add_argument('--check', action='store_true', help='저장소의 공개 데이터만 검사한다(--work가 있으면 원본 대조도)')
    args = parser.parse_args(argv)
    if args.check:
        report = check_all(args.repo, args.work)
        verb = '검사'
    else:
        report = run_assemble(args.repo, args.work or str(Path.home() / 'hsk30-work'))
        verb = '조립'
    for error in report.errors:
        print('  ! ' + error)
    if report.errors:
        print(f'{verb} 실패: 문제 {len(report.errors)}개' + ('(파일은 쓰지 않았습니다)' if verb == '조립' else ''))
        return 1
    print(f'{verb} 통과' + ('' if args.check else f': {len(TESTS) * 3}개 JSON과 {INDEX_PATH}를 썼습니다'))
    if not args.check and not refresh_after_write(args.repo):
        return 1  # 데이터는 쓴 채로, 내 단어장 갱신 색인을 못 쓰면 실패로 끝낸다
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
