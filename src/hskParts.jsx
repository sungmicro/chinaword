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
// tight: 독해 문제처럼 병음을 감출 때 시험지처럼 단어 사이를 붙입니다(띄어 쓰면 단어 경계가 힌트가 됩니다).
// blank: 빈칸 문제에서 정답 단어의 자리. 채우기 전에는 «（　　）»로 가리고, 채우면 강조합니다.
export function Ruby({ words, showPinyin = true, blank = null, fillBlank = false, tight = false }) {
  const marked =
    blank === null
      ? words
      : words.map((word, index) => {
          if (index !== blank) return word;
          return fillBlank ? [word[0], word[1], 'filled'] : ['（　　）', '', 'gap'];
        });

  return (
    <span className={`ruby${tight && !showPinyin ? ' plain' : ''}`}>
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

// 해설의 단어 목록(듣기·독해·쓰기 공통): 한자·병음·뜻·품사.
export function ExplainVocab({ vocab, source }) {
  const mine = useMyVocab();
  return (
    <ul className="listenVocab">
      {vocab.map((word) => (
        <li key={word.hanzi}>
          <strong>{word.hanzi}</strong>
          <span className="vocabPinyinText">{word.pinyin}</span>
          <span className="vocabMeaningText">{word.meaningKo}</span>
          {word.partOfSpeech ? <em>{word.partOfSpeech}</em> : null}
          <MineButton
            saved={mine.has(wordKey(word.hanzi, word.pinyin))}
            label={word.hanzi}
            onToggle={() => mine.toggle(wordEntry(word, source))}
          />
        </li>
      ))}
    </ul>
  );
}

// 해설의 문장 구조(문법) 목록(듣기·독해 공통): 패턴과 설명. 사람이 새로 지은 예문이 있으면(독해 H31001~H31005)
// 카드 안 설명 아래에 함께 보여 줍니다. 예문이 없으면 듣기와 똑같습니다.
export function ExplainGrammar({ grammar, source }) {
  const mine = useMyVocab();
  return (
    <ul className="listenGrammar">
      {grammar.map((note, index) => (
        <li key={index}>
          <div className="grammarHead">
            <strong>{note.pattern}</strong>
            <MineButton
              saved={mine.has(patternKey(note.pattern))}
              label={note.pattern}
              onToggle={() => mine.toggle(patternEntry(note, source))}
            />
          </div>
          <p>{note.note}</p>
          {note.example ? (
            <div className="grammarExample">
              <Ruby words={note.example.words} />
              <p className="listenKo">{note.example.ko}</p>
            </div>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
