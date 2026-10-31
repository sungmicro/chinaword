"""Validate the independently authored first 49 official reorder answers."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
PART = Path(__file__).with_name('a.json')
source = json.loads((ROOT / 'public/writing/hsk3-all.json').read_text())
ordered = sorted((i for i in source['items'] if i['kind'] == 'reorder'), key=lambda i: i['id'])
expected = ordered[:46]
part = json.loads(PART.read_text())
assert part['version'] == 1
assert list(part['items']) == [i['id'] for i in expected]
answer_count = vocab_count = 0
for question in expected:
    entry = part['items'][question['id']]
    assert len(entry['answers']) == len(question['answers'])
    for index, answer in enumerate(entry['answers']):
        assert answer['answerIndex'] == index
        assert ''.join(h for h, _ in answer['words']) == question['answers'][index], question['id']
        assert answer['ko'].strip()
        for hanzi, pinyin in answer['words']:
            assert hanzi
            if re.search(r'[\u3400-\u9fff0-9]', hanzi):
                assert pinyin.strip(), (question['id'], hanzi)
                assert not re.search(r'[0-9\u3400-\u9fff]', pinyin)
            else:
                assert pinyin == '', (question['id'], hanzi)
        answer_count += 1
    assert 2 <= len(entry['vocab']) <= 8
    assert len({v['hanzi'] for v in entry['vocab']}) == len(entry['vocab'])
    for vocab in entry['vocab']:
        assert set(vocab) == {'hanzi', 'pinyin', 'meaningKo', 'partOfSpeech'}
        assert all(isinstance(v, str) and v.strip() for v in vocab.values())
        assert all(vocab['hanzi'] in sentence for sentence in question['answers'])
        assert not re.search(r'[0-9\u3400-\u9fff]', vocab['pinyin'])
        vocab_count += 1
assert answer_count == 49
print(json.dumps({
    'part': 'a', 'questionCount': len(expected), 'answerCount': answer_count,
    'vocabOccurrences': vocab_count, 'ids': list(part['items']),
    'checks': ['official sentence reconstruction', 'answer index and coverage',
               'nonempty Korean and vocabulary fields', 'vocabulary present in every official answer',
               'unique vocabulary entries', 'spoken text has pinyin and punctuation has none'],
    'manualReview': ['900=jiǔ bǎi; 8=bā; 一米七=yì mǐ qī',
                     'sentence 一/不 sandhi, adjective 地 and complement 得, aspect 了',
                     'polyphonic 长=cháng, 还=hái, 花=huā',
                     'dictionary vocab uses citation tones; 小姐=xiǎojiě; 汉字=hànzì'],
    'openQuestions': []
}, ensure_ascii=False, indent=2))
