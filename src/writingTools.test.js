import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { WRITING_PART_CHIPS, gradeOrder, restoreWritingPrefs, selectedText, tokensOf, toggleToken, validSelection, writingCounts, writingExams, writingItemsOf } from './writingTools.js';
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
test('쓰기는 회차별로, 1부분 어순·2부분 한자로 나뉜다', () => {
  const exams = writingExams(items);
  assert.equal(exams.length, 19);
  assert.equal(exams[0], 'H31001');
  for (const exam of exams) {
    assert.deepEqual(writingItemsOf(items, exam, 1).map((x) => x.no), [71, 72, 73, 74, 75]);
    assert.deepEqual(writingItemsOf(items, exam, 2).map((x) => x.no), [76, 77, 78, 79, 80]);
    assert.deepEqual(writingItemsOf(items, exam, '전체').map((x) => x.no), [71, 72, 73, 74, 75, 76, 77, 78, 79, 80]);
    assert.ok(writingItemsOf(items, exam, 1).every((x) => x.kind === 'reorder'));
    assert.ok(writingItemsOf(items, exam, 2).every((x) => x.kind === 'hanzi'));
  }
  assert.deepEqual(WRITING_PART_CHIPS, ['전체', 1, 2]);
});
test('저장된 쓰기 설정 복원: 새 형식은 그대로, 예전 연속 번호는 회차·부분·번호로 바꾼다', () => {
  assert.deepEqual(restoreWritingPrefs({ testId: 'H31005', part: 2, positions: { H31005: 78 } }, items),
    { testId: 'H31005', part: 2, positions: { H31005: 78 } });
  // 예전 index 17 = 2회차(H31002)의 78번(한자)
  assert.deepEqual(restoreWritingPrefs({ index: 17 }, items), { testId: 'H31002', part: 2, positions: { H31002: 78 } });
  assert.deepEqual(restoreWritingPrefs({ index: 999 }, items), { testId: 'H31001', part: 1, positions: {} });
  assert.deepEqual(restoreWritingPrefs(null, items), { testId: 'H31001', part: 1, positions: {} });
  assert.deepEqual(restoreWritingPrefs({ testId: 'NOPE', part: 3 }, items), { testId: 'H31001', part: 1, positions: {} });
  assert.equal(restoreWritingPrefs({ testId: 'H31001', part: 7 }, items).part, 1);
});

test('3.0 쓰기: part가 적힌 문항은 그 부분, 부분 칩·안내는 데이터에서 나온다', async () => {
  const { WRITING_KIND_GUIDES, countEssayChars, restoreTabWritingPrefs, usesWord, writingPart, writingPartChips, writingPartGuide } = await import('./writingTools.js');
  const w3 = JSON.parse(fs.readFileSync(new URL('./__fixtures__/S30-3-writing.json', import.meta.url))).items;
  const w4 = JSON.parse(fs.readFileSync(new URL('./__fixtures__/S30-4-writing.json', import.meta.url))).items;
  assert.equal(writingPart(w3.find((x) => x.kind === 'hanzi')), 1);
  assert.equal(writingPart(w3.find((x) => x.kind === 'picture')), 2);
  assert.equal(writingPart(w4.find((x) => x.kind === 'picture')), 1);
  assert.equal(writingPart(w4.find((x) => x.kind === 'essay')), 2);
  // 기출(2.0)은 part 없이 형식으로 정한다(예전 그대로).
  assert.equal(writingPart(items.find((x) => x.kind === 'reorder')), 1);
  assert.equal(writingPart(items.find((x) => x.kind === 'hanzi')), 2);
  assert.deepEqual(writingPartChips(items), WRITING_PART_CHIPS);
  assert.deepEqual(writingPartChips(w4), ['전체', 1, 2]);
  assert.equal(writingPartGuide(items, 1), '문장 순서 맞추기');
  assert.equal(writingPartGuide(items, 2), '병음 보고 한자 쓰기');
  assert.equal(writingPartGuide(w3, 1), WRITING_KIND_GUIDES.hanzi);
  assert.equal(writingPartGuide(w4, 2), '짧은 글 쓰기');
  assert.equal(writingPartGuide(w4, 2, [{ part: 2, guide: '80자 이상 짧은 글' }]), '80자 이상 짧은 글');
  assert.equal(countEssayChars('我 每天\n跑步。'), 6);
  assert.equal(countEssayChars(undefined), 0);
  assert.ok(usesWord('他正在看书。', '正在'));
  assert.ok(!usesWord('他看书。', '正在'));

  const saved = { testId: 'H31005', part: 2, positions: { H31005: 78, 'S30-4': 70 }, levels: { hsk4: { testId: 'S30-4', part: 2 } } };
  assert.deepEqual(restoreTabWritingPrefs(saved, items, 'past'), { testId: 'H31005', part: 2, positions: saved.positions });
  assert.deepEqual(restoreTabWritingPrefs(saved, w4, 'hsk4'), { testId: 'S30-4', part: 2, positions: saved.positions });
  // 처음 여는 3급은 기출 설정을 가져오지 않는다.
  assert.deepEqual(restoreTabWritingPrefs(saved, w3, 'hsk3'), { testId: 'S30-3', part: 1, positions: saved.positions });
  // 예전 연속 번호(index)는 기출(2.0)에서만 쓴다.
  assert.deepEqual(restoreTabWritingPrefs({ index: 17 }, items, 'past'), { testId: 'H31002', part: 2, positions: { H31002: 78 } });
  assert.equal(restoreTabWritingPrefs({ index: 17 }, w3, 'hsk3').testId, 'S30-3');
});
