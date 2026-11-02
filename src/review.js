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

// 단어장을 다시 만들면서 사라진 카드(src/data/vocab-retired.json의 retired)의 기록을, 그 뜻을 이어받은
// 카드(movedTo 한자의 카드)로 옮깁니다. 옮길 카드가 없으면 그대로 둡니다 — 오답노트는 지금 있는 카드의
// id로만 찾으므로(review[item.id]) 남은 기록은 조용히 무시됩니다. 같은 카드에 기록이 이미 있으면 틀린 횟수는
// 더하고 연속 맞힘은 작은 쪽을 남깁니다.
export function migrateReview(review, items, retired = {}) {
  const ids = new Set(items.map((item) => item.id));
  const byHanzi = new Map();
  items.forEach((item) => {
    if (!String(item.id).startsWith('mine:') && !byHanzi.has(item.hanzi)) byHanzi.set(item.hanzi, item.id);
  });
  let changed = false;
  const next = { ...review };
  Object.keys(review).forEach((id) => {
    if (ids.has(id)) return;
    const target = byHanzi.get(retired[id]?.movedTo);
    if (!target) return;
    const moved = review[id] ?? {};
    const existing = next[target];
    next[target] = existing
      ? { streak: Math.min(existing.streak ?? 0, moved.streak ?? 0), wrong: (existing.wrong ?? 0) + (moved.wrong ?? 0) }
      : moved;
    delete next[id];
    changed = true;
  });
  return { review: next, changed };
}

// 오답노트를 불러오면서 사라진 카드의 기록을 옮기고, 옮긴 것이 있으면 한 번 저장합니다.
export function loadReviewFor(items, retired) {
  const { review, changed } = migrateReview(loadReview(), items, retired);
  if (changed) saveReview(review);
  return review;
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
