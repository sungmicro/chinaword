"""assemble30.py 단위 테스트 + 저장소의 공개 데이터 검사.

  ~/venv-store/hsk-listening/bin/python -m unittest discover -s tools/hsk30
작업 폴더(HSK30_WORK, 기본 ~/hsk30-work)가 있으면 조립 결과가 저장소 파일과 같은지도 본다(없으면 건너뜀).
"""
import copy
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import assemble30 as a  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
WORK = Path(os.environ.get('HSK30_WORK', str(Path.home() / 'hsk30-work')))


def errors_of(func, *args, **kwargs):
    report = a.Report()
    func(*args, report=report, **kwargs)
    return report.errors


VOCAB = {'hanzi': '学校', 'pinyin': 'xuéxiào', 'partOfSpeech': '명사', 'meaningKo': '학교'}


class WordsTest(unittest.TestCase):
    def test_pass(self):
        self.assertEqual(errors_of(a.check_words, [['你', 'nǐ'], ['好', 'hǎo'], ['！', '']], 'x', source='你好！'), [])

    def test_missing_pinyin(self):
        self.assertTrue(errors_of(a.check_words, [['你', ''], ['！', '']], 'x'))

    def test_digit_needs_pinyin(self):
        self.assertTrue(errors_of(a.check_words, [['41', '']], 'x'))
        self.assertEqual(errors_of(a.check_words, [['41', 'sìshíyī']], 'x'), [])

    def test_concat_must_equal_source(self):
        self.assertTrue(errors_of(a.check_words, [['你', 'nǐ'], ['好', 'hǎo']], 'x', source='你们好'))

    def test_slot_only_where_allowed(self):
        words = [['（58）', '', 'slot:58']]
        self.assertTrue(errors_of(a.check_words, words, 'x'))
        self.assertEqual(errors_of(a.check_words, words, 'x', allow_slot=True), [])

    def test_celsius_sign_has_reading(self):
        self.assertEqual(errors_of(a.check_words, [['20', 'èrshí'], ['℃', 'shèshìdù']], 'x'), [])


class VocabTest(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(errors_of(a.check_vocab, [VOCAB], 'x'), [])

    def test_meaning_needs_hangul(self):
        self.assertTrue(errors_of(a.check_vocab, [{**VOCAB, 'meaningKo': 'school'}], 'x'))

    def test_pos_not_word(self):
        self.assertTrue(errors_of(a.check_vocab, [{**VOCAB, 'partOfSpeech': '단어'}], 'x'))

    def test_empty_field_and_limit(self):
        self.assertTrue(errors_of(a.check_vocab, [{**VOCAB, 'pinyin': ''}], 'x'))
        self.assertTrue(errors_of(a.check_vocab, [VOCAB] * 9, 'x'))
        self.assertTrue(errors_of(a.check_vocab, [], 'x'))

    def test_grammar_range(self):
        g = {'pattern': '一直 + 동사', 'note': '계속됨을 나타낸다.'}
        self.assertEqual(errors_of(a.check_grammar, [g], 'x'), [])
        self.assertTrue(errors_of(a.check_grammar, [g] * 4, 'x'))
        self.assertTrue(errors_of(a.check_grammar, [], 'x'))


class WritingTest(unittest.TestCase):
    def hanzi(self, **over):
        item = {'id': 'S30-3-61', 'exam': 'S30-3', 'no': 61, 'part': 1, 'kind': 'hanzi', 'sentence': '我们去___吧。',
                'pinyin': 'fāng', 'answers': ['方'],
                'explain': {'words': [['我们', 'wǒmen'], ['去', 'qù'], ['方', 'fāng'], ['吧', 'ba'], ['。', '']],
                            'ko': '우리 가자.', 'vocab': [VOCAB]}}
        item.update(over)
        return item

    def run_check(self, item):
        report = a.Report()
        a.check_writing('S30-3', {'items': [item] * 10}, REPO / 'public' / 'hsk30', report)
        return [e for e in report.errors if '문항 수' not in e]

    def test_hanzi_ok(self):
        self.assertEqual(self.run_check(self.hanzi()), [])

    def test_hanzi_needs_single_blank(self):
        self.assertTrue(self.run_check(self.hanzi(sentence='我们去______吧。')))
        self.assertTrue(self.run_check(self.hanzi(sentence='我们___去___吧。')))

    def test_explain_sentence_matches(self):
        bad = self.hanzi()
        bad['explain']['words'][0] = ['你们', 'nǐmen']
        self.assertTrue(self.run_check(bad))


class ReadingClozeTest(unittest.TestCase):
    def test_group_nos(self):
        self.assertEqual(a.group_nos('58-60'), [58, 59, 60])
        self.assertEqual(a.group_nos('7'), [7])

    def test_index_contract(self):
        index = a.build_index()
        self.assertEqual([e['id'] for e in index], ['S30-3', 'S30-4'])
        self.assertEqual(index[0]['listening'], {'file': 'S30-3-listening.json', 'count': 30})
        self.assertEqual(index[1]['writing'], {'file': 'S30-4-writing.json', 'count': 6})
        self.assertEqual([e['level'] for e in index], [3, 4])


class CommittedDataTest(unittest.TestCase):
    """저장소에 있는 공개 데이터만으로 통과해야 한다(작업 폴더 없이)."""

    def test_committed_data_passes(self):
        report = a.check_all(REPO)
        self.assertEqual(report.errors, [])

    def load(self, name):
        return json.loads((REPO / 'public' / 'hsk30' / name).read_text(encoding='utf-8'))

    def test_counts_and_answers(self):
        for sid, want in (('S30-3', (30, 30, 10)), ('S30-4', (32, 32, 6))):
            got = tuple(len(self.load(f'{sid}-{area}.json')['items']) for area in a.AREAS)
            self.assertEqual(got, want)

    def test_breaking_data_is_caught(self):
        data = self.load('S30-3-listening.json')
        data['items'][1]['script'][0]['words'][0][1] = ''
        data['items'][2]['vocab'][0]['meaningKo'] = 'x'
        data['audio'] = 'missing.mp3'
        report = a.Report()
        a.check_listening('S30-3', data, REPO / 'public' / 'hsk30', report)
        text = '\n'.join(report.errors)
        self.assertIn('병음 없음', text)
        self.assertIn('한글이 없음', text)
        self.assertIn('음원', text)

    def test_cloze_item_has_all_slots(self):
        data = self.load('S30-4-reading.json')
        by_no = {i['no']: i for i in data['items']}
        for no in (58, 61):
            slots = {w[2] for line in by_no[no]['lines'] for w in line['words'] if len(w) == 3}
            self.assertEqual(slots, {f'slot:{n}' for n in a.group_nos(by_no[no]['group'])})

    def test_missing_slot_is_caught(self):
        data = self.load('S30-4-reading.json')
        for item in data['items']:
            if item['no'] == 59:
                item['lines'][0]['words'] = [w for w in item['lines'][0]['words'] if len(w) != 3]
        report = a.Report()
        a.check_reading('S30-4', data, report)
        self.assertTrue(any('빈칸 토큰' in e for e in report.errors))

    def test_every_reading_item_has_explain(self):
        for sid in a.TESTS:
            for item in self.load(f'{sid}-reading.json')['items']:
                ex = item['explain']
                self.assertTrue(ex['basis']['quote'] and ex['basis']['note'])
                self.assertTrue(ex['vocab'] and ex['grammar'])

    def test_missing_image_is_caught(self):
        data = self.load('S30-3-writing.json')
        data['items'][6]['image'] = 'nope.jpg'
        report = a.Report()
        a.check_writing('S30-3', data, REPO / 'public' / 'hsk30', report)
        self.assertTrue(any('사진' in e for e in report.errors))


@unittest.skipUnless((WORK / 'S30-3' / 'paper.json').exists(), '작업 폴더(~/hsk30-work)가 없음')
class AssembleFromWorkTest(unittest.TestCase):
    def test_assembled_equals_committed_and_writes_only_its_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / 'public' / 'hsk30').mkdir(parents=True)
            (repo / 'src' / 'data').mkdir(parents=True)
            for asset in (REPO / 'public' / 'hsk30').iterdir():
                if asset.suffix in ('.jpg', '.mp3'):
                    (repo / 'public' / 'hsk30' / asset.name).symlink_to(asset)
            report = a.run_assemble(repo, WORK)
            self.assertEqual(report.errors, [])
            written = sorted(p.relative_to(repo).as_posix() for p in repo.rglob('*') if p.is_file() and not p.is_symlink())
            expected = sorted([f'public/hsk30/{sid}-{area}.json' for sid in a.TESTS for area in a.AREAS] + ['src/data/hsk30-index.json'])
            self.assertEqual(written, expected)
            for name in expected:
                self.assertEqual((repo / name).read_text(encoding='utf-8'), (REPO / name).read_text(encoding='utf-8'), name)

    def test_failed_check_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / 'public' / 'hsk30').mkdir(parents=True)  # 이미지·음원이 없어 검사가 실패한다
            report = a.run_assemble(repo, WORK)
            self.assertTrue(report.errors)
            self.assertEqual([p for p in repo.rglob('*') if p.is_file()], [])


if __name__ == '__main__':
    unittest.main()
