import copy
import json
from pathlib import Path
import unittest
from study import load, merge_study, validate_study

ROOT = Path(__file__).resolve().parents[2]


class StudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = json.loads((ROOT / 'public/writing/hsk3-all.json').read_text())['items']

    def test_complete_study_and_unchanged_items(self):
        study = load()
        validate_study(self.items, study)
        self.assertEqual(len(study), 95)
        self.assertEqual(sum(len(entry['answers']) for entry in study.values()), 98)
        clean = [{key: value for key, value in item.items() if key != 'study'} for item in self.items]
        original = copy.deepcopy(clean)
        self.assertEqual(merge_study(clean), self.items)
        self.assertEqual(clean, original)
        self.assertTrue(all('study' not in item for item in self.items if item['kind'] == 'hanzi'))

    def test_reject_incomplete_or_incorrect_study(self):
        sample = [{'id': 'sample', 'kind': 'reorder', 'answers': ['我有2本书。', '2本书我有。']}]
        entry = {'answers': [
            {'answerIndex': 0, 'words': [['我', 'wǒ'], ['有', 'yǒu'], ['2', 'liǎng'], ['本', 'běn'], ['书', 'shū'], ['。', '']], 'ko': '나는 책 두 권이 있다.'},
            {'answerIndex': 1, 'words': [['2', 'liǎng'], ['本', 'běn'], ['书', 'shū'], ['我', 'wǒ'], ['有', 'yǒu'], ['。', '']], 'ko': '책 두 권을 나는 가지고 있다.'}],
            'vocab': [{'hanzi': '书', 'pinyin': 'shū', 'meaningKo': '책', 'partOfSpeech': '명사'}]}
        validate_study(sample, {'sample': entry})
        changes = [
            lambda e: e['answers'].pop(),
            lambda e: e['answers'][1].update(answerIndex=0),
            lambda e: e['answers'][0].update(ko=''),
            lambda e: e['answers'][0]['words'][0].__setitem__(1, ''),
            lambda e: e['answers'][0]['words'][2].__setitem__(1, ''),
            lambda e: e['answers'][0]['words'].pop(),
            lambda e: e.update(vocab=[]),
            lambda e: e['vocab'].append(copy.deepcopy(e['vocab'][0])),
            lambda e: e['vocab'][0].update(hanzi='朋友'),
            lambda e: e['vocab'][0].update(partOfSpeech=''),
        ]
        for change in changes:
            bad = copy.deepcopy(entry)
            change(bad)
            with self.subTest(change=change):
                with self.assertRaises(AssertionError): validate_study(sample, {'sample': bad})
        with self.assertRaises(AssertionError): validate_study(sample, {})


if __name__ == '__main__': unittest.main()
