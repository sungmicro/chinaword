import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { groupText, tokenRoles, grammarIsVisible } from './writingGrammar.js';
import { normalizeAnswer } from './writingTools.js';
const items = JSON.parse(fs.readFileSync(new URL('../public/writing/hsk3-all.json', import.meta.url))).items;
test('95개 문항의 98개 분석을 실제 문자 범위에서 재구성한다', () => {
  let count = 0;
  for (const item of items.filter((x) => x.kind === 'reorder')) {
    for (const analysis of item.grammar.analyses) {
      count++;
      assert.equal(normalizeAnswer(analysis.groups.map((g) => groupText(item, g)).join('')), normalizeAnswer(item.answers[analysis.answerIndex]));
      tokenRoles(item, analysis).forEach((token) => assert.equal(token.roles.map((r) => r.text).join(''), token.text));
    }
  }
  assert.equal(count, 98);
});
test('답 공개 상태에서만 해설을 표시하고 다시 풀기 상태와 한자에서는 숨긴다', () => {
  const reorder = items[0];
  for (const status of ['right', 'wrong', 'unknown', 'revealed']) assert.equal(grammarIsVisible(reorder, status), true);
  for (const status of [undefined, '', 'pending']) assert.equal(grammarIsVisible(reorder, status), false);
  assert.equal(grammarIsVisible(items.find((x) => x.kind === 'hanzi'), 'revealed'), false);
  const saved = JSON.parse(JSON.stringify({ status: 'unknown' }));
  assert.equal(grammarIsVisible(reorder, saved.status), true);
  assert.equal(grammarIsVisible(reorder, {}.status), false);
});
test('같은 제시 토큰의 서로 다른 역할을 모두 보존한다', () => {
  const item = items[0];
  assert.deepEqual(tokenRoles(item, item.grammar.analyses[0])[2].roles.map((x) => x.text), ['高兴', '地']);
});
