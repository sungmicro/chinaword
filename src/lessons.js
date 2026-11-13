// 단원 이름 다루기. 단어장과 랜덤 학습이 같이 씁니다.

// HSK1~HSK5는 HSK 3.0 공식 대강 단원(tools/hsk_outline/build_outline.py, 5급은 성미님이 고른 500개).
// 기출은 HSK3 모의고사 듣기·독해 해설에서 나온 단어 중 다른 단원에 없는 것.
export const STUDY_GROUPS = {
  HSK1: ['HSK 3.0 1급'],
  HSK2: ['HSK 3.0 2급'],
  HSK3: ['HSK 3.0 3급'],
  HSK4: ['HSK 3.0 4급'],
  HSK5: ['HSK 3.0 5급(선택)'],
  기출: ['HSK3 듣기', 'HSK3 독해'],
  교재1: Array.from({ length: 8 }, (_, index) => `Lesson ${index + 1}`)
};
export const STUDY_GROUP_OPTIONS = ['전체', 'HSK1', 'HSK2', 'HSK3', 'HSK4', 'HSK5', '기출', '교재1'];

export function normalizeStudyGroup(group) {
  return STUDY_GROUP_OPTIONS.includes(group) ? group : '전체';
}

export function matchesStudyGroup(item, group) {
  return group === '전체' || (STUDY_GROUPS[group]?.includes(item.lesson) ?? false);
}

// 교재 항목은 몇 과인지 목록에서 바로 보이게 합니다 (칩이 묶여서 과 구분이 사라졌으므로).
export function lessonBadge(lesson) {
  const outline = /^HSK 3\.0 (\d)급/.exec(String(lesson ?? ''));
  if (outline) return `${outline[1]}급`;
  const match = /^Lesson\s+(\d+)$/.exec(String(lesson ?? ''));
  return match ? `${match[1]}과` : '';
}
