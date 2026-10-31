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
