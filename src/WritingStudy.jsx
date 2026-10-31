import React from 'react';
import { Ruby, ExplainVocab } from './hskParts';
import { studyAnswers, writingStudySource } from './writingStudy.js';

export function WritingAnswers({ item }) {
  const answers = studyAnswers(item);
  if (!answers.length) return item.answers.map((answer) => <p key={answer} className="writingAnswerText" lang="zh-CN">{answer}</p>);
  return <section className="writingStudyAnswers" aria-label="완성 문장과 뜻">
    {answers.map((answer) => <div className="writingStudyAnswer" key={answer.answerIndex}>
      {answers.length > 1 ? <p className="writingAnswerLabel">정답 {answer.answerIndex + 1}</p> : null}
      <div lang="zh-CN"><Ruby words={answer.words} /></div>
      <p className="listenKo" lang="ko">{answer.ko}</p>
    </div>)}
  </section>;
}

export function WritingVocab({ item }) {
  if (item.kind !== 'reorder' || !item.study) return null;
  return <section className="writingStudyVocab" aria-label="핵심 단어장">
    <h3>핵심 단어장</h3>
    <ExplainVocab vocab={item.study.vocab} source={writingStudySource(item)} />
  </section>;
}
