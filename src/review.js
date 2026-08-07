// 오답노트. 틀린 항목을 기기에 저장해뒀다가 다음 시험에 먼저 냅니다.
// 연속 GRADUATE_STREAK번 맞히면 목록에서 빠집니다.

const STORAGE_KEY = 'sungmi-vocab-review-v1';
const GRADUATE_STREAK = 2;

export function loadReview() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    const parsed = saved ? JSON.parse(saved) : {};
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function saveReview(review) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(review));
  } catch {
    // 저장 실패는 학습을 막을 이유가 없으므로 무시합니다.
  }
}

// 채점 결과를 반영한 새 오답노트를 돌려줍니다.
export function applyResults(review, results) {
  const next = { ...review };

  results.forEach(({ id, correct }) => {
    const entry = next[id];

    if (!correct) {
      next[id] = { streak: 0, wrong: (entry?.wrong ?? 0) + 1 };
      return;
    }

    if (!entry) return; // 오답노트에 없던 걸 맞힌 건 기록하지 않습니다.

    const streak = (entry.streak ?? 0) + 1;
    if (streak >= GRADUATE_STREAK) delete next[id];
    else next[id] = { ...entry, streak };
  });

  saveReview(next);
  return next;
}

export function reviewCount(review, items) {
  return items.filter((item) => review[item.id]).length;
}

// 오답노트 항목을 앞에 놓고, 나머지는 무작위로 채웁니다.
export function pickQuestions(pool, review, size) {
  const shuffled = shuffle(pool);
  const due = shuffled.filter((item) => review[item.id]);
  const rest = shuffled.filter((item) => !review[item.id]);

  return shuffle([...due, ...rest].slice(0, size));
}

export function shuffle(list) {
  const copy = [...list];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}
