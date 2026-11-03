#!/usr/bin/env python3
"""paper.json(원문·정답) + enrich-*.json(병음·해석·해설)을 합쳐 앱이 읽는
public/reading/<회차>.json을 만들고, 독해 핵심 단어를 단어장(vocab.json)에 넣는다.

  assemble.py H31001 H31002 ... --work ~/hsk-reading-work --repo .
  assemble.py H31001 --work ~/hsk-reading-work --repo . --check   # 검사만, 파일을 쓰지 않음

쓰기 전에 해설을 기계적으로 검사한다. 단어 묶음의 한자를 이으면 원문과 같아야 하고(2부분은 빈칸 단어를
'（）'로 바꾼 결과), 해설 칸이 기준 개수대로 차 있어야 한다. pypinyin과 음절이 다른 단어는 목록으로만 보여준다.

해설의 단어·문법은 듣기 탭과 같은 형식으로 맞춰 쓴다(normalize_explain): 단어는 한자·병음·품사·뜻만,
문법은 패턴·설명에 사람이 새로 지은 예문(example)이 있으면 그것까지 남긴다. 예전 해설 파일의 끊어 읽기(breakdown)·
단어 용법(usage)·단어 예문(example)과, 지문 문장을 되풀이한 자동 문법 예문은 버린다.
"""
import argparse
import json
import sys
from pathlib import Path

from hsktext import check_words, join_words, words_to_pinyin

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vocab_fixes import CardIds, fix_vocab, vocab_problems  # noqa: E402  tools/vocab_fixes.py
from mine_refresh import refresh_after_write  # noqa: E402  tools/mine_refresh.py

LESSON = 'HSK3 독해'
PART_GUIDES = {
    1: '서로 이어지는 문장 짝 찾기',
    2: '빈칸에 알맞은 단어 고르기',
    3: '짧은 글을 읽고 질문에 답하기',
}
BLANK = '（）'


def load_enrich(base):
    groups, items = {}, {}
    for path in sorted(base.glob('enrich-*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        for group in data.get('groups', []):
            groups[group['id']] = group
        for item in data.get('items', []):
            items[item['no']] = item
    return groups, items


def check_annotated(annotated, source_text, where, problems, reading_diffs):
    check_words(annotated.get('words') or [], source_text, where, problems, reading_diffs)
    if not (annotated.get('ko') or '').strip():
        problems.append(f'{where}: 해석 없음')


def check_example(example, where, problems, reading_diffs):
    if not example.get('zh') or not example.get('words') or not example.get('ko'):
        problems.append(f'{where}: 예문(zh·words·ko) 없음')
        return
    check_words(example['words'], example['zh'], where, problems, reading_diffs)


VOCAB_KEYS = ('hanzi', 'pinyin', 'partOfSpeech', 'meaningKo')


def grammar_note(entry):
    """예전 독해 문법의 짧은 뜻(meaningKo)은 듣기처럼 설명 앞에 ‘뜻’으로 붙인다."""
    note = (entry.get('note') or '').strip()
    meaning = (entry.get('meaningKo') or '').strip()
    if not meaning or meaning in note:
        return note
    return f'‘{meaning}’. {note}' if note else f'‘{meaning}’.'


def written_example(example, quote, texts):
    """문법 예문은 선택이다. 사람이 새로 지은 예문만 남긴다.

    auto_enrich가 만든 예전 독해 문법 예문(H31006 이후)은 정답 근거 인용(basis.quote)을 그대로 되풀이했고,
    사람이 쓴 예문(H31001~H31005)은 문항 글에 없는 새 문장이다. 그래서 예문이 정답 근거 인용과 같거나
    문항 화면의 문장(지문·질문·보기) 안에 그대로 있으면 지문 반복으로 보고 버린다.
    """
    if not isinstance(example, dict):
        return None
    zh = (example.get('zh') or '').strip()
    if not zh or zh == (quote or '').strip() or any(zh in text for text in texts):
        return None
    return {'zh': zh, 'words': example.get('words') or [], 'ko': example.get('ko', '')}


def normalize_grammar(entry, quote, texts):
    grammar = {'pattern': entry.get('pattern', ''), 'note': grammar_note(entry)}
    example = written_example(entry.get('example'), quote, texts)
    if example:
        grammar['example'] = example
    return grammar


def normalize_explain(explain, texts=(), where=None):
    """해설의 단어·문법을 듣기 탭 형식으로 맞춘다. 정답 근거·오답 이유는 그대로 둔다.

    texts: 그 문항 화면에 나오는 문장들. 문법 예문이 지문을 되풀이한 것인지 가릴 때 쓴다.
    where: 'reading/H31006/52' 같은 문항 주소. 단어 보정 사전(tools/vocab_fixes.json)의 문항별 보정에 쓴다.
    """
    if not explain:
        return explain
    quote = (explain.get('basis') or {}).get('quote', '')
    return {
        'basis': explain.get('basis'),
        'distractors': explain.get('distractors') or [],
        'vocab': fix_vocab([{key: entry.get(key, '') for key in VOCAB_KEYS} for entry in explain.get('vocab') or []], where),
        'grammar': [normalize_grammar(entry, quote, texts) for entry in explain.get('grammar') or []],
    }


def build_groups(paper_groups, notes, test_id, problems, reading_diffs):
    groups = []
    for group in paper_groups:
        note = notes.get(group['id'])
        if not note:
            problems.append(f'{test_id} {group["id"]}: 묶음 해설 없음')
            continue
        annotated = {option['label']: option for option in note.get('options', [])}
        options = []
        for option in group['options']:
            where = f'{test_id} {group["id"]} 보기 {option["label"]}'
            entry = annotated.get(option['label']) or {}
            check_annotated(entry, option['text'], where, problems, reading_diffs)
            options.append({'label': option['label'], 'words': entry.get('words') or [], 'ko': entry.get('ko', '')})
        groups.append({'id': group['id'], 'part': group['part'], 'options': options, 'example': group['example']})
    return groups


def build_lines(source, note, paper_group, where, problems, reading_diffs):
    annotated = note.get('lines') or []
    if source['part'] == 3:
        passage = source['lines'][0]['text']
        joined = ''.join(join_words(line.get('words') or []) for line in annotated)
        if joined != passage:
            problems.append(f'{where} 지문: 문장을 이으면 원문과 다름\n    원문 {passage}\n    결과 {joined}')
        for index, line in enumerate(annotated):
            words = line.get('words') or []
            check_annotated(line, join_words(words), f'{where} 지문 {index + 1}문장', problems, reading_diffs)
        return [{'speaker': None, 'words': line.get('words') or [], 'ko': line.get('ko', '')} for line in annotated]

    if len(annotated) != len(source['lines']):
        problems.append(f'{where}: 줄 수가 다름 ({len(source["lines"])} vs {len(annotated)})')
        return []
    lines, blanks = [], 0
    for index, (line, entry) in enumerate(zip(source['lines'], annotated)):
        here = f'{where} {index + 1}줄'
        words = entry.get('words') or []
        blank = entry.get('blank')
        if blank is None:
            check_annotated(entry, line['text'], here, problems, reading_diffs)
        else:
            blanks += 1
            if not isinstance(blank, int) or not 0 <= blank < len(words):
                problems.append(f'{here}: blank 위치가 단어 범위 밖 ({blank})')
                continue
            gapped = [w if i != blank else [BLANK, ''] for i, w in enumerate(words)]
            check_annotated({'words': gapped, 'ko': entry.get('ko')}, line['text'], here, problems, reading_diffs)
            check_words([words[blank]], words[blank][0], f'{here} 빈칸 단어', problems, reading_diffs)
            answer_word = None
            if paper_group:
                answer_word = next((o['text'] for o in paper_group['options'] if o['label'] == source['answer']), None)
            if words[blank][0] != answer_word:
                problems.append(f'{here}: 빈칸 단어 {words[blank][0]}가 정답 보기 {answer_word}와 다름')
        item_line = {'speaker': line['speaker'], 'words': words, 'ko': entry.get('ko', '')}
        if blank is not None:
            item_line['blank'] = blank
        lines.append(item_line)
    if source['part'] == 2 and blanks != 1:
        problems.append(f'{where}: 빈칸 표시(blank)가 {blanks}개')
    if source['part'] == 1 and blanks:
        problems.append(f'{where}: 1부분에는 빈칸이 없음')
    return lines


def check_explain(explain, part, answer, labels, texts, where, problems, reading_diffs):
    """labels: 고를 수 있는 보기 이름(예시 제외), texts: 그 문항 화면에 나오는 문장들(빈칸 채움)."""
    if not explain:
        problems.append(f'{where}: 해설(explain) 없음')
        return

    basis = explain.get('basis') or {}
    if not basis.get('quote') or not basis.get('note'):
        problems.append(f'{where}: 정답 근거(quote·note) 비었음')
    elif not any(basis['quote'] in text for text in texts):
        problems.append(f'{where}: 정답 근거 인용이 문항 글에 없음: {basis["quote"]}')

    distractors = explain.get('distractors') or []
    named = [d.get('label') for d in distractors]
    if any(label not in labels or label == answer for label in named) or any(not d.get('note') for d in distractors):
        problems.append(f'{where}: 오답 이유의 보기 이름·설명이 이상함 {named}')
    if part == 3 and sorted(named) != sorted(label for label in labels if label != answer):
        problems.append(f'{where}: 3부분 오답 이유는 나머지 두 보기 모두 {named}')
    if part in (1, 2) and not 1 <= len(distractors) <= 2:
        problems.append(f'{where}: 1·2부분 오답 이유는 1~2개 ({len(distractors)}개)')

    vocab = explain.get('vocab') or []
    if not 3 <= len(vocab) <= 8:
        problems.append(f'{where}: 단어는 3~8개 ({len(vocab)}개)')
    for entry in vocab:
        here = f'{where} 단어 {entry.get("hanzi")}'
        missing = [key for key in VOCAB_KEYS if not entry.get(key)]
        if missing:
            problems.append(f'{here}: {missing} 없음')
        if entry.get('hanzi') and entry.get('pinyin'):
            check_words([[entry['hanzi'], entry['pinyin']]], entry['hanzi'], here, problems, reading_diffs)
        problems.extend(vocab_problems(entry, where))

    grammar = explain.get('grammar') or []
    if not 1 <= len(grammar) <= 3:
        problems.append(f'{where}: 문법은 1~3개 ({len(grammar)}개)')
    for entry in grammar:
        here = f'{where} 문법 {entry.get("pattern")}'
        missing = [key for key in ('pattern', 'note') if not entry.get(key)]
        if missing:
            problems.append(f'{here}: {missing} 없음')
        if 'example' in entry:
            check_example(entry['example'], f'{here} 예문', problems, reading_diffs)


def build_item(source, note, paper_group, group_options, where, problems, reading_diffs):
    part, answer = source['part'], source['answer']
    lines = build_lines(source, note, paper_group, where, problems, reading_diffs)

    question, options = None, None
    if part == 3:
        annotated_question = note.get('question') or {}
        check_annotated(annotated_question, source['question'], f'{where} ★', problems, reading_diffs)
        question = {'words': annotated_question.get('words') or [], 'ko': annotated_question.get('ko', '')}
        annotated = {option['label']: option for option in note.get('options') or []}
        options = []
        for option in source['options']:
            entry = annotated.get(option['label']) or {}
            check_annotated(entry, option['text'], f'{where} 보기 {option["label"]}', problems, reading_diffs)
            options.append({'label': option['label'], 'words': entry.get('words') or [], 'ko': entry.get('ko', '')})

    pair = note.get('pair')
    if part == 1 and pair not in ('item-first', 'option-first'):
        problems.append(f'{where}: pair는 item-first 또는 option-first ({pair})')
    if part != 1:
        pair = None

    visible = options if part == 3 else group_options
    texts = [join_words(line['words']) for line in lines]
    texts += [join_words(question['words'])] if question else []
    texts += [join_words(option['words']) for option in visible]
    example = paper_group['example'] if paper_group else None
    labels = [option['label'] for option in visible if option['label'] != example]
    explain = normalize_explain(note.get('explain'), texts, f'reading/{where.split()[0]}/{source["no"]}')
    check_explain(explain, part, answer, labels, texts, where, problems, reading_diffs)

    return {
        'no': source['no'],
        'part': part,
        'group': source['group'],
        'answer': answer,
        'lines': lines,
        'question': question,
        'options': options,
        'pair': pair,
        'explain': explain,
    }


def build_test(test_id, work, problems, reading_diffs):
    base = work / test_id
    paper = json.loads((base / 'paper.json').read_text(encoding='utf-8'))
    group_notes, item_notes = load_enrich(base)
    groups = build_groups(paper['groups'], group_notes, test_id, problems, reading_diffs)
    options_by_group = {group['id']: group['options'] for group in groups}
    paper_groups = {group['id']: group for group in paper['groups']}

    items = []
    for source in paper['items']:
        where = f'{test_id} {source["no"]}번'
        note = item_notes.get(source['no'])
        if not note:
            problems.append(f'{where}: 해설 없음')
            continue
        items.append(build_item(source, note, paper_groups.get(source['group']),
                                options_by_group.get(source['group'], []), where, problems, reading_diffs))

    return {
        'id': test_id,
        'title': f'HSK 3급 {test_id}',
        'parts': [{'part': part, 'guide': guide} for part, guide in PART_GUIDES.items()],
        'groups': groups,
        'items': items,
    }


def example_for(word, item, group_options):
    """단어가 나온 시험 문장(빈칸 채움·질문·보기)을 예문으로 쓴다(듣기와 같이, 없으면 빈칸)."""
    sentences = list(item['lines'])
    if item['question']:
        sentences.append(item['question'])
    sentences += item['options'] or []
    sentences += group_options
    for sentence in sentences:
        text = join_words(sentence['words'])
        if word['hanzi'] in text:
            return text, words_to_pinyin(sentence['words']), sentence['ko']
    return '', '', ''


def update_vocab(tests, repo):
    path = repo / 'src' / 'data' / 'vocab.json'
    vocab = json.loads(path.read_text(encoding='utf-8'))
    # 다시 돌려도 같은 결과가 나오게 지난번에 넣은 독해 단어는 지우고 새로 넣는다.
    # 오답노트가 카드 id로 기록되므로, 지난번에 있던 단어는 같은 id를 다시 쓰고 새 단어만 다음 번호를 받는다.
    # 사라진 카드의 id는 src/data/vocab-retired.json에 은퇴시켜 다시 쓰지 않는다(tools/vocab_fixes.py CardIds).
    ids = CardIds(repo, 'HSK3R', {entry['hanzi']: entry['id'] for entry in vocab if entry.get('lesson') == LESSON})
    vocab = [entry for entry in vocab if entry.get('lesson') != LESSON]
    known = {entry['hanzi'] for entry in vocab}
    added = []
    for test in tests:
        options_by_group = {group['id']: group['options'] for group in test['groups']}
        for item in test['items']:
            for word in item['explain']['vocab']:
                if word['hanzi'] in known:
                    continue
                known.add(word['hanzi'])
                zh, py, ko = example_for(word, item, options_by_group.get(item['group'], []))
                added.append({
                    'id': ids.id_for(word['hanzi']),
                    'level': 'HSK3',
                    'lesson': LESSON,
                    'category': f'{LESSON} {test["id"]}',
                    'itemType': '단어',
                    'hanzi': word['hanzi'],
                    'pinyin': word['pinyin'],
                    'meaningKo': word['meaningKo'],
                    'partOfSpeech': word.get('partOfSpeech', ''),
                    'exampleZh': zh,
                    'examplePinyin': py,
                    'exampleKo': ko,
                    'source': f'HSK3 공식 모의고사 {test["id"]} 독해 {item["no"]}번',
                    'tags': ['HSK3', '단어', LESSON, test['id']],
                })
    ids.write(path, vocab + added)  # 장부를 먼저 계산·검사하고 vocab.json과 함께 바꾼다
    return len(added)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('test_ids', nargs='+')
    parser.add_argument('--work', required=True)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--check', action='store_true', help='검사만 하고 파일을 쓰지 않는다')
    parser.add_argument('--show-readings', action='store_true', help='pypinyin과 음절이 다른 단어를 모두 보여준다')
    args = parser.parse_args()
    work, repo = Path(args.work).expanduser(), Path(args.repo)

    problems, reading_diffs, tests = [], [], []
    for test_id in args.test_ids:
        tests.append(build_test(test_id, work, problems, reading_diffs))

    print(f'pypinyin과 음절이 다른 단어 {len(reading_diffs)}개 (다음자·변조는 맞을 수 있음)')
    if args.show_readings:
        for diff in reading_diffs:
            print('  ? ' + diff)
    if problems:
        for problem in problems:
            print('  ! ' + problem)
        print(f'문제 {len(problems)}개. 파일을 쓰지 않았습니다.')
        return 1
    if args.check:
        print('검사 통과 (--check라 파일은 쓰지 않았습니다).')
        return 0

    public = repo / 'public' / 'reading'
    public.mkdir(parents=True, exist_ok=True)
    for test in tests:
        (public / f'{test["id"]}.json').write_text(json.dumps(test, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    index = [{'id': test['id'], 'title': test['title'], 'count': len(test['items'])} for test in tests]
    (repo / 'src' / 'data' / 'reading-index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    added = update_vocab(tests, repo)
    print(f'회차 {len(tests)}개를 썼고, 단어장에 «{LESSON}» 단어 {added}개를 넣었습니다.')
    refresh_after_write(repo)  # 내 단어장 갱신 색인(src/data/mine-refresh.json)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
