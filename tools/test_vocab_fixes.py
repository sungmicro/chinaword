import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import tempfile

from vocab_fixes import (BANNED_PART, ID_REGISTRY, VOCAB_KEYS, CardIds, VocabProblems, apply_listening, fix_vocab,
                         has_hangul, load_fixes, load_id_registry, vocab_problems)

TABLE = {
    'words': {'李': {'pinyin': 'lǐ', 'partOfSpeech': '고유명사', 'meaningKo': '리(李, 성씨)'}},
    'split': {'比较忙': ['比较', '忙'], '儿': [], '很多': ['多#많다']},
    'parts': {
        '比较': {'pinyin': 'bǐjiào', 'partOfSpeech': '부사', 'meaningKo': '비교적, 꽤'},
        '忙': {'pinyin': 'máng', 'partOfSpeech': '형용사', 'meaningKo': '바쁘다'},
        '多#많다': {'pinyin': 'duō', 'partOfSpeech': '형용사', 'meaningKo': '많다'},
        '好#낫다': {'pinyin': 'hǎo', 'partOfSpeech': '형용사', 'meaningKo': '(병이) 낫다'},
    },
    'items': {'reading/H31110/60': {'你好': ['好#낫다']}},
}


def word(hanzi, meaning=None, part='명사', pinyin='x'):
    return {'hanzi': hanzi, 'pinyin': pinyin, 'partOfSpeech': part, 'meaningKo': meaning or hanzi}


class FixVocabTest(unittest.TestCase):
    def test_words_replace_pinyin_part_and_meaning(self):
        self.assertEqual(fix_vocab([word('李')], table=TABLE),
                         [{'hanzi': '李', 'pinyin': 'lǐ', 'partOfSpeech': '고유명사', 'meaningKo': '리(李, 성씨)'}])

    def test_split_glued_token_and_drop_duplicates(self):
        # H31006 52번: 比较忙(품사 '단어', 병음 bǐjiàománg) → 比较 / 忙, 이미 있는 忙은 한 번만
        vocab = [word('工作', '일'), word('比较忙', part=BANNED_PART, pinyin='bǐjiàománg'), word('忙', '바쁘다', '형용사', 'máng')]
        self.assertEqual([w['hanzi'] for w in fix_vocab(vocab, table=TABLE)], ['工作', '比较', '忙'])

    def test_empty_split_drops_the_token(self):
        self.assertEqual(fix_vocab([word('菜单', '메뉴'), word('儿')], table=TABLE), [word('菜单', '메뉴')])

    def test_item_override_only_applies_to_that_item(self):
        vocab = [word('你好', '안녕하세요', '표현')]
        self.assertEqual(fix_vocab(vocab, 'reading/H31110/60', TABLE)[0]['hanzi'], '好')
        self.assertEqual(fix_vocab(vocab, 'listening/H31003/22', TABLE), vocab)

    def test_split_parts_are_cut_first_when_over_eight(self):
        vocab = [word(h, '뜻') for h in '甲乙丙丁戊己庚'] + [word('比较忙')]
        fixed = [w['hanzi'] for w in fix_vocab(vocab, table=TABLE)]
        self.assertEqual(fixed, list('甲乙丙丁戊己庚') + ['比较'])

    def test_fixing_twice_gives_the_same_result(self):
        vocab = [word('李'), word('比较忙'), word('很多')]
        once = fix_vocab(vocab, table=TABLE)
        self.assertEqual(fix_vocab(once, table=TABLE), once)

    def test_problems_need_hangul_meaning_and_no_bare_word_part(self):
        self.assertEqual(vocab_problems(word('门口', '입구'), 'T'), [])
        self.assertTrue(any('한글' in p for p in vocab_problems(word('李'), 'T')))
        self.assertTrue(any('단어' in p for p in vocab_problems(word('手', '손', BANNED_PART), 'T')))


    def test_problems_need_hanzi_and_pinyin(self):
        self.assertTrue(any('병음' in p for p in vocab_problems(word('门口', '입구', pinyin=''), 'T')))
        self.assertTrue(any('한자' in p for p in vocab_problems({**word('门口', '입구'), 'hanzi': ' '}, 'T')))


class ApplyListeningTest(unittest.TestCase):
    def test_refuses_to_write_when_problems_remain(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / 'public' / 'listening').mkdir(parents=True)
            (repo / 'src' / 'data').mkdir(parents=True)
            data = {'id': 'H39999', 'items': [{'no': 1, 'vocab': [word('新词', pinyin='xīncí')]}]}
            path = repo / 'public' / 'listening' / 'H39999.json'
            path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
            before = path.read_text(encoding='utf-8')
            with self.assertRaises(VocabProblems):
                apply_listening(repo)
            self.assertEqual(path.read_text(encoding='utf-8'), before)
            self.assertFalse((repo / 'src' / 'data' / 'vocab.json').exists())


class CardIdsTest(unittest.TestCase):
    def run_once(self, repo, previous, words):
        ids = CardIds(repo, 'HSK3R', previous)
        cards = [{'id': ids.id_for(hanzi), 'hanzi': hanzi} for hanzi in words]
        ids.finish(cards + [{'id': 'K-1', 'hanzi': '多'}])
        return {card['hanzi']: card['id'] for card in cards}

    def test_deleted_id_is_retired_and_never_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            first = self.run_once(repo, {}, ['门口', '很多'])
            self.assertEqual(first, {'门口': 'HSK3R-001', '很多': 'HSK3R-002'})
            # 很多를 지운다(가장 큰 번호) → 은퇴, 이어받는 카드는 다른 단원의 多
            second = self.run_once(repo, first, ['门口'])
            registry = load_id_registry(repo)
            self.assertEqual(registry['retired'], {'HSK3R-002': {'hanzi': '很多', 'movedTo': '多'}})
            # 다음 실행에서 새 카드를 더해도 은퇴한 HSK3R-002를 다시 쓰지 않는다
            third = self.run_once(repo, second, ['门口', '新词'])
            self.assertEqual(third, {'门口': 'HSK3R-001', '新词': 'HSK3R-003'})
            self.assertEqual(load_id_registry(repo)['lastNo'], {'HSK3R': 3})
            self.assertTrue((repo / ID_REGISTRY).exists())

    def test_registry_last_number_is_respected_even_without_retired_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / ID_REGISTRY).parent.mkdir(parents=True)
            (repo / ID_REGISTRY).write_text(json.dumps({'lastNo': {'HSK3R': 347}, 'retired': {}}), encoding='utf-8')
            self.assertEqual(self.run_once(repo, {'门口': 'HSK3R-001'}, ['门口', '新词'])['新词'], 'HSK3R-348')


class FixesFileTest(unittest.TestCase):
    """저장소의 vocab_fixes.json 자체가 규칙을 지키는지 본다."""

    def setUp(self):
        self.table = load_fixes()

    def entries(self):
        for key, fields in list(self.table['words'].items()) + list(self.table['parts'].items()):
            yield key, {'hanzi': key.split('#', 1)[0], **fields}

    def test_every_entry_has_pinyin_part_and_korean_meaning(self):
        for key, entry in self.entries():
            self.assertEqual(sorted(entry), sorted(VOCAB_KEYS), key)
            self.assertTrue(entry['pinyin'] and ' ' not in entry['pinyin'], key)
            self.assertTrue(entry['partOfSpeech'] and entry['partOfSpeech'] != BANNED_PART, key)
            self.assertTrue(has_hangul(entry['meaningKo']), key)
            self.assertNotEqual(entry['meaningKo'], entry['hanzi'], key)

    def test_split_and_item_parts_exist(self):
        targets = [part for parts in self.table['split'].values() for part in parts]
        targets += [part for item in self.table['items'].values() for parts in item.values() for part in parts]
        for part in targets:
            self.assertTrue(part in self.table['parts'] or part in self.table['words'], part)

    def test_public_data_has_no_untranslated_vocab(self):
        repo = Path(__file__).resolve().parent.parent
        for kind in ('reading', 'listening'):
            for path in sorted((repo / 'public' / kind).glob('H*.json')):
                data = json.loads(path.read_text(encoding='utf-8'))
                for item in data['items']:
                    vocab = item['explain']['vocab'] if kind == 'reading' else item['vocab']
                    for entry in vocab:
                        self.assertEqual(vocab_problems(entry, f'{kind} {data["id"]} {item["no"]}'), [])


if __name__ == '__main__':
    unittest.main()
