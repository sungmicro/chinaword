import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { basicTerms, glossary, learningPoints, roleTerm } from './writingGrammarHelp.js';
const items = JSON.parse(fs.readFileSync(new URL('../public/writing/hsk3-all.json', import.meta.url))).items.filter((item) => item.kind === 'reorder');
test('역할 16종은 품사와 문장 성분을 구별하는 쉬운 용어 정의에 연결한다', () => {
  assert.equal(Object.keys(glossary.roleTerms).length, 16);
  for (const role of Object.keys(glossary.roleTerms)) {
    assert.ok(roleTerm(role).definition);
    assert.ok(roleTerm(role).question);
  }
  assert.equal(roleTerm('subject').category, '문장 성분');
  assert.equal(roleTerm('preposition').category, '품사');
  assert.equal(roleTerm('verb').category, '품사');
});
test('공개 전 도움말은 용어 정본만 반환하며 현재 문장이나 역할 배정을 노출하지 않는다', () => {
  for (const item of items) {
    const terms = basicTerms(item);
    assert.ok(terms.length);
    terms.forEach(({ id, ...term }) => assert.deepEqual(term, glossary.terms[id]));
    // 개별 문장 풀이를 바꾸어도 공개 전 기초 내용은 동일하다.
    const changed = structuredClone(item);
    for (const a of changed.grammar.analyses) if (a.learning) a.learning.points = [{ explanation: 'SECRET', parts: [] }];
    assert.deepEqual(basicTerms(changed), terms);
  }
});
test('98개 문장별 설명은 정본 용법과 실제 문자 범위에 연결된다', () => {
  let count = 0;
  for (const item of items) for (const analysis of item.grammar.analyses) {
    if (!analysis.learning) continue;
    count++;
    for (const point of learningPoints(item, analysis)) {
      assert.ok(point.text);
      assert.ok(point.explanation);
      assert.ok(!/[\u4e00-\u9fff]/.test(point.hanzi) || point.pinyin);
      assert.ok(point.forms.includes(point.text), `${item.id}: ${point.usageId} ${point.text}`);
    }
  }
  assert.equal(count, 98);
});
test('단어 내부 글자와 실제 기능어를 혼동하지 않는다', () => {
  for (const item of items) for (const analysis of item.grammar.analyses) for (const point of learningPoints(item, analysis)) {
    if (point.usageId.startsWith('zai-')) assert.ok(!point.text.includes('现在'), item.id);
    if (point.usageId === 'bi-comparison') assert.ok(!point.text.includes('比较'), item.id);
    if (point.usageId === 'result-complement') assert.ok(!point.text.includes('不到'), item.id);
    if (point.usageId === 'de-complement') assert.ok(!point.text.includes('觉得'), item.id);
  }
  const last = items.find((x) => x.id === 'H31332-75').grammar.analyses[0];
  assert.ok(last.learning.points.some((p) => p.usageId === 'le-disposal-plan'));
  assert.ok(items.find((x) => x.id === 'H31332-73').grammar.analyses[0].learning.points.some((p) => p.usageId === 'shi-de-assertion'));
});
