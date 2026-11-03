import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, RotateCcw } from 'lucide-react';
import WritingGrammar from './WritingGrammar.jsx';
import { WritingGrammarBasics } from './WritingGrammarHelp.jsx';
import { WritingAnswers, WritingVocab } from './WritingStudy.jsx';
import { grammarIsVisible } from './writingGrammar.js';
import { fetchCached, readJson, writeJson } from './practiceStore';
import {
  WRITING_PART_CHIPS, WRITING_PART_GUIDES, gradeOrder, restoreWritingPrefs, selectedText, tokensOf, toggleToken,
  validSelection, writingCounts, writingExams, writingItemsOf, writingPart
} from './writingTools';

// HSK3 쓰기. 독해·듣기처럼 회차(시험지)를 고르고, 1부분(문장 순서 맞추기)·2부분(한자 쓰기)을 나눠 풉니다.
// 데이터는 19회차 190문항이 한 파일(public/writing/hsk3-all.json, tools/writing/generate.py)이라 받은 뒤 회차로 묶습니다.
const STORE_KEY = 'sungmi-vocab-writing-v1';
const PREF_KEY = 'sungmi-vocab-writing-prefs-v1';

export default function Writing() {
  const [allItems, setAllItems] = useState([]);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [prefs, setPrefs] = useState(null); // 데이터를 받은 뒤 저장값과 맞춰 정합니다.
  const [records, setRecords] = useState(() => readJson(STORE_KEY, {}));
  const bodyRef = useRef(null);
  useEffect(() => {
    let alive = true;
    setError('');
    fetchCached('/writing/hsk3-all.json', '쓰기').then((data) => {
      if (!alive) return;
      setAllItems(data.items);
      setPrefs((current) => current ?? restoreWritingPrefs(readJson(PREF_KEY, {}), data.items));
    }).catch((err) => alive && setError(err.message));
    return () => { alive = false; };
  }, [attempt]);
  useEffect(() => {
    if (prefs) writeJson(PREF_KEY, prefs);
  }, [prefs]);
  const exams = useMemo(() => writingExams(allItems), [allItems]);
  const testId = prefs?.testId;
  const part = prefs?.part ?? 1;
  const testItems = useMemo(() => writingItemsOf(allItems, testId, '전체'), [allItems, testId]);
  const items = useMemo(() => writingItemsOf(allItems, testId, part), [allItems, testId, part]);
  const index = Math.max(0, items.findIndex((entry) => entry.no === prefs?.positions[testId]));
  const item = items[index];
  useEffect(() => {
    bodyRef.current?.scrollTo?.({ top: 0 });
  }, [testId, item?.id]);
  const record = item ? records[item.id] ?? {} : {};
  const selected = item ? validSelection(item, record.selected) : [];
  const revealed = ['right', 'wrong', 'unknown', 'revealed'].includes(record.status);
  const counts = writingCounts(testItems, records);
  const solved = Object.values(counts).reduce((a, b) => a + b, 0);
  function update(next) {
    const all = { ...records, [item.id]: next };
    setRecords(all);
    writeJson(STORE_KEY, all);
  }
  function reveal(unknown = false) {
    update({ selected, status: unknown ? 'unknown' : item.kind === 'hanzi' ? 'revealed' : gradeOrder(item, selected) ? 'right' : 'wrong' });
  }
  function go(nextIndex) {
    const next = items[nextIndex];
    if (next) setPrefs((prev) => ({ ...prev, positions: { ...prev.positions, [testId]: next.no } }));
  }
  function changeTest(nextTest) {
    setPrefs((prev) => ({ ...prev, testId: nextTest }));
  }
  function changePart(nextPart) {
    const first = writingItemsOf(allItems, testId, nextPart)[0];
    setPrefs((prev) => ({ ...prev, part: nextPart, positions: first ? { ...prev.positions, [testId]: first.no } : prev.positions }));
  }
  return (
    <section className="listenPanel writingPanel">
      <div className="listenControls">
        <div className="lessonChips listenTests" aria-label="회차 선택">
          {exams.map((exam) => (
            <button key={exam} type="button" className={`lessonChip ${testId === exam ? 'active' : ''}`} onClick={() => changeTest(exam)}>
              {exam}
            </button>
          ))}
        </div>
        <div className="listenToolbar">
          <div className="memoToggles" aria-label="부분 선택">
            {WRITING_PART_CHIPS.map((chip) => (
              <button key={chip} type="button" className={`memoToggle ${part === chip ? 'active' : ''}`} aria-pressed={part === chip} onClick={() => changePart(chip)}>
                {chip === '전체' ? '전체' : `${chip}부분 · ${WRITING_PART_GUIDES[chip]}`}
              </button>
            ))}
          </div>
        </div>
        <p className="listCount">{testItems.length ? `맞힘 ${counts.right} · 틀림 ${counts.wrong} · 모름 ${counts.unknown} · 답 확인 ${counts.revealed} · 안 푼 문제 ${testItems.length - solved}` : ' '}</p>
      </div>
      <div className="listenBody" ref={bodyRef}>
        {error ? <div className="readError"><p className="listEmpty">{error}</p><button className="subButton" onClick={() => setAttempt((n) => n + 1)}>다시 받기</button></div> : !item ? <p className="listEmpty">불러오는 중…</p> : null}
        {item ? <article className="listenCard">
          <div className="quizProgress"><span>{item.no}번 · {writingPart(item)}부분</span><span>{item.kind === 'reorder' ? '어순 배열' : '병음 보고 한자 떠올리기'}</span></div>
          {item.kind === 'reorder' ? <>
            <p className="writingGuide">단어를 문장 순서대로 누르세요. 다시 누르면 선택이 풀려요.</p>
            <WritingGrammarBasics key={`basics-${item.id}-${revealed}`} item={item} />
            <div className="writingTokens" aria-label="문장 단어">
              {tokensOf(item).map((token) => {
                const order = selected.indexOf(token.id);
                return <button type="button" key={token.id} className={`writingToken ${order >= 0 ? 'selected' : ''}`} aria-pressed={order >= 0} aria-label={`${token.text}${order >= 0 ? `, 선택 순서 ${order + 1}` : ''}`} disabled={revealed} onClick={() => update({ selected: toggleToken(selected, token.id) })}>
                  <span lang="zh-CN">{token.text}</span>{order >= 0 ? <span className="writingBadge">{order + 1}</span> : null}
                </button>;
              })}
            </div>
            <p className="writingSentence writingSelected" lang="zh-CN" aria-live="polite">{selectedText(item, selected) || '…'}</p>
          </> : <>
            <p className="writingGuide">빈칸의 한자를 머릿속으로 떠올린 뒤 답을 확인하세요.</p>
            <p className="writingSentence" lang="zh-CN">{item.sentence.split('___')[0]}<ruby className="writingBlank">（　）<rt>{item.pinyin}</rt></ruby>{item.sentence.split('___')[1]}</p>
          </>}
          {revealed ? <section className="writingAnswer" aria-live="polite">
            <p className="listenVerdict">{record.status === 'right' ? '맞았어요' : record.status === 'wrong' ? '다시 살펴보세요' : record.status === 'unknown' ? '모르겠음으로 기록했어요' : '정답'}</p>
            <WritingAnswers item={item} />
            {item.note ? <p className="writingNote">{item.note}</p> : null}
            {grammarIsVisible(item, record.status) ? <WritingGrammar key={item.id} item={item} /> : null}
            <WritingVocab key={`vocab-${item.id}`} item={item} />
            <button type="button" className="subButton listenRetry" onClick={() => update({ selected: [] })}><RotateCcw size={15} /> 이 문제 다시 풀기</button>
          </section> : <div className="writingActions">
            <button type="button" className="listenPlay" disabled={item.kind === 'reorder' && selected.length !== item.tokens.length} onClick={() => reveal()}>답 확인</button>
            <button type="button" className="subButton" onClick={() => reveal(true)}>모르겠음</button>
          </div>}
        </article> : null}
      </div>
      <div className="listenNav">
        <button type="button" className="listenNavButton" disabled={index <= 0 || !item} onClick={() => go(index - 1)}><ChevronLeft size={18} /> 이전</button>
        <span>{item ? `${index + 1} / ${items.length}` : ''}</span>
        <button type="button" className="listenNavButton" disabled={!item || index >= items.length - 1} onClick={() => go(index + 1)}>다음 <ChevronRight size={18} /></button>
      </div>
    </section>
  );
}
