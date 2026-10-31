import React, { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight, RotateCcw } from 'lucide-react';
import WritingGrammar from './WritingGrammar.jsx';
import { grammarIsVisible } from './writingGrammar.js';
import { fetchCached, readJson, writeJson } from './practiceStore';
import { gradeOrder, selectedText, tokensOf, toggleToken, validSelection, writingCounts } from './writingTools';

const STORE_KEY = 'sungmi-vocab-writing-v1';
const PREF_KEY = 'sungmi-vocab-writing-prefs-v1';

export default function Writing() {
  const [items, setItems] = useState([]);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [index, setIndex] = useState(() => {
    const saved = readJson(PREF_KEY, {}).index;
    return Number.isInteger(saved) && saved >= 0 && saved < 190 ? saved : 0;
  });
  const [records, setRecords] = useState(() => readJson(STORE_KEY, {}));
  useEffect(() => {
    let alive = true;
    setError('');
    fetchCached('/writing/hsk3-all.json', '쓰기').then((data) => {
      if (alive) setItems(data.items);
    }).catch((err) => alive && setError(err.message));
    return () => { alive = false; };
  }, [attempt]);
  const item = items[index];
  const record = item ? records[item.id] ?? {} : {};
  const selected = item ? validSelection(item, record.selected) : [];
  const revealed = ['right', 'wrong', 'unknown', 'revealed'].includes(record.status);
  const counts = writingCounts(items, records);
  function update(next) {
    const all = { ...records, [item.id]: next };
    setRecords(all);
    writeJson(STORE_KEY, all);
  }
  function reveal(unknown = false) {
    update({ selected, status: unknown ? 'unknown' : item.kind === 'hanzi' ? 'revealed' : gradeOrder(item, selected) ? 'right' : 'wrong' });
  }
  function go(next) {
    const position = Math.min(items.length - 1, Math.max(0, next));
    setIndex(position);
    writeJson(PREF_KEY, { index: position });
  }
  return (
    <section className="listenPanel writingPanel">
      <div className="listenControls">
        <p className="listCount">맞힘 {counts.right} · 틀림 {counts.wrong} · 모름 {counts.unknown} · 답 확인 {counts.revealed} · 안 푼 문제 {items.length - Object.values(counts).reduce((a, b) => a + b, 0)}</p>
      </div>
      <div className="listenBody">
        {error ? <div className="readError"><p className="listEmpty">{error}</p><button className="subButton" onClick={() => setAttempt((n) => n + 1)}>다시 받기</button></div> : !item ? <p className="listEmpty">불러오는 중…</p> : null}
        {item ? <article className="listenCard">
          <div className="quizProgress"><span>{index + 1} / {items.length}</span><span>{item.kind === 'reorder' ? '어순 배열' : '병음 보고 한자 떠올리기'}</span></div>
          {item.kind === 'reorder' ? <>
            <p className="writingGuide">단어를 문장 순서대로 누르세요. 다시 누르면 선택이 풀려요.</p>
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
            {item.answers.map((answer) => <p key={answer} className="writingAnswerText" lang="zh-CN">{answer}</p>)}
            {item.note ? <p className="writingNote">{item.note}</p> : null}
            {grammarIsVisible(item, record.status) ? <WritingGrammar key={item.id} item={item} /> : null}
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
