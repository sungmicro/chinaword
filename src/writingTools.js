// 토큰은 텍스트가 같아도 각 위치의 id로 구별합니다.
export function tokensOf(item) {
  return (item.tokens ?? []).map((text, index) => ({ id: `${item.id}-t${index}`, text }));
}
export function toggleToken(selected, tokenId) {
  return selected.includes(tokenId) ? selected.filter((id) => id !== tokenId) : [...selected, tokenId];
}
export function selectedText(item, selected) {
  const tokens = new Map(tokensOf(item).map((token) => [token.id, token.text]));
  return selected.map((id) => tokens.get(id) ?? '').join('');
}
export function normalizeAnswer(text) {
  return text.replace(/[\s。，、！？,.!?]/gu, '');
}
export function gradeOrder(item, selected) {
  if (selected.length !== item.tokens.length || new Set(selected).size !== selected.length) return false;
  const validIds = new Set(tokensOf(item).map((token) => token.id));
  if (selected.some((id) => !validIds.has(id))) return false;
  return item.answers.some((answer) => normalizeAnswer(answer) === normalizeAnswer(selectedText(item, selected)));
}
export function writingCounts(items, records) {
  return items.reduce((counts, item) => {
    const status = records[item.id]?.status;
    if (Object.hasOwn(counts, status)) counts[status] += 1;
    return counts;
  }, { right: 0, wrong: 0, unknown: 0, revealed: 0 });
}
export function validSelection(item, selected) {
  if (!Array.isArray(selected)) return [];
  const ids = new Set(tokensOf(item).map((token) => token.id));
  return [...new Set(selected)].filter((id) => ids.has(id));
}

// 쓰기 1부분(71~75번)은 어순 배열, 2부분(76~80번)은 병음 보고 한자 쓰기입니다.
export const WRITING_PART_CHIPS = ['전체', 1, 2];
export const WRITING_PART_GUIDES = { 1: '문장 순서 맞추기', 2: '병음 보고 한자 쓰기' };

export function writingPart(item) {
  return item.kind === 'reorder' ? 1 : 2;
}

// 회차는 데이터에 나온 순서대로(생성기 EXAMS 순서) 한 번씩.
export function writingExams(items) {
  return [...new Set(items.map((item) => item.exam))];
}

export function writingItemsOf(items, testId, part) {
  return items.filter((item) => item.exam === testId && (part === '전체' || writingPart(item) === part));
}

// 저장된 설정을 지금 데이터에 맞춥니다. 예전 화면은 190문항 연속 번호 위치({ index })만 저장했으므로,
// 그 문항의 회차·부분·번호로 바꿔 이어서 풀게 합니다.
export function restoreWritingPrefs(saved, items) {
  const exams = writingExams(items);
  const prefs = saved && typeof saved === 'object' ? saved : {};
  const positions = prefs.positions && typeof prefs.positions === 'object' ? { ...prefs.positions } : {};
  if (exams.includes(prefs.testId)) {
    return { testId: prefs.testId, part: WRITING_PART_CHIPS.includes(prefs.part) ? prefs.part : 1, positions };
  }
  const legacy = Number.isInteger(prefs.index) ? items[prefs.index] : undefined;
  if (legacy) {
    return { testId: legacy.exam, part: writingPart(legacy), positions: { ...positions, [legacy.exam]: legacy.no } };
  }
  return { testId: exams[0], part: 1, positions };
}
