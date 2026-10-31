import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { gradeOrder, selectedText, tokensOf, toggleToken, validSelection, writingCounts } from './writingTools.js';
const items = JSON.parse(fs.readFileSync(new URL('../public/writing/hsk3-all.json', import.meta.url))).items;

test('동일 텍스트 토큰은 따로 선택하고 중간 해제 시 순서가 즉시 재정렬된다', () => {
  const item = { id: 'repeat', tokens: ['的', '我', '的'] };
  const tokens = tokensOf(item);
  let selected = [];
  for (const token of tokens) selected = toggleToken(selected, token.id);
  selected = toggleToken(selected, tokens[1].id);
  assert.deepEqual(selected, [tokens[0].id, tokens[2].id]);
  assert.equal(selected.indexOf(tokens[2].id) + 1, 2);
  assert.equal(selectedText(item, selected), '的的');
});
test('공식 복수 정답을 모두 채점하고 누락·중복·다른 순서는 거부한다', () => {
  const item = items.find((x) => x.id === 'H31004-75');
  const tokens = tokensOf(item);
  for (const answer of item.answers) {
    function order(prefix, remaining) {
      if (!remaining.length) return gradeOrder(item, prefix) && selectedText(item, prefix) === answer.replace(/[。？]/g, '') ? prefix : null;
      for (const t of remaining) { const found = order([...prefix, t.id], remaining.filter((v) => v !== t)); if (found) return found; }
      return null;
    }
    assert.ok(order([], tokens), answer);
  }
  assert.equal(gradeOrder(item, []), false);
  assert.equal(gradeOrder(item, tokens.map(() => tokens[0].id)), false);
  assert.equal(gradeOrder(item, tokens.map((t) => t.id)), false);
});
test('학습 기록은 한자 답 확인을 맞힘으로 세지 않는다', () => {
  const records = { [items[0].id]: { status: 'right' }, [items[5].id]: { status: 'revealed' }, [items[6].id]: { status: 'unknown' } };
  assert.deepEqual(writingCounts(items, records), { right: 1, wrong: 0, unknown: 1, revealed: 1 });
  assert.deepEqual(validSelection(items[0], ['bad', tokensOf(items[0])[0].id, tokensOf(items[0])[0].id]), [tokensOf(items[0])[0].id]);
});
test('190문항·학습 override·중복 및 한자 최소 표시 데이터 보존', () => {
  assert.equal(items.length, 190);
  assert.equal(new Set(items.map((x) => x.id)).size, 190);
  assert.deepEqual(items.map((x) => x.seq), Array.from({ length: 190 }, (_, i) => i + 1));
  assert.deepEqual(items.find((x) => x.id === 'H31007-72').answers, ['他的姓名被写错了。']);
  assert.deepEqual(items.find((x) => x.id === 'H31007-77').answers, ['元', '圆']);
  for (const item of items.filter((x) => x.kind === 'hanzi')) {
    assert.equal(item.sentence.split('___').length, 2);
    assert.ok(!/^[．，、]/.test(item.sentence));
    assert.equal(item.tokens, undefined);
  }
});
