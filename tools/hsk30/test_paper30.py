"""paper30.py 단위 테스트 + (원본이 있으면) 실제 샘플 PDF 검사.

  ~/venv-store/hsk-listening/bin/python -m unittest discover -s tools/hsk30
실제 PDF 검사는 HSK30_SRC(기본 ~/hsk30-work/src)에 S30-3.pdf 등이 있을 때만 돈다.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper30  # noqa: E402

SRC = Path(os.environ.get('HSK30_SRC', str(Path.home() / 'hsk30-work' / 'src')))


class ParseTest(unittest.TestCase):
    def test_chunks_split_on_two_spaces(self):
        self.assertEqual(paper30.chunks('  A 翻译准确              B 每部 300 元'), ['A 翻译准确', 'B 每部 300 元'])

    def test_bank_part_match_with_example(self):
        lines = [
            '第 31～35 题',
            'A 那我们还是买别的衣服吧。',
            'E 当然。我们先坐公交车，然后换地铁。',
            '例如：你知道怎么去国家图书馆吗？              （ E   ）',
            '31．这条裙子很漂亮，但是我有一条几乎一样的。       （     ）',
        ]
        groups, items = paper30.parse_bank_part(lines, 1, 'match', {31: 'A'})
        self.assertEqual(groups[0]['example'], 'E')
        self.assertEqual([o['label'] for o in groups[0]['options']], ['A', 'E'])
        self.assertEqual(items[0]['lines'][0]['text'], '这条裙子很漂亮，但是我有一条几乎一样的。')
        self.assertEqual(items[0]['answer'], 'A')

    def test_bank_part_wordbank_dialogue(self):
        lines = [
            '第 38～42 题：选词填空。请注意：其中一个选项为干扰项，需排除。',
            '  A 自信   B 心情   C 修理     D 到底    E 可惜   F 倒',
            '38．A：冰箱里还有我上午做的葡萄汁，给你（           ）一杯？',
            '  B：不用了，我肚子有点儿难受，喝不了凉的。',
        ]
        groups, items = paper30.parse_bank_part(lines, 1, 'wordbank', {38: 'F'})
        self.assertTrue(groups[0]['distractor'])
        self.assertEqual(len(groups[0]['options']), 6)
        self.assertEqual([l['speaker'] for l in items[0]['lines']], ['A', 'B'])
        self.assertIn('（）一杯', items[0]['lines'][0]['text'])

    def test_passage_group_shares_text(self):
        lines = [
            '57～58．',
            '  兴趣是最好的老师。如果对一件事情很感兴趣，',
            '也更容易坚持。',
            '   ★ 根据这段话，感兴趣的事情：',
            '     A 不难坚持      B 可能变化         C 必须是有用的',
            '   ★ 为了提高拍照水平，他：',
            '     A 去大学上课     B 常出门拍照        C 买不同的相机',
        ]
        items = paper30.parse_passage_part(lines, 3, {57: 'A', 58: 'B'})
        self.assertEqual([i['no'] for i in items], [57, 58])
        self.assertEqual({i['passageGroup'] for i in items}, {'57-58'})
        self.assertEqual(items[0]['lines'], items[1]['lines'])
        self.assertEqual(items[1]['options'][1]['text'], '常出门拍照')

    def test_cloze_keeps_numbered_blanks(self):
        lines = [
            '58～60．',
            '  一位作家花了四个月的时间，（58）                    ，去了 41 个城市的 56 家',
            '动物园。（59）    ，好。（60）  。',
            '  A 他说自己从小就很喜欢动物园',
            '  B 尊重生命',
            '  C 走遍了中国几乎所有的省',
        ]
        groups, items = paper30.parse_cloze_part(lines, 3, {58: 'C', 59: 'A', 60: 'B'})
        self.assertIn('时间，（58），去了41个城市的56家动物园。', groups[0]['text'])
        self.assertEqual(len(groups[0]['options']), 3)
        self.assertEqual([i['group'] for i in items], ['58-60'] * 3)

    def test_bottom_block_drops_tail_of_picture_above(self):
        rows = [2, 3] + list(range(30, 50))
        self.assertEqual(paper30.bottom_block(rows, 12), list(range(30, 50)))
        self.assertEqual(paper30.bottom_block([5, 10, 15], 12), [5, 10, 15])

    def test_read_pgm(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'x.pgm'
            path.write_bytes(b'P5 4 3 255\n' + bytes(range(12)))
            self.assertEqual(paper30.read_pgm(path), (4, 3, bytes(range(12))))


@unittest.skipUnless((SRC / 'S30-3.pdf').exists() and (SRC / 'S30-4.pdf').exists(), '샘플 PDF 없음')
class RealPaperTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.papers = {}
        for level in (3, 4):
            pdf = SRC / f'S30-{level}.pdf'
            cls.papers[level] = (paper30.build_paper(f'S30-{level}', level, pdf, SRC / f'S30-{level}-answers.pdf',
                                                     Path(cls.tmp.name)),
                                 subprocess.run(['pdftotext', '-layout', str(pdf), '-'], capture_output=True,
                                                text=True, check=True).stdout)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_counts_and_checks(self):
        for level, (paper, text) in self.papers.items():
            with self.subTest(level=level):
                self.assertEqual(paper30.check_paper(paper, text), [])
                counts = {k: len(paper[k]['items']) for k in ('listening', 'reading', 'writing')}
                self.assertEqual(counts, paper30.COUNTS[level])

    def test_answer_keys(self):
        p3, p4 = self.papers[3][0], self.papers[4][0]
        self.assertEqual(''.join(i['answer'] for i in p3['listening']['items']), 'BCAEFBAECDBABCABBCBACCAACCAACB')
        self.assertEqual(''.join(i['answer'] for i in p3['reading']['items']), 'AFBCDEACDBDBCAFFAEBCCBBCACABBA')
        self.assertEqual(''.join(i['answer'] for i in p4['listening']['items']), 'ABBDCCACDACACACBAADACDAAACBABBDB')
        self.assertEqual(''.join(i['answer'] for i in p4['reading']['items']), 'BCADEFDAEBCDCBDCCAABDBDDBCABBADC')

    def test_groups(self):
        p3, p4 = self.papers[3][0], self.papers[4][0]
        self.assertEqual({i['passageGroup'] for i in p3['reading']['items'] if i.get('passageGroup')}, {'57-58', '59-60'})
        self.assertEqual({i['passageGroup'] for i in p4['reading']['items'] if i.get('passageGroup')},
                         {'51-52', '53-54', '55-57'})
        self.assertEqual([g['id'] for g in p4['reading']['cloze']], ['58-60', '61-64'])
        self.assertEqual([i['no'] for i in p3['listening']['items'] if i['group']], [29, 30])

    def test_writing(self):
        p3, p4 = self.papers[3][0], self.papers[4][0]
        hanzi = [(i['pinyin'], i['answers'][0]) for i in p3['writing']['items'] if i['kind'] == 'hanzi']
        self.assertEqual(hanzi, [('fāng', '方'), ('gāi', '该'), ('máo', '毛'), ('chéng', '成'), ('fǎ', '法')])
        self.assertEqual([i['word'] for i in p3['writing']['items'] if i['kind'] == 'picture'],
                         ['羽毛球', '饱', '爬', '结婚', '地图'])
        self.assertEqual([i['word'] for i in p4['writing']['items'] if i['kind'] == 'picture'],
                         ['结账', '幅', '文件', '活泼', '正式'])
        essay = p4['writing']['items'][-1]
        self.assertEqual((essay['no'], essay['kind'], essay['minChars']), (70, 'essay', 80))
        for i in p3['writing']['items'] + p4['writing']['items']:
            if i['kind'] == 'picture':
                self.assertTrue((Path(self.tmp.name) / i['image']).stat().st_size > 3000)


if __name__ == '__main__':
    unittest.main()
