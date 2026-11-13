import test from 'node:test';
import assert from 'node:assert/strict';
import vocab from './data/vocab.json' with { type: 'json' };
import { STUDY_GROUP_OPTIONS, lessonBadge, matchesStudyGroup, normalizeStudyGroup } from './lessons.js';

test('그룹은 명시된 단원만 포함하며 실제 데이터 합계와 일치한다', () => {
  assert.deepEqual(STUDY_GROUP_OPTIONS, ['전체', 'HSK1', 'HSK2', 'HSK3', 'HSK4', 'HSK5', '기출', '교재1']);
  // 2026-11-02: 듣기·독해 단어 보정(tools/vocab_fixes.json)으로 붙은 토큰(很多·一斤 등)을 나눠 다른 단원과 겹친 50개가 빠졌다.
  // 2026-11-03: 이름+호칭 묶음(李先生·小马 등)을 성씨와 호칭으로 나누고, 듣기 대본 인식 오류에서 나온 단어(散·占·原·院 등)를
  // 대본을 고치며 뺐다. 사라진 카드 26개는 은퇴(src/data/vocab-retired.json), 새 카드는 刘·选 2개.
  // 2026-11-11: HSK 3.0 4급 새 단어 929개를 «HSK4 (3.0)» 단원으로 넣었다(tools/hsk30/build_level4.py).
  // 2026-11-13: HSK 단원을 HSK 3.0 공식 대강(1~4급 2,000 + 선택 5급 500, 같은 급수 동형어 2쌍 합침)으로 바꾸고 HSK2 공식문제를 뺐다. 대강과 겹친 듣기 87·독해 84개는 빠지고 예전 HSK에만 있던 듣기 단어 24개가 들어왔다(tools/hsk_outline/build_outline.py).
  assert.equal(vocab.length, 3572);
  for (const [group, count] of [['전체', 3572], ['HSK1', 300], ['HSK2', 199], ['HSK3', 500], ['HSK4', 999], ['HSK5', 500], ['기출', 488], ['교재1', 586]]) {
    assert.equal(vocab.filter((item) => matchesStudyGroup(item, group)).length, count);
  }
  assert.equal(matchesStudyGroup({ lesson: 'Lesson 8' }, '교재1'), true);
  assert.equal(matchesStudyGroup({ lesson: 'Lesson 9' }, '교재1'), false);
  assert.equal(matchesStudyGroup({ lesson: '미지정' }, '교재1'), false);
  assert.equal(matchesStudyGroup({ lesson: '미지정' }, '전체'), true);
  assert.equal(matchesStudyGroup({ lesson: 'HSK1 150' }, '잘못된 그룹'), false);
  assert.equal(matchesStudyGroup({ lesson: 'HSK1 150' }, null), false);
  assert.equal(STUDY_GROUP_OPTIONS.slice(1).filter((group) => matchesStudyGroup({ lesson: 'HSK3 듣기' }, group)).length, 1);
});

test('저장된 잘못된 그룹은 전체로 정규화한다', () => {
  assert.equal(normalizeStudyGroup('HSK3'), 'HSK3');
  assert.equal(normalizeStudyGroup('Lesson 9'), '전체');
  assert.equal(normalizeStudyGroup(null), '전체');
});

test('대강 단원과 교재 단원은 배지가 붙고 나머지는 비어 있다', () => {
  assert.equal(lessonBadge('HSK 3.0 4급'), '4급');
  assert.equal(lessonBadge('Lesson 3'), '3과');
  assert.equal(lessonBadge('HSK3 듣기'), '');
});
