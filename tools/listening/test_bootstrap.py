import unittest

from bootstrap import clean_text, repeated_pairs
from refine import refine_item


class BootstrapTest(unittest.TestCase):
    def test_clean_text_removes_item_number_and_known_whisper_tail(self):
        self.assertEqual(
            clean_text('15。不要走。谢谢大家收看 下次见。'),
            '不要走',
        )

    def test_repeated_pairs_accepts_matching_adjacent_segments(self):
        segments = [
            {'start': 0.0, 'end': 2.0, 'text': '今天天气很好。'},
            {'start': 2.2, 'end': 4.2, 'text': '今天天气很好。'},
        ]
        pairs = repeated_pairs(segments)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]['text'], '今天天气很好。')

    def test_refine_part_two_keeps_printed_statement_out_of_script(self):
        item = {'part': 2, 'lines': []}
        refine_item(item, '15。先听前面的内容。纸上的判断句。')
        self.assertEqual(item['lines'], [{'speaker': None, 'text': '先听前面的内容。'}])


if __name__ == '__main__':
    unittest.main()
