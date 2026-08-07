import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Check, RotateCcw, Volume2, X } from 'lucide-react';
import { buildLessonChips, matchesLessonChip } from './lessons';
import { buildToneChoices, isToneQuizable, patternLabel } from './tone';
import { applyResults, loadReview, pickQuestions, reviewCount } from './review';

const QUIZ_SIZE = 10;

function buildQuestion(item) {
  const choices = buildToneChoices(item.pinyin);
  return choices ? { item, choices } : null;
}

function StartScreen({ chips, range, onRange, poolSize, dueCount, onStart, onStartReview }) {
  return (
    <div className="quizStart">
      <div className="quizIntro">
        <h2>성조 시험</h2>
        <p>한자를 보고 발음을 들은 뒤, 성조가 맞는 병음을 고르세요. 한 번에 {QUIZ_SIZE}문항입니다.</p>
      </div>

      <div className="quizRange">
        <p className="quizRangeLabel">시험 범위</p>
        <div className="lessonChips" aria-label="시험 범위 선택">
          {chips.map((chip) => (
            <button
              key={chip}
              type="button"
              className={`lessonChip ${range === chip ? 'active' : ''}`}
              onClick={() => onRange(chip)}
            >
              {chip}
            </button>
          ))}
        </div>
        <p className="listCount">출제 가능한 단어 {poolSize}개</p>
      </div>

      <div className="quizStartActions">
        <button className="mainButton" onClick={onStart} disabled={!poolSize}>
          시험 시작
        </button>
        {dueCount ? (
          <button className="subButton" onClick={onStartReview}>
            <RotateCcw size={16} /> 틀렸던 {dueCount}개만 풀기
          </button>
        ) : (
          <p className="quizNote">틀린 문제는 자동으로 오답노트에 쌓여 다음 시험에 먼저 나옵니다.</p>
        )}
      </div>
    </div>
  );
}

function QuestionScreen({ question, index, total, picked, canSpeak, onPick, onSpeak, onNext }) {
  const { item, choices } = question;
  const answered = picked !== null;

  return (
    <div className="quizQuestion">
      <div className="quizProgress">
        <span>{index + 1} / {total}</span>
        <span>{item.itemType}</span>
      </div>

      <div className="quizPrompt">
        <p className="quizHanzi">{item.hanzi}</p>
        {canSpeak ? (
          <button type="button" className="quizListen" onClick={() => onSpeak(item.hanzi)}>
            <Volume2 size={16} /> 다시 듣기
          </button>
        ) : null}
      </div>

      <div className="quizChoices">
        {choices.map((choice) => {
          const isPicked = picked === choice.text;
          const reveal = answered && choice.correct;
          const wrong = answered && isPicked && !choice.correct;

          return (
            <button
              key={choice.text}
              type="button"
              className={`quizChoice ${reveal ? 'right' : ''} ${wrong ? 'wrong' : ''}`}
              onClick={() => onPick(choice)}
              disabled={answered}
            >
              <span className="quizChoiceText">{choice.text}</span>
              <span className="quizChoiceTone">{patternLabel(choice.pattern)}</span>
              {reveal ? <Check size={18} /> : null}
              {wrong ? <X size={18} /> : null}
            </button>
          );
        })}
      </div>

      {answered ? (
        <div className="quizFeedback">
          <p className="quizMeaning">{item.meaningKo}</p>
          <button className="mainButton" onClick={onNext}>
            {index + 1 === total ? '결과 보기' : '다음 문제'}
          </button>
        </div>
      ) : null}
    </div>
  );
}

function ResultScreen({ results, canSpeak, onSpeak, onRetryWrong, onRestart }) {
  const wrong = results.filter((result) => !result.correct);
  const score = results.length - wrong.length;

  return (
    <div className="quizResult">
      <div className="quizScore">
        <p className="quizScoreValue">{score} / {results.length}</p>
        <p className="quizScoreLabel">
          {wrong.length ? `틀린 ${wrong.length}개는 오답노트에 담았어요` : '전부 맞혔어요'}
        </p>
      </div>

      {wrong.length ? (
        <ul className="quizWrongList">
          {wrong.map((result) => (
            <li key={result.id}>
              <button
                type="button"
                className="quizWrongRow"
                onClick={() => canSpeak && onSpeak(result.hanzi)}
              >
                <div>
                  <p className="quizWrongHanzi">{result.hanzi}</p>
                  <p className="quizWrongPinyin">
                    {result.pinyin} <span>{patternLabel(result.pattern)}</span>
                  </p>
                  <p className="quizWrongMeaning">{result.meaningKo}</p>
                </div>
                <div className="quizWrongPicked">
                  <span>고른 답</span>
                  <strong>{result.picked}</strong>
                </div>
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      <div className="quizResultActions">
        {wrong.length ? (
          <button className="mainButton" onClick={onRetryWrong}>
            <RotateCcw size={16} /> 틀린 것만 다시 풀기
          </button>
        ) : null}
        <button className={wrong.length ? 'subButton' : 'mainButton'} onClick={onRestart}>
          새 시험
        </button>
      </div>
    </div>
  );
}

export default function ToneQuiz({ items, canSpeak, onSpeak }) {
  const [range, setRange] = useState('전체');
  const [stage, setStage] = useState('ready');
  const [questions, setQuestions] = useState([]);
  const [index, setIndex] = useState(0);
  const [picked, setPicked] = useState(null);
  const [results, setResults] = useState([]);
  const [review, setReview] = useState(() => loadReview());

  const quizableItems = useMemo(() => items.filter((item) => item.itemType === '단어' && isToneQuizable(item)), [items]);
  const chips = useMemo(() => buildLessonChips(quizableItems), [quizableItems]);
  const pool = useMemo(
    () => quizableItems.filter((item) => matchesLessonChip(item, range)),
    [quizableItems, range]
  );
  const dueCount = useMemo(() => reviewCount(review, pool), [review, pool]);

  const current = questions[index] ?? null;

  // 문제가 바뀌면 발음을 한 번 들려줍니다. (시험 시작 버튼이 사용자 조작이라 이후 재생이 허용됩니다.)
  const spokenFor = useRef(null);
  useEffect(() => {
    if (stage !== 'playing' || !current || !canSpeak) return;
    const key = `${index}-${current.item.id}`;
    if (spokenFor.current === key) return;
    spokenFor.current = key;
    onSpeak(current.item.hanzi);
  }, [stage, current, index, canSpeak, onSpeak]);

  const startWith = useCallback((sourceItems) => {
    const built = sourceItems.map(buildQuestion).filter(Boolean);
    if (!built.length) return;
    spokenFor.current = null;
    setQuestions(built);
    setIndex(0);
    setPicked(null);
    setResults([]);
    setStage('playing');
  }, []);

  function startQuiz() {
    startWith(pickQuestions(pool, review, QUIZ_SIZE));
  }

  function startReview() {
    const due = pool.filter((item) => review[item.id]);
    startWith(due.slice(0, QUIZ_SIZE));
  }

  function retryWrong() {
    const wrongItems = results.filter((result) => !result.correct).map((result) => result.item);
    startWith(wrongItems);
  }

  function pick(choice) {
    if (picked !== null || !current) return;
    setPicked(choice.text);

    const { item, choices } = current;
    const answer = choices.find((entry) => entry.correct);
    setResults((prev) => [
      ...prev,
      {
        id: item.id,
        item,
        hanzi: item.hanzi,
        pinyin: answer.text,
        pattern: answer.pattern,
        meaningKo: item.meaningKo,
        picked: choice.text,
        correct: choice.correct
      }
    ]);

    // 오답이면 정답 발음을 한 번 더 들려줍니다.
    if (!choice.correct && canSpeak) onSpeak(item.hanzi);
  }

  function goNext() {
    if (index + 1 < questions.length) {
      setIndex(index + 1);
      setPicked(null);
      return;
    }

    setReview((prev) => applyResults(prev, results));
    setStage('done');
  }

  if (stage === 'playing' && current) {
    return (
      <section className="quizPanel" aria-label="성조 시험">
        <QuestionScreen
          question={current}
          index={index}
          total={questions.length}
          picked={picked}
          canSpeak={canSpeak}
          onPick={pick}
          onSpeak={onSpeak}
          onNext={goNext}
        />
      </section>
    );
  }

  if (stage === 'done') {
    return (
      <section className="quizPanel" aria-label="성조 시험 결과">
        <ResultScreen
          results={results}
          canSpeak={canSpeak}
          onSpeak={onSpeak}
          onRetryWrong={retryWrong}
          onRestart={() => setStage('ready')}
        />
      </section>
    );
  }

  return (
    <section className="quizPanel" aria-label="성조 시험 시작">
      <StartScreen
        chips={chips}
        range={range}
        onRange={setRange}
        poolSize={pool.length}
        dueCount={dueCount}
        onStart={startQuiz}
        onStartReview={startReview}
      />
    </section>
  );
}
