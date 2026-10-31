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

    def test_complete_learning_and_role_definitions(self):
        from grammar import load_glossary
        glossary = load_glossary()
        self.assertEqual(len(glossary['roleTerms']), 16)
        self.assertEqual(sum('learning' in a for g in self.grammar.values() for a in g['analyses']), 98)
        self.assertEqual(glossary['terms']['preposition']['category'], '품사')
        self.assertEqual(glossary['terms']['subject']['category'], '문장 성분')

    def test_reject_learning_mismatches(self):
        for mutation in ('term', 'usage', 'range', 'surface', 'explanation'):
            data = copy.deepcopy(self.grammar)
            a = data['H31001-71']['analyses'][0]
            if mutation == 'term': a['learning']['termIds'] = ['invalid']
            if mutation == 'usage': a['learning']['points'][0]['usageId'] = 'invalid'
            if mutation == 'range': a['learning']['points'][0]['parts'][0]['end'] = 999
            if mutation == 'surface': a['learning']['points'][0]['parts'] = [{'token': 0, 'start': 0, 'end': 2}]
            if mutation == 'explanation': a['learning']['points'][0]['explanation'] = ''
            with self.subTest(mutation=mutation), self.assertRaises(AssertionError): validate_grammar(self.items, data)
