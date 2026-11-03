// 단원 이름 다루기. 단어장과 랜덤 학습이 같이 씁니다.

export const STUDY_GROUPS = {
  'HSK1&2': ['HSK1 150', 'HSK2 추가 150', 'HSK2 공식문제'],
  HSK3: ['HSK3 추가 300', 'HSK3 듣기', 'HSK3 독해'],
  교재1: Array.from({ length: 8 }, (_, index) => `Lesson ${index + 1}`)
};
export const STUDY_GROUP_OPTIONS = ['전체', 'HSK1&2', 'HSK3', '교재1'];

export function normalizeStudyGroup(group) {
  return STUDY_GROUP_OPTIONS.includes(group) ? group : '전체';
}

export function matchesStudyGroup(item, group) {
  return group === '전체' || (STUDY_GROUPS[group]?.includes(item.lesson) ?? false);
}

// 교재 항목은 몇 과인지 목록에서 바로 보이게 합니다 (칩이 묶여서 과 구분이 사라졌으므로).
export function lessonBadge(lesson) {
  const match = /^Lesson\s+(\d+)$/.exec(String(lesson ?? ''));
  return match ? `${match[1]}과` : '';
}
