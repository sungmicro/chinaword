#!/usr/bin/env python3
"""원본 PDF의 layout 텍스트에서 쓰기 190문항을 생성한다. 원본은 읽기만 한다."""
import argparse
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path
import re
import subprocess
from grammar import merge_grammar
from study import merge_study

EXAMS = 'H31001 H31002 H31003 H31004 H31005 H31006 H31007 H31008 H31009 H31110 H31111 H31218 H31219 H31220 H31221 H31328 H31329 H31330 H31332'.split()
HERE = Path(__file__).parent

def clean(s):
    return re.sub(r'\s+', '', s)

def normalized(s):
    return re.sub(r'[\s。，、！？,.!?]', '', s)

def pages(pdf):
    text = subprocess.run(['pdftotext', '-layout', str(pdf), '-'], check=True, capture_output=True, text=True).stdout
    return text.split('\f')

def without_marks(text):
    return re.sub(r'Facebook\s*&\s*Youtube:\s*Hancai\s*Chinese|H3\d{4}\s*-\s*\d+', '', text)

def parse_exam(exam, pdf, override):
    sheet = pages(pdf)
    question_pages = [i for i, page in enumerate(sheet) if '第 71-75 题' in page or '第 76-80 题' in page]
    assert len(question_pages) == 2, (exam, question_pages)
    answer_pages = [(i, page) for i, page in enumerate(sheet) if re.search(r'71．\s*\S', page) and i not in question_pages]
    if override:
        official = {int(k): v for k, v in override['answers'].items()}
        answer_page = override['answerPage']
    else:
        assert len(answer_pages) == 1, exam
        answer_page, text = answer_pages[0]
        answer_page += 1
        official = {int(n): [clean(a) for a in answer.split('/')] for n, answer in re.findall(r'^(7[1-9]|80)．([^\n]+)', without_marks(text), re.M)}
    result = []
    for page_index in question_pages:
        text = without_marks(sheet[page_index])
        if page_index == question_pages[0]:
            for number, row in re.findall(r'^(7[1-5])．([^\n]+)', text, re.M):
                # PDF는 한 칸 공백도 토큰 구분에 사용합니다. 숫자와 뒤의 단위는 한 토큰으로 보존합니다.
                tokens = [clean(t) for t in re.split(r'\s+', row.strip())]
                tokens = [t for t in tokens if t]
                merged = []
                for t in tokens:
                    if merged and merged[-1].isdigit(): merged[-1] += t
                    else: merged.append(t)
                result.append({'no': int(number), 'kind': 'reorder', 'tokens': merged, 'page': page_index + 1})
        else:
            blocks = re.split(r'\n\s*\n', text)
            for block in blocks:
                match = re.search(r'^(7[6-9]|80)．', block, re.M)
                if not match: continue
                before = block[:match.start()]
                py = re.search(r'[A-Za-zÀ-žǍ-ǜüÜ]+', before)
                assert py, (exam, block)
                # 일부 PDF는 번호 앞에 여는 괄호를 둔다 (예: H31001-79).
                sentence = block[match.end():]
                prefix = '（' if '（' in before[py.end():] else ''
                if prefix: sentence = prefix + sentence
                sentence = clean(sentence).replace('（）', '___')
                assert sentence.count('___') == 1, (exam, block, sentence)
                result.append({'no': int(match[1]), 'kind': 'hanzi', 'sentence': sentence, 'pinyin': py[0], 'page': page_index + 1})
    for item in result:
        no = item['no']
        item.update(id=f'{exam}-{no}', exam=exam, answers=official[no])
        item['source'] = {'file': pdf.name, 'page': item.pop('page'), 'sha256': hashlib.sha256(pdf.read_bytes()).hexdigest(), 'answerFile': override['answerFile'] if override else pdf.name, 'answerPage': answer_page}
        if override:
            item['source']['method'] = override['method']
            item['source']['answerSha256'] = override['answerSha256']
            assert answer_page <= override['answerPageCount']
            change = override.get('learningOverrides', {}).get(str(no))
            if change:
                item['source']['officialAnswers'] = official[no]
                item.update(change)
    assert [x['no'] for x in result] == list(range(71, 81)), (exam, result)
    return result

def validate(items):
    assert len(items) == 190
    assert Counter(x['kind'] for x in items) == {'reorder': 95, 'hanzi': 95}
    assert len({x['id'] for x in items}) == 190
    assert [x['seq'] for x in items] == list(range(1, 191))
    for exam in EXAMS:
        assert [x['no'] for x in items if x['exam'] == exam] == list(range(71, 81))
    for x in items:
        assert x['answers'] and all(x['answers']) and x['source']['page'] > 0 and x['source']['answerPage'] > 0
        if x['kind'] == 'reorder':
            candidates = {''.join(p) for p in itertools.permutations(x['tokens'])}
            assert all(normalized(a) in candidates for a in x['answers']), (x['id'], x['tokens'], x['answers'])
        else:
            assert x['sentence'].count('___') == 1 and x['pinyin']
    by_id = {x['id']: x for x in items}
    for a, b in [('H31006-71', 'H31009-71'), ('H31006-78', 'H31009-78')]:
        assert by_id[a]['answers'] == by_id[b]['answers']
    assert [x['id'] for x in items if len(x['answers']) > 1] == ['H31004-75', 'H31005-72', 'H31006-75', 'H31007-77']

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=Path.home() / 'hsk-listening-work/src')
    parser.add_argument('--output', type=Path, default=HERE.parents[1] / 'public/writing/hsk3-all.json')
    args = parser.parse_args()
    overrides = json.loads((HERE / 'overrides.json').read_text())
    items = []
    for exam in EXAMS: items.extend(parse_exam(exam, args.source / f'{exam}.pdf', overrides.get(exam)))
    for seq, item in enumerate(items, 1): item['seq'] = seq
    validate(items)
    items = merge_grammar(items)
    items = merge_study(items)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'version': 1, 'items': items}, ensure_ascii=False, indent=2) + '\n')
    print('19회차 × 10 = 190문항, 어순 95 · 한자 95, 번호·정답·복수답·중복 검증 통과')
    repo = HERE.parents[1]
    if args.output.resolve() == (repo / 'public/writing/hsk3-all.json').resolve():
        import sys
        sys.path.insert(0, str(HERE.parent))
        from mine_refresh import refresh_after_write  # 쓰기 핵심 단어도 내 단어장 갱신 색인에 들어간다
        if not refresh_after_write(repo):
            raise SystemExit(1)  # 쓰기 데이터는 썼지만 내 단어장 갱신 색인을 쓰지 못했다
if __name__ == '__main__': main()
