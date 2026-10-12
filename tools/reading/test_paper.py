import unittest
from pathlib import Path

from paper import check_paper, parse_answers, parse_reading, raw_lines, reading_section

PDF_DIR = Path.home() / 'hsk-listening-work' / 'src'
TEST_IDS = ['H31001', 'H31002', 'H31003', 'H31004', 'H31005']
H31001_ANSWERS = dict(zip(range(41, 71), 'CBADFBDEACFDCBAABEFCAACBBAABBC'))

FIXTURE = '''第 一 部 分
第 41-45 题
A 太好了！需要我帮忙吗？
B 今天把我饿坏了，还有什么吃的吗？
例如：你知道怎么去那儿吗？ （ B ）
41．我的作业早就完成了。 （ ）
第 二 部 分
第 56-60 题
A 刻 B 一直 C 节 D 爱好 E 被 F 打扫
例如：A：你有什么（ D ）？
B：我喜欢体育。
56．A：请问，现在是十一点吗？
B：现在十一点十五了，您的表慢了一（ ） 。
第 三 部 分
第 61-70 题
例如：您是来参加今天会议的吗？您来早了一点儿，现在才八点半。您先进来
坐吧。
★ 会议最可能几点开始？
A 8 点 B 8 点半 C 9 点 √
63．我对这儿很满意，虽然没有花园，但是离河边很近，
还有鸟。
★ 使他觉得满意的是：
A 没有花园 B 房间很大 C 离河很近'''.splitlines()


class ParseReadingFixtureTest(unittest.TestCase):
    def setUp(self):
        paper = parse_reading(FIXTURE)
        self.items = {item['no']: item for item in paper['items']}
        self.groups = {group['id']: group for group in paper['groups']}

    def test_only_items_are_collected(self):
        self.assertEqual(sorted(self.items), [41, 56, 63])
        self.assertEqual(sorted(self.groups), ['41-45', '56-60'])

    def test_part1_group_options_and_example(self):
        group = self.groups['41-45']
        self.assertEqual([o['label'] for o in group['options']], ['A', 'B'])
        self.assertEqual(group['options'][1]['text'], '今天把我饿坏了，还有什么吃的吗？')
        self.assertEqual(group['example'], 'B')

    def test_part1_item_drops_answer_brackets(self):
        self.assertEqual(self.items[41]['lines'], [{'speaker': None, 'text': '我的作业早就完成了。'}])
        self.assertEqual(self.items[41]['group'], '41-45')

    def test_part2_word_bank_and_dialogue_blank(self):
        group = self.groups['56-60']
        self.assertEqual([o['text'] for o in group['options']], ['刻', '一直', '节', '爱好', '被', '打扫'])
        self.assertEqual(group['example'], 'D')
        self.assertEqual(self.items[56]['lines'], [
            {'speaker': 'A', 'text': '请问，现在是十一点吗？'},
            {'speaker': 'B', 'text': '现在十一点十五了，您的表慢了一（）。'},
        ])

    def test_part3_skips_example_and_joins_passage(self):
        item = self.items[63]
        self.assertEqual(item['lines'], [{'speaker': None, 'text': '我对这儿很满意，虽然没有花园，但是离河边很近，还有鸟。'}])
        self.assertEqual(item['question'], '使他觉得满意的是：')
        self.assertEqual([o['text'] for o in item['options']], ['没有花园', '房间很大', '离河很近'])
        self.assertIsNone(item['group'])


@unittest.skipUnless((PDF_DIR / 'H31001.pdf').exists(), '시험지 PDF 없음 (~/hsk-listening-work/src)')
class RealPaperTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.papers = {}
        for test_id in TEST_IDS:
            lines = raw_lines(PDF_DIR / f'{test_id}.pdf')
            paper = parse_reading(reading_section(lines))
            answers = parse_answers(lines)
            for item in paper['items']:
                item['answer'] = answers.get(item['no'])
            cls.papers[test_id] = paper

    def item(self, test_id, no):
        return next(item for item in self.papers[test_id]['items'] if item['no'] == no)

    def test_all_papers_pass_checks(self):
        for test_id, paper in self.papers.items():
            with self.subTest(test_id):
                self.assertEqual(check_paper(paper), [])

    def test_h31001_answers_match_answer_key(self):
        got = {item['no']: item['answer'] for item in self.papers['H31001']['items']}
        self.assertEqual(got, H31001_ANSWERS)

    def test_blank_bracket_on_its_own_line_h31004_55(self):
        self.assertEqual(self.item('H31004', 55)['lines'], [{'speaker': None, 'text': '（）更好地解决问题，必须提高自己的水平。'}])

    def test_blank_at_start_of_b_line_h31004_60(self):
        self.assertEqual(self.item('H31004', 60)['lines'][1], {'speaker': 'B', 'text': '（）我只想听听那些老歌。'})

    def test_passage_first_line_above_number_h31002_67(self):
        text = self.item('H31002', 67)['lines'][0]['text']
        self.assertTrue(text.startswith('“再见”是一个很有意思的词语。“再见”表示'), text)

    def test_quote_spacing_h31003_65(self):
        text = self.item('H31003', 65)['lines'][0]['text']
        self.assertTrue(text.startswith('“6月的天，孩子的脸，说变就变。”刚才还是大晴天'), text)


if __name__ == '__main__':
    unittest.main()
