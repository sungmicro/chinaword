// React 실제 컴포넌트를 SSR하여 모든 답의 공개 전/후 렌더링을 검사합니다.
import { createServer } from 'vite';
import { renderToStaticMarkup } from 'react-dom/server';
import React from 'react';
import fs from 'node:fs';
import assert from 'node:assert/strict';
const server = await createServer({ server: { middlewareMode: true } });
try {
  const { WritingGrammarBasics } = await server.ssrLoadModule('/src/WritingGrammarHelp.jsx');
  const { default: WritingGrammar } = await server.ssrLoadModule('/src/WritingGrammar.jsx');
  const items = JSON.parse(fs.readFileSync('public/writing/hsk3-all.json')).items.filter((x) => x.kind === 'reorder');
  let count = 0;
  for (const item of items) {
    const before = renderToStaticMarkup(React.createElement(WritingGrammarBasics, { item }));
    assert.ok(before.includes('문법 기초 보기'));
    assert.ok(!before.includes('이 문장의 문법 풀어보기'));
    for (const analysis of item.grammar.analyses) {
      count++;
      for (const point of analysis.learning.points) assert.ok(!before.includes(point.explanation), item.id);
    }
    const after = renderToStaticMarkup(React.createElement(WritingGrammar, { item }));
    assert.ok(after.includes('이 문장의 문법 풀어보기'));
    for (const analysis of item.grammar.analyses) for (const point of analysis.learning.points) assert.ok(after.includes(point.explanation.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#x27;')), item.id);
  }
  assert.equal(count, 98);
  console.log(`공개 전 95문항·공개 후 ${count}분석 SSR 통과`);
} finally { await server.close(); }
