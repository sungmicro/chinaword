import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Check, ChevronLeft, ChevronRight, Eye, Headphones, Play, RotateCcw, Square, X } from 'lucide-react';
import testIndex from './data/listening-index.json';
import {
  UNKNOWN,
  fetchTest,
  gradeOf,
  loadAnswers,
  loadPrefs,
  saveAnswers,
  savePrefs,
  tally,
  useClipPlayer
} from './listeningTools';

// HSK 공식 모의고사 듣기. 문항마다 '듣기 → 고르기(또는 모르겠음) → 대본·해설 확인'.
// 음원은 회차마다 문제 낭독만 이어 붙인 mp3 하나이고, 문항은 그 안의 구간입니다.

const PART_CHIPS = ['전체', 1, 2, 3, 4];
const SPEAKER_LABELS = { 男: '남', 女: '여', 问: '질문', '★': '★' };
const TRUE_FALSE = [
  { value: '√', label: '✓ 맞다' },
  { value: '×', label: '✗ 틀리다' }
];

function answerLabel(item) {
  if (item.choices.type === 'truefalse') return item.answer === '√' ? '✓ 맞다' : '✗ 틀리다';
  return item.answer;
}

const OPENING_PUNCT = new Set(['“', '‘', '《', '（']);

// 문장부호가 혼자 다음 줄로 넘어가지 않게 앞 단어에 붙입니다 (여는 따옴표는 뒤 단어에).
function groupWords(words) {
  const units = [];
  let prefix = '';
  words.forEach(([hanzi, pinyin]) => {
    if (!pinyin && OPENING_PUNCT.has(hanzi)) {
      prefix += hanzi;
    } else if (!pinyin && units.length && !prefix) {
      units[units.length - 1].suffix += hanzi;
    } else {
      units.push({ prefix, hanzi, pinyin, suffix: '' });
      prefix = '';
    }
  });
  if (prefix) units.push({ prefix, hanzi: '', pinyin: '', suffix: '' });
  return units;
}

// 한자 바로 아래에 병음을 붙여 단어 단위로 보여줍니다.
function Ruby({ words, showPinyin = true }) {
  return (
    <span className="ruby">
      {groupWords(words).map((unit, index) => (
        <span className="rubyUnit" key={index}>
          {unit.prefix ? <span className="rubyPunct">{unit.prefix}</span> : null}
          <span className="rubyWord">
            <span className="rubyHanzi">{unit.hanzi}</span>
            {showPinyin ? <span className="rubyPinyin">{unit.pinyin || ' '}</span> : null}
          </span>
          {unit.suffix ? <span className="rubyPunct">{unit.suffix}</span> : null}
        </span>
      ))}
    </span>
  );
}

function ChoiceButton({ value, picked, item, revealed, onPick, className = '', children }) {
  const answered = Boolean(picked);
  const isPicked = picked === value;
  const isAnswer = value === item.answer;
  const state =
    (answered || revealed) && isAnswer ? 'right' : isPicked && value === UNKNOWN ? 'unknown' : isPicked ? 'wrong' : '';

  return (
    <button
      type="button"
      className={`listenChoice ${className} ${state}`}
      onClick={() => onPick(value)}
      disabled={answered}
    >
      {children}
      {state === 'right' ? <Check size={16} /> : null}
      {state === 'wrong' ? <X size={16} /> : null}
    </button>
  );
}

function Choices({ item, picked, revealed, onPick }) {
  const { choices } = item;
  const shared = { item, picked, revealed, onPick };

  if (choices.type === 'picture') {
    return (
      <div className="listenChoices">
        <img
          className="listenPicture"
          src={`/listening/${choices.image}`}
          alt={`${item.no}번 보기 사진 ${choices.labels.join(', ')}`}
        />
        <div className="listenLetters">
          {choices.labels.map((label) => (
            <ChoiceButton key={label} value={label} className="letter" {...shared}>
              {label}
            </ChoiceButton>
          ))}
          <ChoiceButton value={UNKNOWN} className="letter unknownChoice" {...shared}>
            모르겠음
          </ChoiceButton>
        </div>
      </div>
    );
  }

  if (choices.type === 'truefalse') {
    return (
      <div className="listenChoices">
        <div className="listenStatement">
          <span className="listenStar">★</span>
          <div>
            <Ruby words={choices.statement.words} showPinyin={revealed} />
            {revealed ? <p className="listenKo">{choices.statement.ko}</p> : null}
          </div>
        </div>
        <div className="listenLetters">
          {TRUE_FALSE.map((option) => (
            <ChoiceButton key={option.value} value={option.value} className="wide" {...shared}>
              {option.label}
            </ChoiceButton>
          ))}
          <ChoiceButton value={UNKNOWN} className="wide unknownChoice" {...shared}>
            모르겠음
          </ChoiceButton>
        </div>
      </div>
    );
  }

  return (
    <div className="listenChoices listenOptions">
      {choices.options.map((option) => (
        <ChoiceButton key={option.label} value={option.label} className="option" {...shared}>
          <span className="optionLabel">{option.label}</span>
          <span className="optionText">
            <Ruby words={option.words} showPinyin={revealed} />
            {revealed ? <span className="listenKo">{option.ko}</span> : null}
          </span>
        </ChoiceButton>
      ))}
      <ChoiceButton value={UNKNOWN} className="option unknownChoice" {...shared}>
        <span className="optionLabel">D</span>
        <span className="optionText">모르겠음</span>
      </ChoiceButton>
    </div>
  );
}

function Verdict({ item, picked }) {
  const grade = gradeOf(item, picked);
  if (!grade) return null;
  const text = {
    right: '정답이에요',
    wrong: `아쉬워요 · 정답은 ${answerLabel(item)}`,
    unknown: `정답은 ${answerLabel(item)}`
  }[grade];
  return <p className={`listenVerdict ${grade}`}>{text}</p>;
}

function Explanation({ item }) {
  return (
    <section className="listenReveal">
      <h3>대본</h3>
      <ol className="listenScript">
        {item.script.map((line, index) => (
          <li key={index} className="listenLine">
            {line.speaker ? (
              <span className={`listenSpeaker ${line.speaker === '问' ? 'question' : ''}`}>
                {SPEAKER_LABELS[line.speaker] ?? line.speaker}
              </span>
            ) : null}
            <div className="listenLineBody">
              <Ruby words={line.words} />
              <p className="listenKo">{line.ko}</p>
            </div>
          </li>
        ))}
      </ol>

      <h3>핵심 단어</h3>
      <ul className="listenVocab">
        {item.vocab.map((word) => (
          <li key={word.hanzi}>
            <strong>{word.hanzi}</strong>
            <span className="vocabPinyinText">{word.pinyin}</span>
            <span className="vocabMeaningText">{word.meaningKo}</span>
            {word.partOfSpeech ? <em>{word.partOfSpeech}</em> : null}
          </li>
        ))}
      </ul>

      <h3>문장 구조</h3>
      <ul className="listenGrammar">
        {item.grammar.map((note, index) => (
          <li key={index}>
            <strong>{note.pattern}</strong>
            <p>{note.note}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function Listening() {
  const initial = useMemo(loadPrefs, []);
  const [testId, setTestId] = useState(
    testIndex.some((test) => test.id === initial.testId) ? initial.testId : testIndex[0]?.id
  );
  const [part, setPart] = useState(initial.part ?? '전체');
  const [positions, setPositions] = useState(initial.positions ?? {});
  const [answers, setAnswers] = useState(loadAnswers);
  const [shown, setShown] = useState({}); // 고르지 않고 '대본 보기'로 펼친 문항
  const [test, setTest] = useState(null);
  const [error, setError] = useState('');
  const bodyRef = useRef(null);

  useEffect(() => {
    let alive = true;
    setTest(null);
    setError('');
    fetchTest(testId)
      .then((data) => alive && setTest(data))
      .catch((err) => alive && setError(err.message));
    return () => {
      alive = false;
    };
  }, [testId]);

  useEffect(() => {
    savePrefs({ testId, part, positions });
  }, [testId, part, positions]);

  const items = useMemo(
    () => (test ? test.items.filter((item) => part === '전체' || item.part === part) : []),
    [test, part]
  );
  const allItems = test?.items ?? [];
  const { playing, playItem, playRun, stop } = useClipPlayer(test ? `/listening/${test.audio}` : null, allItems);

  const savedNo = positions[testId];
  const index = Math.max(0, items.findIndex((item) => item.no === savedNo));
  const item = items[index];

  // 이어 듣기 중에는 들리는 문항으로 카드가 따라갑니다.
  useEffect(() => {
    if (playing?.mode === 'run' && playing.no && playing.no !== savedNo && items.some((i) => i.no === playing.no)) {
      setPositions((prev) => ({ ...prev, [testId]: playing.no }));
    }
  }, [playing, savedNo, items, testId]);

  useEffect(() => {
    bodyRef.current?.scrollTo?.({ top: 0 });
  }, [testId, item?.no]);

  const picks = answers[testId] ?? {};
  const picked = item ? picks[item.no] : undefined;
  const revealed = Boolean(item && (picked || shown[`${testId}-${item.no}`]));
  const counts = tally(allItems, picks);

  function goTo(nextIndex) {
    const next = items[nextIndex];
    if (!next) return;
    if (playing?.mode === 'item') stop();
    setPositions((prev) => ({ ...prev, [testId]: next.no }));
  }

  function changeTest(id) {
    stop();
    setTestId(id);
  }

  function changePart(nextPart) {
    stop();
    setPart(nextPart);
    const first = test?.items.find((i) => nextPart === '전체' || i.part === nextPart);
    if (first) setPositions((prev) => ({ ...prev, [testId]: first.no }));
  }

  function pick(value) {
    const next = { ...answers, [testId]: { ...picks, [item.no]: value } };
    setAnswers(next);
    saveAnswers(next);
  }

  function retry() {
    const { [item.no]: _removed, ...rest } = picks;
    const next = { ...answers, [testId]: rest };
    setAnswers(next);
    saveAnswers(next);
    setShown((prev) => ({ ...prev, [`${testId}-${item.no}`]: false }));
  }

  function toggleRun() {
    if (playing?.mode === 'run') stop();
    else playRun(items.slice(index));
  }

  const itemPlaying = playing?.mode === 'item' && playing.no === item?.no;
  const guide = test?.parts.find((p) => p.part === item?.part)?.guide;

  return (
    <section className="listenPanel">
      <div className="listenControls">
        <div className="lessonChips listenTests" aria-label="회차 선택">
          {testIndex.map((entry) => (
            <button
              key={entry.id}
              type="button"
              className={`lessonChip ${testId === entry.id ? 'active' : ''}`}
              onClick={() => changeTest(entry.id)}
            >
              {entry.id}
            </button>
          ))}
        </div>
        <div className="listenToolbar">
          <div className="memoToggles" aria-label="부분 선택">
            {PART_CHIPS.map((chip) => (
              <button
                key={chip}
                type="button"
                className={`memoToggle ${part === chip ? 'active' : ''}`}
                onClick={() => changePart(chip)}
              >
                {chip === '전체' ? '전체' : `${chip}부분`}
              </button>
            ))}
          </div>
          <button
            type="button"
            className={`memoPlay ${playing?.mode === 'run' ? 'active' : ''}`}
            onClick={toggleRun}
            disabled={!item}
          >
            {playing?.mode === 'run' ? <Square size={15} /> : <Headphones size={16} />}
            {playing?.mode === 'run' ? '멈추기' : '이어 듣기'}
          </button>
        </div>
        <p className="listCount">
          {allItems.length
            ? `맞힘 ${counts.right} · 틀림 ${counts.wrong} · 모름 ${counts.unknown} · 안 푼 문제 ${
                allItems.length - counts.right - counts.wrong - counts.unknown
              }`
            : ' '}
        </p>
      </div>

      <div className="listenBody" ref={bodyRef}>
        {error ? <p className="listEmpty">{error}</p> : null}
        {!error && !item ? <p className="listEmpty">불러오는 중…</p> : null}
        {item ? (
          <article className="listenCard">
            <div className="quizProgress">
              <span>
                {item.no}번 · {item.part}부분
              </span>
              <span>{guide}</span>
            </div>

            <div className="listenPlayRow">
              <button
                type="button"
                className={`listenPlay ${itemPlaying ? 'active' : ''}`}
                onClick={() => (itemPlaying ? stop() : playItem(item))}
              >
                {itemPlaying ? <Square size={18} /> : <Play size={18} />}
                {itemPlaying ? '멈추기' : '문제 듣기'}
              </button>
            </div>

            <Choices item={item} picked={picked} revealed={revealed} onPick={pick} />
            <Verdict item={item} picked={picked} />

            {revealed ? (
              <>
                <Explanation item={item} />
                <button type="button" className="subButton listenRetry" onClick={retry}>
                  <RotateCcw size={15} /> 이 문제 다시 풀기
                </button>
              </>
            ) : (
              <button
                type="button"
                className="subButton listenShow"
                onClick={() => setShown((prev) => ({ ...prev, [`${testId}-${item.no}`]: true }))}
              >
                <Eye size={15} /> 고르지 않고 대본 보기
              </button>
            )}
          </article>
        ) : null}
      </div>

      <div className="listenNav">
        <button type="button" className="listenNavButton" onClick={() => goTo(index - 1)} disabled={index <= 0}>
          <ChevronLeft size={18} /> 이전
        </button>
        <span>{items.length ? `${index + 1} / ${items.length}` : ''}</span>
        <button
          type="button"
          className="listenNavButton"
          onClick={() => goTo(index + 1)}
          disabled={index >= items.length - 1}
        >
          다음 <ChevronRight size={18} />
        </button>
      </div>
    </section>
  );
}
