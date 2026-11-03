// 내 단어장 갱신: 담은 순간의 병음·뜻·품사가 저장돼 있어, 해설 데이터를 고친 뒤에도 옛 내용(뜻 = 한자, 比较忙 같은
// 붙은 토큰, 이름+호칭, 대본 오인식 단어)이 남습니다. 불러올 때 단어 항목을 지금 데이터에 맞춥니다.
// 색인 src/data/mine-refresh.json은 tools/mine_refresh.py가 공개 데이터에서 만듭니다(형식은 그 파일 머리말).
// 독해·듣기 회차 JSON은 받지 않고, 이미 번들에 있는 vocab.json과 이 색인(약 40KB)만 씁니다.
//
// 규칙 (단어 항목만. 문장·패턴 항목은 그대로 둡니다)
//  1. 출처가 문항(«H31006 독해 52번», «… 듣기 N번», «… 쓰기 N번»)이면 그 문항에서 옮긴 단어(moved)가 있으면 그 단어들로,
//     그 문항 해설에 다른 뜻으로 있으면(at) 그 뜻으로 바꿉니다.
//     출처가 «랜덤 학습 · <단원>»이면 그 단원의 같은 한자 «단어» 카드를 씁니다.
//  2. 나뉜 묶음(split: 比较忙 → 比较·忙, 李先生 → 李·先生)은 조각으로 바꿉니다.
//  3. 나머지는 vocab.json의 첫 «단어» 카드, 없으면 해설의 기본 뜻(base)으로 맞춥니다.
//  4. 어디에도 없는 단어는 뜻에 한글이 있으면 그대로 두고, 없으면 뺍니다. 옮길 단어가 빈 목록이면 뺍니다.
// 조각·바꾼 단어는 원래 항목의 출처·담은 시각·담은 방법(addedBy)·메모·모름 횟수를 이어받고, 이미 담긴 단어와 겹치면
// 하나로 합칩니다(모름 횟수는 큰 값, 직접 담은 쪽이 이깁니다). 두 번 돌려도 결과가 같습니다.

const HANGUL = /[가-힣]/;
const WORD_TYPE = '단어';
const UNKNOWN = 'unknown'; // myVocab.js ADDED_BY_UNKNOWN과 같은 값

export const hasHangul = (text) => HANGUL.test(String(text ?? ''));

// 앱이 «＋ 담기»·«모르겠어»에 적는 출처를 문항 주소(tools/vocab_fixes.json items와 같은 형식)로.
export function sourceAddress(source) {
  const match = String(source ?? '').match(/^(\S+) (독해|듣기|쓰기) (\d+)번$/);
  if (!match) return null;
  const kind = { 독해: 'reading', 듣기: 'listening', 쓰기: 'writing' }[match[2]];
  return `${kind}/${match[1]}/${match[3]}`;
}

export function sourceLesson(source) {
  const match = String(source ?? '').match(/^랜덤 학습 · (.+)$/);
  return match ? match[1] : null;
}

const has = (object, key) => Boolean(object) && Object.prototype.hasOwnProperty.call(object, key);

function fieldsOf(card) {
  return { pinyin: card.pinyin ?? '', meaningKo: card.meaningKo ?? '', partOfSpeech: card.partOfSpeech ?? '' };
}

function mergeText(a, b) {
  if (!a) return b ?? '';
  if (!b || a.includes(b)) return a;
  return `${a} / ${b}`;
}

const countOf = (entry) => (Number.isInteger(entry?.unknownCount) && entry.unknownCount > 0 ? entry.unknownCount : 0);

// 같은 열쇠가 된 두 항목을 하나로. 앞(a)의 자리·출처·담은 시각을 둡니다.
export function mergeEntries(a, b) {
  const merged = { ...a, note: mergeText(a.note, b.note) };
  const count = Math.max(countOf(a), countOf(b));
  if (count) merged.unknownCount = count;
  else delete merged.unknownCount;
  if (a.addedBy === UNKNOWN && b.addedBy !== UNKNOWN) delete merged.addedBy; // 한쪽이라도 직접 담았으면 직접 담은 것
  if (!a.exampleZh && b.exampleZh) {
    merged.exampleZh = b.exampleZh;
    merged.examplePinyin = b.examplePinyin ?? '';
    merged.exampleKo = b.exampleKo ?? '';
  }
  return merged;
}

// index: src/data/mine-refresh.json, vocab: src/data/vocab.json, wordKey: myVocab.js의 열쇠 함수.
export function makeMineRefresher(index, vocab, wordKey) {
  const firstCard = new Map();
  const lessonCard = new Map();
  for (const card of vocab ?? []) {
    if (card.itemType !== WORD_TYPE) continue;
    if (!firstCard.has(card.hanzi)) firstCard.set(card.hanzi, card);
    const key = `${card.lesson}\u0000${card.hanzi}`;
    if (!lessonCard.has(key)) lessonCard.set(key, card);
  }
  const senseAt = (number) => {
    const [pinyin, meaningKo, partOfSpeech] = index.senses[number];
    return { pinyin, meaningKo, partOfSpeech };
  };

  // 그 맥락에서 이 한자의 지금 뜻. 없으면 null.
  function lookup(hanzi, context) {
    const here = context.address && index.at[context.address];
    if (has(here, hanzi)) return senseAt(here[hanzi]);
    const inLesson = context.lesson && lessonCard.get(`${context.lesson}\u0000${hanzi}`);
    if (inLesson) return fieldsOf(inLesson);
    const card = firstCard.get(hanzi);
    if (card) return fieldsOf(card);
    if (has(index.base, hanzi)) return senseAt(index.base[hanzi]);
    return null;
  }

  // 다른 단어(들)로 바꿔야 하면 그 한자 목록, 아니면 null.
  function targetsOf(hanzi, context) {
    const moved = context.address && index.moved[context.address];
    if (has(moved, hanzi)) return moved[hanzi];
    if (has(context.address && index.at[context.address], hanzi)) return null;
    if (context.lesson && lessonCard.has(`${context.lesson}\u0000${hanzi}`)) return null;
    if (has(index.split, hanzi)) return index.split[hanzi];
    return null;
  }

  function withSense(entry, hanzi, sense) {
    if (
      entry.hanzi === hanzi &&
      entry.pinyin === sense.pinyin &&
      entry.meaningKo === sense.meaningKo &&
      entry.partOfSpeech === sense.partOfSpeech &&
      entry.key === wordKey(hanzi, sense.pinyin)
    ) {
      return entry;
    }
    return { ...entry, key: wordKey(hanzi, sense.pinyin), hanzi, ...sense };
  }

  // 항목 하나 → 지금 데이터의 항목 0개 이상. 바뀌지 않았으면 같은 객체를 돌려줍니다.
  function refreshEntry(entry) {
    if (entry.kind !== 'word' || (entry.itemType && entry.itemType !== WORD_TYPE)) return [entry];
    const context = { address: sourceAddress(entry.source), lesson: sourceLesson(entry.source) };
    const targets = targetsOf(entry.hanzi, context);
    if (targets) {
      return targets.flatMap((hanzi) => {
        const sense = lookup(hanzi, context);
        return sense ? [withSense(entry, hanzi, sense)] : [];
      });
    }
    const sense = lookup(entry.hanzi, context);
    if (sense) return [withSense(entry, entry.hanzi, sense)];
    return hasHangul(entry.meaningKo) ? [entry] : [];
  }

  // 목록 전체. 바뀐 것이 없으면 같은 배열을 돌려줍니다.
  // 겹치면 먼저 나온 자리에 하나로 합치고, 바뀌지 않은(이미 담겨 있던) 항목의 출처·담은 시각을 남깁니다.
  function refreshItems(items) {
    const out = [];
    const position = new Map();
    const unchanged = new Set();
    let changed = false;
    items.forEach((entry) => {
      const produced = refreshEntry(entry);
      if (produced.length === 1 && produced[0] === entry) unchanged.add(entry);
      else changed = true;
      produced.forEach((next) => {
        if (position.has(next.key)) {
          const at = position.get(next.key);
          const prev = out[at];
          out[at] = unchanged.has(next) && !unchanged.has(prev) ? mergeEntries(next, prev) : mergeEntries(prev, next);
          changed = true;
        } else {
          position.set(next.key, out.length);
          out.push(next);
        }
      });
    });
    return changed ? out : items;
  }

  return { refreshEntry, refreshItems, lookup };
}
