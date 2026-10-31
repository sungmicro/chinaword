import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { studyAnswers, writingStudySource } from './writingStudy.js';
import { wordEntry, wordKey, toggleEntry } from './myVocab.js';

const items = JSON.parse(fs.readFileSync(new URL('../public/writing/hsk3-all.json', import.meta.url))).items;

test('95개 어순 문항의 98개 공식답 전체 병음과 뜻을 정답 순서로 보존한다', () => {
  let count = 0;
  for (const item of items) {
    const answers = studyAnswers(item);
    if (item.kind === 'hanzi') {
      assert.deepEqual(answers, []);
      assert.equal(item.study, undefined);
      continue;
    }
    assert.deepEqual(answers.map((answer) => answer.answerIndex), item.answers.map((_, index) => index));
    for (const answer of answers) {
      count++;
      assert.equal(answer.words.map(([hanzi]) => hanzi).join(''), item.answers[answer.answerIndex]);
      assert.ok(answer.ko.trim());
      answer.words.forEach(([hanzi, pinyin]) => {
        if (/[\p{Script=Han}\d]/u.test(hanzi)) assert.ok(pinyin.trim());
      });
    }
  }
  assert.equal(count, 98);
});

test('쓰기 핵심 단어를 기존 단어장 형식과 키로 담고 빼며 출처를 보존한다', () => {
  for (const item of items.filter((entry) => entry.kind === 'reorder')) {
    for (const word of item.study.vocab) {
      const entry = wordEntry(word, writingStudySource(item));
      assert.equal(entry.key, wordKey(word.hanzi, word.pinyin));
      for (const key of ['hanzi', 'pinyin', 'meaningKo', 'partOfSpeech']) assert.equal(entry[key], word[key]);
      assert.equal(entry.source, `${item.exam} 쓰기 ${item.no}번`);
      const saved = toggleEntry([], entry);
      assert.equal(saved.length, 1);
      assert.deepEqual(toggleEntry(saved, entry), []);
    }
  }
});
