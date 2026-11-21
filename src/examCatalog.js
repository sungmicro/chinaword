// 화면 탭과 시험지 목록. 3급·4급은 HSK 3.0 공식 샘플(public/hsk30, src/data/hsk30-index.json),
// 기출(2.0)은 HSK 2.0 3급 기출 H31001~H31332(public/listening·reading·writing)입니다.
// node 테스트가 바로 가져다 쓰므로 JSON을 직접 import하지 않고, main.jsx가 목록을 넘겨 buildCatalog를 부릅니다.

export const VIEW_OPTIONS = [
  { key: 'study', label: '랜덤 학습' },
  { key: 'list', label: '단어장' },
  { key: 'hsk3', label: '3급' },
  { key: 'hsk4', label: '4급' },
  { key: 'past', label: '기출(2.0)' }
];

// 시험지를 푸는 탭. 탭마다 아래 서브탭(듣기·독해·쓰기)이 있습니다.
export const EXAM_TABS = ['hsk3', 'hsk4', 'past'];

export const SUB_OPTIONS = [
  { key: 'listen', label: '듣기' },
  { key: 'read', label: '독해' },
  { key: 'write', label: '쓰기' }
];

export const VIEW_KEY = 'sungmi-vocab-view-v1';
export const SUB_KEY = 'sungmi-vocab-level-sub-v1';
export const DEFAULT_SUBS = { hsk3: 'listen', hsk4: 'listen', past: 'listen' };

const SUB_KEYS = SUB_OPTIONS.map((option) => option.key);
const VIEW_KEYS = VIEW_OPTIONS.map((option) => option.key);
const isObject = (value) => Boolean(value) && typeof value === 'object' && !Array.isArray(value);

// 저장된 탭을 지금 탭 구성에 맞춥니다. 예전 화면의 듣기·독해·쓰기 탭(listen·read·write)은
// 같은 내용(H31 기출)이 있는 기출(2.0) 탭의 그 서브탭으로 엽니다.
export function restoreView(savedView, savedSubs) {
  const subs = { ...DEFAULT_SUBS };
  if (isObject(savedSubs)) {
    for (const tab of EXAM_TABS) if (SUB_KEYS.includes(savedSubs[tab])) subs[tab] = savedSubs[tab];
  }
  if (SUB_KEYS.includes(savedView)) return { view: 'past', subs: { ...subs, past: savedView } };
  return { view: VIEW_KEYS.includes(savedView) ? savedView : 'study', subs };
}

const pastEntry = (id, base) => ({ id, label: id, base, file: `${id}.json`, format: 'hsk20' });

function levelArea(hsk30, level, area) {
  return (Array.isArray(hsk30) ? hsk30 : [])
    .filter((entry) => entry?.level === level && entry[area]?.file)
    .map((entry) => ({
      id: entry.id,
      label: entry.label ?? '공식 샘플',
      base: '/hsk30',
      file: entry[area].file,
      format: 'hsk30',
      count: entry[area].count
    }));
}

// 탭·영역별 시험지 목록 { hsk3: { listen: [...], read: [...], write: [...] }, hsk4: …, past: … }.
// 한 항목은 { id, label, base, file, format }이고, 데이터는 `${base}/${file}`에서 받습니다.
// 쓰기는 파일 하나에 여러 회차가 들어 있어(기출 hsk3-all.json) 파일 단위로 적고, 회차는 받은 문항의 exam으로 나눕니다.
export function buildCatalog({ listening = [], reading = [], hsk30 = [] } = {}) {
  const levelTab = (level) => ({
    listen: levelArea(hsk30, level, 'listening'),
    read: levelArea(hsk30, level, 'reading'),
    write: levelArea(hsk30, level, 'writing')
  });
  return {
    hsk3: levelTab(3),
    hsk4: levelTab(4),
    past: {
      listen: listening.map((entry) => pastEntry(entry.id, '/listening')),
      read: reading.map((entry) => pastEntry(entry.id, '/reading')),
      write: [{ id: 'H31', label: '기출 19회', base: '/writing', file: 'hsk3-all.json', format: 'hsk20' }]
    }
  };
}

export const examUrl = (entry) => `${entry.base}/${entry.file}`;

// 듣기·독해 설정 { testId, part, positions, levels: { hsk3: { testId, part }, hsk4: …, past: … } }.
// 예전에 저장한 맨 위 testId·part는 기출(2.0) 값으로 쓰고, 기출(2.0)을 고치면 맨 위 값도 같이 고칩니다
// (예전 화면으로 되돌려도 이어서 풀 수 있게). positions는 회차 ID가 겹치지 않아 탭끼리 같이 씁니다.
export function tabPrefs(saved, tab) {
  const prefs = isObject(saved) ? saved : {};
  const level = isObject(prefs.levels) ? prefs.levels[tab] : undefined;
  if (isObject(level)) return { testId: level.testId, part: level.part };
  return tab === 'past' ? { testId: prefs.testId, part: prefs.part } : {};
}

export function withTabPrefs(saved, tab, { testId, part }, extra = {}) {
  const prefs = isObject(saved) ? saved : {};
  const levels = isObject(prefs.levels) ? prefs.levels : {};
  const next = { ...prefs, ...extra, levels: { ...levels, [tab]: { testId, part } } };
  if (tab === 'past') Object.assign(next, { testId, part });
  return next;
}

// 부분 칩: 시험지 데이터의 parts 순서대로.
export function partChips(test) {
  return ['전체', ...(test?.parts ?? []).map((entry) => entry.part)];
}

// 독해 부분의 형식. 새 데이터는 parts[].kind에 적혀 있고, 예전 H31 데이터는 부분 번호로 정해져 있습니다.
const LEGACY_READING_KINDS = { 1: 'match', 2: 'wordbank', 3: 'passage' };

export function partKind(test, item) {
  const kind = test?.parts?.find((entry) => entry.part === item.part)?.kind;
  return kind ?? LEGACY_READING_KINDS[item.part] ?? 'passage';
}

// "29-30" → "29~30번 같은 글"
export function groupLabel(group) {
  if (!group) return '';
  return `${String(group).replace('-', '~')}번 같은 글`;
}

// «모르겠음» 버튼 글자: 보기 다음 글자(보기 A~C면 D, A~D면 E).
export function nextLetter(labels) {
  const last = labels.length ? labels[labels.length - 1] : '@';
  return String.fromCharCode(last.charCodeAt(0) + 1);
}

// cloze 지문의 줄 해석은 그 줄의 빈칸(slot:N)이 모두 채워졌을 때만 보여 준다(남은 빈칸의 정답 뜻이 새지 않게).
export function clozeKoVisible(words, filled) {
  return words.every((word) => {
    const slot = /^slot:(\d+)$/.exec(word[2] ?? '');
    return !slot || Boolean(filled[Number(slot[1])]);
  });
}
