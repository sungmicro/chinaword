"""build_outline.py 테스트. 듣기 도구가 pypinyin을 쓰므로 ~/venv-store/hsk-listening/bin/python으로 돌린다."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_outline as b  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


class ToneKeyTest(unittest.TestCase):
    def test_table(self):
        # src/myVocab.test.js pinyinKey 표와 같은 기대값
        self.assertEqual('hao3', b.tone_key('hǎo', '好'))
        self.assertEqual('hao4', b.tone_key('hào', '好'))
        self.assertEqual('guo4', b.tone_key('guò', '过'))
        self.assertEqual('guo0', b.tone_key('guo', '过'))
        self.assertEqual('xuesheng2', b.tone_key('xuésheng', '学生'))
        self.assertEqual('xuesheng2', b.tone_key('xuéshēng', '学生'))
        self.assertEqual('lv4', b.tone_key('lǜ', '绿'))
        self.assertEqual('nver3', b.tone_key('nǚ’ér', '女儿'))
        self.assertEqual('yikuair1', b.tone_key('yíkuàir', '一块儿'))
        self.assertEqual('bukeqi4', b.tone_key('bú kèqi', '不客气'))
        self.assertEqual('bu4', b.tone_key('bú', '不'))
        self.assertEqual('shei2', b.tone_key('shéi/shuí', '谁'))
        self.assertNotEqual(b.tone_key('hái', '还'), b.tone_key('huán', '还'))


class PosGroupsTest(unittest.TestCase):
    def test_groups(self):
        self.assertEqual([('명사', 4), ('동사', 5)], b.pos_groups('名、（动）', '四级（五级）'))
        self.assertEqual([('형용사', 1), ('부사', 2), ('동사', 4)], b.pos_groups('形、（副）、（动）', '一级（二级）（四级）'))
        self.assertEqual([('동사', 2), ('명사', 4), ('양사', 4)], b.pos_groups('动、（名、量）', '二级（四级）'))
        self.assertEqual([], b.pos_groups('', '一级'))


class ConvertMeaningTest(unittest.TestCase):
    def flags(self, codex, pos):
        return b.convert_meaning(codex, pos)

    def test_conversion(self):
        self.assertEqual(('사랑하다, 좋아하다', []), self.flags('(동) 사랑하다, 좋아하다', ['동사']))
        self.assertEqual('좋아하다 / (명) 취미', self.flags('(동) 좋아하다; (명) 취미', ['동사', '명사'])[0])
        draft, flags = self.flags('(동·명) 보도하다; 보도', ['동사', '명사'])
        self.assertEqual('보도하다 / (명) 보도', draft)
        self.assertEqual([], flags)
        draft, flags = self.flags('(수·양) 조금', ['수량사'])
        self.assertEqual('조금', draft)
        self.assertEqual([], flags)
        _, flags = self.flags('(동·명) 느끼다; 느낌; 체험', ['동사', '명사'])
        self.assertTrue(any('배정 확인' in flag for flag in flags), flags)
        _, flags = self.flags('(동) 일어나다; (동사 뒤) ~하기 시작하다', ['동사'])
        self.assertTrue(any('괄호 안이 품사가 아님' in flag for flag in flags), flags)
        _, flags = self.flags('(동) ' + '가' * 41, ['동사'])
        self.assertTrue(any('40자 초과' in flag for flag in flags), flags)
        self.assertEqual('B / (명) A', self.flags('(명) A; (형) B', ['형용사', '명사'])[0])


class DocTest(unittest.TestCase):
    def test_parse_doc_and_hanja(self):
        text = ('| 爱 〔1〕 | ài | (동) 사랑하다 |\n'
                '| 爱护 〔5〕 | àihù | (동) 아끼다<br>愛 사랑 애 · 護 도울 호 |\n'
                '\n## 🤖 품사 보완\n\n- 你好 (id=147): 구 - 인사\n\n## 끝\n')
        rows, fills = b.parse_doc(text)
        self.assertEqual(2, len(rows))
        self.assertEqual('愛 사랑 애 · 護 도울 호', rows[1]['hanjaLine'])
        self.assertEqual({'147': {'head': '你好', 'pos': '구'}}, fills)
        self.assertEqual('', b.hanja_ko('啊 —'))
        self.assertEqual('不 아닐 불 · 够 —', b.hanja_ko('不 아닐 불 · 够 —'))


class MergedItemsTest(unittest.TestCase):
    def test_same_level_homographs_merge(self):
        def item(api_id, head, level):
            return {'apiId': api_id, 'head': head, 'hanzi': '花', 'pinyin': 'huā', 'level': level,
                    'pos': [('동사', level)], 'codexKo': f'(동) 뜻{api_id}', 'hanjaKo': ''}
        raw = {'items': [item('1', '花1', 2), item('2', '花2', 2), item('3', '花', 4)]}
        merged = b.merged_items(raw)
        self.assertEqual(2, len(merged))
        self.assertEqual(['1', '2'], merged[0]['officialIds'])
        self.assertEqual('花1+花2', merged[0]['head'])
        self.assertEqual(['3'], merged[1]['officialIds'])


class ExampleFromTest(unittest.TestCase):
    def test_source(self):
        self.assertEqual('H31001 듣기 31번', b.example_from({'source': '新HSK3급 … PDF · 예문: H31001 듣기 31번'}))
        self.assertEqual('H31006 독해 52번', b.example_from({'source': 'HSK3 공식 모의고사 H31006 독해 52번'}))
        self.assertEqual('', b.example_from({}))


class PlanVocabTest(unittest.TestCase):
    def setUp(self):
        self.saved_ids_path = b.IDS_PATH
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        b.IDS_PATH = self.root / 'card_ids.json'
        (self.root / 'src' / 'data').mkdir(parents=True)
        vocab = [
            {'id': 'HSK1-001', 'lesson': 'HSK1 150', 'hanzi': '爱', 'itemType': '단어'},
            {'id': 'HSK2EX-001', 'lesson': 'HSK2 공식문제', 'hanzi': '我爱你。', 'itemType': '문장'},
            {'id': 'L8-001', 'lesson': 'Lesson 8', 'hanzi': '课', 'itemType': '단어'},
            {'id': 'HSK3L-001', 'lesson': 'HSK3 듣기', 'hanzi': '听', 'itemType': '단어'},
        ]
        self.write(vocab, {'lastNo': {}, 'retired': {}})

    def tearDown(self):
        b.IDS_PATH = self.saved_ids_path
        self.tmp.cleanup()

    def write(self, vocab, registry):
        (self.root / 'src' / 'data' / 'vocab.json').write_text(json.dumps(vocab, ensure_ascii=False), encoding='utf-8')
        (self.root / 'src' / 'data' / 'vocab-retired.json').write_text(json.dumps(registry, ensure_ascii=False), encoding='utf-8')

    @staticmethod
    def entry(key, level, hanzi, pinyin):
        return {'key': key, 'level': level, 'lesson': b.LESSONS[level], 'hanzi': hanzi, 'pinyin': pinyin,
                'example': None, 'officialIds': [key], 'head': hanzi}

    @staticmethod
    def meanings(*keys):
        return {key: {'meaningKo': '뜻', 'partOfSpeech': '동사'} for key in keys}

    def test_order_retired_and_stable_ids(self):
        selection = {'add': [self.entry('1', 1, '爱', 'ài'), self.entry('2', 2, '帮助', 'bāngzhù')]}
        final, registry, _, new_ids = b.plan_vocab(self.root, selection, self.meanings('1', '2'))
        self.assertEqual(['H1-001', 'H2-001', 'L8-001', 'HSK3L-001'], [c['id'] for c in final])
        self.assertEqual({'hanzi': '爱', 'movedTo': '爱'}, registry['retired']['HSK1-001'])
        self.assertIsNone(registry['retired']['HSK2EX-001']['movedTo'])
        self.assertEqual(1, registry['lastNo']['H1'])
        self.assertEqual(1, registry['lastNo']['H2'])
        # 결과를 쓰고 다시 계획하면 같은 id
        self.write(final, registry)
        b.IDS_PATH.write_text(b.ids_text(new_ids), encoding='utf-8')
        final2, _, _, new_ids2 = b.plan_vocab(self.root, selection, self.meanings('1', '2'))
        self.assertEqual(new_ids, new_ids2)
        self.assertEqual([c['id'] for c in final], [c['id'] for c in final2])
        # 帮助를 빼고 새 단어를 넣으면 帮助 id는 은퇴, 새 단어는 H2-002
        selection3 = {'add': [self.entry('1', 1, '爱', 'ài'), self.entry('3', 2, '大家', 'dàjiā')]}
        final3, registry3, _, new_ids3 = b.plan_vocab(self.root, selection3, self.meanings('1', '3'))
        self.assertEqual('H2-002', new_ids3['3'])
        self.assertIn('H2-001', registry3['retired'])
        self.assertIsNone(registry3['retired']['H2-001']['movedTo'])


class RealDataTest(unittest.TestCase):
    def test_vocab_matches_plan(self):
        # 유닛 G의 apply 전까지 실패하는 것이 정상이다.
        selected = b.select(b.load_json(b.RAW_PATH), b.app_cards(REPO))
        saved = b.load_json(b.SELECT_PATH)
        self.assertEqual([e['key'] for e in saved['add']], [e['key'] for e in selected['add']])
        final, registry, *_ = b.plan_vocab(REPO, selected, b.load_meanings())
        final, registry, _ = b.simulate(REPO, final, registry)
        self.assertEqual(b.load_json(REPO / b.VOCAB_PATH), final)
        self.assertEqual(b.load_json(REPO / b.ID_REGISTRY), registry)


if __name__ == '__main__':
    unittest.main()
