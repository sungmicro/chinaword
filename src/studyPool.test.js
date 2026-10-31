import test from 'node:test';
import assert from 'node:assert/strict';
import { randomIndex, selectStudyPool } from './studyPool.js';

const items = [{ lesson: 'HSK1 150' }, { lesson: 'HSK3 독해' }, { lesson: 'Lesson 8' }, { lesson: 'Lesson 9' }];
const mine = [{ lesson: '내 단어장' }];

test('내 단어장 우선 및 빈 목록일 때 그룹 복귀', () => {
  assert.equal(selectStudyPool(items, mine, 'HSK3', true), mine);
  assert.deepEqual(selectStudyPool(items, [], 'HSK3', true), [items[1]]);
  assert.deepEqual(selectStudyPool(items, mine, '교재1', false), [items[2]]);
  assert.deepEqual(selectStudyPool(items, mine, '전체', false), items);
});

test('랜덤 인덱스는 범위 안이고 이전 인덱스를 피한다', () => {
  assert.equal(randomIndex(0), 0);
  assert.equal(randomIndex(1, 0), 0);
  for (let length = 2; length <= 10; length++) {
    for (let previous = 0; previous < length; previous++) {
      for (let trial = 0; trial < 30; trial++) {
        const next = randomIndex(length, previous);
        assert.ok(next >= 0 && next < length);
        assert.notEqual(next, previous);
      }
    }
  }
});
