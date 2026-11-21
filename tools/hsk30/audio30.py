#!/usr/bin/env python3
"""HSK 3.0 샘플 듣기 원본 mp3를 문항별로 잘라 이어 붙인다 (tools/listening/audio.py의 함수를 가져다 쓴다).

  audio30.py transcribe S30-3 --mp3 S30-3.mp3 --work ~/hsk30-work --large ggml-large-v3-turbo.bin --small ggml-small.bin
      무음으로 원본을 조각낸다. 쉼 1.0초 이상으로 나눈 «덩어리»(blocks)와 쉼 0.3초 이상으로 나눈 «마디»(fine)를
      둘 다 large-v3-turbo·small로 받아쓴다 → <work>/<회차>/segments.json
  audio30.py propose S30-3 --work ~/hsk30-work
      번호·묶음 안내(«十一。», «第二十到二十一题») 위치로 문항 구간 초안을 만든다 → <work>/<회차>/cuts.json
      3급은 두 번 읽으므로 첫 낭독만, 4급은 한 번. 묶음 문항은 [지문, 자기 질문] 두 구간(ranges)이다.
      예시·안내·끝 인사는 넣지 않는다. 손으로 고친 cuts.json은 덮어쓰지 않는다(--force 때만).
  audio30.py build S30-3 --work ~/hsk30-work --public public/hsk30
      cuts.json 구간을 잘라 2초 쉼으로 이어 붙이고 loudnorm·32k CBR mp3로 → <public>/<회차>.mp3, <work>/<회차>/timings.json
  audio30.py verify S30-3 --work ~/hsk30-work --public public/hsk30 --model ggml-large-v3-turbo.bin
      만든 mp3를 문항 구간마다 다시 받아써, 원본 구간 받아쓰기(segments.json)와 얼마나 맞는지 본다 → verify.json

원본·PDF는 믿지 않는 자료다. ffmpeg·whisper-cli만 부른다.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'listening'))
from audio import (GAP_BETWEEN, LEAD_IN, SAMPLE_RATE, coverage, cut_wav, detect_silences, duration,  # noqa: E402
                   run, syllables)

PROMPT = '以下是普通话的句子，使用简体中文。'


def transcribe(wavs, model, out_dir, tag):
    """audio.py transcribe와 같은 설정. 다만 whisper-cli 화면 출력에 깨진 UTF-8이 섞여도 멈추지 않게
    바이트로 받고, 결과를 <wav>.<tag>.txt로 남겨 다시 돌릴 때 재사용한다."""
    todo = [w for w in wavs if not Path(f'{w}.{tag}.txt').exists()]
    if todo:
        cmd = ['whisper-cli', '-m', str(model), '-l', 'zh', '-t', '8', '-nt', '-otxt', '--prompt', PROMPT]
        for wav in todo:
            cmd += ['-f', str(wav)]
        subprocess.run(cmd, check=True, capture_output=True, cwd=out_dir)
        for wav in todo:
            Path(f'{wav}.txt').rename(f'{wav}.{tag}.txt')
    return [Path(f'{w}.{tag}.txt').read_text(encoding='utf-8', errors='replace').strip() for w in wavs]

BLOCK_GAP = 1.0   # 이 이상 쉬면 다른 덩어리 (번호 ↔ 대화, 대화 ↔ 질문, 낭독 ↔ 반복 사이)
FINE_GAP = 0.3    # 말 차례·쉼표 단위 마디
MIN_SPEECH = 0.15
PAD = 0.3         # 구간 앞뒤 여유 (이웃 말소리를 침범하지 않게 무음 가운데까지만)

CN_NUM = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10, '零': 0}


def cn_to_int(text):
    """'二十一' → 21, '十五' → 15, '21' → 21."""
    text = text.strip()
    if text.isdigit():
        return int(text)
    if not text or any(ch not in CN_NUM for ch in text):
        return None
    if '十' not in text:
        return CN_NUM[text] if len(text) == 1 else None
    tens, _, ones = text.partition('十')
    return (CN_NUM[tens] if tens else 1) * 10 + (CN_NUM[ones] if ones else 0)


def speech_spans(silences, total, gap):
    spans, cursor = [], 0.0
    for start, end in [(s, e) for s, e in silences if e - s >= gap] + [(total, total)]:
        if start - cursor >= MIN_SPEECH:
            spans.append({'start': round(cursor, 3), 'end': round(start, 3)})
        cursor = end
    return spans


def number_only(text):
    """'十一。' '21.' '二十二' 처럼 번호만 읽은 조각이면 번호, 아니면 None."""
    t = re.sub(r'[\s。.,，、:：!！?？]', '', text or '')
    t = re.sub(r'^第', '', t)
    t = re.sub(r'题$', '', t)
    return cn_to_int(t) if t else None




def cmd_transcribe(args):
    work = Path(args.work).expanduser() / args.test_id
    work.mkdir(parents=True, exist_ok=True)
    wav = work / 'source.wav'
    if not wav.exists():
        run(['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-i', str(Path(args.mp3).expanduser()),
             '-ac', '1', '-ar', '16000', str(wav)])
    total = duration(wav)
    silences = detect_silences(wav)
    out = {'id': args.test_id, 'source': str(Path(args.mp3).expanduser()), 'wav': str(wav), 'duration': total,
           'silences': silences}
    models = {'large': Path(args.large).expanduser(), 'small': Path(args.small).expanduser()}
    for name, gap in (('blocks', BLOCK_GAP), ('fine', FINE_GAP)):
        spans = speech_spans(silences, total, gap)
        seg_dir = work / f'seg-{name}'
        seg_dir.mkdir(exist_ok=True)
        wavs = []
        for index, span in enumerate(spans):
            path = seg_dir / f'{index:03d}.wav'
            # 앞뒤 0.1초 여유: 첫 자음이 잘리지 않게 (구간이 바뀌었으면 지난 받아쓰기를 지운다)
            stamp = Path(f'{path}.span')
            key = f"{span['start']} {span['end']}"
            if stamp.exists() and stamp.read_text() != key:
                for old in seg_dir.glob(f'{index:03d}.wav*'):
                    old.unlink()
            stamp.write_text(key)
            cut_wav(wav, max(0, span['start'] - 0.1), min(total, span['end'] + 0.1), path)
            wavs.append(path)
        for model_name, model in models.items():
            if name == 'fine' and model_name == 'small':
                continue  # 마디는 큰 모델로만 (경계·말 차례 확인용)
            texts = transcribe(wavs, model, seg_dir, model_name)
            for span, text in zip(spans, texts):
                span[model_name] = text
        out[name] = [dict(i=index, **span) for index, span in enumerate(spans)]
        print(f'{args.test_id}: {name} {len(spans)}개 받아씀')
    (work / 'segments.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    return 0


NUMBER_MAX = 1.3   # 번호만 읽은 덩어리는 이보다 짧다 (받아쓰기는 «R»·«哦»처럼 틀리기 쉬워 길이로 판단)
NUMBER_GAP = 1.8   # 번호 앞 쉼은 2초 넘는다 (대화 안의 «对。»·«妈。» 같은 짧은 말은 앞 쉼이 1.5초 이하)


def similar(a, b):
    sa, sb = syllables(a), syllables(b)
    return bool(sa and sb) and coverage(sa, sb) >= 0.8 and coverage(sb, sa) >= 0.8


def propose_cuts(segments, paper, unit='blocks'):
    """덩어리를 차례대로 훑어 문항 구간 초안을 만든다.

    - «第X部分…»·«例如» 뒤의 예시는 «现在开始…»까지 건너뛴다.
    - unit: 3급은 덩어리(blocks), 4급은 마디(fine). 4급은 번호·묶음 안내가 1초 안쪽 쉼으로 질문·지문에 붙어
      덩어리로는 갈리지 않고, large 받아쓰기가 긴 덩어리를 통째로 빠뜨린 일도 있었다(10번).
    - 앞 쉼이 NUMBER_GAP 이상인 짧은 조각(NUMBER_MAX 미만)은 번호 읽기로 보고, 받아쓴 숫자 대신 «다음 문항 번호»를 붙인다.
    - 3급(두 번 읽기): 같은 내용이 다시 나오면 다음 번호까지 버린다(첫 낭독만).
    - «…是根据下面一段话» 묶음: 문항마다 [지문] + [번호+자기 질문] 두 구간. 안내 문장은 넣지 않는다.
      3급 묶음 반복 낭독은 지문이 다시 나오는 데서 시작하고, 묶음 번호 수만큼 번호를 건너뛴다.
    """
    blocks = segments[unit]
    repeats = paper['level'] == 3
    order = [i['no'] for i in paper['listening']['items']]
    groups = {}
    for gid in paper['listening']['groups']:
        a, b = map(int, gid.split('-'))
        groups[a] = (gid, list(range(a, b + 1)))
    cuts, notes = {}, []
    state = {'nxt': 0, 'mode': 'skip', 'current': None, 'group': None}

    def add(no, blk, kind):
        cuts.setdefault(no, {'blocks': [], 'kinds': []})
        cuts[no]['blocks'].append(blk['i'])
        cuts[no]['kinds'].append(kind)

    def new_item(blk, kind):
        if state['nxt'] >= len(order):
            notes.append(f'{blk["i"]}: 문항이 다 찼는데 남은 조각 «{blk["large"]}»')
            state['mode'] = 'skip'
            return None
        no = order[state['nxt']]
        state['nxt'] += 1
        state['current'] = no
        add(no, blk, kind)
        return no

    prev_end = 0.0
    for blk in blocks:
        text, length = blk['large'], blk['end'] - blk['start']
        gap_before, prev_end = blk['start'] - prev_end, blk['end']
        mode = state['mode']
        if '听力' in text and '结束' in text:
            break
        if '现在开始' in text and '听力考试现在开始' not in text:
            # «第一部分…每题听一次，现在开始第一题»처럼 안내가 한 덩어리로 붙어 나오기도 한다
            state['mode'] = 'wait'
            continue
        if text.startswith(('第一部分', '第二部分', '第三部分')) or '例如' in text:
            state['mode'] = 'skip'
            continue
        if mode == 'skip':
            continue
        if '根据下面' in text:
            no = order[state['nxt']] if state['nxt'] < len(order) else None
            if no not in groups:
                notes.append(f'{blk["i"]}: 묶음 안내 «{text}»인데 {no}번은 묶음 시작이 아님')
                continue
            gid, nos = groups[no]
            state['group'] = {'gid': gid, 'nos': nos, 'passage': [], 'asked': 0, 'skip': 0}
            state['mode'] = 'g-passage'
            continue
        number = length < NUMBER_MAX and gap_before >= NUMBER_GAP
        group = state['group']
        if mode == 'g-repeat':
            if not number:
                continue
            if group['skip'] > 0:
                group['skip'] -= 1
                continue
            mode = 'wait'
        if mode in ('g-passage', 'g-question'):
            if number and group['asked'] < len(group['nos']):
                no = new_item(blk, 'number')
                group['asked'] += 1
                cuts[no]['passage'] = list(group['passage'])
                state['mode'] = 'g-question'
                continue
            if number:  # 묶음 질문이 다 나온 뒤의 번호
                if repeats:
                    state['mode'], group['skip'] = 'g-repeat', len(group['nos']) - 1
                    continue
                new_item(blk, 'number')
                state['mode'] = 'item'
                continue
            if mode == 'g-passage':
                group['passage'].append(blk['i'])
                continue
            if repeats and group['passage'] and similar(text, blocks[group['passage'][0]]['large']):
                state['mode'], group['skip'] = 'g-repeat', len(group['nos'])
                continue
            add(state['current'], blk, 'question')
            continue
        if number:
            new_item(blk, 'number')
            state['mode'] = 'item'
            continue
        if mode == 'repeat':
            continue
        if mode == 'wait':
            new_item(blk, 'content')  # «现在开始第一题» 바로 뒤처럼 번호 없이 시작
            state['mode'] = 'item'
            continue
        if mode == 'item':
            cur = cuts[state['current']]
            first = [i for i, k in zip(cur['blocks'], cur['kinds']) if k == 'content']
            if repeats and first and similar(text, blocks[first[0]]['large']):
                state['mode'] = 'repeat'
                continue
            add(state['current'], blk, 'content')
    if state['nxt'] != len(order):
        notes.append(f'문항 {state["nxt"]}개만 찾음 (기대 {len(order)})')

    items = []
    for no in order:
        c = cuts.get(no)
        if not c:
            notes.append(f'{no}번 구간 없음')
            continue
        own = [blocks[i] for i in c['blocks']]
        ranges = []
        if c.get('passage'):
            ranges.append([blocks[c['passage'][0]]['start'], blocks[c['passage'][-1]]['end']])
        ranges.append([own[0]['start'], own[-1]['end']])
        item = {'no': no, 'ranges': [[round(a, 3), round(b, 3)] for a, b in ranges],
                'blocks': c.get('passage', []) + c['blocks'],
                'heard': ' / '.join(blocks[i]['large'] for i in c.get('passage', []) + c['blocks'])}
        if c.get('passage'):
            item['group'] = next(g for g, nos in groups.values() if no in nos)
        items.append(item)
    return {'id': segments['id'], 'items': items}, notes


def cmd_propose(args):
    work = Path(args.work).expanduser() / args.test_id
    out_path = work / 'cuts.json'
    if out_path.exists() and not args.force:
        print(f'{out_path} 이미 있음 (--force로 덮어쓰기)')
        return 1
    segments = json.loads((work / 'segments.json').read_text(encoding='utf-8'))
    paper = json.loads((work / 'paper.json').read_text(encoding='utf-8'))
    unit = args.unit or ('blocks' if paper['level'] == 3 else 'fine')
    cuts, notes = propose_cuts(segments, paper, unit)
    cuts['unit'] = unit
    out_path.write_text(json.dumps(cuts, ensure_ascii=False, indent=1), encoding='utf-8')
    for item in cuts['items']:
        spans = ' + '.join(f'{a:.1f}-{b:.1f}' for a, b in item['ranges'])
        print(f"{item['no']:>2} {spans:<26} {item['heard'][:100]}")
    for n in notes:
        print('  !', n)
    return 1 if notes else 0


def snap(start, end, silences):
    """앞뒤로 PAD만큼 늘리되 이웃 말소리 쪽 무음의 가운데를 넘지 않는다."""
    before = [s for s in silences if s[1] <= start + 0.05]
    after = [s for s in silences if s[0] >= end - 0.05]
    lo = max(start - PAD, (before[-1][0] + before[-1][1]) / 2) if before else max(0, start - PAD)
    hi = min(end + PAD, (after[0][0] + after[0][1]) / 2) if after else end + PAD
    return round(lo, 3), round(hi, 3)


def cmd_build(args):
    work = Path(args.work).expanduser() / args.test_id
    cuts = json.loads((work / 'cuts.json').read_text(encoding='utf-8'))
    segments = json.loads((work / 'segments.json').read_text(encoding='utf-8'))
    source, silences = segments['wav'], segments['silences']
    src_mp3 = segments['source']

    clip_dir = work / 'clips'
    clip_dir.mkdir(exist_ok=True)
    for old in clip_dir.glob('*'):
        old.unlink()
    gap, lead, inner = clip_dir / 'gap.wav', clip_dir / 'lead.wav', clip_dir / 'inner.wav'
    for path, seconds in ((gap, GAP_BETWEEN), (lead, LEAD_IN), (inner, 0.6)):
        run(['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i',
             f'anullsrc=r={SAMPLE_RATE}:cl=mono', '-t', str(seconds), str(path)])

    playlist, timings, cursor = [lead], [], LEAD_IN
    for item in cuts['items']:
        no = item['no']
        parts, sources = [], []
        for k, (start, end) in enumerate(item['ranges']):
            lo, hi = snap(start, end, silences)
            clip = clip_dir / f'{no:02d}-{k}.wav'
            cut_wav(src_mp3, lo, hi, clip, rate=SAMPLE_RATE)
            if parts:
                parts.append(inner)  # 묶음 문항: 지문과 질문 사이 짧은 쉼
            parts.append(clip)
            sources.append([lo, hi])
        length = sum(duration(p) for p in parts)
        timings.append({'no': no, 'start': round(cursor, 3), 'end': round(cursor + length, 3), 'source': sources})
        playlist += parts + [gap]
        cursor += length + GAP_BETWEEN

    list_file = clip_dir / 'list.txt'
    list_file.write_text(''.join(f"file '{p}'\n" for p in playlist))
    joined = clip_dir / 'joined.wav'
    run(['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(list_file),
         '-c', 'copy', str(joined)])
    public = Path(args.public)
    public.mkdir(parents=True, exist_ok=True)
    out_mp3 = public / f'{args.test_id}.mp3'
    # tools/listening/audio.py build와 같은 음량·형식 (고정 비트레이트라야 브라우저 구간 이동이 정확하다)
    run(['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-i', str(joined),
         '-af', 'loudnorm=I=-18:TP=-1.5:LRA=11', '-ac', '1', '-ar', str(SAMPLE_RATE),
         '-c:a', 'libmp3lame', '-b:a', '32k', str(out_mp3)])
    (work / 'timings.json').write_text(json.dumps(timings, indent=1), encoding='utf-8')
    lengths = [t['end'] - t['start'] for t in timings]
    print(f'{args.test_id}: {out_mp3.name} {duration(out_mp3):.0f}초, 조각 {len(timings)}개 '
          f'(가장 짧은 {min(lengths):.1f}초, 가장 긴 {max(lengths):.1f}초)')
    return 0


def reference_text(item_cut, segments):
    """원본 구간 안에 든 덩어리들의 large 받아쓰기를 잇는다 (번호 덩어리는 뺀다)."""
    texts = []
    for start, end in item_cut['ranges']:
        for blk in segments['blocks']:
            if blk['start'] >= start - 0.05 and blk['end'] <= end + 0.05 and number_only(blk['large']) is None:
                texts.append(blk['large'])
    return ''.join(texts)


def cmd_verify(args):
    work = Path(args.work).expanduser() / args.test_id
    cuts = {c['no']: c for c in json.loads((work / 'cuts.json').read_text(encoding='utf-8'))['items']}
    segments = json.loads((work / 'segments.json').read_text(encoding='utf-8'))
    timings = json.loads((work / 'timings.json').read_text(encoding='utf-8'))
    script_path = work / 'script.json'
    script = {}
    if script_path.exists():
        script = {i['no']: ''.join(l['text'] for l in i['lines'])
                  for i in json.loads(script_path.read_text(encoding='utf-8'))['items']}
    mp3 = Path(args.public) / f'{args.test_id}.mp3'
    check_dir = work / 'verify'
    check_dir.mkdir(exist_ok=True)
    for old in check_dir.glob('*'):
        old.unlink()
    # 문항 조각을 통째로 받아쓰면 Whisper가 긴 조각(20초 넘게)의 가운데를 통째로 빠뜨리는 일이 있어서
    # 조각 안의 쉼(FINE_GAP)마다 다시 잘라 받아쓰고 잇는다.
    pieces, owner = [], []
    for t in timings:
        path = check_dir / f"{t['no']:02d}.wav"
        cut_wav(mp3, t['start'], t['end'], path)
        total = duration(path)
        for k, span in enumerate(speech_spans(detect_silences(path), total, FINE_GAP)):
            piece = check_dir / f"{t['no']:02d}-{k:02d}.wav"
            cut_wav(path, max(0, span['start'] - 0.1), min(total, span['end'] + 0.1), piece)
            pieces.append(piece)
            owner.append(t['no'])
    heard_pieces = transcribe(pieces, Path(args.model).expanduser(), check_dir, 'verify')
    joined = {}
    for no, text in zip(owner, heard_pieces):
        joined.setdefault(no, []).append(text)
    texts = [''.join(joined.get(t['no'], [])) for t in timings]
    report, low = [], []
    for t, text in zip(timings, texts):
        expected_text = script.get(t['no']) or reference_text(cuts[t['no']], segments)
        expected, heard = syllables(expected_text), syllables(text)
        cov = coverage(expected, heard)
        spill = len(heard) / max(1, len(expected))
        row = {'no': t['no'], 'against': 'script' if t['no'] in script else 'segments', 'coverage': round(cov, 3),
               'lengthRatio': round(spill, 2), 'heard': text, 'expected': expected_text}
        report.append(row)
        if cov < 0.85 or spill > 1.3:
            low.append(row)
    (work / 'verify.json').write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
    average = sum(r['coverage'] for r in report) / len(report)
    print(f'{args.test_id}: 평균 일치도 {average:.3f}, 확인 필요 {len(low)}개')
    for r in low:
        print(f"  ! {r['no']}번 일치도 {r['coverage']} 길이비 {r['lengthRatio']} 들린 글: {r['heard'][:60]}")
    return 1 if low else 0


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('transcribe')
    p.add_argument('test_id')
    p.add_argument('--mp3', required=True)
    p.add_argument('--work', required=True)
    p.add_argument('--large', required=True)
    p.add_argument('--small', required=True)
    p = sub.add_parser('propose')
    p.add_argument('test_id')
    p.add_argument('--work', required=True)
    p.add_argument('--force', action='store_true')
    p.add_argument('--unit', choices=('blocks', 'fine'))
    p = sub.add_parser('build')
    p.add_argument('test_id')
    p.add_argument('--work', required=True)
    p.add_argument('--public', required=True)
    p = sub.add_parser('verify')
    p.add_argument('test_id')
    p.add_argument('--work', required=True)
    p.add_argument('--public', required=True)
    p.add_argument('--model', required=True)
    args = parser.parse_args()
    return {'transcribe': cmd_transcribe, 'propose': cmd_propose, 'build': cmd_build, 'verify': cmd_verify}[args.command](args)


if __name__ == '__main__':
    raise SystemExit(main())
