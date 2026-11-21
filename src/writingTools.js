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

// 기출(2.0) 쓰기 1부분(71~75번)은 어순 배열, 2부분(76~80번)은 병음 보고 한자 쓰기입니다.
// 3.0 공식 샘플은 문항에 part가 적혀 있습니다(3급: 1부분 한자·2부분 사진 문장, 4급: 1부분 사진 문장·2부분 짧은 글).
export const WRITING_PART_CHIPS = ['전체', 1, 2];
export const WRITING_PART_GUIDES = { 1: '문장 순서 맞추기', 2: '병음 보고 한자 쓰기' };
export const WRITING_KIND_GUIDES = {
  reorder: '문장 순서 맞추기',
  hanzi: '병음 보고 한자 쓰기',
  picture: '사진 보고 문장 쓰기',
  essay: '짧은 글 쓰기'
};
export const WRITING_KIND_TITLES = {
  reorder: '어순 배열',
  hanzi: '병음 보고 한자 떠올리기',
  picture: '사진 보고 문장 쓰기',
  essay: '짧은 글 쓰기'
};

export function writingPart(item) {
  if (Number.isInteger(item.part)) return item.part;
  return item.kind === 'reorder' ? 1 : 2;
}

// 부분 칩: 받은 문항에 있는 부분만, 번호 순서대로.
export function writingPartChips(items) {
  return ['전체', ...[...new Set(items.map(writingPart))].sort((a, b) => a - b)];
}

// 부분 안내: 데이터에 parts[{ part, guide }]가 있으면 그것을, 없으면 그 부분 첫 문항의 형식으로 정합니다.
export function writingPartGuide(items, part, parts = []) {
  const given = parts.find((entry) => entry.part === part)?.guide;
  if (given) return given;
  const first = items.find((item) => writingPart(item) === part);
  return first ? WRITING_KIND_GUIDES[first.kind] ?? '' : '';
}

// 짧은 글 글자 수: 원고지처럼 문장부호도 한 칸으로 세고, 띄어쓰기·줄바꿈은 세지 않습니다.
export function countEssayChars(text) {
  return [...String(text ?? '').replace(/\s/gu, '')].length;
}

// 사진 문장: 제시어를 문장에 넣었는지.
export function usesWord(text, word) {
  return Boolean(word) && String(text ?? '').includes(word);
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
  const chips = writingPartChips(items);
  const firstPart = chips[1] ?? 1;
  const prefs = saved && typeof saved === 'object' ? saved : {};
  const positions = prefs.positions && typeof prefs.positions === 'object' ? { ...prefs.positions } : {};
  if (exams.includes(prefs.testId)) {
    return { testId: prefs.testId, part: chips.includes(prefs.part) ? prefs.part : firstPart, positions };
  }
  const legacy = Number.isInteger(prefs.index) ? items[prefs.index] : undefined;
  if (legacy) {
    return { testId: legacy.exam, part: writingPart(legacy), positions: { ...positions, [legacy.exam]: legacy.no } };
  }
  return { testId: exams[0], part: firstPart, positions };
}

// 탭(3급·4급·기출(2.0))마다 따로 저장한 쓰기 설정을 꺼냅니다. 저장 모양은 듣기·독해와 같아서
// { testId, part, positions, levels: { hsk3: { testId, part }, … } }이고, 맨 위 testId·part(와 예전 index)는 기출(2.0) 값입니다.
export function restoreTabWritingPrefs(saved, items, tab) {
  const prefs = saved && typeof saved === 'object' ? saved : {};
  const level = prefs.levels && typeof prefs.levels === 'object' ? prefs.levels[tab] : undefined;
  if (level && typeof level === 'object') return restoreWritingPrefs({ ...level, positions: prefs.positions }, items);
  return restoreWritingPrefs(tab === 'past' ? prefs : { positions: prefs.positions }, items);
}
