import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mine_refresh import (INDEX_PATH, IndexProblems, build_index, check_mine_refresh, index_text, merged_moves,
                          write_mine_refresh)

REPO = Path(__file__).resolve().parents[1]


def card(hanzi, pinyin, meaning, lesson='HSK3 추가 300', item_type='단어', part='명사'):
    return {'id': f'T-{hanzi}', 'lesson': lesson, 'itemType': item_type, 'hanzi': hanzi, 'pinyin': pinyin,
            'meaningKo': meaning, 'partOfSpeech': part}


def word(hanzi, pinyin, meaning, part='명사'):
    return {'hanzi': hanzi, 'pinyin': pinyin, 'meaningKo': meaning, 'partOfSpeech': part}


FIXES = {
    'split': {'比较忙': ['比较', '忙'], '儿': [], '老李': ['老#호칭', '李']},
    'items': {'listening/H1/2': {'谢': ['谢#성씨'], '北': []}, 'listening/H1/3': {'可乐': []}},
}
MOVES = {'_about': '테스트', 'words': {'车辆': {'pinyin': 'chēliàng', 'partOfSpeech': '명사', 'meaningKo': '차량'},
                                    '角#자오': {'pinyin': 'jiǎo', 'partOfSpeech': '양사', 'meaningKo': '자오(돈 단위)'}},
         'split': {'很着急': ['着急']}, 'moved': {'listening/H1/3': {'可乐': ['渴']}}}


def make_repo(root, reading=None, listening=None, vocab=None):
    root = Path(root)
    (root / 'src' / 'data').mkdir(parents=True)
    (root / 'public' / 'reading').mkdir(parents=True)
    (root / 'public' / 'listening').mkdir(parents=True)
    (root / 'src' / 'data' / 'vocab.json').write_text(json.dumps(vocab or [
        card('比较', 'bǐjiào', '비교하다'), card('忙', 'máng', '바쁘다'), card('老', 'lǎo', '늙다'),
        card('渴', 'kě', '목마르다'), card('谢', 'xiè', '감사하다'), card('着急', 'zháojí', '조급해하다'),
        card('句子', 'jùzi', '문장', item_type='문장'),
    ], ensure_ascii=False), encoding='utf-8')
    (root / 'public' / 'reading' / 'H1.json').write_text(json.dumps({'id': 'H1', 'items': reading or [
        {'no': 52, 'explain': {'vocab': [word('比较', 'bǐjiào', '비교적', '부사'), word('忙', 'máng', '바쁘다'),
                                         word('李', 'lǐ', '리(李, 성씨)', '고유명사')]}},
    ]}, ensure_ascii=False), encoding='utf-8')
    (root / 'public' / 'listening' / 'H1.json').write_text(json.dumps({'id': 'H1', 'items': listening or [
        {'no': 2, 'vocab': [word('谢', 'xiè', '셰(谢, 성씨)', '고유명사'), word('老', 'lǎo', '라오(호칭)', '접두사')]},
        {'no': 3, 'vocab': [word('渴', 'kě', '목마르다', '형용사')]},
    ]}, ensure_ascii=False), encoding='utf-8')
    return root


class BuildIndexTest(unittest.TestCase):
    def test_committed_index_matches_current_data(self):
        self.assertTrue(check_mine_refresh(REPO), f'{INDEX_PATH}가 오래됐다 → tools/mine_refresh.py --repo .')

    def test_index_keeps_only_senses_that_differ_from_vocab_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = build_index(make_repo(tmp), FIXES, MOVES)
        senses = [tuple(sense) for sense in index['senses']]
        # vocab.json에 없는 李는 기본 뜻(base)으로, vocab.json과 뜻이 다른 문항 단어는 at으로
        self.assertEqual(senses[index['base']['李']], ('lǐ', '리(李, 성씨)', '고유명사'))
        self.assertEqual(senses[index['at']['reading/H1/52']['比较']], ('bǐjiào', '비교적', '부사'))
        self.assertNotIn('李', index['at'].get('reading/H1/52', {}))  # 기본 뜻과 같다
        self.assertNotIn('忙', index['at'].get('reading/H1/52', {}))  # vocab.json과 같다
        self.assertEqual(senses[index['at']['listening/H1/2']['谢']], ('xiè', '셰(谢, 성씨)', '고유명사'))
        self.assertEqual(index['split'], {'儿': [], '很着急': ['着急'], '老李': ['老', '李'], '比较忙': ['比较', '忙']})

    def test_mine_words_become_base_and_tagged_targets_only_apply_in_that_question(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(tmp, vocab=[card('比较', 'bǐjiào', '비교하다'), card('忙', 'máng', '바쁘다'), card('老', 'lǎo', '늙다'),
                                         card('渴', 'kě', '목마르다'), card('谢', 'xiè', '감사하다'), card('角', 'jiǎo', '모서리'),
                                         card('着急', 'zháojí', '조급해하다')])
            moves = {**MOVES, 'moved': {'listening/H1/3': {'可乐': ['渴'], '脚': ['角#자오']}}}
            index = build_index(repo, FIXES, moves)
        senses = [tuple(sense) for sense in index['senses']]
        self.assertEqual(senses[index['base']['车辆']], ('chēliàng', '차량', '명사'))
        self.assertEqual(senses[index['at']['listening/H1/3']['角']], ('jiǎo', '자오(돈 단위)', '양사'))
        self.assertEqual(index['moved']['listening/H1/3'], {'可乐': ['渴'], '脚': ['角']})
        self.assertNotIn('角', index['base'])

    def test_moves_merge_items_and_mine_moves(self):
        moved = merged_moves(FIXES, MOVES)
        # 같은 한자의 뜻만 바꾼 것(谢 → 谢#성씨)은 빼고, mine_moves가 items를 이긴다
        self.assertEqual(moved, {'listening/H1/2': {'北': []}, 'listening/H1/3': {'可乐': ['渴']}})

    def test_problems_stop_before_writing(self):
        cases = [
            ({**MOVES, 'moved': {'listening/H1/3': {'可乐': ['没有的词']}}}, FIXES, '뜻을 찾을 수 없음'),
            ({**MOVES, 'moved': {'listening/H1/3': {'渴': ['忙']}}}, FIXES, '해설에 아직 있음'),
            ({**MOVES, 'moved': {'listening/H9/9': {'可乐': []}}}, FIXES, '그런 문항이 없음'),
            ({**MOVES, 'moved': {'listening/H1/3': {'可乐': ['角#없는뜻']}}}, FIXES, 'words에 뜻이 없음'),
            ({**MOVES, 'words': {'忙': {'pinyin': 'máng', 'partOfSpeech': '형용사', 'meaningKo': '바쁘다'}}}, FIXES, '이미 있음'),
            ({**MOVES, 'split': {'比较忙': ['比较', '忙']}}, FIXES, 'vocab_fixes.json split에도'),
            (MOVES, {**FIXES, 'split': {**FIXES['split'], '忙了': ['忙'], '忙': ['忙']}}, '다시 split'),
            (MOVES, {**FIXES, 'split': {**FIXES['split'], '渴': []}}, '해설에 아직 있음'),
        ]
        for moves, fixes, message in cases:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(IndexProblems) as caught:
                    build_index(make_repo(tmp), fixes, moves)
                self.assertTrue(any(message in problem for problem in caught.exception.problems), caught.exception.problems)

    def test_meaning_without_hangul_is_a_problem(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(tmp, listening=[{'no': 2, 'vocab': [word('户照', 'hùzhào', '户照')]},
                                             {'no': 3, 'vocab': [word('渴', 'kě', '목마르다')]}])
            with self.assertRaises(IndexProblems) as caught:
                build_index(repo, FIXES, MOVES)
        self.assertTrue(any('한글' in problem for problem in caught.exception.problems))

    def test_write_is_stable_and_skips_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(tmp)
            import mine_refresh
            original = (mine_refresh.load_fixes, mine_refresh.MOVES_PATH)
            moves_path = Path(tmp) / 'moves.json'
            moves_path.write_text(json.dumps(MOVES, ensure_ascii=False), encoding='utf-8')
            mine_refresh.load_fixes, mine_refresh.MOVES_PATH = (lambda: FIXES), moves_path
            try:
                self.assertTrue(write_mine_refresh(repo))
                first = (repo / INDEX_PATH).read_text(encoding='utf-8')
                self.assertFalse(write_mine_refresh(repo))
                self.assertTrue(check_mine_refresh(repo))
            finally:
                mine_refresh.load_fixes, mine_refresh.MOVES_PATH = original
        self.assertEqual(json.loads(first), json.loads(index_text(json.loads(first))))



class FailurePropagationTest(unittest.TestCase):
    """색인을 못 쓰면 refresh_after_write가 False, 데이터를 쓰는 도구는 0이 아닌 코드로 끝난다."""

    def setUp(self):
        import mine_refresh
        import sentence_split
        self.mine_refresh, self.sentence_split = mine_refresh, sentence_split
        self.saved = (mine_refresh.write_mine_refresh, sentence_split.SPLITS_PATH)
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = make_repo(self.tmp.name)
        sentence_split.SPLITS_PATH = Path(self.tmp.name) / 'sentence_splits.json'

        def broken(repo):
            raise IndexProblems(['테스트: 색인 문제'])
        mine_refresh.write_mine_refresh = broken

    def tearDown(self):
        self.mine_refresh.write_mine_refresh, self.sentence_split.SPLITS_PATH = self.saved
        self.tmp.cleanup()

    def test_refresh_after_write_reports_failure(self):
        self.assertFalse(self.mine_refresh.refresh_after_write(self.repo))

    def test_apply_sentences_exits_non_zero_when_index_fails(self):
        import vocab_fixes
        self.assertEqual(vocab_fixes.main(['--repo', str(self.repo), '--apply-sentences']), 1)

    def test_tool_mains_return_the_refresh_result(self):
        # assemble·auto_enrich·generate는 작업 폴더가 필요해 직접 돌리지 않고, 결과를 그대로 돌려주는지 소스로 확인한다.
        tools = Path(__file__).resolve().parent
        for path, expected in [('listening/assemble.py', 'return 0 if refresh_after_write(repo) else 1'),
                               ('reading/assemble.py', 'return 0 if refresh_after_write(repo) else 1'),
                               ('auto_enrich.py', 'return 0 if all(results) else 1'),
                               ('writing/generate.py', 'raise SystemExit(1)')]:
            with self.subTest(path=path):
                self.assertIn(expected, (tools / path).read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
