// 단원 이름 다루기. 단어장과 시험 탭이 같이 씁니다.

// 교재 과(Lesson N)는 번호로 자동 정렬하므로, 여기엔 HSK 계열만 순서대로 적습니다.
export const LESSON_ORDER = ['HSK1 150', 'HSK2 추가 150', 'HSK2 공식문제', 'HSK3 추가 300', 'HSK3 듣기'];

export function lessonSortKey(lesson) {
  const index = LESSON_ORDER.indexOf(lesson);
  if (index >= 0) return index;

  // 교재 과는 HSK 뒤에 번호 순으로 놓습니다. 새 과가 들어와도 손댈 곳이 없습니다.
  const match = /^Lesson\s+(\d+)$/.exec(String(lesson ?? ''));
  if (match) return LESSON_ORDER.length + Number(match[1]);

  return Number.MAX_SAFE_INTEGER;
}

// 교재 과가 늘어날수록 필터 칩이 화면을 다 먹어서, 네 과씩 한 칩으로 묶습니다.
// (Lesson 9가 들어오면 자동으로 "Lesson 9-12" 칩이 생깁니다.)
const LESSONS_PER_CHIP = 4;

export function lessonChipLabel(lesson) {
  const match = /^Lesson\s+(\d+)$/.exec(String(lesson ?? ''));
  if (!match) return lesson; // HSK 계열은 원래 이름 그대로
  const number = Number(match[1]);
  const start = Math.floor((number - 1) / LESSONS_PER_CHIP) * LESSONS_PER_CHIP + 1;
  return `Lesson ${start}-${start + LESSONS_PER_CHIP - 1}`;
}

// 교재 항목은 몇 과인지 목록에서 바로 보이게 합니다 (칩이 묶여서 과 구분이 사라졌으므로).
export function lessonBadge(lesson) {
  const match = /^Lesson\s+(\d+)$/.exec(String(lesson ?? ''));
  return match ? `${match[1]}과` : '';
}

// 항목 목록에서 필터 칩 목록을 만듭니다.
export function buildLessonChips(items) {
  const unique = [...new Set(items.map((item) => item.lesson).filter(Boolean))];
  unique.sort((a, b) => lessonSortKey(a) - lessonSortKey(b));

  const chips = [];
  unique.forEach((name) => {
    const label = lessonChipLabel(name);
    if (!chips.includes(label)) chips.push(label);
  });

  return ['전체', ...chips];
}

export function matchesLessonChip(item, chip) {
  return chip === '전체' || lessonChipLabel(item.lesson) === chip;
}
