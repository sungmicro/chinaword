import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import index from './data/mine-refresh.json' with { type: 'json' };
import vocab from './data/vocab.json' with { type: 'json' };
import { hasHangul, makeMineRefresher, mergeEntries, sourceAddress, sourceLesson } from './mineRefresh.js';
import { ADDED_BY_UNKNOWN, patternEntry, studyCardEntry, wordEntry, wordKey } from './myVocab.js';

const { refreshEntry, refreshItems, lookup } = makeMineRefresher(index, vocab, wordKey);
const NOW = new Date('2026-10-30T05:00:00Z');

// 지금 공개 해설 데이터(앱이 «＋ 담기» 출처로 적는 문항 단위). tools/mine_refresh.py load_questions와 같다.
function loadQuestions() {
  const questions = new Map();
  const kinds = { reading: '독해', listening: '듣기' };
  for (const kind of Object.keys(kinds)) {
    const dir = new URL(`../public/${kind}/`, import.meta.url);
    for (const name of fs.readdirSync(dir).filter((file) => /^H.*\.json$/.test(file)).sort()) {
      const data = JSON.parse(fs.readFileSync(new URL(name, dir), 'utf8'));
      for (const item of data.items) {
        const words = kind === 'reading' ? item.explain.vocab : item.vocab;
        questions.set(`${data.id} ${kinds[kind]} ${item.no}번`, words);
      }
    }
  }
  const writing = JSON.parse(fs.readFileSync(new URL('../public/writing/hsk3-all.json', import.meta.url), 'utf8'));
  for (const item of writing.items) {
    if (item.study?.vocab?.length) questions.set(`${item.exam} 쓰기 ${item.no}번`, item.study.vocab);
  }
  return questions;
}
const QUESTIONS = loadQuestions();

// 예전 기기에 남은 항목 (담은 순간의 내용이 그대로 저장돼 있다)
function saved(hanzi, pinyin, meaningKo, source, extra = {}) {
  return {
    key: wordKey(hanzi, pinyin), kind: 'word', hanzi, pinyin, meaningKo, partOfSpeech: extra.partOfSpeech ?? '단어',
    note: '', exampleZh: '', examplePinyin: '', exampleKo: '', source, addedAt: '2026-10-20T05:00:00.000Z', ...extra
  };
}
const OLD_BIJIAOMANG = saved('比较忙', 'bǐjiàománg', '比较忙', 'H31006 독해 52번', { unknownCount: 1, addedBy: ADDED_BY_UNKNOWN });

test('sourceAddress·sourceLesson: 앱이 적는 출처를 문항 주소·단원으로', () => {
  assert.equal(sourceAddress('H31006 독해 52번'), 'reading/H31006/52');
  assert.equal(sourceAddress('H31329 듣기 5번'), 'listening/H31329/5');
  assert.equal(sourceAddress('H31001 쓰기 71번'), 'writing/H31001/71');
  assert.equal(sourceAddress('랜덤 학습 · HSK3 독해'), null);
  assert.equal(sourceLesson('랜덤 학습 · HSK3 독해'), 'HSK3 독해');
  assert.equal(sourceLesson('랜덤 학습'), null);
});

test('比较忙(H31006 독해 52번): 比较·忙으로 나누고 모름 횟수·담은 방법·출처·담은 시각을 이어받는다', () => {
  const words = QUESTIONS.get('H31006 독해 52번');
  const current = (hanzi) => words.find((word) => word.hanzi === hanzi);
  const [bijiao, mang] = refreshEntry(OLD_BIJIAOMANG);
  for (const [entry, hanzi] of [[bijiao, '比较'], [mang, '忙']]) {
    assert.equal(entry.hanzi, hanzi);
    assert.equal(entry.key, wordKey(hanzi, current(hanzi).pinyin));
    assert.equal(entry.pinyin, current(hanzi).pinyin);
    assert.equal(entry.meaningKo, current(hanzi).meaningKo);
    assert.equal(entry.partOfSpeech, current(hanzi).partOfSpeech);
    assert.equal(entry.unknownCount, 1);
    assert.equal(entry.addedBy, ADDED_BY_UNKNOWN);
    assert.equal(entry.source, 'H31006 독해 52번');
    assert.equal(entry.addedAt, OLD_BIJIAOMANG.addedAt);
  }
});

test('이미 담긴 조각은 겹치지 않고, 모름 횟수는 큰 값·직접 담은 쪽·먼저 담겨 있던 항목의 출처를 남긴다', () => {
  const mang = { ...wordEntry({ hanzi: '忙', pinyin: 'máng', meaningKo: '바쁘다', partOfSpeech: '형용사' }, 'H31001 듣기 3번', NOW), unknownCount: 3 };
  const result = refreshItems([OLD_BIJIAOMANG, mang]);
  assert.deepEqual(result.map((entry) => entry.hanzi), ['比较', '忙']);
  const merged = result[1];
  assert.equal(merged.unknownCount, 3);
  assert.equal(merged.addedBy, undefined); // 忙은 직접 담았다
  assert.equal(merged.source, 'H31001 듣기 3번');
  assert.equal(merged.addedAt, mang.addedAt);

  const small = { ...mang, unknownCount: 0 };
  delete small.unknownCount;
  assert.equal(refreshItems([small, { ...OLD_BIJIAOMANG, unknownCount: 4 }]).find((entry) => entry.hanzi === '忙').unknownCount, 4);
});

test('이름+호칭(李先生)·옛 단원 카드(老李)·나눈 묶음은 조각으로', () => {
  const liXiansheng = saved('李先生', 'lǐxiānsheng', '리 선생(李先生, 남성 존칭)', 'H31004 듣기 17번', { partOfSpeech: '고유명사' });
  assert.deepEqual(refreshEntry(liXiansheng).map((entry) => [entry.hanzi, entry.meaningKo]), [
    ['李', '리(李, 성씨)'],
    ['先生', '선생님, ~씨']
  ]);
  const laoLi = saved('老李', 'lǎolǐ', '라오리', '랜덤 학습 · HSK3 듣기', { itemType: '단어', addedBy: ADDED_BY_UNKNOWN, unknownCount: 2 });
  const pieces = refreshEntry(laoLi);
  assert.deepEqual(pieces.map((entry) => entry.hanzi), ['老', '李']);
  assert.ok(pieces.every((entry) => entry.unknownCount === 2 && entry.source === '랜덤 학습 · HSK3 듣기'));
});

test('대본 오인식 단어는 고친 단어로(散 → 伞, 难 → 男), 고친 단어가 없으면 뺀다(使·原)', () => {
  const san = saved('散', 'sàn', '흩어진', 'H31329 듣기 5번', { partOfSpeech: '형용사', unknownCount: 2 });
  assert.deepEqual(refreshEntry(san).map((entry) => [entry.hanzi, entry.pinyin, entry.meaningKo, entry.unknownCount]), [['伞', 'sǎn', '우산', 2]]);
  assert.deepEqual(refreshEntry(saved('难', 'nán', '어렵다, 힘들다', 'H31006 듣기 23번')).map((entry) => entry.hanzi), ['男']);
  assert.deepEqual(refreshEntry(saved('使', 'shǐ', '~에게 ~시키다', 'H31329 듣기 10번')), []);
  assert.deepEqual(refreshEntry(saved('原', 'yuán', '원본', 'H31332 듣기 26번')), []);
  // 다른 문항의 같은 한자는 진짜 단어라 그대로(뜻만 지금 데이터로)
  assert.deepEqual(refreshEntry(saved('难', 'nán', '어렵다', 'H31003 듣기 1번')).map((entry) => entry.hanzi), ['难']);
});

test('같은 단어는 병음·뜻·품사를 지금 값으로: 碗 wàn → wǎn, 马 «말하다» → 출처 문항의 뜻', () => {
  const wan = saved('碗', 'wàn', '사발, 공기, 그릇', 'H31001 듣기 9번', { partOfSpeech: '명사' });
  const [fixed] = refreshEntry(wan);
  assert.equal(fixed.pinyin, 'wǎn');
  assert.equal(fixed.key, wan.key); // 성조만 달라 열쇠는 같다
  const ma = saved('马', 'mǎ', '말하다, 이야기하다', 'H31110 듣기 34번', { partOfSpeech: '명사' });
  const now = QUESTIONS.get('H31110 듣기 34번').find((word) => word.hanzi === '马');
  assert.equal(refreshEntry(ma)[0].meaningKo, now.meaningKo);
  // 랜덤 학습으로 담은 단원 카드는 그 단원의 카드로
  const card = vocab.find((entry) => entry.hanzi === '碗' && entry.lesson === 'HSK3 추가 300');
  const fromStudy = { ...studyCardEntry({ ...card, pinyin: 'wàn' }, NOW), unknownCount: 1 };
  assert.equal(refreshEntry(fromStudy)[0].pinyin, card.pinyin);
});

test('문장·패턴 항목과 메모는 건드리지 않는다', () => {
  const pattern = patternEntry({ pattern: '虽然A，但是B', meaningKo: 'A이긴 하지만 B', note: '내 메모' }, 'H31001 독해 63번', NOW);
  const sentence = { ...saved('我比较忙。', 'wǒ bǐjiào máng', '我比较忙。', '랜덤 학습 · HSK3 듣기'), itemType: '문장' };
  [pattern, sentence].forEach((entry) => assert.deepEqual(refreshEntry(entry), [entry]));
  assert.equal(refreshEntry(pattern)[0], pattern);
  const memo = saved('马', 'mǎ', '말하다, 이야기하다', 'H31004 듣기 33번', {
    partOfSpeech: '명사', note: '말 = 马, 엄마 = 妈', exampleZh: '我会骑马。', exampleKo: '나는 말을 탈 줄 안다.'
  });
  const [kept] = refreshEntry(memo);
  assert.equal(kept.meaningKo, '말(동물)');
  assert.equal(kept.note, memo.note);
  assert.equal(kept.exampleZh, memo.exampleZh);
  assert.equal(kept.exampleKo, memo.exampleKo);
  // 나눌 때도 메모는 조각마다 남는다
  const splitMemo = { ...OLD_BIJIAOMANG, note: '꽤 바쁘다' };
  assert.ok(refreshEntry(splitMemo).every((entry) => entry.note === '꽤 바쁘다'));
});

test('어디에도 없는 단어: 뜻에 한글이 있으면 그대로, 없으면 뺀다', () => {
  const unknownKo = saved('电脑游戏', 'diànnǎoyóuxì', '컴퓨터 게임', 'H31111 듣기 39번');
  assert.equal(refreshEntry(unknownKo)[0], unknownKo);
  assert.deepEqual(refreshEntry(saved('车辆', 'chēliàng', '车辆', 'H31007 독해 61번')), []);
  assert.deepEqual(refreshEntry(saved('有借有还', 'yǒujièyǒuhuán', '有借有还', '랜덤 학습 · HSK3 독해', { itemType: '단어' })), []);
});

test('바뀐 것이 없으면 같은 배열, 두 번 돌려도 같다(멱등)', () => {
  const items = [
    OLD_BIJIAOMANG,
    saved('李先生', 'lǐxiānsheng', '李先生', 'H31110 듣기 14번'),
    saved('碗', 'wàn', '사발, 공기, 그릇', 'H31001 듣기 9번', { partOfSpeech: '명사' }),
    saved('散', 'sàn', '흩어진', 'H31329 듣기 5번'),
    saved('使', 'shǐ', '~에게 ~시키다', 'H31329 듣기 10번'),
    patternEntry({ pattern: '越来越', note: '점점' }, 'H31001 듣기 1번', NOW)
  ];
  const once = refreshItems(items);
  assert.notEqual(once, items);
  const twice = refreshItems(once);
  assert.equal(twice, once);
  assert.deepEqual(twice, once);
});

test('색인이 지금 해설 데이터와 맞는다: 모든 문항의 모든 단어가 그 문항의 병음·뜻·품사로 갱신된다', () => {
  let words = 0;
  for (const [source, list] of QUESTIONS) {
    for (const word of list) {
      words += 1;
      const entry = wordEntry({ ...word, meaningKo: word.hanzi, partOfSpeech: '단어' }, source, NOW);
      const out = refreshEntry(entry);
      assert.equal(out.length, 1, `${source} ${word.hanzi}`);
      assert.deepEqual(
        [out[0].hanzi, out[0].pinyin, out[0].meaningKo, out[0].partOfSpeech],
        [word.hanzi, word.pinyin, word.meaningKo, word.partOfSpeech ?? ''],
        `${source} ${word.hanzi}: 색인이 데이터와 다르다 → tools/mine_refresh.py --repo .`
      );
    }
  }
  assert.ok(words > 10000);
});

test('갱신 뒤에는 뜻에 한글이 없는 단어 항목이 남지 않는다', () => {
  // 지금 데이터의 모든 한자와 보정 표의 모든 예전 토큰을, 뜻 = 한자(한글 없음)로 모든 문항·단원 출처에 담아 본다.
  const hanziSet = new Set(vocab.map((card) => card.hanzi));
  QUESTIONS.forEach((list) => list.forEach((word) => hanziSet.add(word.hanzi)));
  Object.keys(index.split).forEach((token) => hanziSet.add(token));
  Object.values(index.moved).forEach((table) => Object.keys(table).forEach((token) => hanziSet.add(token)));
  const sources = [...Object.keys(index.moved).map((address) => {
    const [kind, test, no] = address.split('/');
    return `${test} ${{ reading: '독해', listening: '듣기', writing: '쓰기' }[kind]} ${no}번`;
  }), 'H31006 독해 52번', '랜덤 학습 · HSK3 듣기', '랜덤 학습 · HSK3 독해', '랜덤 학습', ''];
  let checked = 0;
  for (const source of sources) {
    const items = [...hanziSet, '没有这个词'].map((hanzi) => saved(hanzi, 'x', hanzi, source));
    for (const entry of refreshItems(items)) {
      checked += 1;
      assert.ok(hasHangul(entry.meaningKo), `${source} ${entry.hanzi}: 뜻 ${entry.meaningKo}`);
    }
  }
  assert.ok(checked > 1000);
});

test('보정 표에서 빼기로 한 단어(대응 단어·카드가 없음) 목록', () => {
  const removed = [];
  for (const [address, table] of Object.entries(index.moved)) {
    const [kind, test, no] = address.split('/');
    const source = `${test} ${{ reading: '독해', listening: '듣기', writing: '쓰기' }[kind]} ${no}번`;
    for (const hanzi of Object.keys(table)) {
      if (!refreshEntry(saved(hanzi, 'x', '뜻', source)).length) removed.push(`${source} ${hanzi}`);
    }
  }
  for (const token of Object.keys(index.split)) {
    if (!refreshEntry(saved(token, 'x', '뜻', '랜덤 학습')).length) removed.push(token);
  }
  assert.deepEqual(removed.sort(), [
    'H31001 듣기 17번 明', 'H31004 듣기 40번 北', 'H31006 듣기 35번 脚', 'H31006 듣기 40번 偏',
    'H31007 독해 59번 东', 'H31007 독해 59번 向', 'H31009 독해 70번 云', 'H31221 듣기 22번 云',
    'H31328 듣기 9번 晓', 'H31329 듣기 10번 使', 'H31330 듣기 10번 识', 'H31332 듣기 10번 使',
    'H31332 듣기 26번 原', 'H31332 듣기 26번 院', '儿'
  ].sort());
});

test('mergeEntries: 메모는 합치고 예문은 빈 쪽만 채운다', () => {
  const a = saved('忙', 'máng', '바쁘다', 'H31001 듣기 3번', { note: '메모 A', addedBy: ADDED_BY_UNKNOWN, unknownCount: 1 });
  const b = saved('忙', 'máng', '바쁘다', 'H31002 듣기 4번', { note: '메모 B', exampleZh: '我很忙。', addedBy: ADDED_BY_UNKNOWN });
  const merged = mergeEntries(a, b);
  assert.equal(merged.note, '메모 A / 메모 B');
  assert.equal(merged.exampleZh, '我很忙。');
  assert.equal(merged.addedBy, ADDED_BY_UNKNOWN);
  assert.equal(merged.source, a.source);
  assert.equal(mergeEntries(a, { ...b, note: '메모 A' }).note, '메모 A');
});

test('lookup: vocab.json 첫 «단어» 카드가 기본 뜻', () => {
  const first = vocab.find((card) => card.itemType === '단어' && card.hanzi === '忙');
  assert.equal(lookup('忙', {}).meaningKo, first.meaningKo);
  assert.equal(lookup('没有这个词', {}), null);
});
