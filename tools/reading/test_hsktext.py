import unittest

from hsktext import check_words, join_words, tidy, toneless, words_to_pinyin


class TidyTest(unittest.TestCase):
    def test_removes_spaces_next_to_hanzi_and_punctuation(self):
        self.assertEqual(tidy('今天是 9 月 10 日，教师（ ） ！'), '今天是9月10日，教师（）！')

    def test_joins_numbers_with_units(self):
        self.assertEqual(tidy('写着 1.21 元，前面的 1 表示元'), '写着1.21元，前面的1表示元')

    def test_keeps_single_space_between_latin(self):
        self.assertEqual(tidy('A   8 点'), 'A 8点')


class TonelessTest(unittest.TestCase):
    def test_strips_tones_and_writes_u_umlaut_as_v(self):
        self.assertEqual(toneless('lǜsè'), 'lvse')
        self.assertEqual(toneless('Mǎnyì'), 'manyi')


class CheckWordsTest(unittest.TestCase):
    def test_reports_mismatch_with_source(self):
        problems, diffs = [], []
        check_words([['我', 'wǒ'], ['很', 'hěn']], '我很好', 'T', problems, diffs)
        self.assertEqual(len(problems), 1)
        self.assertIn('원문과 다름', problems[0])

    def test_reports_missing_pinyin_and_pinyin_on_punctuation(self):
        problems, diffs = [], []
        check_words([['满意', ''], ['。', 'x']], '满意。', 'T', problems, diffs)
        self.assertEqual(len(problems), 2)

    def test_lists_reading_differences_without_failing(self):
        problems, diffs = [], []
        check_words([['满意', 'mǎnyì'], ['还', 'huán']], '满意还', 'T', problems, diffs)
        self.assertEqual(problems, [])
        self.assertEqual(len(diffs), 1)


class WordsTest(unittest.TestCase):
    def test_join_words(self):
        self.assertEqual(join_words([['我', 'wǒ'], ['。', '']]), '我。')

    def test_words_to_pinyin_builds_sentence(self):
        words = [['我', 'wǒ'], ['对', 'duì'], ['这儿', 'zhèr'], ['很', 'hěn'], ['满意', 'mǎnyì'], ['。', '']]
        self.assertEqual(words_to_pinyin(words), 'Wǒ duì zhèr hěn mǎnyì.')


if __name__ == '__main__':
    unittest.main()
