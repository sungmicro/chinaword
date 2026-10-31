import React from 'react';
import { groupText, tokenRoles } from './writingGrammar.js';
import { RoleHelp, WritingGrammarLearning } from './WritingGrammarHelp.jsx';

function TokenRoles({ item, analysis }) {
  return <details className="writingRoleDetails"><summary>제시 단어별 역할</summary><ul>{tokenRoles(item, analysis).map((token, index) => <li key={index}><span className="writingRoleToken" lang="zh-CN">{token.text}</span><div>{token.roles.map((role, part) => <div className="writingRolePart" key={part}><span lang="zh-CN">{role.text}</span> · <RoleHelp role={role.role} label={role.label} /></div>)}</div></li>)}</ul></details>;
}
function Analysis({ item, analysis }) {
  return <div className="writingGrammarAnalysis">
    <WritingGrammarLearning item={item} analysis={analysis} />
    <h3>문장 구조</h3>
    <div className="writingStructure">{analysis.groups.map((group, index) => <div className="writingGroup" key={index}><span lang="zh-CN">{groupText(item, group)}</span><RoleHelp role={group.role} label={group.label} /></div>)}</div>
    <h3>왜 이 순서인가</h3>
    <ol className="writingGrammarSteps">{analysis.steps.map((step, index) => <li key={index}>{step.text}</li>)}</ol>
    <p className="writingKeyRule"><strong>핵심 규칙</strong>{analysis.keyRule}</p>
    {analysis.caution ? <p className="writingGrammarCaution"><strong>주의</strong>{analysis.caution}</p> : null}
    {analysis.difference ? <p><strong>다른 정답과의 차이</strong> {analysis.difference}</p> : null}
  </div>;
}
export default function WritingGrammar({ item }) {
  const analyses = [...item.grammar.analyses].sort((a, b) => a.answerIndex - b.answerIndex);
  return <section className="writingGrammar" aria-label="어순 문법 해설">
    <Analysis item={item} analysis={analyses[0]} />
    {analyses.slice(1).map((analysis) => <details className="writingAlternative" key={analysis.answerIndex}><summary>정답 {analysis.answerIndex + 1} 문법 분석</summary><Analysis item={item} analysis={analysis} /><TokenRoles item={item} analysis={analysis} /></details>)}
    <TokenRoles item={item} analysis={analyses[0]} />
  </section>;
}
