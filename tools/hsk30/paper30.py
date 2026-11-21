#!/usr/bin/env python3
"""HSK 3.0 공식 샘플(3급·4급) 시험지 PDF와 정답 PDF에서 듣기·독해·쓰기 문항을 뽑는다.

사용:
  paper30.py S30-3 --level 3 --pdf S30-3.pdf --answers S30-3-answers.pdf --work ~/hsk30-work --public public/hsk30
결과:
  <work>/<회차>/paper.json  문항·보기·묶음·정답·쓰기 문장·제시어·병음
  <public>/<회차>-p1-1.jpg, -p1-2.jpg (3급 듣기 1부분 사진 묶음, A~F 글자 포함)
  <public>/<회차>-w<번호>.jpg (사진 보고 문장 쓰기 문항 사진)

PDF는 믿지 않는 자료로 다룬다. pdftotext·pdftoppm만 부르고, 글은 고치지 않고 공백만 걷어낸다.
듣기 묶음(29~30번 등)은 시험지에 표시가 없고 음원 안내(«第二十到二十一题是根据下面一段话»)로만 나온다.
그래서 LISTENING_GROUPS에 적어 두고 audio30.py가 음원 안내와 맞는지 확인한다.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'reading'))
from hsktext import tidy  # noqa: E402

LISTENING_GROUPS = {
    3: ['29-30'],
    4: ['20-21', '22-23', '24-25', '26-27', '28-29', '30-32'],
}
COUNTS = {3: {'listening': 30, 'reading': 30, 'writing': 10}, 4: {'listening': 32, 'reading': 32, 'writing': 6}}
LISTENING_PARTS = {
    3: [(1, 1, 10), (2, 11, 20), (3, 21, 30)],
    4: [(1, 1, 14), (2, 15, 32)],
}
READING_KINDS = {3: {1: 'match', 2: 'wordbank', 3: 'passage'}, 4: {1: 'wordbank', 2: 'passage', 3: 'cloze'}}

FOOTER = re.compile(r'^\s*(HSK（[三四]级）样卷\s*-\s*\d+|H41001\s*-\s*\d+)\s*$')
PART = re.compile(r'^第([一二三])部分$')
PART_NUMBERS = {'一': 1, '二': 2, '三': 3}
RANGE = re.compile(r'^第(\d+)～(\d+)题')
ITEM = re.compile(r'^\s*(\d{1,2})．\s*(.*)$')
GROUP_HEAD = re.compile(r'^\s*(\d{1,2})～(\d{1,2})．\s*$')
SPEAKER = re.compile(r'^([AB])：\s*(.*)$')
OPTION = re.compile(r'^([A-F])\s+(.+)$')
EXAMPLE_LABEL = re.compile(r'（\s*([A-F])\s*）')
BLANK = re.compile(r'（\s*）')
PINYIN_LINE = re.compile(r'^\s*([a-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü]+)\s*$')
HANZI = re.compile(r'[一-鿿]')


def squash(line):
    return re.sub(r'\s', '', line)


def pdf_lines(pdf):
    out = subprocess.run(['pdftotext', '-layout', str(pdf), '-'], capture_output=True, text=True, check=True).stdout
    lines = [line.replace('\f', '').rstrip() for line in out.splitlines()]
    return [line for line in lines if not FOOTER.match(line) and not re.fullmatch(r'\s*-{5,}\s*', line)]


def section(lines, start_marker, end_marker=None):
    start = next(i for i, line in enumerate(lines) if squash(line).startswith(start_marker))
    end = len(lines)
    if end_marker:
        end = next(i for i in range(start + 1, len(lines)) if squash(lines[i]).startswith(end_marker))
    return lines[start + 1:end]


def chunks(line):
    """두 칸 이상 띄운 곳에서 나눈다 (두 단 배치·한 줄에 늘어놓은 보기)."""
    return [c for c in re.split(r'\s{2,}', line.strip()) if c]


def options_from(chunk_list, where):
    out = []
    for chunk in chunk_list:
        m = OPTION.match(chunk)
        if not m:
            raise ValueError(f'{where}: 보기로 읽을 수 없는 조각 {chunk!r}')
        out.append({'label': m.group(1), 'text': tidy(m.group(2).replace('√', ''))})
    return out


# ───────────────────────── 정답 ─────────────────────────

def parse_answers(pdf):
    lines = pdf_lines(pdf)
    writing_at = next(i for i, line in enumerate(lines) if squash(line).startswith(('三、书写', '三、写作')))
    choice_text = '\n'.join(lines[:writing_at])
    answers = {int(no): label for no, label in re.findall(r'(\d{1,2})．\s*([A-F])', choice_text)}
    writing = {}
    for line in lines[writing_at + 1:]:
        m = ITEM.match(line)
        if m and m.group(2).strip():
            writing[int(m.group(1))] = tidy(m.group(2))
    return answers, writing


# ───────────────────────── 듣기 ─────────────────────────

def parse_listening(lines, level):
    body = section(lines, '一、听力', '下面是阅读部分')
    options = {}
    if level == 3:
        for line in body:
            m = ITEM.match(line)
            if m and m.group(2).strip().startswith('A '):
                options[int(m.group(1))] = options_from(chunks(m.group(2)), f'듣기 {m.group(1)}번')
    else:
        # 두 단 배치: 줄마다 왼쪽 조각은 왼쪽 문항, 오른쪽 조각은 오른쪽 문항에 붙는다.
        current = [None, None]
        for line in body:
            parts = chunks(line)
            if not parts or not re.match(r'^(\d{1,2}．)?\s*[A-D]\s', parts[0]):
                continue
            if len(parts) != 2:
                raise ValueError(f'듣기 두 단 배치가 아닌 줄: {line!r}')
            for col, chunk in enumerate(parts):
                m = re.match(r'^(?:(\d{1,2})．)?\s*([A-D])\s+(.+)$', chunk)
                if not m:
                    raise ValueError(f'듣기 보기 조각을 읽을 수 없음: {chunk!r}')
                if m.group(1):
                    current[col] = int(m.group(1))
                    options[current[col]] = []
                options[current[col]].append({'label': m.group(2), 'text': tidy(m.group(3))})
    return options


def listening_items(lines, level, answers, picture_groups):
    options = parse_listening(lines, level)
    group_of = {}
    for gid in LISTENING_GROUPS[level]:
        a, b = map(int, gid.split('-'))
        for no in range(a, b + 1):
            group_of[no] = gid
    picture_of = {no: g for g in picture_groups for no in g['nos']}
    items = []
    for part, first, last in LISTENING_PARTS[level]:
        for no in range(first, last + 1):
            item = {'no': no, 'part': part, 'group': group_of.get(no), 'answer': answers.get(no)}
            if no in picture_of:
                item['choices'] = {'type': 'picture', 'image': picture_of[no]['image'], 'labels': picture_of[no]['labels']}
                if picture_of[no].get('example'):
                    item['choices']['example'] = picture_of[no]['example']
            else:
                item['choices'] = {'type': 'text', 'options': options.get(no)}
            items.append(item)
    return items


# ───────────────────────── 독해 ─────────────────────────

def split_parts(body):
    parts, current = {}, None
    for line in body:
        m = PART.match(squash(line))
        if m:
            current = PART_NUMBERS[m.group(1)]
            parts[current] = []
        elif current:
            parts[current].append(line)
    return parts


def parse_bank_part(lines, part, kind, answers):
    """문장 짝(match)·단어 빈칸(wordbank) 부분. '第 31～35 题'마다 보기 묶음 하나."""
    groups, items = [], []
    group = None
    in_example = False
    current = None
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        sq = squash(line)
        rng = RANGE.match(sq)
        if rng:
            group = {'id': f'{rng.group(1)}-{rng.group(2)}', 'part': part, 'options': [], 'example': None,
                     'distractor': '干扰项' in sq}
            groups.append(group)
            in_example, current = False, None
            continue
        if sq.startswith('例如'):
            in_example, current = True, None
            line = re.sub(r'^例如：\s*', '', line)
        item = ITEM.match(raw)
        if item:
            in_example = False
            no = int(item.group(1))
            current = {'no': no, 'part': part, 'kind': kind, 'group': group['id'], 'lines': [],
                       'answer': answers.get(no)}
            items.append(current)
            line = item.group(2).strip()
        if in_example:
            label = EXAMPLE_LABEL.search(line)
            if label:
                group['example'] = label.group(1)
            continue
        if current is None:
            # 보기 줄: 'A 那我们还是买别的衣服吧。' 한 줄에 하나, 또는 'A 地方 B 迟到 …' 한 줄에 여럿
            if re.match(r'^[A-F]\s', line):
                if kind == 'wordbank':
                    group['options'] += [{'label': lab, 'text': tidy(word)}
                                         for lab, word in re.findall(r'([A-F])\s+(\S+)', line)]
                else:
                    m = OPTION.match(line)
                    group['options'].append({'label': m.group(1), 'text': tidy(m.group(2))})
            continue
        speaker = SPEAKER.match(line)
        if speaker:
            current['lines'].append({'speaker': speaker.group(1), 'text': speaker.group(2)})
        elif current['lines']:
            current['lines'][-1]['text'] += line
        else:
            current['lines'].append({'speaker': None, 'text': line})
    for item in items:
        for entry in item['lines']:
            text = tidy(entry['text'])
            if kind == 'match':
                text = re.sub(r'（）$', '', BLANK.sub('（）', text))  # 답 쓰는 칸
            else:
                text = BLANK.sub('（）', text)
            entry['text'] = text
    return groups, items


def parse_passage_part(lines, part, answers):
    """지문 + ★ 질문 + 보기. '57～58．' 묶음은 지문 하나에 ★ 질문이 여럿."""
    items = []
    passage, block_nos, block = None, [], None
    in_example = False
    pending_q = None

    def start_block(nos):
        return {'nos': nos, 'text': '', 'questions': []}

    blocks = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        sq = squash(line)
        if RANGE.match(sq):
            continue
        if sq.startswith('例如'):
            in_example = True
            continue
        head = GROUP_HEAD.match(raw)
        item = ITEM.match(raw) if not head else None
        if head:
            in_example = False
            block = start_block(list(range(int(head.group(1)), int(head.group(2)) + 1)))
            blocks.append(block)
            continue
        if item and not in_example:
            block = start_block([int(item.group(1))])
            blocks.append(block)
            line = item.group(2).strip()
        elif item and in_example:
            in_example = False
            block = start_block([int(item.group(1))])
            blocks.append(block)
            line = item.group(2).strip()
        if in_example or block is None:
            continue
        if line.startswith('★'):
            block['questions'].append({'question': line.lstrip('★').strip(), 'options': []})
        elif block['questions'] and re.match(r'^[A-D]\s', line):
            block['questions'][-1]['options'] += options_from(chunks(line), f'독해 {block["nos"]}')
        elif block['questions']:
            raise ValueError(f'독해 {block["nos"]}: 질문 뒤 알 수 없는 줄 {line!r}')
        else:
            block['text'] += line
    for block in blocks:
        if len(block['questions']) != len(block['nos']):
            raise ValueError(f'독해 {block["nos"]}: 질문 {len(block["questions"])}개')
        gid = f'{block["nos"][0]}-{block["nos"][-1]}' if len(block['nos']) > 1 else None
        for no, q in zip(block['nos'], block['questions']):
            items.append({'no': no, 'part': part, 'kind': 'passage', 'passageGroup': gid,
                          'lines': [{'speaker': None, 'text': tidy(block['text'])}],
                          'question': tidy(q['question']), 'options': q['options'], 'answer': answers.get(no)})
    return items


def parse_cloze_part(lines, part, answers):
    """선택 문장 빈칸(4급 58~64): '58～60．' 지문 + A~C 문장 보기."""
    groups, items = [], []
    group = None
    for raw in lines:
        line = raw.strip()
        if not line or RANGE.match(squash(line)):
            continue
        head = GROUP_HEAD.match(raw)
        if head:
            a, b = int(head.group(1)), int(head.group(2))
            group = {'id': f'{a}-{b}', 'part': part, 'nos': list(range(a, b + 1)), 'text': '', 'options': []}
            groups.append(group)
            continue
        if group is None:
            continue
        m = OPTION.match(line)
        if m and (group['options'] or re.match(r'^[A-F]\s', line)) and '（' not in line:
            group['options'].append({'label': m.group(1), 'text': tidy(m.group(2))})
        else:
            group['text'] += line
    for group in groups:
        group['text'] = re.sub(r'（\s*(\d+)\s*）', r'（\1）', tidy(group['text']))
        for no in group['nos']:
            if f'（{no}）' not in group['text']:
                raise ValueError(f'빈칸 문장 {group["id"]}: （{no}） 없음')
            # 조립 때 '（N）'을 ["（N）","","slot:N"] 토큰으로 바꾼다. 글 전체를 문항마다 둔다.
            items.append({'no': no, 'part': part, 'kind': 'cloze', 'group': group['id'],
                          'lines': [{'speaker': None, 'text': group['text']}], 'answer': answers.get(no)})
    return groups, items


def reading_items(lines, level, answers):
    body = section(lines, '二、阅读', '下面是书写部分' if level == 3 else '下面是写作部分')
    parts = split_parts(body)
    kinds = READING_KINDS[level]
    groups, items, cloze = [], [], []
    for part in sorted(parts):
        kind = kinds[part]
        if kind in ('match', 'wordbank'):
            g, i = parse_bank_part(parts[part], part, kind, answers)
            groups += g
            items += i
        elif kind == 'passage':
            items += parse_passage_part(parts[part], part, answers)
        else:
            g, i = parse_cloze_part(parts[part], part, answers)
            cloze += g
            items += i
    parts_meta = [{'part': p, 'kind': kinds[p]} for p in sorted(parts)]
    return parts_meta, groups, cloze, sorted(items, key=lambda x: x['no'])


# ───────────────────────── 쓰기 ─────────────────────────

def writing_items(lines, level, writing_answers, pictures):
    body = section(lines, '三、书写' if level == 3 else '三、写作')
    parts = split_parts(body)
    items, example = [], None
    if level == 3:
        pinyin = None
        for raw in parts[1]:
            p = PINYIN_LINE.match(raw)
            if p:
                pinyin = p.group(1)
                continue
            m = ITEM.match(raw)
            if m:
                no = int(m.group(1))
                sentence = BLANK.sub('___', tidy(m.group(2)))
                if sentence.count('___') != 1 or pinyin is None:
                    raise ValueError(f'쓰기 {no}번: 빈칸·병음을 못 찾음')
                answer = writing_answers.get(no)
                items.append({'no': no, 'part': 1, 'kind': 'hanzi', 'sentence': sentence, 'pinyin': pinyin,
                              'answers': [answer] if answer else []})
                pinyin = None
            elif squash(raw).startswith('例如'):
                pinyin = None
    picture_part = parts[2] if level == 3 else parts[1]
    for raw in picture_part:
        sq = squash(raw)
        if sq.startswith('例如'):
            c = chunks(re.sub(r'^\s*例如：', '', raw))
            example = {'word': tidy(c[0]), 'answer': tidy(c[1])}
            continue
        for no, word in re.findall(r'(\d{1,2})．\s*(\S+)', raw):
            no = int(no)
            answer = writing_answers.get(no)
            items.append({'no': no, 'part': 2 if level == 3 else 1, 'kind': 'picture', 'word': tidy(word),
                          'image': pictures.get(no), 'answers': [answer] if answer else []})
    if level == 4:
        for raw in parts[2]:
            m = ITEM.match(raw)
            if m:
                prompt = tidy(m.group(2))
                chars = re.search(r'不少于(\d+)字', prompt)
                items.append({'no': int(m.group(1)), 'part': 2, 'kind': 'essay', 'prompt': prompt,
                              'minChars': int(chars.group(1)) if chars else None,
                              'officialAnswer': writing_answers.get(int(m.group(1)))})
    return sorted(items, key=lambda x: x['no']), example


# ───────────────────────── 사진 자르기 ─────────────────────────

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


def render_jpeg(pdf, page_no, box, dpi, dest):
    """box=(x0, y0, x1, y1) PDF 포인트. dest는 확장자 없는 경로."""
    scale = dpi / 72
    x0, y0, x1, y1 = box
    subprocess.run([
        'pdftoppm', '-jpeg', '-jpegopt', 'quality=82', '-r', str(dpi), '-f', str(page_no), '-l', str(page_no),
        '-x', str(int(x0 * scale)), '-y', str(int(y0 * scale)),
        '-W', str(int((x1 - x0) * scale)), '-H', str(int((y1 - y0) * scale)),
        '-singlefile', str(pdf), str(dest),
    ], check=True)


def read_pgm(path):
    data = Path(path).read_bytes()
    # P5 width height maxval\n<bytes>
    m = re.match(rb'P5\s+(\d+)\s+(\d+)\s+(\d+)\s', data)
    width, height = int(m.group(1)), int(m.group(2))
    return width, height, data[m.end():]


def bottom_block(ys, gap):
    """잉크가 있는 줄 번호들 중 맨 아래 덩어리만: 위로 올라가다 gap 넘게 빈 줄이 나오면 멈춘다.
    (사진 위에 앞 문항·예시 사진의 꼬리가 걸려 들어오는 것을 막는다.)"""
    keep = [ys[-1]]
    for y in reversed(ys[:-1]):
        if keep[-1] - y > gap:
            break
        keep.append(y)
    return sorted(keep)


def ink_box(pdf, page_no, region, dpi=72, threshold=235, bottom_gap=None):
    """region(PDF 포인트) 안에서 흰색이 아닌 화소가 있는 가장 작은 상자 (PDF 포인트)."""
    scale = dpi / 72
    x0, y0, x1, y1 = region
    tmpdir = tempfile.TemporaryDirectory()
    tmp = Path(tmpdir.name) / 'ink'
    subprocess.run([
        'pdftoppm', '-gray', '-r', str(dpi), '-f', str(page_no), '-l', str(page_no),
        '-x', str(int(x0 * scale)), '-y', str(int(y0 * scale)),
        '-W', str(int((x1 - x0) * scale)), '-H', str(int((y1 - y0) * scale)),
        '-singlefile', str(pdf), str(tmp),
    ], check=True)
    pgm = Path(f'{tmp}.pgm')
    width, height, pixels = read_pgm(pgm)
    tmpdir.cleanup()
    rows = {}
    for y in range(height):
        row = pixels[y * width:(y + 1) * width]
        dark = [x for x, v in enumerate(row) if v < threshold]
        if dark:
            rows[y] = (dark[0], dark[-1])
    if not rows:
        return None
    ys = bottom_block(sorted(rows), bottom_gap * scale) if bottom_gap else sorted(rows)
    xs = [x for y in ys for x in rows[y]]
    return (x0 + min(xs) / scale, y0 + min(ys) / scale, x0 + (max(xs) + 1) / scale, y0 + (max(ys) + 1) / scale)


def crop_listening_pictures(pdf, test_id, public_dir, words_by_page):
    """듣기 1부분 '第 1～5 题', '第 6～10 题' 아래의 사진 묶음 (A~F 글자 포함)."""
    groups = []
    for page_no, words in enumerate(words_by_page, start=1):
        for index, word in enumerate(words[:-1]):
            nxt = words[index + 1]['text']
            if word['text'] != '第' or nxt not in ('1～5', '6～10'):
                continue
            first, last = map(int, nxt.split('～'))
            top = word['y1'] + 6
            below = [w['y0'] for w in words if w['y0'] > top + 40 and w['text'] in ('例如：', f'{first}．')]
            bottom = min(below) - 6
            labels = sorted({w['text'] for w in words if top < w['y0'] < bottom and re.fullmatch(r'[A-F]', w['text'])})
            box = ink_box(pdf, page_no, (70, top, 545, bottom))
            box = (70, max(top, box[1] - 4), min(545, box[2] + 6), min(bottom, box[3] + 4))
            name = f'{test_id}-p1-{len(groups) + 1}.jpg'
            render_jpeg(pdf, page_no, box, 150, public_dir / name[:-4])
            # 예시 답: '例如：' 줄과 첫 문항 번호 사이 오른쪽에 찍힌 글자 하나 (3급 1~5는 D)
            ex_top = [w['y0'] for w in words if w['text'] == '例如：' and w['y0'] > bottom - 10]
            first_no = [w['y0'] for w in words if w['text'] == f'{first}．']
            example = None
            if ex_top and first_no:
                marks = [w['text'] for w in words if ex_top[0] - 2 <= w['y0'] < first_no[0] - 2
                         and w['x0'] > 400 and re.fullmatch(r'[A-F]', w['text'])]
                example = marks[0] if len(marks) == 1 else None
            groups.append({'nos': list(range(first, last + 1)), 'labels': labels, 'image': name,
                           'example': example, 'page': page_no})
    return groups


def crop_writing_pictures(pdf, test_id, public_dir, words_by_page, word_texts):
    """사진 보고 문장 쓰기: 번호('66．')와 제시어 사이, 번호 줄 위의 사진."""
    pictures = {}
    for page_no, words in enumerate(words_by_page, start=1):
        numbers = [w for w in words if re.fullmatch(r'\d{2}．', w['text']) and int(w['text'][:2]) in word_texts]
        for num in numbers:
            no = int(num['text'][:2])
            keyword = min((w for w in words if w['text'] == word_texts[no] and w['x0'] > num['x1']
                           and abs(w['y0'] - num['y0']) < 8), key=lambda w: w['x0'])
            # 위쪽 경계: 같은 단의 위 번호 줄(또는 제목·例如 줄) 아래
            above = [w['y1'] for w in words if w['y1'] < num['y0'] - 20 and w['x0'] < keyword['x0']
                     and w['x1'] > num['x0']]
            top = (max(above) + 4) if above else 60
            region = (num['x1'] + 2, top, keyword['x0'] - 2, num['y1'] + 12)
            box = ink_box(pdf, page_no, region, bottom_gap=12)
            if box is None:
                raise ValueError(f'{no}번 사진을 찾지 못함')
            pad = 3
            box = (max(region[0], box[0] - pad), max(region[1], box[1] - pad),
                   min(region[2], box[2] + pad), min(region[3], box[3] + pad))
            name = f'{test_id}-w{no}.jpg'
            render_jpeg(pdf, page_no, box, 220, public_dir / name[:-4])
            pictures[no] = name
    return pictures


# ───────────────────────── 조립 ─────────────────────────

def build_paper(test_id, level, pdf, answers_pdf, public_dir):
    lines = pdf_lines(pdf)
    answers, writing_answers = parse_answers(answers_pdf)
    words_by_page = page_words(pdf)
    public_dir.mkdir(parents=True, exist_ok=True)

    picture_groups = crop_listening_pictures(pdf, test_id, public_dir, words_by_page) if level == 3 else []
    # 제시어 목록을 먼저 텍스트에서 얻은 뒤 사진을 자른다.
    draft, _ = writing_items(lines, level, writing_answers, {})
    word_texts = {i['no']: i['word'] for i in draft if i['kind'] == 'picture'}
    pictures = crop_writing_pictures(pdf, test_id, public_dir, words_by_page, word_texts)
    writing, example = writing_items(lines, level, writing_answers, pictures)
    writing = [{'id': f'{test_id}-{i["no"]}', 'exam': test_id, **i} for i in writing]

    listening = listening_items(lines, level, answers, picture_groups)
    parts_meta, groups, cloze, reading = reading_items(lines, level, answers)
    return {
        'id': test_id,
        'level': level,
        'source': {'pdf': Path(pdf).name, 'answers': Path(answers_pdf).name},
        'counts': COUNTS[level],
        'listening': {'parts': [{'part': p, 'first': a, 'last': b} for p, a, b in LISTENING_PARTS[level]],
                      'groups': LISTENING_GROUPS[level], 'pictureGroups': picture_groups, 'items': listening},
        'reading': {'parts': parts_meta, 'groups': groups, 'cloze': cloze, 'items': reading},
        'writing': {'example': example, 'items': writing},
    }


def check_paper(paper, pdf_text):
    """문항 수·정답 수·보기 수, 그리고 모든 한자 글이 PDF 글에 그대로 있는지 본다."""
    problems = []
    flat = re.sub(r'\s', '', pdf_text)
    level = paper['level']

    def present(text, where):
        if text and HANZI.search(text) and re.sub(r'（\d*）|___', '', text) not in re.sub(r'（\d*）', '', flat):
            # 빈칸 표시만 다를 수 있으므로 빈칸 앞뒤 조각을 따로 찾는다.
            pieces = [p for p in re.split(r'（\d*）|___', text) if p]
            if not all(p in flat for p in pieces):
                problems.append(f'{where}: PDF에 없는 글 {text!r}')

    counts = paper['counts']
    for area in ('listening', 'reading', 'writing'):
        n = len(paper[area]['items'])
        if n != counts[area]:
            problems.append(f'{area}: 문항 {n}개 (기대 {counts[area]})')
    expected_choices = 3 if level == 3 else 4
    for item in paper['listening']['items']:
        if item['answer'] is None:
            problems.append(f'듣기 {item["no"]}: 정답 없음')
        if item['choices']['type'] == 'text':
            opts = item['choices']['options'] or []
            if [o['label'] for o in opts] != list('ABCD'[:expected_choices]):
                problems.append(f'듣기 {item["no"]}: 보기 {[o["label"] for o in opts]}')
            for o in opts:
                present(o['text'], f'듣기 {item["no"]}{o["label"]}')
            if item['answer'] not in [o['label'] for o in opts]:
                problems.append(f'듣기 {item["no"]}: 정답 {item["answer"]}이 보기에 없음')
        else:
            if item['answer'] not in item['choices']['labels']:
                problems.append(f'듣기 {item["no"]}: 정답 {item["answer"]}이 사진 라벨에 없음')
    for group in paper['reading']['groups']:
        for o in group['options']:
            present(o['text'], f'독해 {group["id"]}{o["label"]}')
    for group in paper['reading']['cloze']:
        present(group['text'], f'독해 {group["id"]} 지문')
        for o in group['options']:
            present(o['text'], f'독해 {group["id"]}{o["label"]}')
    group_labels = {g['id']: [o['label'] for o in g['options']] for g in paper['reading']['groups'] + paper['reading']['cloze']}
    for item in paper['reading']['items']:
        if item['answer'] is None:
            problems.append(f'독해 {item["no"]}: 정답 없음')
        for line in item.get('lines', []):
            present(line['text'], f'독해 {item["no"]} 글')
        if item['kind'] == 'passage':
            present(item['question'], f'독해 {item["no"]} 질문')
            labels = [o['label'] for o in item['options']]
            if labels != list('ABCD'[:expected_choices]):
                problems.append(f'독해 {item["no"]}: 보기 {labels}')
            for o in item['options']:
                present(o['text'], f'독해 {item["no"]}{o["label"]}')
        else:
            labels = group_labels.get(item['group'], [])
            if item['answer'] not in labels:
                problems.append(f'독해 {item["no"]}: 정답 {item["answer"]}이 보기 {labels}에 없음')
        if item['kind'] == 'wordbank':
            blanks = sum(line['text'].count('（）') for line in item['lines'])
            if blanks != 1:
                problems.append(f'독해 {item["no"]}: 빈칸 {blanks}개')
    for item in paper['writing']['items']:
        if item['kind'] == 'hanzi':
            present(item['sentence'], f'쓰기 {item["no"]}')
            if not item['answers']:
                problems.append(f'쓰기 {item["no"]}: 정답 없음')
        elif item['kind'] == 'picture':
            present(item['word'], f'쓰기 {item["no"]} 제시어')
            if not item['answers']:
                problems.append(f'쓰기 {item["no"]}: 참고답안 없음')
            elif item['word'] not in item['answers'][0]:
                problems.append(f'쓰기 {item["no"]}: 참고답안에 제시어 {item["word"]} 없음')
            if not item.get('image'):
                problems.append(f'쓰기 {item["no"]}: 사진 없음')
        elif item['kind'] == 'essay':
            present(item['prompt'], f'쓰기 {item["no"]} 지시문')
    return problems


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('test_id')
    parser.add_argument('--level', type=int, required=True, choices=(3, 4))
    parser.add_argument('--pdf', required=True)
    parser.add_argument('--answers', required=True)
    parser.add_argument('--work', required=True)
    parser.add_argument('--public', required=True)
    args = parser.parse_args()

    pdf = Path(args.pdf).expanduser()
    paper = build_paper(args.test_id, args.level, pdf, Path(args.answers).expanduser(), Path(args.public))
    text = subprocess.run(['pdftotext', '-layout', str(pdf), '-'], capture_output=True, text=True, check=True).stdout
    problems = check_paper(paper, text)
    out_dir = Path(args.work).expanduser() / args.test_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'paper.json').write_text(json.dumps(paper, ensure_ascii=False, indent=1), encoding='utf-8')
    c = {k: len(paper[k]['items']) for k in ('listening', 'reading', 'writing')}
    print(f"{args.test_id}: 듣기 {c['listening']} · 독해 {c['reading']} · 쓰기 {c['writing']} → {out_dir / 'paper.json'}")
    for p in problems:
        print('  !', p)
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
