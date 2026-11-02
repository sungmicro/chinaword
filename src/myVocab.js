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

// 단어장·랜덤 학습이 쓰는 카드 모양으로 바꿉니다 (최근에 담은 것이 앞).
export function mineToStudyItems(items) {
  return items.map((entry) => ({
    id: `mine:${entry.key}`,
    itemType: entry.kind === 'pattern' ? '패턴' : '단어',
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
    mineKey: entry.key
  }));
}

function sanitize(saved) {
  const items = Array.isArray(saved?.items) ? saved.items : [];
  return items.filter((entry) => entry && typeof entry.key === 'string' && typeof entry.hanzi === 'string');
}

// --- 저장소 (지금은 이 기기의 localStorage) ---
let current = null;
const listeners = new Set();

export function loadMine() {
  if (current === null) {
    const saved = sanitize(readJson(MINE_KEY, {}));
    current = saved.map(dropAutoReadingUsage);
    // 지운 것이 있으면 한 번 저장해 둡니다(다음부터는 바꿀 것이 없어 쓰지 않습니다).
    if (current.some((entry, index) => entry !== saved[index])) writeJson(MINE_KEY, { version: 1, items: current });
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

export function subscribeMine(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function resetMineForTest() {
  current = null;
  listeners.clear();
}

// 독해·듣기 해설, 단어장, 랜덤 학습이 같은 목록을 봅니다.
export function useMyVocab() {
  const items = useSyncExternalStore(subscribeMine, loadMine, loadMine);
  return {
    items,
    has: (key) => items.some((item) => item.key === key),
    toggle: toggleMine,
    remove: removeMine
  };
}
