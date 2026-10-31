import json
from pathlib import Path
import unittest
from generate import EXAMS, pages, parse_exam, validate
from grammar import merge_grammar

ROOT = Path(__file__).resolve().parents[2]
class WritingTests(unittest.TestCase):
    def test_dataset_and_official_alternatives(self):
        items = json.loads((ROOT / 'public/writing/hsk3-all.json').read_text())['items']
        validate(items)
        self.assertEqual(len(EXAMS), 19)
        self.assertEqual(sum(x['kind'] == 'hanzi' for x in items), 95)

    def test_originals_reproduce_dataset_and_page_bounds(self):
        source = Path.home() / 'hsk-listening-work/src'
        if not source.exists(): self.skipTest('원본 PDF가 없는 환경')
        overrides = json.loads((Path(__file__).parent / 'overrides.json').read_text())
        actual = []
        for exam in EXAMS:
            pdf = source / f'{exam}.pdf'
            result = parse_exam(exam, pdf, overrides.get(exam))
            page_count = len(pages(pdf)) - 1
            for x in result:
                self.assertLessEqual(x['source']['page'], page_count)
                if exam != 'H31007': self.assertLessEqual(x['source']['answerPage'], page_count)
            actual.extend(result)
        for seq, x in enumerate(actual, 1): x['seq'] = seq
        self.assertEqual(merge_grammar(actual), json.loads((ROOT / 'public/writing/hsk3-all.json').read_text())['items'])

if __name__ == '__main__': unittest.main()
