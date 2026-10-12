import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, Eye, Languages, RotateCcw } from 'lucide-react';
import testIndex from './data/reading-index.json';
import { UNKNOWN, fetchCached, readJson, tally, writeJson } from './practiceStore';
import { ChoiceButton, ExplainGrammar, ExplainVocab, Ruby, Verdict } from './hskParts';

// HSK 공식 모의고사 독해. 문항마다 '읽기 → 고르기(또는 모르겠음) → 정답·해설'.
// 회차 데이터 public/reading/<회차>.json은 tools/reading/assemble.py가 만듭니다.

const ANSWER_KEY = 'sungmi-vocab-reading-v1';
const PREF_KEY = 'sungmi-vocab-reading-prefs-v1';
const PART_CHIPS = ['전체', 1, 2, 3];

const fetchTest = (id) => fetchCached(`/reading/${id}.json`, id);
const hanziOf = (words) => words.map(([hanzi]) => hanzi).join('');

// 1·2부분은 다섯 문항이 묶음 보기를 같이 쓰고, 3부분은 문항마다 A·B·C가 있습니다.
function choicesOf(test, item) {
  if (item.part === 3) return { options: item.options ?? [], example: null };
  const group = test.groups.find((entry) => entry.id === item.group);
  return { options: group?.options ?? [], example: group?.example ?? null };
}

function answerText(item, options) {
  if (item.part !== 2) return item.answer;
  const word = options.find((option) => option.label === item.answer);
  return word ? `${item.answer} ${hanziOf(word.words)}` : item.answer;
}

// 지문(3부분), 문항 문장(1부분), 빈칸 문장(2부분). 2부분은 답을 고르면 빈칸이 채워집니다.
function Lines({ item, showPinyin, revealed }) {
  return (
    <div className="readLines">
      {item.lines.map((line, index) => (
        <div className="readLine" key={index}>
          {line.speaker ? <span className="listenSpeaker">{line.speaker}</span> : null}
          <div className="listenLineBody">
            <Ruby
              words={line.words}
              tight
              showPinyin={showPinyin || revealed}
              blank={line.blank ?? null}
              fillBlank={revealed}
            />
            {revealed ? <p className="listenKo">{line.ko}</p> : null}
          </div>
        </div>
      ))}
    </div>
  );
}

function Question({ question, showPinyin, revealed }) {
  return (
    <div className="listenStatement">
      <span className="listenStar">★</span>
      <div>
        <Ruby words={question.words} tight showPinyin={showPinyin || revealed} />
        {revealed ? <p className="listenKo">{question.ko}</p> : null}
      </div>
    </div>
  );
}

function Choices({ item, options, example, picked, revealed, showPinyin, onPick }) {
  const shared = { item, picked, revealed, onPick };
  const wordBank = item.part === 2;
  const kind = wordBank ? 'readWord' : 'option';
  return (
    <div className={`listenChoices ${wordBank ? 'readBank' : 'listenOptions'}`}>
      {options.map((option) => {
        const isExample = option.label === example;
        return (
          <ChoiceButton key={option.label} value={option.label} className={kind} blocked={isExample} {...shared}>
            <span className="optionLabel">{option.label}</span>
            <span className="optionText">
              <Ruby words={option.words} tight showPinyin={showPinyin || revealed} />
              {revealed ? <span className="listenKo">{option.ko}</span> : null}
            </span>
            {isExample ? <span className="readExampleTag">예시</span> : null}
          </ChoiceButton>
        );
      })}
      <ChoiceButton value={UNKNOWN} className={`${kind} unknownChoice`} {...shared}>
        <span className="optionText">모르겠음</span>
      </ChoiceButton>
    </div>
  );
}

// 1부분: 짝지은 두 문장을 대화 순서대로 이어 보여줍니다.
function PairDialogue({ item, options }) {
  const partner = options.find((option) => option.label === item.answer);
  if (!partner) return null;
  const own = { key: 'item', tag: `${item.no}`, words: item.lines[0].words, ko: item.lines[0].ko };
  const other = { key: 'option', tag: partner.label, words: partner.words, ko: partner.ko };
  const order = item.pair === 'option-first' ? [other, own] : [own, other];
  return (
    <>
      <h3>이어 읽기</h3>
      <ol className="listenScript">
        {order.map((line) => (
          <li key={line.key} className="listenLine">
            <span className="listenSpeaker">{line.tag}</span>
            <div className="listenLineBody">
              <Ruby words={line.words} />
              <p className="listenKo">{line.ko}</p>
            </div>
          </li>
        ))}
      </ol>
    </>
  );
}

function Explanation({ item, options, source }) {
  const { basis, distractors, breakdown, vocab, grammar } = item.explain;
  const optionOf = (label) => options.find((option) => option.label === label);
  return (
    <section className="listenReveal">
      {item.part === 1 ? <PairDialogue item={item} options={options} /> : null}

      <h3>정답 근거</h3>
      <div className="readBasis">
        <p className="readQuote">{basis.quote}</p>
        <p>{basis.note}</p>
      </div>

      {distractors.length ? (
        <>
          <h3>오답 이유</h3>
          <ul className="readDistractors">
            {distractors.map((entry) => (
              <li key={entry.label}>
                <span className="optionLabel">{entry.label}</span>
                <div>
                  <p className="readDistractorText">{hanziOf(optionOf(entry.label)?.words ?? [])}</p>
                  <p>{entry.note}</p>
                </div>
              </li>
            ))}
          </ul>
        </>
      ) : null}

      <h3>끊어 읽기</h3>
      <ul className="readBreakdown">
        {breakdown.map((sentence, index) => (
          <li key={index}>
            <div className="readChunks">
              {sentence.chunks.map((chunk, chunkIndex) => (
                <span className="readChunk" key={chunkIndex}>
                  <span className="readChunkText">{chunk.text}</span>
                  <span className="readChunkRole">{chunk.role}</span>
                </span>
              ))}
            </div>
            <p>{sentence.note}</p>
          </li>
        ))}
      </ul>

      <h3>단어</h3>
      <ExplainVocab vocab={vocab} source={source} />

      <h3>문법</h3>
      <ExplainGrammar grammar={grammar} source={source} />
    </section>
  );
}

export default function Reading() {
  const initial = useMemo(() => readJson(PREF_KEY, {}), []);
  const [testId, setTestId] = useState(
    testIndex.some((entry) => entry.id === initial.testId) ? initial.testId : testIndex[0]?.id
  );
  const [part, setPart] = useState(PART_CHIPS.includes(initial.part) ? initial.part : '전체');
  const [positions, setPositions] = useState(
    initial.positions && typeof initial.positions === 'object' ? initial.positions : {}
  );
  const [showPinyin, setShowPinyin] = useState(initial.showPinyin === true);
  const [answers, setAnswers] = useState(() => readJson(ANSWER_KEY, {}));
  const [shown, setShown] = useState({}); // 고르지 않고 '해설 보기'로 펼친 문항
  const [test, setTest] = useState(null);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0); // '다시 받기'를 누를 때마다 늘려 같은 회차를 다시 받습니다.
  const bodyRef = useRef(null);

  useEffect(() => {
    if (!testId) return undefined;
    let alive = true;
    setTest(null);
    setError('');
    fetchTest(testId)
      .then((data) => alive && setTest(data))
      .catch((err) => alive && setError(err.message));
    return () => {
      alive = false;
    };
  }, [testId, attempt]);

  useEffect(() => {
    writeJson(PREF_KEY, { testId, part, positions, showPinyin });
  }, [testId, part, positions, showPinyin]);

  const items = useMemo(
    () => (test ? test.items.filter((entry) => part === '전체' || entry.part === part) : []),
    [test, part]
  );
  const allItems = test?.items ?? [];
  const savedNo = positions[testId];
  const index = Math.max(0, items.findIndex((entry) => entry.no === savedNo));
  const item = items[index];

  useEffect(() => {
    bodyRef.current?.scrollTo?.({ top: 0 });
  }, [testId, item?.no]);

  const picks = answers[testId] ?? {};
  const picked = item ? picks[item.no] : undefined;
  const revealed = Boolean(item && (picked || shown[`${testId}-${item.no}`]));
  const counts = tally(allItems, picks);
  const { options, example } = item && test ? choicesOf(test, item) : { options: [], example: null };
  const guide = test?.parts.find((entry) => entry.part === item?.part)?.guide;

  function goTo(nextIndex) {
    const next = items[nextIndex];
    if (next) setPositions((prev) => ({ ...prev, [testId]: next.no }));
  }

  function changePart(nextPart) {
    setPart(nextPart);
    const first = test?.items.find((entry) => nextPart === '전체' || entry.part === nextPart);
    if (first) setPositions((prev) => ({ ...prev, [testId]: first.no }));
  }

  function pick(value) {
    const next = { ...answers, [testId]: { ...picks, [item.no]: value } };
    setAnswers(next);
    writeJson(ANSWER_KEY, next);
  }

  function retry() {
    const { [item.no]: _removed, ...rest } = picks;
    const next = { ...answers, [testId]: rest };
    setAnswers(next);
    writeJson(ANSWER_KEY, next);
    setShown((prev) => ({ ...prev, [`${testId}-${item.no}`]: false }));
  }

  return (
    <section className="listenPanel">
      <div className="listenControls">
        <div className="lessonChips listenTests" aria-label="회차 선택">
          {testIndex.map((entry) => (
            <button
              key={entry.id}
              type="button"
              className={`lessonChip ${testId === entry.id ? 'active' : ''}`}
              onClick={() => setTestId(entry.id)}
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
            className={`memoToggle readPinyinToggle ${showPinyin ? 'active' : ''}`}
            onClick={() => setShowPinyin((on) => !on)}
            aria-pressed={showPinyin}
          >
            <Languages size={14} /> 병음 보기
          </button>
        </div>
        <p className="listCount">
          {allItems.length
            ? `맞힘 ${counts.right} · 틀림 ${counts.wrong} · 모름 ${counts.unknown} · 안 푼 문제 ${
                allItems.length - counts.right - counts.wrong - counts.unknown
              }`
            : ' '}
        </p>
      </div>

      <div className="listenBody" ref={bodyRef}>
        {error ? (
          <div className="readError">
            <p className="listEmpty">{error}</p>
            <button type="button" className="subButton" onClick={() => setAttempt((count) => count + 1)}>
              <RotateCcw size={15} /> 다시 받기
            </button>
          </div>
        ) : null}
        {!error && !item ? <p className="listEmpty">불러오는 중…</p> : null}
        {item ? (
          <article className="listenCard">
            <div className="quizProgress">
              <span>
                {item.no}번 · {item.part}부분
              </span>
              <span>{guide}</span>
            </div>

            <Lines item={item} showPinyin={showPinyin} revealed={revealed} />
            {item.question ? <Question question={item.question} showPinyin={showPinyin} revealed={revealed} /> : null}
            <Choices
              item={item}
              options={options}
              example={example}
              picked={picked}
              revealed={revealed}
              showPinyin={showPinyin}
              onPick={pick}
            />
            <Verdict item={item} picked={picked} answerText={answerText(item, options)} />

            {revealed ? (
              <>
                <Explanation item={item} options={options} source={`${testId} 독해 ${item.no}번`} />
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
                <Eye size={15} /> 고르지 않고 해설 보기
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
