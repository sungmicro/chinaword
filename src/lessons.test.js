import test from 'node:test';
import assert from 'node:assert/strict';
import vocab from './data/vocab.json' with { type: 'json' };
import { STUDY_GROUP_OPTIONS, matchesStudyGroup, normalizeStudyGroup } from './lessons.js';

test('그룹은 명시된 단원만 포함하며 실제 데이터 합계와 일치한다', () => {
  assert.deepEqual(STUDY_GROUP_OPTIONS, ['전체', 'HSK1&2', 'HSK3', '교재1']);
  // 2026-11-02: 듣기·독해 단어 보정(tools/vocab_fixes.json)으로 붙은 토큰(很多·一斤 등)을 나눠 다른 단원과 겹친 50개가 빠졌다.
  assert.equal(vocab.length, 1970);
  for (const [group, count] of [['전체', 1970], ['HSK1&2', 425], ['HSK3', 959], ['교재1', 586]]) {
    assert.equal(vocab.filter((item) => matchesStudyGroup(item, group)).length, count);
  }
  assert.equal(matchesStudyGroup({ lesson: 'Lesson 8' }, '교재1'), true);
  assert.equal(matchesStudyGroup({ lesson: 'Lesson 9' }, '교재1'), false);
  assert.equal(matchesStudyGroup({ lesson: '미지정' }, '교재1'), false);
  assert.equal(matchesStudyGroup({ lesson: '미지정' }, '전체'), true);
  assert.equal(matchesStudyGroup({ lesson: 'HSK1 150' }, '잘못된 그룹'), false);
  assert.equal(matchesStudyGroup({ lesson: 'HSK1 150' }, null), false);
  assert.equal(STUDY_GROUP_OPTIONS.slice(1).filter((group) => matchesStudyGroup({ lesson: 'HSK2 공식문제' }, group)).length, 1);
});

test('저장된 잘못된 그룹은 전체로 정규화한다', () => {
  assert.equal(normalizeStudyGroup('HSK3'), 'HSK3');
  assert.equal(normalizeStudyGroup('Lesson 9'), '전체');
  assert.equal(normalizeStudyGroup(null), '전체');
});
