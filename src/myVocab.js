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

export const wordKey = (hanzi) => `word:${hanzi}`;
export const patternKey = (pattern) => `pattern:${pattern}`;

// 해설의 단어 하나를 담는 순간 그대로 저장합니다. 독해 단어에는 용법·예문이 있고 듣기 단어에는 없습니다.
export function wordEntry(word, source, now = new Date()) {
  return {
    key: wordKey(word.hanzi),
    kind: 'word',
    hanzi: word.hanzi,
    pinyin: word.pinyin ?? '',
    meaningKo: word.meaningKo ?? '',
    partOfSpeech: word.partOfSpeech ?? '',
    note: word.usage ?? '',
    exampleZh: word.example?.zh ?? '',
    examplePinyin: wordsToPinyin(word.example?.words),
    exampleKo: word.example?.ko ?? '',
    source,
    addedAt: now.toISOString()
  };
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
  if (current === null) current = sanitize(readJson(MINE_KEY, {}));
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
