export function studyAnswers(item) {
  if (item.kind !== 'reorder' || !item.study) return [];
  return [...item.study.answers].sort((a, b) => a.answerIndex - b.answerIndex);
}

export function writingStudySource(item) {
  return `${item.exam} 쓰기 ${item.no}번`;
}
