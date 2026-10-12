import React from 'react';
import { Check, Plus, X } from 'lucide-react';
import { UNKNOWN, gradeOf } from './practiceStore';
import { patternEntry, patternKey, useMyVocab, wordEntry, wordKey } from './myVocab';

// 듣기·독해 탭이 같이 쓰는 화면 조각: 한자 아래 병음, 보기 버튼, 채점 문구,
// 해설의 단어·문장 구조 목록(항목마다 «＋ 담기»).

const OPENING_PUNCT = new Set(['“', '‘', '《', '（']);

// 문장부호가 혼자 다음 줄로 넘어가지 않게 앞 단어에 붙입니다 (여는 따옴표는 뒤 단어에).
// 세 번째 칸(mark)이 있는 단어는 빈칸 표시라 문장부호로 보지 않습니다.
function groupWords(words) {
  const units = [];
  let prefix = '';
  words.forEach(([hanzi, pinyin, mark]) => {
    if (!pinyin && !mark && OPENING_PUNCT.has(hanzi)) {
      prefix += hanzi;
    } else if (!pinyin && !mark && units.length && !prefix) {
      units[units.length - 1].suffix += hanzi;
    } else {
      units.push({ prefix, hanzi, pinyin, suffix: '', mark });
      prefix = '';
    }
  });
  if (prefix) units.push({ prefix, hanzi: '', pinyin: '', suffix: '' });
  return units;
}

// 한자 바로 아래에 병음을 붙여 단어 단위로 보여줍니다.
// 병음을 감추면 시험지처럼 단어 사이를 붙입니다(띄어 쓰면 단어 경계가 힌트가 됩니다).
// blank: 빈칸 문제에서 정답 단어의 자리. 채우기 전에는 «（　　）»로 가리고, 채우면 강조합니다.
export function Ruby({ words, showPinyin = true, blank = null, fillBlank = false }) {
  const marked =
    blank === null
      ? words
      : words.map((word, index) => {
          if (index !== blank) return word;
          return fillBlank ? [word[0], word[1], 'filled'] : ['（　　）', '', 'gap'];
        });

  return (
    <span className={`ruby${showPinyin ? '' : ' plain'}`}>
      {groupWords(marked).map((unit, index) => (
        <span className={`rubyUnit${unit.mark ? ` ruby-${unit.mark}` : ''}`} key={index}>
          {unit.prefix ? <span className="rubyPunct">{unit.prefix}</span> : null}
          <span className="rubyWord">
            <span className="rubyHanzi">{unit.hanzi}</span>
            {showPinyin ? <span className="rubyPinyin">{unit.pinyin || ' '}</span> : null}
          </span>
          {unit.suffix ? <span className="rubyPunct">{unit.suffix}</span> : null}
        </span>
      ))}
    </span>
  );
}

// blocked: 예시에 쓰인 보기처럼 고를 수 없는 보기.
export function ChoiceButton({ value, picked, item, revealed, onPick, blocked = false, className = '', children }) {
  const answered = Boolean(picked);
  const isPicked = picked === value;
  const isAnswer = value === item.answer;
  const state =
    (answered || revealed) && isAnswer ? 'right' : isPicked && value === UNKNOWN ? 'unknown' : isPicked ? 'wrong' : '';

  return (
    <button
      type="button"
      className={`listenChoice ${className} ${state}${blocked ? ' blocked' : ''}`}
      onClick={() => onPick(value)}
      disabled={answered || blocked}
    >
      {children}
      {state === 'right' ? <Check size={16} /> : null}
      {state === 'wrong' ? <X size={16} /> : null}
    </button>
  );
}

export function Verdict({ item, picked, answerText }) {
  const grade = gradeOf(item, picked);
  if (!grade) return null;
  const text = {
    right: '정답이에요',
    wrong: `아쉬워요 · 정답은 ${answerText}`,
    unknown: `정답은 ${answerText}`
  }[grade];
  return <p className={`listenVerdict ${grade}`}>{text}</p>;
}

function MineButton({ saved, label, onToggle }) {
  return (
    <button
      type="button"
      className={`mineButton${saved ? ' saved' : ''}`}
      onClick={onToggle}
      aria-pressed={saved}
      aria-label={saved ? `${label} 내 단어장에서 빼기` : `${label} 내 단어장에 담기`}
    >
      {saved ? <Check size={13} /> : <Plus size={13} />}
      {saved ? '담음' : '담기'}
    </button>
  );
}

function Example({ example }) {
  return (
    <div className="readExample">
      <Ruby words={example.words} />
      <p className="listenKo">{example.ko}</p>
    </div>
  );
}

// 해설의 단어 목록. 독해 단어에는 용법(usage)·예문(example)이 더 있어 한 줄에 하나씩 넓게 보여줍니다.
export function ExplainVocab({ vocab, source }) {
  const mine = useMyVocab();
  const detailed = vocab.some((word) => word.usage || word.example);
  return (
    <ul className={`listenVocab${detailed ? ' readVocab' : ''}`}>
      {vocab.map((word) => (
        <li key={word.hanzi}>
          <strong>{word.hanzi}</strong>
          <span className="vocabPinyinText">{word.pinyin}</span>
          <span className="vocabMeaningText">{word.meaningKo}</span>
          {word.partOfSpeech ? <em>{word.partOfSpeech}</em> : null}
          <MineButton
            saved={mine.has(wordKey(word.hanzi))}
            label={word.hanzi}
            onToggle={() => mine.toggle(wordEntry(word, source))}
          />
          {word.usage ? <p className="readUsage">{word.usage}</p> : null}
          {word.example ? <Example example={word.example} /> : null}
        </li>
      ))}
    </ul>
  );
}

// 해설의 문장 구조(문법) 목록. 독해 문법에는 짧은 뜻(meaningKo)·예문이 더 있습니다.
export function ExplainGrammar({ grammar, source }) {
  const mine = useMyVocab();
  return (
    <ul className="listenGrammar">
      {grammar.map((note, index) => (
        <li key={index}>
          <div className="grammarHead">
            <strong>{note.pattern}</strong>
            {note.meaningKo ? <span className="grammarGloss">{note.meaningKo}</span> : null}
            <MineButton
              saved={mine.has(patternKey(note.pattern))}
              label={note.pattern}
              onToggle={() => mine.toggle(patternEntry(note, source))}
            />
          </div>
          <p>{note.note}</p>
          {note.example ? <Example example={note.example} /> : null}
        </li>
      ))}
    </ul>
  );
}
