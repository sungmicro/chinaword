#!/usr/bin/env python3
"""paper.json(원문·정답) + enrich-*.json(병음·해석·해설)을 합쳐 앱이 읽는
public/reading/<회차>.json을 만들고, 독해 핵심 단어를 단어장(vocab.json)에 넣는다.

  assemble.py H31001 H31002 ... --work ~/hsk-reading-work --repo .
  assemble.py H31001 --work ~/hsk-reading-work --repo . --check   # 검사만, 파일을 쓰지 않음

쓰기 전에 해설을 기계적으로 검사한다. 단어 묶음의 한자를 이으면 원문과 같아야 하고(2부분은 빈칸 단어를
'（）'로 바꾼 결과), 해설 칸이 기준 개수대로 차 있어야 한다. pypinyin과 음절이 다른 단어는 목록으로만 보여준다.
"""
import argparse
import json
from pathlib import Path

from hsktext import check_words, join_words, words_to_pinyin

LESSON = 'HSK3 독해'
PART_GUIDES = {
    1: '서로 이어지는 문장 짝 찾기',
    2: '빈칸에 알맞은 단어 고르기',
    3: '짧은 글을 읽고 질문에 답하기',
}
ROLES = {'주어', '술어', '목적어', '관형어', '부사어', '보어', '접속사', '개사구'}
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
    if not example or not example.get('zh') or not example.get('words') or not example.get('ko'):
        problems.append(f'{where}: 예문(zh·words·ko) 없음')
        return
    check_words(example['words'], example['zh'], where, problems, reading_diffs)


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

    breakdown = explain.get('breakdown') or []
    if not 1 <= len(breakdown) <= 2:
        problems.append(f'{where}: 끊어 읽기는 1~2문장 ({len(breakdown)}개)')
    for sentence in breakdown:
        chunks = sentence.get('chunks') or []
        text = ''.join(chunk.get('text', '') for chunk in chunks)
        if not chunks or not any(text in t for t in texts):
            problems.append(f'{where}: 끊어 읽기 문장이 문항 글에 없음: {text}')
        roles = [chunk.get('role') for chunk in chunks if chunk.get('role') not in ROLES]
        if roles:
            problems.append(f'{where}: 끊어 읽기 성분 이름이 목록 밖 {roles}')
        if not sentence.get('note'):
            problems.append(f'{where}: 끊어 읽기 요약(note) 없음')

    vocab = explain.get('vocab') or []
    if not 3 <= len(vocab) <= 6:
        problems.append(f'{where}: 단어는 3~6개 ({len(vocab)}개)')
    for entry in vocab:
        here = f'{where} 단어 {entry.get("hanzi")}'
        missing = [key for key in ('hanzi', 'pinyin', 'partOfSpeech', 'meaningKo', 'usage') if not entry.get(key)]
        if missing:
            problems.append(f'{here}: {missing} 없음')
        if entry.get('hanzi') and entry.get('pinyin'):
            check_words([[entry['hanzi'], entry['pinyin']]], entry['hanzi'], here, problems, reading_diffs)
        check_example(entry.get('example'), f'{here} 예문', problems, reading_diffs)

    grammar = explain.get('grammar') or []
    if not 1 <= len(grammar) <= 3:
        problems.append(f'{where}: 문법은 1~3개 ({len(grammar)}개)')
    for entry in grammar:
        here = f'{where} 문법 {entry.get("pattern")}'
        missing = [key for key in ('pattern', 'meaningKo', 'note') if not entry.get(key)]
        if missing:
            problems.append(f'{here}: {missing} 없음')
        check_example(entry.get('example'), f'{here} 예문', problems, reading_diffs)


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
    check_explain(note.get('explain'), part, answer, labels, texts, where, problems, reading_diffs)

    return {
        'no': source['no'],
        'part': part,
        'group': source['group'],
        'answer': answer,
        'lines': lines,
        'question': question,
        'options': options,
        'pair': pair,
        'explain': note.get('explain'),
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
    """단어가 나온 시험 문장(빈칸 채움·질문·보기)을 예문으로, 없으면 해설 예문을 쓴다."""
    sentences = list(item['lines'])
    if item['question']:
        sentences.append(item['question'])
    sentences += item['options'] or []
    sentences += group_options
    for sentence in sentences:
        text = join_words(sentence['words'])
        if word['hanzi'] in text:
            return text, words_to_pinyin(sentence['words']), sentence['ko']
    example = word['example']
    return example['zh'], words_to_pinyin(example['words']), example['ko']


def update_vocab(tests, repo):
    path = repo / 'src' / 'data' / 'vocab.json'
    vocab = json.loads(path.read_text(encoding='utf-8'))
    # 다시 돌려도 같은 결과가 나오게 지난번에 넣은 독해 단어는 지우고 새로 넣는다.
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
                    'id': f'HSK3R-{len(added) + 1:03d}',
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
    path.write_text(json.dumps(vocab + added, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
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
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
