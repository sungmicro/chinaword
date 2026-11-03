import copy
import json
import re
import unittest
from pathlib import Path

from script_fixes import FIXES_PATH, apply_script_fixes, joined, load_script_fixes

HANZI = re.compile(r'[一-鿿]')


def make_test():
    return {
        'id': 'H39999',
        'items': [
            {'no': 6, 'choices': {'type': 'picture'}, 'script': [
                {'speaker': None, 'words': [['别', 'bié'], ['喝', 'hē'], ['。', '']], 'ko': '마시지 마.'},
                {'speaker': None, 'words': [['太', 'tài'], ['可乐', 'kělè'], ['。', '']], 'ko': '너무 멋지다.'},
            ], 'vocab': [{'hanzi': '可乐', 'pinyin': 'kělè', 'partOfSpeech': '명사', 'meaningKo': '콜라'}], 'grammar': []},
            {'no': 11, 'choices': {'type': 'truefalse', 'statement': {'words': [['他', 'tā'], ['去', 'qù']], 'ko': '그가 간다'}},
             'script': [{'speaker': None, 'words': [['好', 'hǎo']], 'ko': '좋다'},
                        {'speaker': '★', 'words': [['他', 'tā'], ['去', 'qù']], 'ko': '그가 간다'}],
             'vocab': [], 'grammar': []},
        ],
    }


FIX = {
    'H39999/6': {
        'reason': '시험',
        'script': {'2': {'from': '太可乐。', 'words': [['太', 'tài'], ['渴', 'kě'], ['了', 'le'], ['。', '']], 'ko': '너무 목말라.'}},
        'vocab': [{'hanzi': '渴', 'pinyin': 'kě', 'partOfSpeech': '형용사', 'meaningKo': '목마르다'}],
    },
    'H39999/11': {
        'reason': '시험',
        'statement': {'from': '他去', 'words': [['她', 'tā'], ['去', 'qù']], 'ko': '그녀가 간다'},
    },
}


class ScriptFixesTest(unittest.TestCase):
    def test_replaces_line_vocab_and_statement_and_is_idempotent(self):
        test, problems = make_test(), []
        self.assertEqual(sorted(apply_script_fixes(test, problems, FIX)), [6, 11])
        self.assertEqual(problems, [])
        item = test['items'][0]
        self.assertEqual(joined(item['script'][1]['words']), '太渴了。')
        self.assertEqual(item['script'][1]['ko'], '너무 목말라.')
        self.assertEqual(joined(item['script'][0]['words']), '别喝。')  # 다른 줄은 그대로
        self.assertEqual([w['hanzi'] for w in item['vocab']], ['渴'])
        star = test['items'][1]
        self.assertEqual(joined(star['choices']['statement']['words']), '她去')
        self.assertEqual(joined(star['script'][-1]['words']), '她去')  # ★ 줄도 함께
        once = copy.deepcopy(test)
        apply_script_fixes(test, problems, FIX)  # 다시 적용해도 같다
        self.assertEqual(test, once)
        self.assertEqual(problems, [])

    def test_refuses_when_source_line_changed(self):
        test, problems = make_test(), []
        test['items'][0]['script'][1]['words'] = [['太', 'tài'], ['热', 'rè'], ['。', '']]
        apply_script_fixes(test, problems, FIX)
        self.assertTrue(any('from도 고친 문장도 없음' in p for p in problems))
        self.assertEqual(joined(test['items'][0]['script'][1]['words']), '太热。')

    def test_deletes_non_script_line_and_finds_lines_by_text(self):
        fix = {'H39999/6': {**FIX['H39999/6'], 'delete': {'1': '别喝。'}}}
        test, problems = make_test(), []
        apply_script_fixes(test, problems, fix)
        apply_script_fixes(test, problems, fix)  # 두 번째: 지운 줄은 없고, 고친 줄은 고친 문장으로 찾는다
        self.assertEqual(problems, [])
        self.assertEqual([joined(l['words']) for l in test['items'][0]['script']], ['太渴了。'])

    def test_refuses_missing_pinyin_or_ko(self):
        fix = {'H39999/6': {'reason': '시험', 'script': {'2': {'from': '太可乐。', 'words': [['太', ''], ['。', '']], 'ko': ''}}}}
        test, problems = make_test(), []
        apply_script_fixes(test, problems, fix)
        self.assertTrue(any('병음 없음' in p for p in problems))
        self.assertTrue(any('해석(ko) 없음' in p for p in problems))

    def test_fix_file_is_well_formed(self):
        """보정 파일: 근거가 있고, 줄마다 from·ko가 있고, 한자 토큰은 병음이 있다."""
        table = load_script_fixes(FIXES_PATH)
        for key, fix in table.items():
            self.assertRegex(key, r'^H\d{5}/\d+$')
            self.assertTrue(fix.get('reason'), key)
            for line in list(fix.get('script', {}).values()) + ([fix['statement']] if 'statement' in fix else []):
                self.assertTrue(line['from'] and line['ko'], key)
                self.assertNotEqual(line['from'], joined(line['words']), key)
                for token, pinyin in line['words']:
                    if HANZI.search(token):
                        self.assertTrue(pinyin, (key, token))
                    elif not re.search(r'\d', token):
                        self.assertEqual(pinyin, '', (key, token))
            for word in fix.get('vocab', []):
                self.assertTrue(word['pinyin'] and re.search('[가-힣]', word['meaningKo']), (key, word))
        json.loads(Path(FIXES_PATH).read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
