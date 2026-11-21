import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {
  DEFAULT_SUBS, EXAM_TABS, clozeKoVisible, VIEW_OPTIONS, buildCatalog, examUrl, groupLabel, nextLetter, partChips, partKind,
  restoreView, tabPrefs, withTabPrefs
} from './examCatalog.js';

const readJson = (path) => JSON.parse(fs.readFileSync(new URL(path, import.meta.url), 'utf8'));
const listening = readJson('./data/listening-index.json');
const reading = readJson('./data/reading-index.json');
const hsk30 = readJson('./data/hsk30-index.json');
const fixture = (name) => readJson(`./__fixtures__/${name}`);

test('탭은 랜덤 학습·단어장·3급·4급·기출(2.0) 다섯 개다', () => {
  assert.deepEqual(VIEW_OPTIONS.map((option) => option.label), ['랜덤 학습', '단어장', '3급', '4급', '기출(2.0)']);
  assert.deepEqual(EXAM_TABS, ['hsk3', 'hsk4', 'past']);
});

test('시험지 목록: 3급=S30-3, 4급=S30-4(base /hsk30), 기출(2.0)=H31 19회 그대로', () => {
  const catalog = buildCatalog({ listening, reading, hsk30 });
  for (const area of ['listen', 'read', 'write']) {
    assert.deepEqual(catalog.hsk3[area].map((entry) => entry.id), ['S30-3']);
    assert.deepEqual(catalog.hsk4[area].map((entry) => entry.id), ['S30-4']);
    assert.ok([...catalog.hsk3[area], ...catalog.hsk4[area]].every((entry) => entry.base === '/hsk30'));
  }
  assert.equal(examUrl(catalog.hsk3.listen[0]), '/hsk30/S30-3-listening.json');
  assert.equal(examUrl(catalog.hsk4.read[0]), '/hsk30/S30-4-reading.json');
  assert.equal(examUrl(catalog.hsk4.write[0]), '/hsk30/S30-4-writing.json');

  assert.equal(catalog.past.listen.length, 19);
  assert.equal(catalog.past.read.length, 19);
  assert.deepEqual(catalog.past.listen[0], { id: 'H31001', label: 'H31001', base: '/listening', file: 'H31001.json', format: 'hsk20' });
  assert.equal(examUrl(catalog.past.read[0]), '/reading/H31001.json');
  assert.deepEqual(catalog.past.write.map(examUrl), ['/writing/hsk3-all.json']);
});

test('시험지 목록: 3.0 목록이 비었거나 영역이 빠져도 빈 목록으로 둔다', () => {
  const empty = buildCatalog({ listening, reading, hsk30: [] });
  assert.deepEqual(empty.hsk3, { listen: [], read: [], write: [] });
  const partial = buildCatalog({ hsk30: [{ id: 'S30-3', level: 3, listening: { file: 'S30-3-listening.json', count: 30 } }] });
  assert.equal(partial.hsk3.listen.length, 1);
  assert.deepEqual(partial.hsk3.read, []);
  assert.deepEqual(partial.hsk4.listen, []);
});

test('탭 복원: 예전 듣기·독해·쓰기 탭은 기출(2.0)의 같은 서브탭으로 연다', () => {
  assert.deepEqual(restoreView('listen', null), { view: 'past', subs: { ...DEFAULT_SUBS, past: 'listen' } });
  assert.deepEqual(restoreView('read', null), { view: 'past', subs: { ...DEFAULT_SUBS, past: 'read' } });
  assert.deepEqual(restoreView('write', { hsk3: 'read' }), { view: 'past', subs: { hsk3: 'read', hsk4: 'listen', past: 'write' } });
  assert.deepEqual(restoreView('study', null), { view: 'study', subs: DEFAULT_SUBS });
  assert.deepEqual(restoreView('list', null).view, 'list');
  assert.deepEqual(restoreView('hsk4', { hsk4: 'write', past: 'bogus' }), { view: 'hsk4', subs: { ...DEFAULT_SUBS, hsk4: 'write' } });
  assert.deepEqual(restoreView('nope', 'x'), { view: 'study', subs: DEFAULT_SUBS });
});

test('탭별 설정: 예전 testId·part는 기출(2.0) 값이고, 기출(2.0)을 저장하면 맨 위 값도 같이 바뀐다', () => {
  const legacy = { testId: 'H31005', part: 3, positions: { H31005: 27 } };
  assert.deepEqual(tabPrefs(legacy, 'past'), { testId: 'H31005', part: 3 });
  assert.deepEqual(tabPrefs(legacy, 'hsk3'), {});
  assert.deepEqual(tabPrefs(null, 'past'), { testId: undefined, part: undefined });

  const hsk3 = withTabPrefs(legacy, 'hsk3', { testId: 'S30-3', part: 2 }, { positions: { H31005: 27, 'S30-3': 12 } });
  assert.equal(hsk3.testId, 'H31005');
  assert.equal(hsk3.part, 3);
  assert.deepEqual(hsk3.levels, { hsk3: { testId: 'S30-3', part: 2 } });
  assert.deepEqual(tabPrefs(hsk3, 'hsk3'), { testId: 'S30-3', part: 2 });
  assert.deepEqual(tabPrefs(hsk3, 'past'), { testId: 'H31005', part: 3 });

  const past = withTabPrefs(hsk3, 'past', { testId: 'H31002', part: 1 });
  assert.equal(past.testId, 'H31002');
  assert.equal(past.part, 1);
  assert.deepEqual(past.levels.hsk3, { testId: 'S30-3', part: 2 });
  assert.deepEqual(past.positions, { H31005: 27, 'S30-3': 12 });
});

test('독해 부분 형식: parts[].kind가 우선이고, 없으면 예전 1=match·2=wordbank·3=passage', () => {
  const old = readJson('../public/reading/H31001.json');
  assert.deepEqual([1, 2, 3].map((part) => partKind(old, { part })), ['match', 'wordbank', 'passage']);
  const r4 = fixture('S30-4-reading.json');
  assert.deepEqual([1, 2, 3].map((part) => partKind(r4, { part })), ['wordbank', 'passage', 'cloze']);
  assert.equal(partKind(null, { part: 9 }), 'passage');
});

test('부분 칩은 데이터의 parts에서 나온다', () => {
  assert.deepEqual(partChips(null), ['전체']);
  assert.deepEqual(partChips(readJson('../public/listening/H31001.json')), ['전체', 1, 2, 3, 4]);
  assert.deepEqual(partChips(fixture('S30-4-listening.json')), ['전체', 1, 2]);
  assert.deepEqual(partChips(fixture('S30-3-reading.json')), ['전체', 1, 2, 3]);
});

test('묶음 배지와 «모르겠음» 글자', () => {
  assert.equal(groupLabel('29-30'), '29~30번 같은 글');
  assert.equal(groupLabel(null), '');
  assert.equal(nextLetter(['A', 'B', 'C']), 'D');
  assert.equal(nextLetter(['A', 'B', 'C', 'D']), 'E');
});

test('fixture가 데이터 계약을 따른다(조립 결과도 같은 모양이어야 한다)', () => {
  const l3 = fixture('S30-3-listening.json');
  assert.equal(l3.audio, 'S30-3.mp3');
  assert.ok(l3.items.every((item) => typeof item.start === 'number' && typeof item.end === 'number' && item.script.length));
  assert.ok(l3.items.filter((item) => item.group).every((item) => /^\d+-\d+$/.test(item.group)));
  const r4 = fixture('S30-4-reading.json');
  const cloze = r4.items.filter((item) => partKind(r4, item) === 'cloze');
  for (const item of cloze) {
    const slots = item.lines.flatMap((line) => line.words).filter((word) => /^slot:\d+$/.test(word[2] ?? ''));
    assert.ok(slots.some((word) => word[2] === `slot:${item.no}`), `${item.no} 빈칸`);
    assert.ok(r4.groups.some((group) => group.id === item.group), `${item.no} 보기 묶음`);
  }
});

test('clozeKoVisible: 남은 빈칸이 있는 줄은 해석을 숨긴다', () => {
  const line = [['（', '', ''], ['', '', 'slot:59']];
  assert.equal(clozeKoVisible(line, { 58: [] }), false);
  assert.equal(clozeKoVisible(line, { 58: [], 59: [['x', 'x']] }), true);
  assert.equal(clozeKoVisible([['你', 'nǐ']], {}), true);
});
