// 표시는 원래 제시 토큰의 문자 범위에서 계산합니다.
export function groupText(item, group) {
  return group.parts.map(({ token, start, end }) => [...item.tokens[token]].slice(start, end).join('')).join('');
}
export function tokenRoles(item, analysis) {
  return item.tokens.map((text, token) => ({ text, roles: analysis.groups.flatMap((group) => group.parts.filter((part) => part.token === token).map((part) => ({ text: groupText(item, { parts: [part] }), label: group.label }))) }));
}
export function grammarIsVisible(item, status) {
  return item?.kind === 'reorder' && Boolean(item.grammar) && ['right', 'wrong', 'unknown', 'revealed'].includes(status);
}
