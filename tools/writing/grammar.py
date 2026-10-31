"""수작업 문법 정본을 검증하고 생성 데이터에 병합한다."""
import json
from pathlib import Path
import re

ROLES = {'subject', 'verb', 'adverbial', 'particle', 'predicate', 'object', 'preposition', 'attribute', 'complement', 'modal', 'topic', 'time', 'question', 'location', 'quantity', 'connective'}

def normalize(text):
    return re.sub(r'[\s。，、！？,.!?]', '', text)

def load(path=None):
    data = json.loads((path or Path(__file__).with_name('grammar.json')).read_text())
    assert data['version'] == 1
    return data['items']

def validate_grammar(items, grammar):
    glossary = load_glossary()
    reorder = {x['id']: x for x in items if x['kind'] == 'reorder'}
    assert set(reorder) == set(grammar), '어순 문항과 해설 ID 불일치'
    for item in items:
        assert item['kind'] != 'hanzi' or 'grammar' not in item
    for id, item in reorder.items():
        analyses = grammar[id]['analyses']
        assert len(analyses) == len(item['answers']), id
        assert sorted(a['answerIndex'] for a in analyses) == list(range(len(item['answers']))), id
        for a in analyses:
            assert type(a['answerIndex']) is int, id
            order = a['tokenOrder']
            assert all(type(t) is int for t in order) and sorted(order) == list(range(len(item['tokens']))), id
            groups = a['groups']
            assert groups and 2 <= len(a['steps']) <= 4 and a['keyRule'].strip(), id
            covered = set()
            assembled = []
            positions = []
            for g in groups:
                assert g['role'] in ROLES and g['label'].strip() and g['parts'], id
                for p in g['parts']:
                    t, start, end = p['token'], p['start'], p['end']
                    assert all(type(v) is int for v in (t, start, end)), id
                    assert 0 <= t < len(order) and 0 <= start < end <= len(item['tokens'][t]), id
                    for char in range(start, end):
                        assert (t, char) not in covered, (id, '문자 중복')
                        covered.add((t, char))
                        positions.append((order.index(t), char))
                    assembled.append(item['tokens'][t][start:end])
            assert covered == {(t, c) for t, token in enumerate(item['tokens']) for c in range(len(token))}, (id, '문자 누락')
            assert positions == sorted(positions), (id, '구조 순서')
            assert normalize(''.join(assembled)) == normalize(item['answers'][a['answerIndex']]), id
            assert normalize(''.join(item['tokens'][t] for t in order)) == normalize(item['answers'][a['answerIndex']]), id
            for step in a['steps']:
                assert step['text'].strip() and step['groups'], id
                assert all(type(g) is int and 0 <= g < len(groups) for g in step['groups']), id
            if len(analyses) > 1: assert a.get('difference', '').strip(), id
            assert 'learning' in a, (id, '문법 학습 누락')
            validate_learning(item, a, glossary)

def merge_grammar(items, grammar=None):
    grammar = load() if grammar is None else grammar
    validate_grammar(items, grammar)
    return [{**item, **({'grammar': grammar[item['id']]} if item['kind'] == 'reorder' else {})} for item in items]


def validate_learning(item, analysis, glossary):
    """용어 참조와 해당 문장 안의 실제 문자 범위를 검증한다."""
    learning = analysis['learning']
    terms, usages = glossary['terms'], glossary['usages']
    assert learning['termIds'] and len(learning['termIds']) == len(set(learning['termIds'])), item['id']
    assert all(t in terms for t in learning['termIds']), item['id']
    assert learning['points'], item['id']
    for point in learning['points']:
        assert point['usageId'] in usages and point['explanation'].strip(), item['id']
        usage = usages[point['usageId']]
        assert point['parts'], item['id']
        covered = set()
        text = []
        for part in point['parts']:
            token, start, end = part['token'], part['start'], part['end']
            assert all(type(v) is int for v in (token, start, end)), item['id']
            assert 0 <= token < len(item['tokens']) and 0 <= start < end <= len(item['tokens'][token]), item['id']
            for char in range(start, end):
                assert (token, char) not in covered, item['id']
                covered.add((token, char))
            text.append(item['tokens'][token][start:end])
        # 용법이 가리키는 글자는 표면형과 일치해야 한다. 구조 용법은 examples로 별도 명시한다.
        assert ''.join(text) in usage['forms'], (item['id'], point['usageId'], ''.join(text))
        assert all(t in learning['termIds'] for t in usage['termIds']), (item['id'], point['usageId'])


def load_glossary():
    glossary = json.loads((Path(__file__).resolve().parents[2] / 'src/data/writingGrammarGlossary.json').read_text())
    assert set(glossary['roleTerms']) == ROLES
    assert all(t in glossary['terms'] for t in glossary['roleTerms'].values())
    for term in glossary['terms'].values():
        assert all(term[k].strip() for k in ('label', 'category', 'definition', 'question', 'example'))
    for usage in glossary['usages'].values():
        assert all(usage[k].strip() for k in ('hanzi', 'meaning', 'pattern'))
        assert isinstance(usage['pinyin'], str)
        assert not re.search(r'[\u4e00-\u9fff]', usage['hanzi']) or usage['pinyin'].strip()
        assert usage['forms'] and usage['termIds']
        assert all(t in glossary['terms'] for t in usage['termIds'])
    return glossary
