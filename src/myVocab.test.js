import { beforeEach, test } from 'node:test';
import assert from 'node:assert/strict';
import {
  MINE_KEY,
  MINE_LESSON,
  autoReadingUsage,
  configureMineRefresh,
  dropAutoReadingUsage,
  ADDED_BY_UNKNOWN,
  loadMine,
  markKnown,
  markKnownEntry,
  markUnknown,
  markUnknownEntry,
  mineToStudyItems,
  resolveUnknown,
  resolveUnknownEntry,
  sortByUnknown,
  studyCardEntry,
  unknownCountOf,
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

test('dropAutoReadingUsage: 그 한자가 없는 예문은 자동값으로 보지 않아 남기고 문구만 지운다', () => {
  const edited = { ...OLD_READING_SAVED, exampleZh: '我自己写的句子。', examplePinyin: 'Wǒ zìjǐ xiě de jùzi.', exampleKo: '내가 쓴 문장' };
  assert.deepEqual(dropAutoReadingUsage(edited), { ...edited, note: '' });
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

test('저장소: 불러올 때 단어를 지금 데이터로 갱신하고(나눈 묶음은 조각으로), 바뀐 것이 있을 때만 한 번 저장한다', () => {
  const old = {
    key: 'word:比较忙:bijiaomang', kind: 'word', hanzi: '比较忙', pinyin: 'bǐjiàománg', meaningKo: '比较忙', partOfSpeech: '단어',
    note: '', exampleZh: '', examplePinyin: '', exampleKo: '', source: 'H31006 독해 52번',
    addedAt: '2026-10-20T05:00:00.000Z', addedBy: ADDED_BY_UNKNOWN, unknownCount: 1
  };
  const pattern = patternEntry(READING_GRAMMAR, 'H31001 독해 63번', NOW);
  let writes = 0;
  const storage = memoryStorage({ [MINE_KEY]: JSON.stringify({ version: 1, items: [old, pattern] }) });
  const setItem = storage.setItem;
  storage.setItem = (key, value) => {
    writes += 1;
    setItem(key, value);
  };
  useStorage(storage);
  const split = (items) => items.flatMap((entry) => entry.hanzi === '比较忙'
    ? ['比较', '忙'].map((hanzi) => ({ ...entry, hanzi, key: `word:${hanzi}`, meaningKo: `${hanzi} 뜻` }))
    : [entry]);
  const refresh = (items) => (items.some((entry) => entry.hanzi === '比较忙') ? split(items) : items);
  resetMineForTest();
  configureMineRefresh(refresh);
  assert.deepEqual(loadMine().map((entry) => entry.hanzi), ['比较', '忙', pattern.hanzi]);
  assert.equal(writes, 1);
  assert.deepEqual(JSON.parse(storage.getItem(MINE_KEY)).items.map((entry) => [entry.hanzi, entry.unknownCount]),
    [['比较', 1], ['忙', 1], [pattern.hanzi, undefined]]);
  // 다시 열면(새로 불러오면) 바꿀 것이 없어 쓰지 않는다
  resetMineForTest();
  configureMineRefresh(refresh);
  assert.equal(loadMine().length, 3);
  assert.equal(writes, 1);
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

// --- 랜덤 학습 «모르겠어» / «이제 알겠어» ---
const VOCAB_CARD = { id: 'K-12', itemType: '단어', lesson: 'HSK3 추가 300', hanzi: '满意', pinyin: 'mǎnyì', meaningKo: '만족하다', partOfSpeech: '형용사' };

test('studyCardEntry: 단어장 카드를 «모르겠어» 경로로 담는 항목, 키는 해설 담기와 같다', () => {
  const entry = studyCardEntry(VOCAB_CARD, NOW);
  assert.equal(entry.key, wordEntry(READING_WORD, 's', NOW).key);
  assert.equal(entry.addedBy, ADDED_BY_UNKNOWN);
  assert.equal(entry.source, '랜덤 학습 · HSK3 추가 300');
  assert.equal(entry.itemType, '단어');
  assert.equal(studyCardEntry({ ...VOCAB_CARD, mineKey: 'pattern:X' }, NOW).key, 'pattern:X');
  const [card] = mineToStudyItems([studyCardEntry({ ...VOCAB_CARD, itemType: '문장' }, NOW)]);
  assert.equal(card.itemType, '문장'); // 문장 카드는 담은 뒤에도 문장 글씨 크기
});

test('markUnknownEntry: 없으면 횟수 1로 맨 앞에, 있으면 자리·내용 그대로 횟수만 쌓는다', () => {
  const listening = wordEntry(LISTENING_WORD, 'H31001 듣기 25번', NOW);
  let items = markUnknownEntry([listening], studyCardEntry(VOCAB_CARD, NOW));
  assert.deepEqual(items.map((i) => [i.key, unknownCountOf(i)]), [['word:满意:manyi', 1], ['word:门口:menkou', 0]]);
  items = markUnknownEntry(items, studyCardEntry(VOCAB_CARD, NOW));
  items = markUnknownEntry(items, studyCardEntry(VOCAB_CARD, NOW));
  assert.equal(items[0].unknownCount, 3);
  // 직접 담은 항목에 «모르겠어»를 누르면 담은 경로는 그대로(직접)이고 횟수만 는다
  items = markUnknownEntry(items, studyCardEntry({ hanzi: '门口', pinyin: 'ménkǒu', itemType: '단어' }, NOW));
  assert.equal(items[1].unknownCount, 1);
  assert.equal(items[1].addedBy, undefined);
  assert.equal(items[1].source, 'H31001 듣기 25번');
});

test('unknownCountOf: 예전 항목·깨진 값은 0', () => {
  assert.equal(unknownCountOf(OLD_READING_SAVED), 0);
  assert.equal(unknownCountOf({ unknownCount: -2 }), 0);
  assert.equal(unknownCountOf({ unknownCount: '3' }), 0);
  assert.equal(unknownCountOf({ unknownCount: 2.5 }), 0);
  assert.equal(unknownCountOf(undefined), 0);
  assert.equal(mineToStudyItems([OLD_READING_SAVED])[0].unknownCount, 0);
});

test('resolveUnknownEntry: «모르겠어»로 담긴 것은 빼고, 직접 담은 것은 남기고 횟수만 지운다', () => {
  const manual = { ...wordEntry(LISTENING_WORD, 'H31001 듣기 25번', NOW), unknownCount: 2 };
  const viaUnknown = { ...studyCardEntry(VOCAB_CARD, NOW), unknownCount: 4 };
  let items = resolveUnknownEntry([viaUnknown, manual], viaUnknown.key);
  assert.deepEqual(items, [manual]);
  items = resolveUnknownEntry(items, manual.key);
  assert.deepEqual(items, [wordEntry(LISTENING_WORD, 'H31001 듣기 25번', NOW)]);
  assert.equal(resolveUnknownEntry(items, 'word:없음:'), items);
});

test('sortByUnknown: 모름 많은 순, 같으면 원래 순서', () => {
  const cards = [{ id: 'a', unknownCount: 0 }, { id: 'b', unknownCount: 2 }, { id: 'c', unknownCount: 5 }, { id: 'd', unknownCount: 2 }];
  assert.deepEqual(sortByUnknown(cards).map((c) => c.id), ['c', 'b', 'd', 'a']);
});

test('저장소: «모르겠어» 두 번 → 내 단어장에 모름 2, «이제 알겠어» → 빠짐. 저장 형식은 그대로 version 1', () => {
  const old = JSON.stringify({ version: 1, items: [wordEntry(LISTENING_WORD, 'H31001 듣기 25번', NOW)] });
  useStorage(memoryStorage({ [MINE_KEY]: old }));
  resetMineForTest();
  markUnknown(VOCAB_CARD);
  markUnknown(VOCAB_CARD);
  const saved = JSON.parse(localStorage.getItem(MINE_KEY));
  assert.equal(saved.version, 1);
  assert.deepEqual(saved.items.map((i) => [i.key, i.unknownCount, i.addedBy]), [
    ['word:满意:manyi', 2, ADDED_BY_UNKNOWN], ['word:门口:menkou', undefined, undefined]
  ]);
  assert.equal(mineToStudyItems(loadMine())[0].unknownCount, 2);
  resolveUnknown('word:满意:manyi');
  assert.deepEqual(loadMine().map((i) => i.key), ['word:门口:menkou']);
  markUnknown({ hanzi: '门口', pinyin: 'ménkǒu', itemType: '단어' });
  resolveUnknown('word:门口:menkou');
  assert.deepEqual(JSON.parse(localStorage.getItem(MINE_KEY)).items, [wordEntry(LISTENING_WORD, 'H31001 듣기 25번', NOW)]);
});

test('markKnownEntry: 모름 횟수를 1 줄이고, 0이 되면 «모름 표시 지우기»와 같이 해제, 0이면 그대로', () => {
  const manual = { ...wordEntry(LISTENING_WORD, 'H31001 듣기 25번', NOW), unknownCount: 1 };
  const viaUnknown = { ...studyCardEntry(VOCAB_CARD, NOW), unknownCount: 2 };
  let items = markKnownEntry([viaUnknown, manual], viaUnknown.key);
  assert.deepEqual(items.map((i) => [i.key, unknownCountOf(i)]), [['word:满意:manyi', 1], ['word:门口:menkou', 1]]);
  assert.equal(items[0].addedBy, ADDED_BY_UNKNOWN); // 줄이기만 할 때는 담은 경로·자리 그대로
  items = markKnownEntry(items, viaUnknown.key); // 1 → 0: «모르겠어»로 담긴 것은 빠진다
  assert.deepEqual(items.map((i) => i.key), ['word:门口:menkou']);
  items = markKnownEntry(items, manual.key); // 1 → 0: 직접 담은 것은 남고 횟수 칸만 지운다
  assert.deepEqual(items, [wordEntry(LISTENING_WORD, 'H31001 듣기 25번', NOW)]);
  assert.equal(markKnownEntry(items, manual.key), items); // 횟수 0이면 바꾸지 않는다
  assert.equal(markKnownEntry(items, 'word:없음:'), items);
});

test('저장소: «모르겠어» 3번 → 모름 3, «알겠어» 1번 → 모름 2, 모름 0인 단어의 «알겠어»는 저장값을 바꾸지 않는다', () => {
  for (let i = 0; i < 3; i += 1) markUnknown(VOCAB_CARD);
  assert.equal(mineToStudyItems(loadMine())[0].unknownCount, 3);
  markKnown('word:满意:manyi');
  assert.equal(mineToStudyItems(loadMine())[0].unknownCount, 2);
  markKnown('word:满意:manyi');
  markKnown('word:满意:manyi');
  assert.deepEqual(loadMine(), []);
  const before = localStorage.getItem(MINE_KEY);
  let calls = 0;
  subscribeMine(() => { calls += 1; });
  markKnown('word:满意:manyi');
  assert.equal(localStorage.getItem(MINE_KEY), before);
  assert.equal(calls, 0);
});
