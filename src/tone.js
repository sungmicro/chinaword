// 병음의 성조 부호를 읽고 바꿔 끼우는 도구.
// 성조 시험은 "같은 철자, 다른 성조" 보기를 만들어야 하므로,
// 음절을 쪼개는 대신 성조가 찍힌 모음만 제자리에서 갈아끼웁니다.

const TONE_TABLE = {
  a: ['a', 'ā', 'á', 'ǎ', 'à'],
  e: ['e', 'ē', 'é', 'ě', 'è'],
  i: ['i', 'ī', 'í', 'ǐ', 'ì'],
  o: ['o', 'ō', 'ó', 'ǒ', 'ò'],
  u: ['u', 'ū', 'ú', 'ǔ', 'ù'],
  ü: ['ü', 'ǖ', 'ǘ', 'ǚ', 'ǜ']
};

// 성조 붙은 글자 -> { base, tone }. 대문자(Běijīng의 Ě 같은 경우)도 함께 넣습니다.
const MARKED = new Map();
Object.entries(TONE_TABLE).forEach(([base, forms]) => {
  forms.forEach((char, tone) => {
    if (tone === 0) return;
    MARKED.set(char, { base, tone });
    MARKED.set(char.toUpperCase(), { base, tone, upper: true });
  });
});

export const TONE_LABELS = ['경성', '1성', '2성', '3성', '4성'];

// 성조가 찍힌 자리를 찾습니다. 경성 음절은 부호가 없으므로 잡히지 않습니다(그대로 둡니다).
export function readTones(pinyin) {
  const text = String(pinyin ?? '').normalize('NFC');
  const slots = [];

  [...text].forEach((char, index) => {
    const found = MARKED.get(char);
    if (found) slots.push({ index, base: found.base, tone: found.tone, upper: Boolean(found.upper) });
  });

  return { text, slots, pattern: slots.map((slot) => slot.tone) };
}

// 성조 자리마다 원하는 성조를 끼워 새 병음 문자열을 만듭니다.
export function applyTones(pinyin, pattern) {
  const { text, slots } = readTones(pinyin);
  if (slots.length !== pattern.length) return text;

  const chars = [...text];
  slots.forEach((slot, order) => {
    const replacement = TONE_TABLE[slot.base][pattern[order]];
    chars[slot.index] = slot.upper ? replacement.toUpperCase() : replacement;
  });

  return chars.join('');
}

export function patternLabel(pattern) {
  return pattern.map((tone) => TONE_LABELS[tone]).join('·');
}

function samePattern(a, b) {
  return a.length === b.length && a.every((tone, index) => tone === b[index]);
}

function everyPattern(length) {
  if (length <= 0) return [];
  let patterns = [[]];
  for (let step = 0; step < length; step += 1) {
    const next = [];
    patterns.forEach((prefix) => {
      for (let tone = 1; tone <= 4; tone += 1) next.push([...prefix, tone]);
    });
    patterns = next;
  }
  return patterns;
}

function shuffle(list) {
  const copy = [...list];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

// 오답 성조 패턴을 고릅니다.
// 여러 음절이면 "한 음절만 다른" 패턴을 최소 하나 섞어서 너무 쉬워지지 않게 합니다.
export function pickWrongPatterns(correct, count) {
  const candidates = everyPattern(correct.length).filter((pattern) => !samePattern(pattern, correct));
  if (!candidates.length) return [];

  const differsByOne = candidates.filter(
    (pattern) => pattern.filter((tone, index) => tone !== correct[index]).length === 1
  );

  const picked = [];
  if (correct.length > 1 && differsByOne.length) {
    picked.push(shuffle(differsByOne)[0]);
  }

  shuffle(candidates).forEach((pattern) => {
    if (picked.length >= count) return;
    if (picked.some((chosen) => samePattern(chosen, pattern))) return;
    picked.push(pattern);
  });

  return picked.slice(0, count);
}

// 성조 문제로 낼 수 있는 항목인지 (성조 부호가 1~3개)
export function isToneQuizable(item) {
  const { slots } = readTones(item?.pinyin);
  return slots.length >= 1 && slots.length <= 3;
}

// 보기 4개(정답 1 + 오답 3)를 만들어 섞어 돌려줍니다.
export function buildToneChoices(pinyin, count = 4) {
  const { text, pattern } = readTones(pinyin);
  if (!pattern.length) return null;

  const wrongPatterns = pickWrongPatterns(pattern, count - 1);
  const choices = [
    { text, pattern, correct: true },
    ...wrongPatterns.map((wrong) => ({
      text: applyTones(text, wrong),
      pattern: wrong,
      correct: false
    }))
  ];

  // 철자가 같아지는 경우(이론상 없지만 방어) 중복 보기를 걸러냅니다.
  const unique = [];
  choices.forEach((choice) => {
    if (!unique.some((kept) => kept.text === choice.text)) unique.push(choice);
  });

  return shuffle(unique);
}
