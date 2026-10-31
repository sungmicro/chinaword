import test from 'node:test';
import assert from 'node:assert/strict';
import { shuffleVocab } from './vocabOrder.js';

test('같은 목록과 seed는 안정적인 순서이고 seed가 바뀌면 다시 섞인다', () => {
  const items = Array.from({ length: 30 }, (_, id) => ({ id }));
  assert.deepEqual(shuffleVocab(items, 1), shuffleVocab(items, 1));
  assert.notDeepEqual(shuffleVocab(items, 1), shuffleVocab(items, 2));
});

test('원소와 참조를 중복 없이 보존하고 원본 배열을 바꾸지 않는다', () => {
  const items = Object.freeze(Array.from({ length: 30 }, (_, id) => Object.freeze({ id })));
  const before = [...items];
  const shuffled = shuffleVocab(items, 42);
  assert.deepEqual(items, before);
  assert.notEqual(shuffled, items);
  assert.equal(new Set(shuffled).size, items.length);
  assert.deepEqual([...shuffled].sort((a, b) => a.id - b.id), before);
});

test('빈 목록과 한 항목, 필터된 부분 목록도 안전하게 처리한다', () => {
  assert.deepEqual(shuffleVocab([], 0), []);
  const item = { id: 1 };
  assert.deepEqual(shuffleVocab([item], 0), [item]);
  const filtered = [{ id: 3 }, { id: 7 }, { id: 9 }];
  assert.deepEqual(new Set(shuffleVocab(filtered, 123)), new Set(filtered));
});
