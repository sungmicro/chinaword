import React from 'react';
import { basicTerms, glossary, learningPoints, roleTerm } from './writingGrammarHelp.js';

function Term({ term }) {
  return <details className="writingTerm"><summary>{term.label} <small>{term.category}</small></summary><p>{term.definition}</p><p><strong>찾는 질문</strong> {term.question}</p><p className="writingHelpExample">예: {term.example}</p></details>;
}
export function RoleHelp({ role, label }) {
  const term = roleTerm(role);
  return <details className="writingRoleHelp"><summary>{label} <span aria-hidden="true">ⓘ</span></summary><p><strong>{term.label} · {term.category}</strong><br />{term.definition}<br />{term.question}</p></details>;
}
export function WritingGrammarBasics({ item }) {
  const terms = basicTerms(item);
  return <details className="writingGrammarBasics"><summary>문법 기초 보기</summary><p className="writingHelpIntro">문장 성분은 문장 안에서 맡는 자리이고, 품사는 단어의 종류예요. 예를 들어 동사(품사)가 술어(문장 성분)의 중심이 될 수 있어요. 아래는 다른 문장의 예로 익히는 용어예요.</p><div className="writingTerms">{terms.map((term) => <Term key={term.id} term={term} />)}</div><details className="writingAllBasics"><summary>전체 문법 기초 · 的 / 地 / 得</summary><p>세 글자는 보통 de로 읽지만 자리가 달라요. 的는 명사를, 地는 뒤의 동작을 꾸미는 데 쓰이고, 得는 동작·상태 뒤의 보충 설명을 이어요. 글자 하나를 한국어 한 단어로 외우기보다 앞뒤 자리를 보세요.</p><ul><li>관형어 + 的 + 명사: 蓝色的车 · 파란 차</li><li>부사어 + 地 + 동사: 认真地画 · 진지하게 그리다</li><li>동사/형용사 + 得 + 보어: 跑得很快 · 달리는 것이 아주 빠르다</li></ul><div className="writingTerms">{Object.entries(glossary.terms).filter(([id]) => !terms.some((term) => term.id === id)).map(([id, term]) => <Term key={id} term={term} />)}</div></details></details>;
}
export function WritingGrammarLearning({ item, analysis }) {
  const points = learningPoints(item, analysis);
  if (!points.length) return null;
  return <section className="writingGrammarLearning" aria-label="이 문장의 문법 풀어보기"><h3>이 문장의 문법 풀어보기</h3>{points.map((point, index) => <article className="writingLearningPoint" key={index}><h4><span lang="zh-CN">{point.hanzi}</span> <span className="writingUsagePinyin">{point.pinyin}</span>{point.label ? ` · ${point.label}` : ''}</h4>{point.text !== point.hanzi ? <p><strong>문장 속 표현</strong> <span lang="zh-CN">{point.text}</span></p> : null}<p><strong>뜻과 느낌</strong> {point.meaning}</p><p><strong>이 문장에서는</strong> {point.explanation}</p><p className="writingUsagePattern"><strong>자리</strong> {point.pattern}</p>{point.termIds?.length ? <div className="writingTerms">{point.termIds.map((id) => <Term key={id} term={glossary.terms[id]} />)}</div> : null}{point.caution ? <p className="writingNote">{point.caution}</p> : null}</article>)}</section>;
}
