import { test } from 'node:test';
import assert from 'node:assert/strict';
import vocab from './data/vocab.json' with { type: 'json' };
import retiredCards from './data/vocab-retired.json' with { type: 'json' };
import { applyResults, migrateReview, pickQuestions, reviewCount } from './review.js';

const items = [
  { id: 'K-1', hanzi: '多' },
  { id: 'K-2', hanzi: '斤' },
  { id: 'K-3', hanzi: '门口' },
  { id: 'mine:word:多:duo', hanzi: '多' }
];
const retired = {
  'HSK3R-001': { hanzi: '很多', movedTo: '多' },
  'HSK3R-002': { hanzi: '一斤', movedTo: '斤' },
  'HSK3R-003': { hanzi: '儿' }
};

test('오답노트: 사라진 카드 id는 화면 계산에서 조용히 무시된다', () => {
  const review = { 'K-3': { streak: 0, wrong: 1 }, 'GONE-9': { streak: 0, wrong: 4 } };
  assert.equal(reviewCount(review, items), 1);
  const picked = pickQuestions(items, review, 2);
  assert.equal(picked.length, 2);
  assert.ok(picked.every((item) => items.includes(item)));
  const next = applyResults(review, [{ id: 'K-3', correct: true }]);
  assert.deepEqual(next['GONE-9'], { streak: 0, wrong: 4 }); // 건드리지도, 깨지지도 않는다
});

test('오답노트: 은퇴한 id의 기록을 이어받는 카드로 옮기고, 이미 있으면 합친다', () => {
  const review = {
    'HSK3R-001': { streak: 1, wrong: 2 },
    'HSK3R-002': { streak: 0, wrong: 1 },
    'K-2': { streak: 1, wrong: 3 },
    'HSK3R-003': { streak: 0, wrong: 1 },
    'K-3': { streak: 0, wrong: 1 }
  };
  const { review: next, changed } = migrateReview(review, items, retired);
  assert.equal(changed, true);
  assert.deepEqual(next, {
    'K-1': { streak: 1, wrong: 2 }, // 很多 → 多 (내 단어장 카드가 아니라 단어장 카드로)
    'K-2': { streak: 0, wrong: 4 }, // 一斤 → 斤, 기존 기록과 합침
    'HSK3R-003': { streak: 0, wrong: 1 }, // 이어받을 카드가 없으면 그대로(무시됨)
    'K-3': { streak: 0, wrong: 1 }
  });
  assert.equal(migrateReview(next, items, retired).changed, false); // 두 번 돌려도 같다
});

test('카드 id 장부: 은퇴 id는 지금 단어장에 없고, 옮길 한자는 단어장에 있다', () => {
  const ids = new Set(vocab.map((item) => item.id));
  const hanzi = new Set(vocab.map((item) => item.hanzi));
  assert.equal(ids.size, vocab.length); // id 중복 없음
  for (const [id, entry] of Object.entries(retiredCards.retired)) {
    assert.equal(ids.has(id), false, id);
    if (entry.movedTo) assert.equal(hanzi.has(entry.movedTo), true, id);
  }
  for (const [prefix, last] of Object.entries(retiredCards.lastNo)) {
    const used = [...ids].filter((id) => id.startsWith(`${prefix}-`)).map((id) => Number(id.split('-')[1]));
    assert.ok(Math.max(...used) <= last, prefix);
  }
});
