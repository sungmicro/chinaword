import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from auto_enrich import (
    VOCAB_LIMIT,
    VocabCatalog,
    content_words,
    listening_note_texts,
    sync_public_listening_vocab,
    sync_public_reading_vocab,
    vocab_for,
)


class ContentWordsTest(unittest.TestCase):
    def test_level_new_words_come_before_other_core_words(self):
        texts = ['休息一会儿吧，忙一下午了。', '没关系，我马上就搬完了。']

        words = [word for word, _ in content_words(texts, {'马上', '搬'})]

        self.assertEqual(['马上', '搬'], words[:2])
        self.assertIn('休息', words[2:])
        self.assertEqual(VOCAB_LIMIT, len(words))

    def test_result_never_exceeds_eight(self):
        texts = ['年轻人应该注意锻炼身体，认真学习，努力工作，照顾自己。']
        priority = {'年轻', '应该', '注意', '锻炼', '身体', '认真', '学习', '努力', '工作', '照顾', '自己'}

        words = [word for word, _ in content_words(texts, priority)]

        self.assertEqual(VOCAB_LIMIT, len(words))
        self.assertTrue(set(words).issubset(priority))

    def test_longer_official_expression_blocks_shorter_false_match(self):
        words = [word for word, _ in content_words(
            ['没关系，我马上就搬完了。'],
            {'关系', '马上', '搬'},
            lexicon={'没关系', '关系', '马上', '搬'},
        )]

        self.assertEqual(['马上', '搬'], words[:2])
        self.assertNotIn('关系', words)

    def test_listening_vocab_source_uses_recovered_enrich_lines(self):
        note = {
            'lines': [{'words': [['我', 'wǒ'], ['马上', 'mǎshàng'], ['搬', 'bān']]}],
            'statement': None,
            'options': [{'words': [['回家', 'huíjiā']]}],
        }

        self.assertEqual(['我马上搬', '回家'], listening_note_texts(note))


class VocabCatalogTest(unittest.TestCase):
    def test_only_level_additions_become_priority_words(self):
        entries = [
            {'level': 'HSK3', 'lesson': 'HSK3 추가 300', 'hanzi': '马上'},
            {'level': 'HSK3', 'lesson': 'HSK3 듣기', 'hanzi': '临时词'},
            {'level': 'HSK4', 'lesson': 'HSK4 추가 600', 'hanzi': '安排'},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'vocab.json'
            path.write_text(json.dumps(entries, ensure_ascii=False), encoding='utf-8')
            catalog = VocabCatalog(path)

        self.assertEqual({'马上'}, catalog.priority_words('H31001'))
        self.assertEqual({'安排'}, catalog.priority_words('H41001'))


class VocabForTest(unittest.TestCase):
    def catalog(self, entries):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'vocab.json'
            path.write_text(json.dumps(entries, ensure_ascii=False), encoding='utf-8')
            return VocabCatalog(path)

    def test_meaning_is_never_the_hanzi_itself(self):
        # 사전에 없고 번역도 한자를 그대로 돌려준 토큰: 예전에는 meaningKo='门票'로 공개됐다
        catalog = self.catalog([{'level': 'HSK3', 'lesson': 'HSK3 추가 300', 'hanzi': '桌子', 'meaningKo': '탁자',
                                 'partOfSpeech': '명사', 'pinyin': 'zhuōzi'}])
        vocab = vocab_for(['音乐会的门票我放在桌子上了。'], {'门票': '门票', '音乐会': '콘서트'}, catalog, 'H39999')
        for entry in vocab:
            self.assertNotEqual(entry['meaningKo'], entry['hanzi'])
            self.assertNotEqual(entry['partOfSpeech'], '단어')
        self.assertEqual(next(e for e in vocab if e['hanzi'] == '桌子')['meaningKo'], '탁자')

    def test_fix_table_corrects_names_and_glued_words(self):
        catalog = self.catalog([])
        vocab = vocab_for(['因为工作比较忙，小李最近瘦了很多。'], {}, catalog, 'H31006', where='reading/H31006/52')
        by_hanzi = {entry['hanzi']: entry for entry in vocab}
        self.assertNotIn('比较忙', by_hanzi)
        self.assertNotIn('很多', by_hanzi)
        if '李' in by_hanzi:
            self.assertEqual(by_hanzi['李']['meaningKo'], '리(李, 성씨)')


class PublicSyncTest(unittest.TestCase):
    def test_syncs_only_listening_vocab(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            work = root / 'work/H31001'
            public = root / 'repo/public/listening'
            work.mkdir(parents=True)
            public.mkdir(parents=True)
            (work / 'enrich.json').write_text(json.dumps({
                'items': [{'no': 1, 'vocab': [{'hanzi': '马上'}]}],
            }, ensure_ascii=False), encoding='utf-8')
            (public / 'H31001.json').write_text(json.dumps({
                'title': 'keep', 'items': [{'no': 1, 'script': ['keep'], 'vocab': []}],
            }, ensure_ascii=False), encoding='utf-8')

            sync_public_listening_vocab('H31001', root / 'work', root / 'repo')
            result = json.loads((public / 'H31001.json').read_text(encoding='utf-8'))

        self.assertEqual('keep', result['title'])
        self.assertEqual(['keep'], result['items'][0]['script'])
        self.assertEqual([{'hanzi': '马上'}], result['items'][0]['vocab'])

    def test_syncs_only_reading_vocab(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            work = root / 'work/H31001'
            public = root / 'repo/public/reading'
            work.mkdir(parents=True)
            public.mkdir(parents=True)
            (work / 'enrich-41-50.json').write_text(json.dumps({
                'items': [{'no': 41, 'explain': {'vocab': [{'hanzi': '安排'}]}}],
            }, ensure_ascii=False), encoding='utf-8')
            (public / 'H31001.json').write_text(json.dumps({
                'title': 'keep', 'items': [{'no': 41, 'lines': ['keep'], 'explain': {'vocab': []}}],
            }, ensure_ascii=False), encoding='utf-8')

            sync_public_reading_vocab('H31001', root / 'work', root / 'repo')
            result = json.loads((public / 'H31001.json').read_text(encoding='utf-8'))

        self.assertEqual('keep', result['title'])
        self.assertEqual(['keep'], result['items'][0]['lines'])
        self.assertEqual([{'hanzi': '安排'}], result['items'][0]['explain']['vocab'])


if __name__ == '__main__':
    unittest.main()
