"""Validate the independently authored B portion against official answers."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
source = json.loads((ROOT / 'public/writing/hsk3-all.json').read_text())
expected = {
    item['id']: item for item in source['items']
    if item['kind'] == 'reorder' and item['id'] >= 'H31110-72'
}
part = json.loads((Path(__file__).parent / 'b.json').read_text())
assert part['version'] == 1
assert set(part['items']) == set(expected), 'B range mismatch'
count = 0
for item_id, study in part['items'].items():
    official = expected[item_id]['answers']
    assert [answer['answerIndex'] for answer in study['answers']] == list(range(len(official)))
    for answer in study['answers']:
        words = answer['words']
        sentence = official[answer['answerIndex']]
        assert ''.join(word[0] for word in words) == sentence, (item_id, words)
        assert answer['ko'].strip()
        for hanzi, pinyin in words:
            assert hanzi and isinstance(pinyin, str)
            if re.fullmatch(r'[。！？；，、：…]+', hanzi):
                assert pinyin == ''
            else:
                assert pinyin.strip(), (item_id, hanzi)
                assert not re.search(r'[0-9\u4e00-\u9fff]', pinyin), (item_id, pinyin)
        count += 1
    assert 3 <= len(study['vocab']) <= 8
    assert len({v['hanzi'] for v in study['vocab']}) == len(study['vocab'])
    for vocab in study['vocab']:
        assert set(vocab) == {'hanzi', 'pinyin', 'meaningKo', 'partOfSpeech'}
        assert all(vocab.values())
        assert any(vocab['hanzi'] in answer for answer in official), (item_id, vocab)
print(f'PASS: {len(expected)} B items, {count} official answers; exact sentence reconstruction, pinyin presence, vocabulary fields/range/membership')
