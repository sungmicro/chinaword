import glossary from './data/writingGrammarGlossary.json' with { type: 'json' };
import { groupText } from './writingGrammar.js';

export { glossary };
export function roleTerm(role) { return glossary.terms[glossary.roleTerms[role]]; }
// 공개 전에는 용어 정의만 반환합니다. 문항의 문자 범위·정답·개별 설명은 읽지 않습니다.
export function basicTerms(item) {
  const ids = new Set((item.grammar?.analyses ?? []).flatMap((analysis) => analysis.learning?.termIds ?? analysis.groups.map((group) => glossary.roleTerms[group.role])));
  return [...ids].map((id) => ({ id, ...glossary.terms[id] }));
}
export function learningPoints(item, analysis) {
  return (analysis.learning?.points ?? []).map((point) => ({ ...glossary.usages[point.usageId], ...point, text: groupText(item, point) }));
}
