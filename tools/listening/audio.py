#!/usr/bin/env python3
"""HSK 듣기 원본 음원에서 문항별 첫 번째 낭독을 찾아, 문제만 이어 붙인 mp3를 만든다.

  audio.py align H31001 --mp3 H31001.mp3 --work ~/hsk-listening-work --model ggml-small.bin
      무음으로 원본을 조각내고, 조각마다 받아써서 대본(paper.json)과 맞춘다 → <work>/<회차>/align.json
  audio.py build H31001 --work ~/hsk-listening-work --public public/listening
      첫 낭독만 잘라 2초 쉼으로 이어 붙인다 → <public>/<회차>.mp3, <work>/<회차>/timings.json
  audio.py verify H31001 --work ~/hsk-listening-work --model ggml-small.bin
      이어 붙인 mp3를 문항 구간마다 다시 받아써 대본과 얼마나 맞는지 확인한다.

원본에서 각 문항은 '번호+낭독 → 약 2초 쉼 → 같은 낭독 → 6~10초 쉼' 순서로 나온다.
1.6초 이상 쉬는 곳에서 자르면 조각 하나가 대개 낭독 한 번이다.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

from pypinyin import Style, lazy_pinyin

SILENCE_DB = '-35dB'
MIN_SILENCE = 0.3   # 이보다 짧은 쉼은 무시
SPLIT_GAP = 1.6     # 이 이상 쉬면 다른 조각으로 본다 (반복 사이 쉼은 1.9초 이상, 대화 안 쉼은 대개 1.1초 이하)
MAX_RUN = 3         # 대화 중간에 긴 쉼이 있으면 낭독 하나가 조각 여러 개로 나뉜다
GAP_BETWEEN = 2.0   # 이어 붙일 때 문항 사이 쉼
LEAD_IN = 0.5
PAD_BEFORE = 0.25
PAD_AFTER = 0.35
SAMPLE_RATE = 22050
DIGITS = dict(zip('0123456789', '零一二三四五六七八九'))


def run(cmd, **kwargs):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kwargs)


def syllables(text):
    """성조 없는 병음 음절 목록. 번체·동음 오인식이 섞여도 비교가 되게 한다."""
    text = ''.join(DIGITS.get(ch, ch) for ch in text)
    text = re.sub(r'[^一-鿿]', '', text)
    return [s for s in lazy_pinyin(text, style=Style.NORMAL) if s.isalpha()]


def lcs(a, b):
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b):
            cur.append(prev[j] + 1 if x == y else max(prev[j + 1], cur[j]))
        prev = cur
    return prev[-1]


def coverage(expected, observed):
    return lcs(expected, observed) / len(expected) if expected else 0.0


def duration(path):
    out = run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)]).stdout
    return float(out.strip())


def detect_silences(wav):
    out = subprocess.run(
        ['ffmpeg', '-nostdin', '-hide_banner', '-nostats', '-i', str(wav),
         '-af', f'silencedetect=noise={SILENCE_DB}:d={MIN_SILENCE}', '-f', 'null', '-'],
        capture_output=True, text=True, check=True,
    ).stderr
    starts = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', out)]
    ends = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', out)]
    return list(zip(starts, ends))


def speech_segments(silences, total):
    """SPLIT_GAP 이상 쉬는 곳을 경계로 말소리 조각을 만든다."""
    gaps = [(s, e) for s, e in silences if e - s >= SPLIT_GAP]
    segments, cursor = [], 0.0
    for start, end in gaps + [(total, total)]:
        if start - cursor >= 0.6:
            segments.append({'start': round(cursor, 3), 'end': round(start, 3)})
        cursor = end
    return segments


def transcribe(wavs, model, out_dir):
    """whisper-cli 한 번으로 여러 파일을 받아쓴다 (모델을 한 번만 올린다)."""
    cmd = ['whisper-cli', '-m', str(model), '-l', 'zh', '-t', '8', '-nt', '-otxt',
           '--prompt', '以下是普通话的句子，使用简体中文。']
    for wav in wavs:
        cmd += ['-f', str(wav)]
    run(cmd, cwd=out_dir)
    return [Path(f'{wav}.txt').read_text(encoding='utf-8').strip() for wav in wavs]


def cut_wav(src, start, end, dst, rate=16000):
    run(['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-i', str(src), '-ss', f'{start:.3f}', '-to', f'{end:.3f}',
         '-ac', '1', '-ar', str(rate), str(dst)])


def expected_text(item):
    text = ''.join(line['text'] for line in item['lines'])
    if item.get('statement'):
        text += item['statement']
    return text


def match_items(items, segments):
    """문항 순서대로, 대본과 가장 잘 맞는 조각 묶음(첫 낭독)을 찾는다."""
    results, cursor = [], 0
    for item in items:
        expected = syllables(expected_text(item))
        candidates = []
        for j in range(cursor, min(cursor + 12, len(segments))):
            observed = []
            for m in range(1, MAX_RUN + 1):
                if j + m > len(segments):
                    break
                observed = observed + segments[j + m - 1]['syllables']
                cov = coverage(expected, observed)
                extra = max(0, len(observed) - len(expected) * 1.15) / max(1, len(expected))
                candidates.append({'j': j, 'm': m, 'coverage': cov, 'score': cov - 0.6 * extra})
        if not candidates:
            results.append({'no': item['no'], 'ok': False, 'reason': '남은 조각 없음'})
            continue
        best = max(c['score'] for c in candidates)
        # 첫 낭독과 두 번째 낭독이 둘 다 잘 맞으면 앞의 것을, 끝이 같으면 앞 안내 멘트가 덜 붙은 짧은 쪽을 고른다.
        chosen = min((c for c in candidates if c['score'] >= best - 0.08), key=lambda c: (c['j'] + c['m'], -c['j']))
        j, m = chosen['j'], chosen['m']

        # 받아쓰기가 첫 낭독의 앞부분을 빼먹으면 두 번째 낭독이 뽑힌다.
        # 바로 앞에 같은 길이의 조각 묶음이 2~3초 쉼을 두고 있으면 그게 첫 낭독이다.
        span = segments[j + m - 1]['end'] - segments[j]['start']
        if j - m >= cursor:
            prev_span = segments[j - 1]['end'] - segments[j - m]['start']
            gap = segments[j]['start'] - segments[j - 1]['end']
            if abs(prev_span - span) <= 0.25 and gap <= 3.0:
                j = j - m

        # 번호를 읽고 1.6초 넘게 쉬면 번호('13，')만 따로 떨어진 짧은 조각이 된다. 낭독에 붙인다.
        if j - 1 >= cursor:
            number = segments[j - 1]
            if number['end'] - number['start'] < 1.6 and segments[j]['start'] - number['end'] < 1.9 \
                    and re.fullmatch(r'[\d一二三四五六七八九十零.,，。:：\s]*', number['text']):
                j, m = j - 1, m + 1

        first, last = segments[j], segments[j + m - 1]
        reading = {'start': first['start'], 'end': last['end']}

        # 바로 뒤에 같은 길이의 두 번째 낭독이 있는지 본다 (같은 녹음을 두 번 틀기 때문에 길이가 거의 같다).
        length = reading['end'] - reading['start']
        nxt = j + m
        repeat = None
        for m in range(1, MAX_RUN + 1):
            if nxt + m > len(segments):
                break
            span = segments[nxt + m - 1]['end'] - segments[nxt]['start']
            if abs(span - length) <= 0.6:
                repeat = {'start': segments[nxt]['start'], 'end': segments[nxt + m - 1]['end']}
                cursor = nxt + m
                break
        else:
            cursor = nxt

        results.append({
            'no': item['no'],
            'start': reading['start'],
            'end': reading['end'],
            'coverage': round(chosen['coverage'], 3),
            'repeat': repeat,
            # 받아쓰기가 앞부분을 빼먹는 일이 있어서, 반복 낭독과 길이가 같으면 일치도가 낮아도 구간은 맞다고 본다.
            'ok': repeat is not None and (chosen['coverage'] >= 0.6 or (
                chosen['coverage'] >= 0.3 and abs((repeat['end'] - repeat['start']) - length) <= 0.25)),
            'heard': ''.join(seg['text'] for seg in segments[j:j + m]),
        })
    return results


def cmd_align(args):
    work = Path(args.work).expanduser() / args.test_id
    paper = json.loads((work / 'paper.json').read_text(encoding='utf-8'))
    wav = work / 'source.wav'
    run(['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-i', str(args.mp3), '-ac', '1', '-ar', '16000', str(wav)])
    total = duration(wav)
    silences = detect_silences(wav)
    segments = speech_segments(silences, total)

    seg_dir = work / 'segments'
    seg_dir.mkdir(exist_ok=True)
    for old in seg_dir.glob('*'):
        old.unlink()
    wavs = []
    for index, seg in enumerate(segments):
        path = seg_dir / f'{index:03d}.wav'
        cut_wav(wav, seg['start'], seg['end'], path)
        wavs.append(path)
    # 같은 구간은 지난번 받아쓰기를 다시 쓴다 (매칭 규칙만 고쳐서 다시 돌릴 때 빠르게).
    cached = {}
    if (work / 'align.json').exists():
        old = json.loads((work / 'align.json').read_text(encoding='utf-8'))
        cached = {(s['start'], s['end']): s['text'] for s in old['segments']}
    todo = [(seg, path) for seg, path in zip(segments, wavs) if (seg['start'], seg['end']) not in cached]
    fresh = dict(zip([id(seg) for seg, _ in todo],
                     transcribe([path for _, path in todo], Path(args.model).expanduser(), seg_dir) if todo else []))
    texts = [fresh.get(id(seg), cached.get((seg['start'], seg['end']))) for seg in segments]
    for seg, text in zip(segments, texts):
        seg['text'] = text
        seg['syllables'] = syllables(text)

    matches = match_items(paper['items'], segments)
    out = {'id': args.test_id, 'source': str(args.mp3), 'silences': silences,
           'segments': [{k: v for k, v in s.items() if k != 'syllables'} for s in segments], 'items': matches}
    (work / 'align.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')

    bad = [m for m in matches if not m['ok']]
    print(f'{args.test_id}: 조각 {len(segments)}개, 문항 {len(matches)}개 맞춤, 확인 필요 {len(bad)}개')
    for m in bad:
        print(f"  ! {m['no']}번 coverage={m.get('coverage')} repeat={'있음' if m.get('repeat') else '없음'} "
              f"{m.get('start')}–{m.get('end')} 들린 글: {m.get('heard', '')[:40]}")
    return 0


def snap_bounds(start, end, silences):
    """앞뒤 여유를 조금 두되, 이웃한 말소리를 침범하지 않게 무음 안에서만 늘린다."""
    before = [s for s in silences if s[1] <= start + 0.05]
    after = [s for s in silences if s[0] >= end - 0.05]
    lo = max(start - PAD_BEFORE, (before[-1][0] + before[-1][1]) / 2) if before else max(0, start - PAD_BEFORE)
    hi = min(end + PAD_AFTER, (after[0][0] + after[0][1]) / 2) if after else end + PAD_AFTER
    return lo, hi


def cmd_build(args):
    work = Path(args.work).expanduser() / args.test_id
    align = json.loads((work / 'align.json').read_text(encoding='utf-8'))
    overrides = {}
    override_path = work / 'overrides.json'
    if override_path.exists():
        # 자동으로 못 맞춘 문항은 사람이 들어 보고 {"12": [start, end]} 로 적어 둔다.
        overrides = {int(k): v for k, v in json.loads(override_path.read_text()).items()}

    clip_dir = work / 'clips'
    clip_dir.mkdir(exist_ok=True)
    for old in clip_dir.glob('*'):
        old.unlink()

    silence = clip_dir / 'gap.wav'
    lead = clip_dir / 'lead.wav'
    for path, seconds in ((silence, GAP_BETWEEN), (lead, LEAD_IN)):
        run(['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i',
             f'anullsrc=r={SAMPLE_RATE}:cl=mono', '-t', str(seconds), str(path)])

    playlist, timings, cursor = [lead], [], LEAD_IN
    for item in align['items']:
        no = item['no']
        if no in overrides:
            start, end = overrides[no]
        else:
            if 'start' not in item:
                raise SystemExit(f'{no}번 구간이 없습니다. overrides.json에 적어 주세요.')
            start, end = snap_bounds(item['start'], item['end'], align['silences'])
        clip = clip_dir / f'{no:02d}.wav'
        cut_wav(align['source'], start, end, clip, rate=SAMPLE_RATE)
        length = duration(clip)
        timings.append({'no': no, 'start': round(cursor, 3), 'end': round(cursor + length, 3),
                        'source': [round(start, 3), round(end, 3)]})
        cursor += length
        playlist += [clip, silence]
        cursor += GAP_BETWEEN

    list_file = clip_dir / 'list.txt'
    list_file.write_text(''.join(f"file '{p}'\n" for p in playlist))
    public = Path(args.public)
    public.mkdir(parents=True, exist_ok=True)
    joined = clip_dir / 'joined.wav'
    run(['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(list_file),
         '-c', 'copy', str(joined)])
    # 회차마다 원본 음량이 달라서 고르게 맞춘다. 고정 비트레이트(CBR)라야 브라우저에서 구간 이동이 정확하다.
    out_mp3 = public / f'{args.test_id}.mp3'
    run(['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-i', str(joined),
         '-af', 'loudnorm=I=-18:TP=-1.5:LRA=11', '-ac', '1', '-ar', str(SAMPLE_RATE),
         '-c:a', 'libmp3lame', '-b:a', '32k', str(out_mp3)])
    (work / 'timings.json').write_text(json.dumps(timings, indent=1), encoding='utf-8')
    lengths = [t['end'] - t['start'] for t in timings]
    print(f'{args.test_id}: {out_mp3.name} {duration(out_mp3):.0f}초, 조각 {len(timings)}개 '
          f'(가장 짧은 {min(lengths):.1f}초, 가장 긴 {max(lengths):.1f}초)')
    odd = [t['no'] for t in timings if not 3 <= t['end'] - t['start'] <= 40]
    if odd:
        print(f'  ! 길이가 3~40초를 벗어난 문항: {odd}')
    return 0


def cmd_verify(args):
    work = Path(args.work).expanduser() / args.test_id
    paper = {i['no']: i for i in json.loads((work / 'paper.json').read_text(encoding='utf-8'))['items']}
    timings = json.loads((work / 'timings.json').read_text(encoding='utf-8'))
    mp3 = Path(args.public) / f'{args.test_id}.mp3'
    check_dir = work / 'verify'
    check_dir.mkdir(exist_ok=True)
    wavs = []
    for t in timings:
        path = check_dir / f"{t['no']:02d}.wav"
        cut_wav(mp3, t['start'], t['end'], path)
        wavs.append(path)
    texts = transcribe(wavs, Path(args.model).expanduser(), check_dir)
    report, low = [], []
    for t, text in zip(timings, texts):
        expected = syllables(expected_text(paper[t['no']]))
        heard = syllables(text)
        cov = coverage(expected, heard)
        # 다른 문항 소리가 섞여 들어오면 받아쓴 글이 대본보다 훨씬 길어진다.
        spill = len(heard) / max(1, len(expected))
        report.append({'no': t['no'], 'coverage': round(cov, 3), 'lengthRatio': round(spill, 2), 'heard': text})
        if cov < 0.7 or spill > 1.5:
            low.append(report[-1])
    (work / 'verify.json').write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
    average = sum(r['coverage'] for r in report) / len(report)
    print(f'{args.test_id}: 평균 일치도 {average:.2f}, 확인 필요 {len(low)}개')
    for r in low:
        print(f"  ! {r['no']}번 일치도 {r['coverage']} 길이비 {r['lengthRatio']} 들린 글: {r['heard'][:50]}")
    return 1 if low else 0


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    p_align = sub.add_parser('align')
    p_align.add_argument('test_id')
    p_align.add_argument('--mp3', required=True)
    p_align.add_argument('--work', required=True)
    p_align.add_argument('--model', required=True)
    p_build = sub.add_parser('build')
    p_build.add_argument('test_id')
    p_build.add_argument('--work', required=True)
    p_build.add_argument('--public', required=True)
    p_verify = sub.add_parser('verify')
    p_verify.add_argument('test_id')
    p_verify.add_argument('--work', required=True)
    p_verify.add_argument('--public', required=True)
    p_verify.add_argument('--model', required=True)
    args = parser.parse_args()
    return {'align': cmd_align, 'build': cmd_build, 'verify': cmd_verify}[args.command](args)


if __name__ == '__main__':
    raise SystemExit(main())
