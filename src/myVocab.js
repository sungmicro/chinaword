// 내 단어장: 해설에서 «＋ 담기»로 모은 단어·문장 구조.
// 화면은 이 파일만 거칩니다. 로그인을 붙일 때는 아래 '저장소' 부분만 서버 저장으로 바꾸고,
// 첫 로그인 때 기기에 있던 항목을 계정으로 올립니다.
import { useSyncExternalStore } from 'react';
import { readJson, writeJson } from './practiceStore.js';

export const MINE_KEY = 'sungmi-vocab-mine-v1';
export const MINE_LESSON = '내 단어장';

const PUNCT_PINYIN = { '，': ',', '、': ',', '。': '.', '？': '?', '！': '!', '：': ':', '；': ';', '“': '"', '”': '"' };

// [['你','nǐ'],['，','']] → 'Nǐ,' (tools/reading/hsktext.py words_to_pinyin과 같은 규칙)
export function wordsToPinyin(words) {
  let out = '';
  (words ?? []).forEach(([token, pinyin]) => {
    if (pinyin) out += (out && !out.endsWith('"') ? ' ' : '') + pinyin;
    else if (PUNCT_PINYIN[token]) out += PUNCT_PINYIN[token];
  });
  return out.charAt(0).toUpperCase() + out.slice(1);
}

// 성조를 뗀 음절. 같은 한자라도 읽기가 다르면(还 hái/huán) 다른 단어로, 변조만 다르면(不 bù/bú) 같은 단어로 봅니다.
function toneless(pinyin) {
  return String(pinyin ?? '')
    .toLowerCase()
    .replace(/[üǖǘǚǜ]/g, 'v')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z]/g, '');
}

export const wordKey = (hanzi, pinyin) => `word:${hanzi}:${toneless(pinyin)}`;
export const patternKey = (pattern) => `pattern:${pattern}`;

// 해설의 단어 하나를 담는 순간 그대로 저장합니다. 듣기·독해·쓰기 모두 한자·병음·뜻·품사만 있고 용법·예문 칸은 비웁니다.
export function wordEntry(word, source, now = new Date()) {
  return {
    key: wordKey(word.hanzi, word.pinyin),
    kind: 'word',
    hanzi: word.hanzi,
    pinyin: word.pinyin ?? '',
    meaningKo: word.meaningKo ?? '',
    partOfSpeech: word.partOfSpeech ?? '',
    note: '',
    exampleZh: '',
    examplePinyin: '',
    exampleKo: '',
    source,
    addedAt: now.toISOString()
  };
}

// 2026-11-02 전 독해 해설은 단어마다 자동 용법 «<한자>가 쓰인 문장을 함께 확인»과 지문에서 따온 예문을 달았고,
// 담을 때 note·example 칸에 그대로 저장됐습니다. 독해 출처(«<회차> 독해 <번호>번»)의 단어이고 note가 그 단어의
// 자동 문구와 정확히 같을 때만 note를 비웁니다. 그 밖의 메모·패턴·듣기 단어는 그대로 둡니다.
// 함께 저장된 예문은 자동값일 때만 비웁니다. 근거: 앱에는 담은 항목을 고치는 기능이 없었고(담기·빼기뿐),
// 예전 독해 단어 예문 4,369개는 모두 그 단어가 들어간 시험 문장이었습니다. 그래서 예문이 비었거나 그 한자를
// 포함할 때만 자동값으로 보고 비우고, 한자가 없는 예문은 사용자 것일 수 있어 남깁니다.
export const autoReadingUsage = (hanzi) => `${hanzi}가 쓰인 문장을 함께 확인`;
const READING_SOURCE = / 독해 \d+번$/;

export function dropAutoReadingUsage(entry) {
  const auto =
    entry.kind === 'word' &&
    READING_SOURCE.test(String(entry.source ?? '')) &&
    String(entry.note ?? '').trim() === autoReadingUsage(entry.hanzi);
  if (!auto) return entry;
  const exampleIsAuto = !entry.exampleZh || String(entry.exampleZh).includes(entry.hanzi);
  return exampleIsAuto
    ? { ...entry, note: '', exampleZh: '', examplePinyin: '', exampleKo: '' }
    : { ...entry, note: '' };
}

// 문법(문장 구조) 하나. 듣기 문장 구조에는 짧은 뜻이 없어 설명 전체를 뜻 자리에 씁니다.
export function patternEntry(grammar, source, now = new Date()) {
  const short = grammar.meaningKo ?? '';
  return {
    key: patternKey(grammar.pattern),
    kind: 'pattern',
    hanzi: grammar.pattern,
    pinyin: '',
    meaningKo: short || grammar.note || '',
    partOfSpeech: '',
    note: short ? grammar.note ?? '' : '',
    exampleZh: grammar.example?.zh ?? '',
    examplePinyin: wordsToPinyin(grammar.example?.words),
    exampleKo: grammar.example?.ko ?? '',
    source,
    addedAt: now.toISOString()
  };
}

// 같은 단어·패턴은 하나로 칩니다. 있으면 빼고, 없으면 맨 앞에 넣습니다.
export function toggleEntry(items, entry) {
  return items.some((item) => item.key === entry.key)
    ? items.filter((item) => item.key !== entry.key)
    : [entry, ...items];
}

export function removeKey(items, key) {
  return items.filter((item) => item.key !== key);
}

// --- 모름 횟수 ---
// 랜덤 학습의 «모르겠어»를 누를 때마다(같은 카드에서 여러 번 눌러도) 그 항목의 unknownCount가 1 늘고,
// 없던 항목은 내 단어장에 담깁니다.
// addedBy: 'unknown'은 «모르겠어»로 처음 담긴 항목입니다. 칸이 없는 항목(예전 항목, «＋ 담기»)은 직접 담은 것입니다.
// «알겠어»는 모름 횟수를 1 줄입니다. 0이 되면 «모름 표시 지우기»와 같이 해제합니다.
// «모름 표시 지우기»(예전 «이제 알겠어»)는 모름 표시를 한 번에 지웁니다. «모르겠어»로 담긴 항목은
// 내 단어장에서도 빼고, 직접 담은 항목은 그대로 두고 횟수만 지웁니다.
export const ADDED_BY_UNKNOWN = 'unknown';

export function unknownCountOf(entry) {
  const count = entry?.unknownCount;
  return Number.isInteger(count) && count > 0 ? count : 0;
}

// 랜덤 학습 카드(단어장 vocab.json 또는 내 단어장 카드)를 내 단어장 항목으로. 문장·표현도 단어 열쇠로 담습니다.
export function studyCardEntry(card, now = new Date()) {
  return {
    key: card.mineKey ?? wordKey(card.hanzi, card.pinyin),
    kind: card.itemType === '패턴' ? 'pattern' : 'word',
    itemType: card.itemType ?? '단어',
    hanzi: card.hanzi,
    pinyin: card.pinyin ?? '',
    meaningKo: card.meaningKo ?? '',
    partOfSpeech: card.partOfSpeech ?? '',
    note: '',
    exampleZh: '',
    examplePinyin: '',
    exampleKo: '',
    source: card.lesson ? `랜덤 학습 · ${card.lesson}` : '랜덤 학습',
    addedAt: now.toISOString(),
    addedBy: ADDED_BY_UNKNOWN
  };
}

// 이미 있으면 자리와 내용은 그대로 두고 횟수만 늘립니다. 없으면 맨 앞에 횟수 1로 넣습니다.
export function markUnknownEntry(items, entry) {
  if (items.some((item) => item.key === entry.key)) {
    return items.map((item) => item.key === entry.key ? { ...item, unknownCount: unknownCountOf(item) + 1 } : item);
  }
  return [{ ...entry, unknownCount: 1 }, ...items];
}

export function resolveUnknownEntry(items, key) {
  const target = items.find((item) => item.key === key);
  if (!target) return items;
  if (target.addedBy === ADDED_BY_UNKNOWN) return removeKey(items, key);
  return items.map((item) => {
    if (item.key !== key) return item;
    const { unknownCount: _cleared, ...rest } = item;
    return rest;
  });
}

// «알겠어»: 횟수가 1 이상이면 1 줄이고, 0이 되면 resolveUnknownEntry와 같이 해제합니다.
// 없는 항목이나 횟수가 0인 항목은 그대로 둡니다(같은 배열을 돌려줍니다).
export function markKnownEntry(items, key) {
  const target = items.find((item) => item.key === key);
  const count = unknownCountOf(target);
  if (!count) return items;
  if (count === 1) return resolveUnknownEntry(items, key);
  return items.map((item) => item.key === key ? { ...item, unknownCount: count - 1 } : item);
}

// 모름 많은 순. 횟수가 같으면 원래 순서(최근에 담은 것이 앞)를 지킵니다.
export function sortByUnknown(studyItems) {
  return studyItems
    .map((item, index) => ({ item, index }))
    .sort((a, b) => (b.item.unknownCount ?? 0) - (a.item.unknownCount ?? 0) || a.index - b.index)
    .map(({ item }) => item);
}

// 단어장·랜덤 학습이 쓰는 카드 모양으로 바꿉니다 (최근에 담은 것이 앞).
export function mineToStudyItems(items) {
  return items.map((entry) => ({
    id: `mine:${entry.key}`,
    itemType: entry.itemType ?? (entry.kind === 'pattern' ? '패턴' : '단어'),
    lesson: MINE_LESSON,
    hanzi: entry.hanzi,
    pinyin: entry.pinyin,
    meaningKo: entry.meaningKo,
    partOfSpeech: entry.partOfSpeech,
    note: entry.note,
    exampleZh: entry.exampleZh,
    examplePinyin: entry.examplePinyin,
    exampleKo: entry.exampleKo,
    source: entry.source,
    mineKey: entry.key,
    unknownCount: unknownCountOf(entry)
  }));
}

function sanitize(saved) {
  const items = Array.isArray(saved?.items) ? saved.items : [];
  return items.filter((entry) => entry && typeof entry.key === 'string' && typeof entry.hanzi === 'string');
}

// --- 저장소 (지금은 이 기기의 localStorage) ---
let current = null;
const listeners = new Set();

// 불러올 때 단어 항목을 지금 데이터에 맞추는 함수(src/mineRefresh.js). main.jsx가 vocab.json과 갱신 색인으로
// 만들어 넘깁니다. 넘기지 않으면(테스트 등) 그대로 둡니다.
let refreshItems = (items) => items;

export function configureMineRefresh(refresh) {
  refreshItems = refresh ?? ((items) => items);
  current = null;
}

// 2026-11-04 갱신(src/mineRefresh.js)이 처음 바꾸기 전의 저장값을 그대로 한 번만 남겨 둡니다. 이미 있으면 덮지 않습니다.
export const MINE_BACKUP_KEY = `${MINE_KEY}-backup-2026-11-04`;

function backupOnce() {
  try {
    if (localStorage.getItem(MINE_BACKUP_KEY) !== null) return;
    const raw = localStorage.getItem(MINE_KEY);
    if (raw !== null) localStorage.setItem(MINE_BACKUP_KEY, raw);
  } catch {
    // 백업을 못 해도 학습은 막지 않습니다.
  }
}

export function loadMine() {
  if (current === null) {
    const saved = sanitize(readJson(MINE_KEY, {}));
    current = refreshItems(saved.map(dropAutoReadingUsage));
    // 지우거나 바꾼 것이 있으면 원래 저장값을 백업한 뒤 한 번 저장해 둡니다(다음부터는 바꿀 것이 없어 쓰지 않습니다).
    if (current.length !== saved.length || current.some((entry, index) => entry !== saved[index])) {
      backupOnce();
      writeJson(MINE_KEY, { version: 1, items: current });
    }
  }
  return current;
}

function commit(next) {
  current = next;
  writeJson(MINE_KEY, { version: 1, items: next });
  listeners.forEach((listener) => listener());
}

export function toggleMine(entry) {
  commit(toggleEntry(loadMine(), entry));
}

export function removeMine(key) {
  commit(removeKey(loadMine(), key));
}

export function markUnknown(card) {
  commit(markUnknownEntry(loadMine(), studyCardEntry(card)));
}

export function resolveUnknown(key) {
  commit(resolveUnknownEntry(loadMine(), key));
}

export function markKnown(key) {
  const items = loadMine();
  const next = markKnownEntry(items, key);
  if (next !== items) commit(next); // 모름 횟수가 0이면 저장값을 건드리지 않습니다
}

export function subscribeMine(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function resetMineForTest() {
  current = null;
  refreshItems = (items) => items;
  listeners.clear();
}

// 독해·듣기 해설, 단어장, 랜덤 학습이 같은 목록을 봅니다.
export function useMyVocab() {
  const items = useSyncExternalStore(subscribeMine, loadMine, loadMine);
  return {
    items,
    has: (key) => items.some((item) => item.key === key),
    find: (key) => items.find((item) => item.key === key),
    toggle: toggleMine,
    remove: removeMine,
    markUnknown,
    markKnown,
    resolveUnknown
  };
}
