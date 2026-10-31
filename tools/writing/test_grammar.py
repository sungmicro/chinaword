import copy
import json
from pathlib import Path
import unittest
from grammar import load, validate_grammar

class GrammarTests(unittest.TestCase):
    def setUp(self):
        self.items = json.loads((Path(__file__).resolve().parents[2] / 'public/writing/hsk3-all.json').read_text())['items']
        self.grammar = load()

    def test_complete_dataset(self):
        validate_grammar(self.items, self.grammar)
        self.assertEqual(len(self.grammar), 95)
        self.assertEqual(sum(len(x['analyses']) for x in self.grammar.values()), 98)
        for item in self.items:
            if item['kind'] == 'reorder': self.assertEqual(item['grammar'], self.grammar[item['id']])

    def test_reject_corrupt_ranges_orders_references_and_missing_answers(self):
        for mutation in ('overlap', 'missing', 'order', 'reference', 'answer', 'role'):
            data = copy.deepcopy(self.grammar)
            a = data['H31001-71']['analyses'][0]
            if mutation == 'overlap': a['groups'][0]['parts'].append(a['groups'][0]['parts'][0])
            if mutation == 'missing': a['groups'].pop()
            if mutation == 'order': a['tokenOrder'] = [0, 0, 1]
            if mutation == 'reference': a['steps'][0]['groups'] = [999]
            if mutation == 'answer': a['answerIndex'] = 1
            if mutation == 'role': a['groups'][0]['role'] = 'invalid'
            with self.subTest(mutation=mutation), self.assertRaises(AssertionError): validate_grammar(self.items, data)
