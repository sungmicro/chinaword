import React from 'react';
import { RotateCcw } from 'lucide-react';
import { ExplainGrammar, ExplainVocab, Ruby } from './hskParts';
import { writingStudySource } from './writingStudy.js';
import { countEssayChars, usesWord } from './writingTools';

// HSK 3.0 공식 샘플 쓰기의 새 문항 카드.
// 사진 문장(PictureSentence): 사진과 제시어를 보고 문장을 써 본 뒤 공식 참고답안·해설을 봅니다.
// 짧은 글(Essay): 80자 이상 글쓰기. 공식 답안이 «略»라 예시 글은 AI가 쓴 것이고 🤖로 표시합니다.
// 기록은 문항 id마다 { text, status }이고, status는 'revealed'(답 확인)·'unknown'(모르겠음)입니다.

function Explain({ explain, source, grammarTitle = '문장 구조' }) {
  if (!explain) return null;
  return (
    <>
      {explain.vocab?.length ? (
        <>
          <h3>핵심 단어</h3>
          <ExplainVocab vocab={explain.vocab} source={source} />
        </>
      ) : null}
      {explain.grammar?.length ? (
        <>
          <h3>{grammarTitle}</h3>
          <ExplainGrammar grammar={explain.grammar} source={source} />
        </>
      ) : null}
    </>
  );
}

function ReferenceAnswers({ item }) {
  const answers = item.explain?.answers ?? [];
  if (!answers.length) {
    return item.answers.map((answer) => (
      <p key={answer} className="writingAnswerText" lang="zh-CN">
        {answer}
      </p>
    ));
  }
  return (
    <section className="writingStudyAnswers" aria-label="참고 답안과 뜻">
      {answers.map((answer, index) => (
        <div className="writingStudyAnswer" key={index}>
          {answers.length > 1 ? <p className="writingAnswerLabel">참고 답안 {index + 1}</p> : null}
          <div lang="zh-CN">
            <Ruby words={answer.words} />
          </div>
          <p className="listenKo" lang="ko">
            {answer.ko}
          </p>
        </div>
      ))}
    </section>
  );
}

// 3급 1부분 한자 쓰기 문항에 해설(explain { words, ko, vocab })이 있으면 답 아래에 보여 줍니다.
export function HanziExplain({ item }) {
  const { explain } = item;
  if (!explain) return null;
  return (
    <section className="writingStudyAnswers" aria-label="문장과 뜻">
      {explain.words ? (
        <div className="writingStudyAnswer">
          <div lang="zh-CN">
            <Ruby words={explain.words} />
          </div>
          {explain.ko ? (
            <p className="listenKo" lang="ko">
              {explain.ko}
            </p>
          ) : null}
        </div>
      ) : null}
      <div className="writingStudyVocab">
        <Explain explain={{ vocab: explain.vocab, grammar: explain.grammar }} source={writingStudySource(item)} />
      </div>
    </section>
  );
}

export function PictureSentence({ item, base, record, onChange }) {
  const text = record.text ?? '';
  const revealed = record.status === 'revealed' || record.status === 'unknown';
  const used = usesWord(text, item.word);
  const hint = !text.trim()
    ? `제시어 «${item.word}»를 꼭 넣어야 해요`
    : used
      ? `제시어 «${item.word}»를 넣었어요`
      : `제시어 «${item.word}»가 아직 없어요`;

  return (
    <>
      <p className="writingGuide">사진을 보고 제시어를 넣어 문장을 하나 써 보세요.</p>
      <img className="writingPicture" src={`${base}/${item.image}`} alt={`${item.no}번 사진`} />
      <p className="writingWord">
        <span className="writingWordLabel">제시어</span>
        <ruby lang="zh-CN">
          {item.word}
          {item.wordPinyin ? <rt>{item.wordPinyin}</rt> : null}
        </ruby>
      </p>
      <textarea
        className="writingInput"
        lang="zh-CN"
        rows={2}
        value={text}
        placeholder="여기에 중국어 문장을 써 보세요"
        aria-label={`${item.no}번 내 문장`}
        onChange={(event) => onChange({ ...record, text: event.target.value })}
      />
      <p className={`writingHint${used ? ' ok' : ''}`} aria-live="polite">
        {hint}
      </p>
      {revealed ? (
        <section className="writingAnswer" aria-live="polite">
          <p className="listenVerdict">{record.status === 'unknown' ? '모르겠음으로 기록했어요 · 참고 답안' : '참고 답안'}</p>
          <ReferenceAnswers item={item} />
          <div className="writingStudyVocab">
            <Explain explain={item.explain} source={writingStudySource(item)} />
          </div>
          <button type="button" className="subButton listenRetry" onClick={() => onChange({ text })}>
            <RotateCcw size={15} /> 이 문제 다시 풀기
          </button>
        </section>
      ) : (
        <div className="writingActions">
          <button type="button" className="listenPlay" onClick={() => onChange({ text, status: 'revealed' })}>
            답 확인
          </button>
          <button type="button" className="subButton" onClick={() => onChange({ text, status: 'unknown' })}>
            모르겠음
          </button>
        </div>
      )}
    </>
  );
}

export function Essay({ item, base, record, onChange }) {
  const text = record.text ?? '';
  const min = item.minChars ?? 80;
  const count = countEssayChars(text);
  const modelText = (item.model?.lines ?? []).map((line) => line.words.map(([hanzi]) => hanzi).join('')).join('');

  function opened(event) {
    if (event.currentTarget.open && !record.status) onChange({ text, status: 'revealed' });
  }

  return (
    <>
      <p className="writingGuide">
        {min}자 이상 짧은 글을 써 보세요. 원고지처럼 문장부호도 한 칸으로 세고, 띄어쓰기는 세지 않아요.
      </p>
      {item.prompt ? (
        <div className="essayPrompt">
          <div lang="zh-CN">
            <Ruby words={item.prompt.words} />
          </div>
          {item.prompt.ko ? (
            <p className="listenKo" lang="ko">
              {item.prompt.ko}
            </p>
          ) : null}
        </div>
      ) : null}
      {item.image ? <img className="writingPicture" src={`${base}/${item.image}`} alt={`${item.no}번 사진`} /> : null}
      <textarea
        className="writingInput essayInput"
        lang="zh-CN"
        rows={6}
        value={text}
        placeholder="여기에 중국어로 글을 써 보세요"
        aria-label={`${item.no}번 내 글`}
        onChange={(event) => onChange({ ...record, text: event.target.value })}
      />
      <p className={`essayCount${count >= min ? ' ok' : ''}`} aria-live="polite">
        {count}자 / {min}자 · {count >= min ? '기준을 넘었어요' : `${min - count}자 더 써 보세요`}
      </p>
      {item.model ? (
        <details className="essayModel" onToggle={opened}>
          <summary>{item.aiWritten ? '🤖 AI 예시 글 보기' : '예시 글 보기'}</summary>
          {item.aiWritten ? (
            <p className="writingNote">🤖 AI가 쓴 예시 글이에요. 공식 답안이 아니니 표현을 참고만 하세요.</p>
          ) : null}
          <div className="essayModelLines">
            {item.model.lines.map((line, index) => (
              <div className="writingStudyAnswer" key={index}>
                <div lang="zh-CN">
                  <Ruby words={line.words} />
                </div>
                <p className="listenKo" lang="ko">
                  {line.ko}
                </p>
              </div>
            ))}
          </div>
          <p className="writingNote">예시 글 {countEssayChars(modelText)}자</p>
          <div className="writingStudyVocab">
            <Explain explain={item.explain} source={writingStudySource(item)} grammarTitle="핵심 표현" />
          </div>
        </details>
      ) : null}
    </>
  );
}
