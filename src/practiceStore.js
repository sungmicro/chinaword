// 듣기·독해 탭이 같이 쓰는 도우미: 기기 저장, 채점, 회차 데이터 받아오기.
// node 테스트(src/*.test.js)가 바로 가져다 쓰므로 React를 쓰지 않습니다.

// '모르겠음'은 기록에 '?'로 남깁니다. 틀린 것과 따로 셉니다.
export const UNKNOWN = '?';

export function readJson(key, fallback) {
  try {
    const saved = localStorage.getItem(key);
    const parsed = saved ? JSON.parse(saved) : null;
    return parsed && typeof parsed === 'object' ? parsed : fallback;
  } catch {
    return fallback;
  }
}

export function writeJson(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // 저장 실패가 학습을 막을 이유는 없습니다.
  }
}

export function gradeOf(item, picked) {
  if (!picked) return null;
  if (picked === UNKNOWN) return 'unknown';
  return picked === item.answer ? 'right' : 'wrong';
}

export function tally(items, picks = {}) {
  return items.reduce(
    (acc, item) => {
      const grade = gradeOf(item, picks[item.no]);
      if (grade) acc[grade] += 1;
      return acc;
    },
    { right: 0, wrong: 0, unknown: 0 }
  );
}

const cache = new Map();

// 회차 데이터는 그 회차를 고를 때만 받아옵니다. 실패하면 캐시에서 지워 다음에 다시 받습니다.
export function fetchCached(url, label) {
  if (!cache.has(url)) {
    const request = fetch(url).then((response) => {
      if (!response.ok) throw new Error(`${label} 데이터를 불러오지 못했어요 (${response.status})`);
      return response.json();
    });
    request.catch(() => cache.delete(url));
    cache.set(url, request);
  }
  return cache.get(url);
}
