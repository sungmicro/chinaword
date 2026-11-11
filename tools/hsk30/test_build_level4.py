import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_level4 as b  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


def item(oid, hanzi, pinyin, pos, ocr=None):
    return {'officialId': oid, 'hanzi': hanzi, 'pinyin': pinyin, 'pos': pos, 'ocr': ocr or hanzi}


def card(cid, hanzi, pinyin, lesson):
    return {'id': cid, 'hanzi': hanzi, 'pinyin': pinyin, 'lesson': lesson, 'meaningKo': '뜻'}


class SelectTest(unittest.TestCase):
    def run_select(self, items, vocab):
        out = b.select({'items': items}, vocab)
        return {e['hanzi']: e for e in out['add']}, {e['hanzi']: e for e in out['skipped']}

    def test_new_word_is_added_with_korean_pos(self):
        add, _ = self.run_select([item('L4-1', '便利', 'biànlì', 'V/N')], [])
        self.assertEqual(add['便利']['itemType'], '단어')
        self.assertEqual(add['便利']['posKo'], '동사/명사')

    def test_same_word_skipped(self):
        _, skipped = self.run_select([item('L4-1', '你好', 'nǐhǎo', 'N')], [card('a', '你好', 'nǐhǎo', 'Lesson 1')])
        self.assertTrue(skipped['你好']['reason'].startswith('same:'))

    def test_other_reading_skipped_unless_polyphone(self):
        vocab = [card('a', '打', 'dǎ', 'Lesson 1'), card('b', '得', 'de', 'Lesson 1')]
        add, skipped = self.run_select([item('L4-1', '打', 'dá', 'M'), item('L4-2', '得', 'děi', 'Aux')], vocab)
        self.assertTrue(skipped['打']['reason'].startswith('reading:'))
        self.assertEqual(add['得']['existing'], ['de'])
        self.assertIn('다른 읽기', add['得']['note'])

    def test_same_word_spelling_variant(self):
        _, skipped = self.run_select([item('L4-1', '上个月', 'shàng ge yuè', 'N')],
                                     [card('a', '上个月', 'shànggèyuè', 'Lesson 1')])
        self.assertTrue(skipped['上个月']['reason'].startswith('same:'))

    def test_exclude(self):
        _, skipped = self.run_select([item('L4-1', '多年', 'duōnián', 'N')], [])
        self.assertTrue(skipped['多年']['reason'].startswith('exclude:'))

    def test_merge_same_pair(self):
        add, _ = self.run_select([item('L4-1', '批', 'pī', 'V', '批（动）'), item('L4-2', '批', 'pī', 'M', '批（量）')], [])
        self.assertEqual(len(add), 1)
        self.assertEqual(len(add['批']['officialIds']), 2)
        self.assertEqual(add['批']['posKo'], '동사/양사')
        self.assertIn('괄호 안 품사', add['批']['note'])

    def test_pattern(self):
        add, _ = self.run_select([item('L4-1', '…分之…', 'fēnzhī', '')], [])
        self.assertEqual(add['…分之…']['itemType'], '패턴')
        self.assertEqual(add['…分之…']['posKo'], '패턴')

    def test_own_lesson_cards_are_not_existing(self):
        add, skipped = self.run_select([item('L4-1', '便利', 'biànlì', 'Adj')], [card('x', '便利', 'biànlì', b.LESSON)])
        self.assertIn('便利', add)
        self.assertNotIn('便利', skipped)


class MeaningProblemsTest(unittest.TestCase):
    ENTRY = {'key': 'L4-1', 'hanzi': '便利', 'pinyin': 'biànlì', 'posKo': '형용사'}

    def row(self, **kw):
        base = {'key': 'L4-1', 'hanzi': '便利', 'pinyin': 'biànlì', 'partOfSpeech': '형용사', 'meaningKo': '편리하다'}
        base.update(kw)
        return base

    def problems(self, row, entry=None):
        return b.meaning_problems([entry or self.ENTRY], {row['key']: row} if row else {})

    def test_ok(self):
        self.assertEqual(self.problems(self.row()), [])

    def test_bad_cases(self):
        for kw in ({'meaningKo': ''}, {'meaningKo': 'abc'}, {'meaningKo': '가' * 41}, {'meaningKo': ' 편리하다'},
                   {'pinyin': 'bianli'}, {'partOfSpeech': '명사'}, {'partOfSpeech': ''}, {'partOfSpeech': '단어'}):
            with self.subTest(kw=kw):
                entry = dict(self.ENTRY, posKo='') if kw.get('partOfSpeech') in ('단어',) else None
                self.assertTrue(self.problems(self.row(**kw), entry), kw)

    def test_key_mismatch(self):
        extra = b.meaning_problems([self.ENTRY], {'L4-1': self.row(), 'L4-9': self.row(key='L4-9')})
        self.assertTrue(any('L4-9' in p for p in extra))
        missing = b.meaning_problems([self.ENTRY], {})
        self.assertTrue(any('뜻 파일에 없음' in p for p in missing))


class PlanVocabTest(unittest.TestCase):
    def make_repo(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        data = Path(tmp.name) / 'src' / 'data'
        data.mkdir(parents=True)
        vocab = [card('L8-1', '课', 'kè', 'Lesson 8'), card('LS-1', '听', 'tīng', 'HSK3 듣기'),
                 card('RD-1', '读', 'dú', 'HSK3 독해')]
        (data / 'vocab.json').write_text(json.dumps(vocab, ensure_ascii=False), encoding='utf-8')
        (data / 'vocab-retired.json').write_text(json.dumps({'lastNo': {}, 'retired': {}}), encoding='utf-8')
        return Path(tmp.name), data

    @staticmethod
    def sel(*words):
        add = [{'key': f'L4-{i}', 'hanzi': h, 'pinyin': p, 'itemType': '단어'} for i, (h, p) in enumerate(words, 1)]
        meanings = {e['key']: {'meaningKo': '뜻', 'partOfSpeech': '명사'} for e in add}
        return {'add': add}, meanings

    def test_order_ids_and_retire(self):
        repo, data = self.make_repo()
        selection, meanings = self.sel(('甲', 'jiǎ'), ('乙', 'yǐ'))
        final, registry, _ = b.plan_vocab(repo, selection, meanings)
        self.assertEqual([c['id'] for c in final], ['L8-1', 'HSK4-001', 'HSK4-002', 'LS-1', 'RD-1'])
        self.assertEqual(registry['lastNo']['HSK4'], 2)
        (data / 'vocab.json').write_text(json.dumps(final, ensure_ascii=False), encoding='utf-8')
        selection, meanings = self.sel(('乙', 'yǐ'), ('丙', 'bǐng'))
        final, registry, _ = b.plan_vocab(repo, selection, meanings)
        ids = {c['hanzi']: c['id'] for c in final}
        self.assertEqual(ids['乙'], 'HSK4-002')
        self.assertEqual(ids['丙'], 'HSK4-003')
        self.assertEqual(registry['retired']['HSK4-001'], {'hanzi': '甲', 'movedTo': None})


class RealDataTest(unittest.TestCase):
    def test_select_and_vocab_match_files(self):
        raw = b.load_json(b.RAW_PATH)
        vocab = b.load_json(REPO / b.VOCAB_PATH)
        selection = b.load_json(b.SELECT_PATH)
        fresh = b.select(raw, vocab)
        self.assertEqual([e['key'] for e in fresh['add']], [e['key'] for e in selection['add']])
        final, _, _ = b.plan_vocab(REPO, selection, b.load_meanings())
        self.assertEqual(final, vocab)


if __name__ == '__main__':
    unittest.main()
