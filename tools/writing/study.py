"""완성 문장의 병음·뜻과 핵심 단어 정본을 검증하고 병합한다."""
import json
from pathlib import Path
import re


def load(path=None):
    data = json.loads((path or Path(__file__).with_name('study.json')).read_text())
    assert data['version'] == 1
    return data['items']


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def validate_study(items, study):
    reorder = {item['id']: item for item in items if item['kind'] == 'reorder'}
    assert set(reorder) == set(study), '어순 문항과 학습 ID 불일치'
    assert all('study' not in item for item in items if item['kind'] == 'hanzi'), '한자 문항의 study'
    for id, item in reorder.items():
        entry = study[id]
        answers = entry['answers']
        assert all(type(a['answerIndex']) is int for a in answers), id
        assert sorted(a['answerIndex'] for a in answers) == list(range(len(item['answers']))), (id, '정답 누락/중복')
        for answer in answers:
            assert nonempty(answer['ko']) and answer['words'], id
            for word in answer['words']:
                assert isinstance(word, list) and len(word) == 2, id
                hanzi, pinyin = word
                assert nonempty(hanzi) and isinstance(pinyin, str), id
                if re.search(r'[\u3400-\u9fff0-9]', hanzi):
                    assert nonempty(pinyin), (id, hanzi, '병음 누락')
            assert ''.join(word[0] for word in answer['words']) == item['answers'][answer['answerIndex']], (id, '정답 문장 불일치')
        vocab = entry['vocab']
        assert vocab, (id, '단어 누락')
        assert len({word['hanzi'] for word in vocab}) == len(vocab), (id, '단어 중복')
        for word in vocab:
            assert all(nonempty(word.get(key)) for key in ['hanzi', 'pinyin', 'meaningKo', 'partOfSpeech']), (id, word)
            assert any(word['hanzi'] in answer for answer in item['answers']), (id, word['hanzi'], '문장에 없는 단어')


def merge_study(items, study=None):
    study = load() if study is None else study
    validate_study(items, study)
    return [{**item, **({'study': study[item['id']]} if item['kind'] == 'reorder' else {})} for item in items]
