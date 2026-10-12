#!/usr/bin/env python3
"""HSK 3급 시험지 PDF에서 독해 41~70번(묶음 보기·문항·정답)을 뽑는다.

사용: paper.py H31001 --pdf ~/hsk-listening-work/src/H31001.pdf --work ~/hsk-reading-work
결과: <work>/<회차>/paper.json

-layout 추출은 몇 문항에서 줄 순서가 꼬여서(지문 첫 줄이 번호 위로, 빈칸 괄호가 다른 줄로)
내용 순서대로 나오는 -raw를 쓴다. 대신 쪽 번호가 줄 끝에 붙어 나와 지운다.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

from hsktext import tidy

FOOTER = re.compile(r'\s*H3\d{4}\s*-\s*\d+\s*$')
PART = re.compile(r'^第\s*([一二三])\s*部\s*分$')
GROUP = re.compile(r'^第\s*(\d+)\s*-\s*(\d+)\s*题$')
ITEM = re.compile(r'^(\d{2})．\s*(.*)$')
OPTION_LINE = re.compile(r'^([A-F])\s+(.+)$')
BANK_WORD = re.compile(r'([A-F])\s+(\S+)')
EXAMPLE_LABEL = re.compile(r'（\s*([A-F])\s*）')
SPEAKER = re.compile(r'^([AB])：\s*(.*)$')
CHOICES = re.compile(r'^A\s+(.+?)\s+B\s+(.+?)\s+C\s+(.+?)\s*√?\s*$')
TRAILING_BRACKETS = re.compile(r'（）$')
PART_NUMBERS = {'一': 1, '二': 2, '三': 3}


def raw_lines(pdf):
    out = subprocess.run(['pdftotext', '-raw', str(pdf), '-'], capture_output=True, text=True, check=True).stdout
    return [FOOTER.sub('', line.replace('\f', '')).strip() for line in out.splitlines()]


def squash(line):
    return re.sub(r'\s', '', line)


def reading_section(lines):
    """시험지의 '二、阅读' 다음 줄부터 '三、书写' 앞까지 (빈 줄 제외)."""
    start = next(i for i, line in enumerate(lines) if squash(line) == '二、阅读')
    end = next(i for i in range(start + 1, len(lines)) if squash(lines[i]) == '三、书写')
    return [line for line in lines[start + 1:end] if line]


def add_text(item, line):
    """문항 번호 줄 뒤에 이어지는 글을 부분별 규칙으로 붙인다."""
    if item['part'] == 3:
        if line.startswith('★'):
            item['question'] = line.lstrip('★').strip()
        elif item['question'] is not None:
            choices = CHOICES.match(line)
            if choices and item['options'] is None:
                item['options'] = [{'label': label, 'text': text} for label, text in zip('ABC', choices.groups())]
            elif item['options'] is None:
                item['question'] += line  # 질문이 두 줄로 넘어간 경우
        elif item['lines']:
            item['lines'][0]['text'] += line
        else:
            item['lines'].append({'speaker': None, 'text': line})
        return

    speaker = SPEAKER.match(line) if item['part'] == 2 else None
    if speaker:
        item['lines'].append({'speaker': speaker.group(1), 'text': speaker.group(2)})
    elif item['lines']:
        item['lines'][-1]['text'] += line
    else:
        item['lines'].append({'speaker': None, 'text': line})


def finish(item):
    for line in item['lines']:
        text = tidy(line['text'])
        if item['part'] == 1:
            text = TRAILING_BRACKETS.sub('', text)  # 답 쓰는 칸 '（ ）'
        line['text'] = text
    if item['question']:
        item['question'] = tidy(item['question'])
    for option in item['options'] or []:
        option['text'] = tidy(option['text'])


def parse_reading(section):
    """독해 구간 줄들을 묶음(1·2부분 보기)과 문항으로 나눈다. 예시(例如)는 보기 이름만 남기고 버린다."""
    part, group, item, in_example = 0, None, None, False
    groups, items = [], []
    for line in section:
        heading = PART.match(line)
        if heading:
            part, group, item, in_example = PART_NUMBERS[heading.group(1)], None, None, False
            continue
        header = GROUP.match(line)
        if header:
            group = {'id': f'{header.group(1)}-{header.group(2)}', 'part': part, 'options': [], 'example': None}
            if part in (1, 2):
                groups.append(group)
            item, in_example = None, False
            continue
        if line.startswith('例如：'):
            in_example = True
            label = EXAMPLE_LABEL.search(line)
            if part in (1, 2) and label:
                group['example'] = label.group(1)
            continue
        start = ITEM.match(line)
        if start:
            in_example = False
            item = {
                'no': int(start.group(1)),
                'part': part,
                'group': group['id'] if part in (1, 2) else None,
                'lines': [],
                'question': None,
                'options': None,
            }
            items.append(item)
            line = start.group(2)
        elif in_example:
            continue
        elif item is None:
            option = OPTION_LINE.match(line)
            if part == 1 and option:
                group['options'].append({'label': option.group(1), 'text': option.group(2)})
            elif part == 2 and line.startswith('A '):
                group['options'] = [{'label': label, 'text': text} for label, text in BANK_WORD.findall(line)]
            continue
        if line:
            add_text(item, line)

    for item in items:
        finish(item)
    for group in groups:
        for option in group['options']:
            option['text'] = tidy(option['text'])
    return {'groups': groups, 'items': items}


def parse_answers(lines):
    """'卷答案' 아래 정답표에서 41~70번만."""
    start = next(i for i, line in enumerate(lines) if '卷答案' in line)
    pairs = re.findall(r'(\d{2})．\s*([A-F])', '\n'.join(lines[start:]))
    return {int(no): answer for no, answer in pairs if 41 <= int(no) <= 70}


def check_paper(paper):
    problems = []
    items = paper['items']
    groups = {group['id']: group for group in paper['groups']}
    numbers = [item['no'] for item in items]
    if numbers != list(range(41, 71)):
        problems.append(f'문항 번호가 41~70이 아님: {numbers}')

    for group_id, group in groups.items():
        labels = [option['label'] for option in group['options']]
        if len(labels) < 5 or labels != list('ABCDEF'[:len(labels)]):
            problems.append(f'{group_id} 묶음 보기 이상: {labels}')
        if group['part'] == 2 and len(labels) != 6:
            problems.append(f'{group_id} 단어 보기가 6개가 아님')
        answers = [item.get('answer') for item in items if item['group'] == group_id]
        if len(set(answers)) != len(answers):
            problems.append(f'{group_id} 정답이 겹침: {answers}')

    for item in items:
        where = f'{item["no"]}번'
        answer = item.get('answer')
        if not answer:
            problems.append(f'{where} 정답 없음')
            continue
        if not item['lines'] or not all(line['text'] for line in item['lines']):
            problems.append(f'{where} 문장 없음')
        if item['part'] in (1, 2):
            group = groups.get(item['group'])
            if not group:
                problems.append(f'{where} 묶음 없음')
                continue
            if answer not in [option['label'] for option in group['options']]:
                problems.append(f'{where} 정답 {answer}가 묶음 보기에 없음')
            if answer == group['example']:
                problems.append(f'{where} 정답이 예시 보기')
        if item['part'] == 2:
            blanks = sum(line['text'].count('（）') for line in item['lines'])
            if blanks != 1:
                problems.append(f'{where} 빈칸이 {blanks}개')
        if item['part'] == 3:
            if not item['question']:
                problems.append(f'{where} ★ 질문 없음')
            if [option['label'] for option in item['options'] or []] != ['A', 'B', 'C']:
                problems.append(f'{where} 보기가 A·B·C가 아님')
    return problems


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('test_id')
    parser.add_argument('--pdf', required=True)
    parser.add_argument('--work', required=True)
    args = parser.parse_args()

    lines = raw_lines(Path(args.pdf).expanduser())
    parsed = parse_reading(reading_section(lines))
    answers = parse_answers(lines)
    for item in parsed['items']:
        item['answer'] = answers.get(item['no'])
    paper = {'id': args.test_id, **parsed}
    problems = check_paper(paper)

    out_dir = Path(args.work).expanduser() / args.test_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'paper.json').write_text(json.dumps(paper, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{args.test_id}: 묶음 {len(paper["groups"])}개, 문항 {len(paper["items"])}개')
    for problem in problems:
        print('  ! ' + problem)
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
