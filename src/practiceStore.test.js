import { test } from 'node:test';
import assert from 'node:assert/strict';
import { UNKNOWN, fetchCached, gradeOf, readJson, tally, writeJson } from './practiceStore.js';

function memoryStorage(initial = {}) {
  const data = { ...initial };
  return {
    getItem: (key) => (key in data ? data[key] : null),
    setItem: (key, value) => {
      data[key] = String(value);
    },
    data
  };
}

function useStorage(storage) {
  Object.defineProperty(globalThis, 'localStorage', { value: storage, configurable: true, writable: true });
}

test('gradeOf: 안 고름·모름·맞힘·틀림', () => {
  const item = { no: 1, answer: 'B' };
  assert.equal(gradeOf(item, undefined), null);
  assert.equal(gradeOf(item, UNKNOWN), 'unknown');
  assert.equal(gradeOf(item, 'B'), 'right');
  assert.equal(gradeOf(item, 'C'), 'wrong');
});

test('tally는 고른 문항만 센다', () => {
  const items = [{ no: 1, answer: 'A' }, { no: 2, answer: 'B' }, { no: 3, answer: 'C' }, { no: 4, answer: 'D' }];
  assert.deepEqual(tally(items, { 1: 'A', 2: 'C', 3: '?' }), { right: 1, wrong: 1, unknown: 1 });
});

test('readJson: 깨진 값·없는 키·저장소 없음이면 기본값', () => {
  useStorage(memoryStorage({ broken: '{not json', ok: '{"a":1}' }));
  assert.deepEqual(readJson('ok', {}), { a: 1 });
  assert.deepEqual(readJson('broken', { fallback: true }), { fallback: true });
  assert.deepEqual(readJson('missing', {}), {});
  useStorage(undefined);
  assert.deepEqual(readJson('anything', { a: 1 }), { a: 1 });
});

test('writeJson: 저장 실패를 삼킨다', () => {
  useStorage({ getItem: () => null, setItem: () => { throw new Error('full'); } });
  assert.doesNotThrow(() => writeJson('k', { a: 1 }));
  useStorage(undefined);
  assert.doesNotThrow(() => writeJson('k', { a: 1 }));
});

test('fetchCached: 같은 주소는 한 번만 받고, 실패하면 다음에 다시 받는다', async () => {
  let calls = 0;
  let fail = true;
  globalThis.fetch = async (url) => {
    calls += 1;
    if (fail) return { ok: false, status: 503 };
    return { ok: true, json: async () => ({ url }) };
  };
  await assert.rejects(fetchCached('/reading/T1.json', 'T1'), /T1 데이터를 불러오지 못했어요 \(503\)/);
  fail = false;
  const first = await fetchCached('/reading/T1.json', 'T1');
  const second = await fetchCached('/reading/T1.json', 'T1');
  assert.deepEqual(first, { url: '/reading/T1.json' });
  assert.equal(second, first);
  assert.equal(calls, 2);
});
