#!/usr/bin/env python3
"""HSK 3급 시험지 PDF에서 듣기 문항(대본·정답·보기)과 1부분 사진 묶음을 뽑는다.

사용: paper.py H31001 --pdf H31001.pdf --work ~/hsk-listening-work --public public/listening
결과: <work>/<회차>/paper.json, <public>/<회차>-p1-<n>.jpg
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

PART_NAMES = {'第一部分': 1, '第二部分': 2, '第三部分': 3, '第四部分': 4}
FOOTER = re.compile(r'^\s*H3\d{4}\s*-\s*\d+\s*$')
ITEM_START = re.compile(r'^\s*(\d{1,2})\s*．\s*(.*)$')
SPEAKER = re.compile(r'^(男|女|问)：\s*(.*)$')
# 대본 안에서 문항이 아닌 줄들. 이 줄이 나오면 진행 중인 문항이 끝난다.
SECTION_LINE = re.compile(r'^(第[一二三四]部分|一共|例如|现在开始|听力考试现在结束)')
CJK = r'[一-鿿，。！？：；、“”‘’（）《》…—]'


def tidy(text):
    """pdftotext가 한자와 숫자 사이에 넣은 공백을 걷어낸다 ('才 5 点' → '才5点')."""
    text = re.sub(rf'(?<={CJK})\s+|\s+(?={CJK})', '', text.strip())
    return re.sub(r'\s{2,}', ' ', text)


def pdf_text(pdf):
    out = subprocess.run(['pdftotext', '-layout', str(pdf), '-'], capture_output=True, text=True, check=True).stdout
    lines = [line.replace('\f', '') for line in out.splitlines()]
    return [line for line in lines if not FOOTER.match(line)]


def between(lines, start_marker, end_marker):
    start = next(i for i, line in enumerate(lines) if start_marker in line)
    end = next(i for i in range(start + 1, len(lines)) if end_marker in lines[i])
    return lines[start + 1:end]


def parse_script(lines):
    """听力材料 구간을 문항별 대본으로 나눈다. 줄바꿈된 문장은 앞 줄에 이어 붙인다."""
    section = between(lines, '卷听力材料', '听力考试现在结束') + ['听力考试现在结束']
    items, part, current = {}, 0, None

    for raw in section:
        line = raw.strip()
        if not line:
            continue
        if line in PART_NAMES:
            part, current = PART_NAMES[line], None
            continue
        if SECTION_LINE.match(line):
            current = None
            continue

        match = ITEM_START.match(raw)
        if match and part:
            no = int(match.group(1))
            current = {'no': no, 'part': part, 'lines': [], 'statement': None}
            items[no] = current
            line = match.group(2).strip()
        elif current is None:
            continue

        speaker = SPEAKER.match(line)
        if speaker:
            current['lines'].append({'speaker': speaker.group(1), 'text': speaker.group(2)})
        elif line.startswith('★'):
            current['statement'] = line.lstrip('★').strip()
        elif current['statement'] is not None:
            current['statement'] += line
        elif current['lines'] and not match:
            current['lines'][-1]['text'] += line
        else:
            current['lines'].append({'speaker': None, 'text': line})

    for item in items.values():
        for entry in item['lines']:
            entry['text'] = tidy(entry['text'])
        if item['statement']:
            item['statement'] = tidy(item['statement'])
    return items


def parse_answers(lines):
    section = between(lines, '卷答案', '二、阅')
    pairs = re.findall(r'(\d{1,2})．\s*([A-F√×])', '\n'.join(section))
    return {int(no): answer for no, answer in pairs if 1 <= int(no) <= 40}


def parse_paper_choices(lines):
    """시험지 듣기 부분에서 2부분 ★ 문장과 3·4부분 A·B·C 보기를 뽑는다."""
    end = next(i for i, line in enumerate(lines) if '二、阅' in line)
    statements, options = {}, {}
    for raw in lines[:end]:
        statement = re.match(r'^\s*(\d{1,2})．\s*★\s*(.+?)\s*（\s*）\s*$', raw)
        if statement:
            statements[int(statement.group(1))] = tidy(statement.group(2))
            continue
        choice = re.match(r'^\s*(\d{1,2})．\s+A\s+(.+?)\s+B\s+(.+?)\s+C\s+(.+?)\s*$', raw)
        if choice:
            no = int(choice.group(1))
            options[no] = [{'label': label, 'text': tidy(text)} for label, text in zip('ABC', choice.groups()[1:])]
    return statements, options


def page_words(pdf):
    """pdftotext -bbox 결과를 쪽별 단어 목록으로 만든다."""
    out = subprocess.run(['pdftotext', '-bbox', str(pdf), '-'], capture_output=True, text=True, check=True).stdout
    pages = []
    for page in re.split(r'<page ', out)[1:]:
        words = [
            {'text': w[4], 'x0': float(w[0]), 'y0': float(w[1]), 'x1': float(w[2]), 'y1': float(w[3])}
            for w in re.findall(r'xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)<', page)
        ]
        pages.append(words)
    return pages


def crop_picture_groups(pdf, test_id, public_dir):
    """1부분 '第 1-5 题', '第 6-10 题' 아래의 사진 묶음을 잘라 jpg로 저장한다."""
    groups = []
    for page_no, words in enumerate(page_words(pdf), start=1):
        for index, word in enumerate(words[:-1]):
            if word['text'] != '第' or words[index + 1]['text'] not in ('1-5', '6-10'):
                continue
            first, last = map(int, words[index + 1]['text'].split('-'))
            top = word['y1'] + 6
            # 사진 아래 첫 '例如：' 또는 첫 문항 번호 줄에서 끊는다.
            below = [w['y0'] for w in words if w['y0'] > top + 40 and (w['text'] == '例如：' or w['text'] == f'{first}．')]
            bottom = min(below) - 6
            labels = sorted({w['text'] for w in words if top < w['y0'] < bottom and re.fullmatch(r'[A-F]', w['text'])})
            name = f'{test_id}-p1-{len(groups) + 1}.jpg'
            dpi = 150
            scale = dpi / 72
            x0, x1 = 70, 540
            subprocess.run([
                'pdftoppm', '-jpeg', '-jpegopt', 'quality=82', '-r', str(dpi), '-f', str(page_no), '-l', str(page_no),
                '-x', str(int(x0 * scale)), '-y', str(int(top * scale)),
                '-W', str(int((x1 - x0) * scale)), '-H', str(int((bottom - top) * scale)),
                '-singlefile', str(pdf), str(public_dir / name[:-4]),
            ], check=True)
            groups.append({'nos': list(range(first, last + 1)), 'labels': labels, 'image': name})
    return groups


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('test_id')
    parser.add_argument('--pdf', required=True)
    parser.add_argument('--work', required=True)
    parser.add_argument('--public', required=True)
    args = parser.parse_args()

    lines = pdf_text(args.pdf)
    script = parse_script(lines)
    answers = parse_answers(lines)
    statements, options = parse_paper_choices(lines)
    public_dir = Path(args.public)
    public_dir.mkdir(parents=True, exist_ok=True)
    out_dir = Path(args.work).expanduser() / args.test_id
    out_dir.mkdir(parents=True, exist_ok=True)
    groups = crop_picture_groups(args.pdf, args.test_id, public_dir)

    items = []
    for no in sorted(script):
        item = script[no]
        item['answer'] = answers.get(no)
        if item['part'] == 2:
            # 화면에는 시험지에 인쇄된 ★ 문장을 보여준다 (대본은 '八层', 시험지는 '8层'처럼 다를 수 있다).
            item['paperStatement'] = statements.get(no)
        if item['part'] in (3, 4):
            item['options'] = options.get(no)
        items.append(item)

    problems = []
    if [i['no'] for i in items] != list(range(1, 41)):
        problems.append(f"문항 번호가 1~40이 아님: {[i['no'] for i in items]}")
    for item in items:
        no = item['no']
        if not item['answer']:
            problems.append(f'{no}번 정답 없음')
        if not item['lines']:
            problems.append(f'{no}번 대본 없음')
        if item['part'] == 2 and not (item['statement'] and item['paperStatement']):
            problems.append(f'{no}번 ★ 문장 없음')
        if item['part'] in (3, 4) and not item.get('options'):
            problems.append(f'{no}번 보기 없음')
        if item['part'] in (3, 4) and not any(l['speaker'] == '问' for l in item['lines']):
            problems.append(f'{no}번 질문(问) 없음')
    covered = sorted(n for g in groups for n in g['nos'])
    if covered != list(range(1, 11)):
        problems.append(f'1부분 사진 묶음이 1~10을 덮지 않음: {groups}')

    (out_dir / 'paper.json').write_text(
        json.dumps({'id': args.test_id, 'items': items, 'pictureGroups': groups}, ensure_ascii=False, indent=1),
        encoding='utf-8',
    )
    print(f'{args.test_id}: 문항 {len(items)}개, 사진 묶음 {len(groups)}개')
    for problem in problems:
        print('  ! ' + problem)
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
