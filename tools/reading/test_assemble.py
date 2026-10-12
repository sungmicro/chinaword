import copy
import json
import tempfile
import unittest
from pathlib import Path

from assemble import LESSON, build_test, update_vocab


def ex(words, ko):
    return {'zh': ''.join(token for token, _ in words), 'words': words, 'ko': ko}


EXAMPLE = ex([['这', 'zhè'], ['把', 'bǎ'], ['椅子', 'yǐzi'], ['很', 'hěn'], ['舒服', 'shūfu'], ['。', '']], '이 의자는 아주 편하다.')
GRAMMAR = {'pattern': '很不 + 형용사', 'meaningKo': '아주 ~하지 않다', 'note': '很 뒤에 不를 붙여 정도를 부정한다.', 'example': EXAMPLE}


def word(hanzi, pinyin, pos, ko):
    return {'hanzi': hanzi, 'pinyin': pinyin, 'partOfSpeech': pos, 'meaningKo': ko, 'usage': f'{hanzi} 용법', 'example': EXAMPLE}


PAPER = {
    'id': 'T1',
    'groups': [{'id': '51-55', 'part': 2, 'example': 'E', 'options': [
        {'label': label, 'text': text} for label, text in zip('ABCDEF', ['其实', '感冒', '附近', '舒服', '声音', '把'])]}],
    'items': [
        {'no': 51, 'part': 2, 'group': '51-55', 'answer': 'D', 'question': None, 'options': None,
         'lines': [{'speaker': None, 'text': '坐着很不（）。'}]},
        {'no': 61, 'part': 3, 'group': None, 'answer': 'A', 'question': '他觉得怎么样？',
         'lines': [{'speaker': None, 'text': '我对这儿很满意。房间很大。'}],
         'options': [{'label': 'A', 'text': '满意'}, {'label': 'B', 'text': '不满意'}, {'label': 'C', 'text': '很累'}]},
    ],
}

ENRICH_51_60 = {
    'groups': [{'id': '51-55', 'options': [
        {'label': label, 'words': [[text, pinyin]], 'ko': ko}
        for label, text, pinyin, ko in [
            ('A', '其实', 'qíshí', '사실은'), ('B', '感冒', 'gǎnmào', '감기'), ('C', '附近', 'fùjìn', '근처'),
            ('D', '舒服', 'shūfu', '편안하다'), ('E', '声音', 'shēngyīn', '소리'), ('F', '把', 'bǎ', '~을')]]}],
    'items': [{
        'no': 51, 'question': None, 'options': None, 'pair': None,
        'lines': [{'words': [['坐着', 'zuòzhe'], ['很', 'hěn'], ['不', 'bù'], ['舒服', 'shūfu'], ['。', '']],
                   'ko': '앉아 있으면 아주 불편하다.', 'blank': 3}],
        'explain': {
            'basis': {'quote': '很不舒服', 'note': '很不 뒤에는 형용사가 온다.'},
            'distractors': [{'label': 'B', 'note': '感冒는 형용사가 아니다.'}],
            'breakdown': [{'chunks': [{'text': '坐着', 'role': '부사어'}, {'text': '很不舒服', 'role': '술어'}],
                           'note': '앉아 있는 상태 + 불편하다'}],
            'vocab': [word('舒服', 'shūfu', '형용사', '편안하다'), word('坐', 'zuò', '동사', '앉다'), word('低', 'dī', '형용사', '낮다')],
            'grammar': [GRAMMAR],
        },
    }],
}

ENRICH_61_70 = {
    'items': [{
        'no': 61, 'pair': None,
        'lines': [
            {'words': [['我', 'wǒ'], ['对', 'duì'], ['这儿', 'zhèr'], ['很', 'hěn'], ['满意', 'mǎnyì'], ['。', '']], 'ko': '나는 여기가 아주 마음에 든다.'},
            {'words': [['房间', 'fángjiān'], ['很', 'hěn'], ['大', 'dà'], ['。', '']], 'ko': '방이 크다.'},
        ],
        'question': {'words': [['他', 'tā'], ['觉得', 'juéde'], ['怎么样', 'zěnmeyàng'], ['？', '']], 'ko': '그는 어떻게 느끼는가?'},
        'options': [
            {'label': 'A', 'words': [['满意', 'mǎnyì']], 'ko': '만족한다'},
            {'label': 'B', 'words': [['不', 'bù'], ['满意', 'mǎnyì']], 'ko': '만족하지 않는다'},
            {'label': 'C', 'words': [['很', 'hěn'], ['累', 'lèi']], 'ko': '피곤하다'},
        ],
        'explain': {
            'basis': {'quote': '我对这儿很满意', 'note': '첫 문장이 바로 답이다.'},
            'distractors': [{'label': 'B', 'note': '반대 내용'}, {'label': 'C', 'note': '지문에 없음'}],
            'breakdown': [{'chunks': [{'text': '我', 'role': '주어'}, {'text': '对这儿', 'role': '부사어'}, {'text': '很满意', 'role': '술어'}],
                           'note': '对 + 대상 + 满意'}],
            'vocab': [word('满意', 'mǎnyì', '형용사', '만족하다'), word('房间', 'fángjiān', '명사', '방'), word('对', 'duì', '개사', '~에 대해')],
            'grammar': [GRAMMAR],
        },
    }],
}


class AssembleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.work = Path(self.tmp.name)
        self.write(PAPER, ENRICH_51_60, ENRICH_61_70)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, paper, enrich_51, enrich_61):
        base = self.work / 'T1'
        base.mkdir(exist_ok=True)
        (base / 'paper.json').write_text(json.dumps(paper, ensure_ascii=False), encoding='utf-8')
        (base / 'enrich-51-60.json').write_text(json.dumps(enrich_51, ensure_ascii=False), encoding='utf-8')
        (base / 'enrich-61-70.json').write_text(json.dumps(enrich_61, ensure_ascii=False), encoding='utf-8')

    def build(self):
        problems, diffs = [], []
        test = build_test('T1', self.work, problems, diffs)
        return test, problems

    def test_valid_files_merge_without_problems(self):
        test, problems = self.build()
        self.assertEqual(problems, [])
        self.assertEqual([item['no'] for item in test['items']], [51, 61])
        self.assertEqual(test['groups'][0]['example'], 'E')
        self.assertEqual(test['items'][0]['lines'][0]['blank'], 3)
        self.assertEqual(test['items'][1]['question']['ko'], '그는 어떻게 느끼는가?')
        self.assertEqual(test['parts'][1], {'part': 2, 'guide': '빈칸에 알맞은 단어 고르기'})

    def test_blank_word_must_be_the_answer_word(self):
        broken = copy.deepcopy(ENRICH_51_60)
        broken['items'][0]['lines'][0]['words'][3] = ['附近', 'fùjìn']
        self.write(PAPER, broken, ENRICH_61_70)
        _, problems = self.build()
        self.assertTrue(any('빈칸 단어' in p for p in problems), problems)

    def test_passage_sentences_must_join_to_source(self):
        broken = copy.deepcopy(ENRICH_61_70)
        broken['items'][0]['lines'].pop()
        self.write(PAPER, ENRICH_51_60, broken)
        _, problems = self.build()
        self.assertTrue(any('지문' in p and '원문과 다름' in p for p in problems), problems)

    def test_distractor_cannot_be_the_answer(self):
        broken = copy.deepcopy(ENRICH_61_70)
        broken['items'][0]['explain']['distractors'][0]['label'] = 'A'
        self.write(PAPER, ENRICH_51_60, broken)
        _, problems = self.build()
        self.assertTrue(any('오답 이유' in p for p in problems), problems)

    def test_breakdown_must_come_from_the_item(self):
        broken = copy.deepcopy(ENRICH_51_60)
        broken['items'][0]['explain']['breakdown'][0]['chunks'][0]['text'] = '站着'
        self.write(PAPER, broken, ENRICH_61_70)
        _, problems = self.build()
        self.assertTrue(any('끊어 읽기' in p for p in problems), problems)

    def test_vocab_needs_an_example(self):
        broken = copy.deepcopy(ENRICH_61_70)
        del broken['items'][0]['explain']['vocab'][0]['example']
        self.write(PAPER, ENRICH_51_60, broken)
        _, problems = self.build()
        self.assertTrue(any('예문' in p for p in problems), problems)

    def test_update_vocab_skips_known_words_and_is_idempotent(self):
        test, problems = self.build()
        self.assertEqual(problems, [])
        repo = self.work / 'repo'
        (repo / 'src' / 'data').mkdir(parents=True)
        vocab_path = repo / 'src' / 'data' / 'vocab.json'
        vocab_path.write_text(json.dumps([{'id': 'K1', 'lesson': 'HSK3 추가 300', 'hanzi': '舒服'}], ensure_ascii=False), encoding='utf-8')

        added = update_vocab([test], repo)
        first = vocab_path.read_text(encoding='utf-8')
        self.assertEqual(added, 5)
        entries = {entry['hanzi']: entry for entry in json.loads(first) if entry.get('lesson') == LESSON}
        self.assertEqual(sorted(entries), sorted(['坐', '低', '满意', '房间', '对']))
        self.assertEqual(entries['坐']['exampleZh'], '坐着很不舒服。')  # 시험 문장(빈칸 채움)
        self.assertEqual(entries['低']['exampleZh'], '这把椅子很舒服。')  # 시험 문장에 없으면 해설 예문
        self.assertEqual(entries['坐']['source'], 'HSK3 공식 모의고사 T1 독해 51번')

        update_vocab([test], repo)
        self.assertEqual(vocab_path.read_text(encoding='utf-8'), first)


if __name__ == '__main__':
    unittest.main()
