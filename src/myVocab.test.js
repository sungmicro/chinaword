import { beforeEach, test } from 'node:test';
import assert from 'node:assert/strict';
import {
  MINE_KEY,
  MINE_LESSON,
  autoReadingUsage,
  dropAutoReadingUsage,
  loadMine,
  mineToStudyItems,
  patternEntry,
  removeMine,
  resetMineForTest,
  subscribeMine,
  toggleEntry,
  toggleMine,
  wordEntry,
  wordsToPinyin
} from './myVocab.js';

const NOW = new Date('2026-10-12T05:00:00Z');
const READING_WORD = {
  hanzi: '满意', pinyin: 'mǎnyì', partOfSpeech: '형용사', meaningKo: '만족하다', usage: '对A很满意',
  example: { zh: '我很满意。', words: [['我', 'wǒ'], ['很', 'hěn'], ['满意', 'mǎnyì'], ['。', '']], ko: '나는 만족한다.' }
};
const LISTENING_WORD = { hanzi: '门口', pinyin: 'ménkǒu', meaningKo: '입구', partOfSpeech: '명사' };
const READING_GRAMMAR = {
  pattern: '虽然A，但是B', meaningKo: 'A이긴 하지만 B', note: '무게는 B에 있다.',
  example: { zh: '虽然贵，但是好。', words: [['虽然', 'suīrán'], ['贵', 'guì'], ['，', ''], ['但是', 'dànshì'], ['好', 'hǎo'], ['。', '']], ko: '비싸지만 좋다.' }
};
const LISTENING_GRAMMAR = { pattern: '동사 + 到 (결과보어)', note: '목표를 이루었음을 나타낸다.' };

function memoryStorage(initial = {}) {
  const data = { ...initial };
  return {
    getItem: (key) => (key in data ? data[key] : null),
    setItem: (key, value) => {
      data[key] = String(value);
    }
  };
}

function useStorage(storage) {
  Object.defineProperty(globalThis, 'localStorage', { value: storage, configurable: true, writable: true });
}

beforeEach(() => {
  useStorage(memoryStorage());
  resetMineForTest();
});

test('wordsToPinyin: 예문 병음 한 줄', () => {
  assert.equal(wordsToPinyin(READING_GRAMMAR.example.words), 'Suīrán guì, dànshì hǎo.');
  assert.equal(wordsToPinyin(undefined), '');
});

test('wordEntry: 독해 단어도 듣기처럼 용법·예문 칸을 비운다', () => {
  assert.deepEqual(wordEntry(READING_WORD, 'H31001 독해 63번', NOW), {
    key: 'word:满意:manyi', kind: 'word', hanzi: '满意', pinyin: 'mǎnyì', meaningKo: '만족하다', partOfSpeech: '형용사',
    note: '', exampleZh: '', examplePinyin: '', exampleKo: '',
    source: 'H31001 독해 63번', addedAt: '2026-10-12T05:00:00.000Z'
  });
});

// 2026-11-02 전에 독해 해설에서 담은 단어 (자동 용법 + 지문 예문이 함께 저장됨)
const OLD_READING_SAVED = {
  key: 'word:满意:manyi', kind: 'word', hanzi: '满意', pinyin: 'mǎnyì', meaningKo: '만족하다', partOfSpeech: '형용사',
  note: '满意가 쓰인 문장을 함께 확인', exampleZh: '我对这儿很满意。', examplePinyin: 'Wǒ duì zhèr hěn mǎnyì.',
  exampleKo: '나는 여기가 마음에 든다.', source: 'H31006 독해 61번', addedAt: '2026-10-20T05:00:00.000Z'
};

test('dropAutoReadingUsage: 독해 단어의 자동 용법 문구와 함께 담긴 예문만 지운다', () => {
  assert.equal(autoReadingUsage('满意'), '满意가 쓰인 문장을 함께 확인');
  assert.deepEqual(dropAutoReadingUsage(OLD_READING_SAVED), {
    ...OLD_READING_SAVED, note: '', exampleZh: '', examplePinyin: '', exampleKo: ''
  });
});

test('dropAutoReadingUsage: 직접 쓴 메모·다른 단어 문구·패턴·듣기 항목은 그대로 둔다', () => {
  const kept = [
    { ...OLD_READING_SAVED, note: '对A很满意 — 내가 적은 메모' },
    { ...OLD_READING_SAVED, note: '满意가 쓰인 문장을 함께 확인하고 외우기' },
    { ...OLD_READING_SAVED, note: '房间가 쓰인 문장을 함께 확인' },
    { ...OLD_READING_SAVED, source: 'H31001 듣기 25번' },
    { ...OLD_READING_SAVED, kind: 'pattern', key: 'pattern:满意', hanzi: '满意' },
    patternEntry(READING_GRAMMAR, 'H31001 독해 63번', NOW)
  ];
  kept.forEach((entry) => assert.equal(dropAutoReadingUsage(entry), entry));
});

test('저장소: 불러올 때 예전 독해 자동 문구를 지우고 기기에도 한 번 저장한다', () => {
  const pattern = patternEntry(READING_GRAMMAR, 'H31001 독해 63번', NOW);
  const listening = wordEntry(LISTENING_WORD, 'H31001 듣기 25번', NOW);
  const storage = memoryStorage({ [MINE_KEY]: JSON.stringify({ version: 1, items: [OLD_READING_SAVED, pattern, listening] }) });
  useStorage(storage);
  resetMineForTest();
  const [word, savedPattern, savedListening] = loadMine();
  assert.equal(word.note, '');
  assert.equal(word.exampleZh, '');
  assert.equal(word.meaningKo, '만족하다');
  assert.equal(word.source, 'H31006 독해 61번');
  assert.deepEqual(savedPattern, pattern);
  assert.deepEqual(savedListening, listening);
  const stored = JSON.parse(storage.getItem(MINE_KEY)).items;
  assert.equal(stored[0].note, '');
  assert.equal(stored[0].examplePinyin, '');
  assert.equal(stored[1].note, '무게는 B에 있다.');
});

test('저장소: 지울 것이 없으면 기기 저장값을 다시 쓰지 않는다', () => {
  const raw = JSON.stringify({ version: 1, items: [wordEntry(LISTENING_WORD, 'H31001 듣기 25번', NOW)] });
  let writes = 0;
  const storage = memoryStorage({ [MINE_KEY]: raw });
  const setItem = storage.setItem;
  storage.setItem = (key, value) => {
    writes += 1;
    setItem(key, value);
  };
  useStorage(storage);
  resetMineForTest();
  assert.equal(loadMine().length, 1);
  assert.equal(writes, 0);
});

test('wordEntry: 듣기 단어는 용법·예문 칸이 빈다', () => {
  const entry = wordEntry(LISTENING_WORD, 'H31001 듣기 25번', NOW);
  assert.equal(entry.note, '');
  assert.equal(entry.exampleZh, '');
  assert.equal(entry.examplePinyin, '');
});

test('patternEntry: 짧은 뜻이 있으면 뜻 자리에, 없으면 설명 전체가 뜻', () => {
  const reading = patternEntry(READING_GRAMMAR, 'H31001 독해 63번', NOW);
  assert.equal(reading.key, 'pattern:虽然A，但是B');
  assert.equal(reading.kind, 'pattern');
  assert.equal(reading.meaningKo, 'A이긴 하지만 B');
  assert.equal(reading.note, '무게는 B에 있다.');
  assert.equal(reading.examplePinyin, 'Suīrán guì, dànshì hǎo.');
  const listening = patternEntry(LISTENING_GRAMMAR, 'H31001 듣기 25번', NOW);
  assert.equal(listening.meaningKo, '목표를 이루었음을 나타낸다.');
  assert.equal(listening.note, '');
});

test('toggleEntry: 같은 key는 하나만, 다시 누르면 뺀다, 새 항목이 앞', () => {
  let items = toggleEntry([], wordEntry(READING_WORD, 's1', NOW));
  items = toggleEntry(items, patternEntry(READING_GRAMMAR, 's2', NOW));
  assert.deepEqual(items.map((i) => i.key), ['pattern:虽然A，但是B', 'word:满意:manyi']);
  items = toggleEntry(items, wordEntry(READING_WORD, '다른 문항', NOW));
  assert.deepEqual(items.map((i) => i.key), ['pattern:虽然A，但是B']);
});

test('mineToStudyItems: 단어장·랜덤 학습 카드 모양', () => {
  const [card] = mineToStudyItems([patternEntry(READING_GRAMMAR, 'H31001 독해 63번', NOW)]);
  assert.equal(card.id, 'mine:pattern:虽然A，但是B');
  assert.equal(card.itemType, '패턴');
  assert.equal(card.lesson, MINE_LESSON);
  assert.equal(card.hanzi, '虽然A，但是B');
  assert.equal(card.pinyin, '');
  assert.equal(card.meaningKo, 'A이긴 하지만 B');
  assert.equal(card.mineKey, 'pattern:虽然A，但是B');
  assert.equal(card.source, 'H31001 독해 63번');
});

test('저장소: 담기·빼기가 기기에 남고 구독자에게 알린다', () => {
  let calls = 0;
  const off = subscribeMine(() => {
    calls += 1;
  });
  toggleMine(wordEntry(READING_WORD, 's', NOW));
  assert.equal(loadMine().length, 1);
  assert.equal(JSON.parse(localStorage.getItem(MINE_KEY)).items[0].key, 'word:满意:manyi');
  const snapshot = loadMine();
  assert.equal(loadMine(), snapshot); // 바뀌기 전에는 같은 배열 (useSyncExternalStore 조건)
  removeMine('word:满意:manyi');
  assert.equal(loadMine().length, 0);
  assert.equal(calls, 2);
  off();
});

test('저장소: 깨진 저장값은 버리고, 저장소가 없어도 빈 목록으로 동작', () => {
  useStorage(memoryStorage({ [MINE_KEY]: '{"items": [{"key": 1}, null, {"key": "word:好", "hanzi": "好"}]}' }));
  resetMineForTest();
  assert.deepEqual(loadMine().map((i) => i.key), ['word:好']);
  useStorage(undefined);
  resetMineForTest();
  assert.deepEqual(loadMine(), []);
  assert.doesNotThrow(() => toggleMine(wordEntry(READING_WORD, 's', NOW)));
  assert.equal(loadMine().length, 1);
});

test('wordEntry: 다음자는 읽기로 구분하고, 성조 변조는 같은 단어로 본다', () => {
  const hai = wordEntry({ hanzi: '还', pinyin: 'hái' }, 's', NOW).key;
  const huan = wordEntry({ hanzi: '还', pinyin: 'huán' }, 's', NOW).key;
  assert.notEqual(hai, huan);
  assert.equal(wordEntry({ hanzi: '不', pinyin: 'bù' }, 's', NOW).key, wordEntry({ hanzi: '不', pinyin: 'bú' }, 's', NOW).key);
  assert.equal(wordEntry({ hanzi: '绿', pinyin: 'lǜ' }, 's', NOW).key, 'word:绿:lv');
});
