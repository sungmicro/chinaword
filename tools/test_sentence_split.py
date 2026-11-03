import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sentence_split import (fix_pinyin_text, fix_vocab_pinyin, load_splits, sentence_table, split_test_sentences, split_token,
                            split_words, syllables, token_pieces)

REPO = Path(__file__).resolve().parents[1]
TABLE = {'比较忙': ['比较', '忙'], '很多': ['多'], '李先生': ['李', '先生'], '老李': ['老', '李'], '三四年': ['年级'],
         '喜不喜欢': ['喜欢'], '一个班': ['班']}


class SplitTest(unittest.TestCase):
    def test_syllables_follow_characters_and_keep_tones(self):
        self.assertEqual(syllables('比较忙', 'bǐjiàománg'), ['bǐ', 'jiào', 'máng'])
        self.assertEqual(syllables('老李', 'Lǎo Lǐ'), ['Lǎo', 'Lǐ'])
        self.assertEqual(syllables('先生', 'xiānsheng'), ['xiān', 'sheng'])
        self.assertIsNone(syllables('比较忙', 'bǐjiào'))

    def test_pieces_cover_the_whole_token(self):
        self.assertEqual(token_pieces('很多', ['多']), ['很', '多'])
        self.assertEqual(token_pieces('一个班', ['班']), ['一', '个', '班'])
        self.assertEqual(token_pieces('喜不喜欢', ['喜欢']), ['喜', '不', '喜欢'])
        self.assertIsNone(token_pieces('三四年', ['年级']))

    def test_split_token(self):
        self.assertEqual(split_token('比较忙', 'bǐjiàománg', TABLE), [['比较', 'bǐjiào'], ['忙', 'máng']])
        self.assertEqual(split_token('李先生', 'lǐxiānshēng', TABLE), [['李', 'lǐ'], ['先生', 'xiānshēng']])
        # 조각이 토큰 안에 차례로 없으면 한 글자씩
        self.assertEqual(split_token('三四年', 'sānsìnián', TABLE), [['三', 'sān'], ['四', 'sì'], ['年', 'nián']])
        self.assertIsNone(split_token('比较忙', 'xxx', TABLE))  # 병음을 맞출 수 없으면 그대로
        self.assertIsNone(split_token('学生', 'xuésheng', TABLE))

    def test_split_words_logs_only_changed_pinyin(self):
        log = {}
        words = [['因为', 'yīnwèi'], ['比较忙', 'bǐjiàománg'], ['，', ''], ['老李', 'Lǎo Lǐ']]
        self.assertEqual(split_words(words, TABLE, log),
                         [['因为', 'yīnwèi'], ['比较', 'bǐjiào'], ['忙', 'máng'], ['，', ''], ['老', 'Lǎo'], ['李', 'Lǐ']])
        self.assertEqual(log, {'比较忙': {'bǐjiàománg': 'bǐjiào máng'}})

    def test_split_test_sentences_skips_vocab_and_is_idempotent(self):
        test = {'items': [{'script': [{'words': [['比较忙', 'bǐjiàománg']]}],
                           'vocab': [{'hanzi': '比较忙', 'pinyin': 'bǐjiàománg', 'words': [['比较忙', 'bǐjiàománg']]}]}]}
        once = copy.deepcopy(test)
        self.assertEqual(split_test_sentences(once, TABLE), 1)
        self.assertEqual(once['items'][0]['script'][0]['words'], [['比较', 'bǐjiào'], ['忙', 'máng']])
        self.assertEqual(once['items'][0]['vocab'], test['items'][0]['vocab'])
        twice = copy.deepcopy(once)
        self.assertEqual(split_test_sentences(twice, TABLE), 0)
        self.assertEqual(twice, once)

    def test_fix_pinyin_text(self):
        fixes = {'比较忙': {'bǐjiàománg': 'bǐjiào máng'}, '很多': {'hěnduō': 'hěn duō'},
                 '国家图书馆': {'guójiātúshūguǎn': 'guójiā túshūguǎn', 'Guójiātúshūguǎn': 'Guójiā Túshūguǎn'}}
        zh = '因为工作比较忙，小李最近瘦了很多。'
        once = fix_pinyin_text('Yīnwèi gōngzuò bǐjiàománg, xiǎo lǐ zuìjìn shòu le hěnduō.', zh, fixes)
        self.assertEqual(once, 'Yīnwèi gōngzuò bǐjiào máng, xiǎo lǐ zuìjìn shòu le hěn duō.')
        self.assertEqual(fix_pinyin_text(once, zh, fixes), once)
        self.assertEqual(fix_pinyin_text('Hěnduō rén.', '很多人。', fixes), 'Hěn duō rén.')
        self.assertEqual(fix_pinyin_text('hěnduōnián', '很多年', fixes), 'hěnduōnián')
        # 대소문자가 다른 두 표기는 각자 그대로
        self.assertEqual(fix_pinyin_text('zhǐyǒu Guójiātúshūguǎn yǒu', '只有国家图书馆有', fixes), 'zhǐyǒu Guójiā Túshūguǎn yǒu')
        self.assertEqual(fix_pinyin_text('zhǐyǒu guójiātúshūguǎn yǒu', '只有国家图书馆有', fixes), 'zhǐyǒu guójiā túshūguǎn yǒu')


class CurrentDataTest(unittest.TestCase):
    """공개 데이터와 vocab.json에 붙은 토큰·병음이 남지 않았는지(tools/vocab_fixes.py --repo . --apply-sentences)."""

    def test_public_sentences_have_no_splittable_tokens(self):
        table = sentence_table()
        for kind in ('reading', 'listening'):
            for path in sorted((REPO / 'public' / kind).glob('H*.json')):
                data = json.loads(path.read_text(encoding='utf-8'))
                with self.subTest(path=path.name):
                    self.assertEqual(split_test_sentences(data, table), 0)

    def test_vocab_json_example_pinyin_is_fixed(self):
        vocab = json.loads((REPO / 'src' / 'data' / 'vocab.json').read_text(encoding='utf-8'))
        self.assertEqual(fix_vocab_pinyin(vocab, load_splits()), 0)
        self.assertNotIn('bǐjiàománg', json.dumps(vocab, ensure_ascii=False))


if __name__ == '__main__':
    unittest.main()
