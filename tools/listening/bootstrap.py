#!/usr/bin/env python3
"""듣기 대본이 빠진 HSK 시험지를 원본 음원의 반복 낭독으로 복구한다.

공식 음원은 각 문항을 같은 녹음으로 두 번 들려준다. 무음 구간으로 음원을 나눈 뒤
서로 이웃한 반복 조각을 찾아 첫 낭독을 1~40번에 배정하고, Whisper 전사를 paper.json의
대본으로 쓴다. 결과 align.json은 기존 audio.py build/verify가 그대로 사용할 수 있다.

  bootstrap.py H31006 --mp3 H31006.mp3 --work ~/hsk-listening-work --model ggml-small.bin
"""
import argparse
import json
import re
from pathlib import Path

from audio import (
    MAX_RUN,
    coverage,
    cut_wav,
    detect_silences,
    duration,
    run,
    speech_segments,
    syllables,
    transcribe,
)


EXAMPLE_TEXTS = [
    '喂请问张经理在吗他正在开会您半个小时以后再打好吗',
    '为了让自己更健康他每天花一个小时去锻炼身体他希望自己很健康',
    '小王帮我开一下门好吗没问题您去开会了谢谢男的为什么让小王开门',
    '请进您找谁我找张经理他在吗问男的来找谁',
    '今天我想早点回家看了看手表才五点过了一会儿再看表还是五点我这才发现我的手表不走了',
]
INTRO_WORDS = ('欢迎参加', '听力考试分', '听力考试现在开始')


def clean_text(text):
    text = re.sub(r'^\s*(?:第\s*)?[0-9一二三四五六七八九十零两]{1,3}[、，。,.：:\s]+', '', text)
    text = re.sub(r'[。！？?!]?\s*[謝谢]{2}大家收看\s*下次[見见][。！？?!]?', '', text)
    return text.strip()


def split_sentences(text):
    parts = [part.strip() for part in re.findall(r'.+?(?:[。！？?!]|$)', text) if part.strip()]
    return parts or [text.strip()]


def group(segments, start, count):
    chosen = segments[start:start + count]
    text = ''.join(segment['text'] for segment in chosen)
    return {
        'start': chosen[0]['start'],
        'end': chosen[-1]['end'],
        'text': text,
        'syllables': syllables(text),
    }


def repeated_pairs(segments):
    pairs, cursor = [], 0
    while cursor < len(segments) - 1:
        candidates = []
        for first_count in range(1, MAX_RUN + 1):
            second_start = cursor + first_count
            if second_start >= len(segments):
                break
            first = group(segments, cursor, first_count)
            if len(first['syllables']) < 3:
                continue
            for second_count in range(1, MAX_RUN + 1):
                if second_start + second_count > len(segments):
                    break
                second = group(segments, second_start, second_count)
                if len(second['syllables']) < 3:
                    continue
                forward = coverage(first['syllables'], second['syllables'])
                backward = coverage(second['syllables'], first['syllables'])
                similarity = min(forward, backward)
                duration_gap = abs((first['end'] - first['start']) - (second['end'] - second['start']))
                score = similarity - 0.08 * duration_gap - 0.015 * abs(first_count - second_count)
                candidates.append((score, similarity, duration_gap, first_count, second_count, first, second))
        if not candidates:
            cursor += 1
            continue
        best = max(candidates, key=lambda candidate: candidate[0])
        score, similarity, duration_gap, first_count, second_count, first, second = best
        # 같은 녹음이어도 Whisper가 한쪽 낭독의 첫 문장을 통째로 빠뜨릴 수 있다.
        # 길이가 거의 같은 이웃 조각이면 한쪽 방향 일치도가 낮아도 반복으로 인정한다.
        if similarity >= 0.45 and duration_gap <= 1.2 and score >= 0.42:
            pairs.append({
                'segment': cursor,
                'firstCount': first_count,
                'secondCount': second_count,
                'start': first['start'],
                'end': first['end'],
                'repeatStart': second['start'],
                'repeatEnd': second['end'],
                'similarity': round(similarity, 3),
                'text': clean_text(first['text']),
            })
            cursor += first_count + second_count
        else:
            cursor += 1
    return pairs


def is_example(pair):
    text = pair['text']
    if any(word in text for word in INTRO_WORDS):
        return True
    observed = syllables(text)
    return any(coverage(syllables(example), observed) >= 0.55 for example in EXAMPLE_TEXTS)


def choose_questions(pairs):
    usable = [pair for pair in pairs if not is_example(pair)]
    if len(usable) == 40:
        return usable

    # 전사 결과가 예시 한두 개를 다르게 읽었을 때의 표준 시험 순서 보정.
    # 반복 후보는 보통 [안내 1, 예시+문항 11개 × 4부분] = 45개다.
    for offset in range(max(0, len(pairs) - 45), min(4, len(pairs))):
        indices = list(range(offset + 2, offset + 12))
        indices += list(range(offset + 13, offset + 23))
        indices += list(range(offset + 24, offset + 34))
        indices += list(range(offset + 35, offset + 45))
        if indices[-1] < len(pairs):
            chosen = [pairs[index] for index in indices]
            if len(chosen) == 40:
                return chosen
    raise ValueError(f'문항 반복 40개를 고르지 못했습니다: 전체 {len(pairs)}개, 예시 제외 {len(usable)}개')


def fill_paper(paper, questions):
    for item, pair in zip(paper['items'], questions):
        text = pair['text']
        sentences = split_sentences(text)
        if item['part'] == 2:
            # 두 번째 부분은 마지막에 시험지의 ★ 문장을 읽는다.
            item['statement'] = item.get('paperStatement')
            if len(sentences) > 1:
                sentences = sentences[:-1]
        lines = []
        for index, sentence in enumerate(sentences):
            speaker = '问' if item['part'] in (3, 4) and index == len(sentences) - 1 else None
            lines.append({'speaker': speaker, 'text': sentence})
        item['lines'] = lines or [{'speaker': None, 'text': text}]
    return paper


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('test_id')
    parser.add_argument('--mp3', required=True)
    parser.add_argument('--work', required=True)
    parser.add_argument('--model', required=True)
    args = parser.parse_args()

    base = Path(args.work).expanduser() / args.test_id
    paper_path = base / 'paper.json'
    paper = json.loads(paper_path.read_text(encoding='utf-8'))
    wav = base / 'source.wav'
    run(['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-i', args.mp3, '-ac', '1', '-ar', '16000', str(wav)])
    silences = detect_silences(wav)
    segments = speech_segments(silences, duration(wav))

    segment_dir = base / 'bootstrap-segments'
    segment_dir.mkdir(exist_ok=True)
    wavs = []
    for index, segment in enumerate(segments):
        path = segment_dir / f'{index:03d}.wav'
        cut_wav(wav, segment['start'], segment['end'], path)
        wavs.append(path)

    cache_path = base / 'bootstrap-segments.json'
    cached = {}
    if cache_path.exists():
        cached_data = json.loads(cache_path.read_text(encoding='utf-8'))
        cached = {(entry['start'], entry['end']): entry['text'] for entry in cached_data}
    pending = [(segment, path) for segment, path in zip(segments, wavs)
               if (segment['start'], segment['end']) not in cached]
    fresh_texts = transcribe([path for _, path in pending], Path(args.model).expanduser(), segment_dir) if pending else []
    fresh = {(segment['start'], segment['end']): text for (segment, _), text in zip(pending, fresh_texts)}
    for segment in segments:
        key = (segment['start'], segment['end'])
        segment['text'] = fresh.get(key, cached.get(key, ''))
    cache_path.write_text(json.dumps(segments, ensure_ascii=False, indent=1), encoding='utf-8')

    pairs = repeated_pairs(segments)
    questions = choose_questions(pairs)
    (base / 'bootstrap-pairs.json').write_text(json.dumps(pairs, ensure_ascii=False, indent=1), encoding='utf-8')
    paper_path.write_text(json.dumps(fill_paper(paper, questions), ensure_ascii=False, indent=1), encoding='utf-8')

    aligned = []
    for number, pair in enumerate(questions, start=1):
        aligned.append({
            'no': number,
            'start': pair['start'],
            'end': pair['end'],
            'coverage': pair['similarity'],
            'repeat': {'start': pair['repeatStart'], 'end': pair['repeatEnd']},
            'ok': True,
            'heard': pair['text'],
        })
    align = {
        'id': args.test_id,
        # YouTube 원본은 VBR/분할 스트림이라 뒤쪽을 직접 seek하면 위치가 어긋날 수 있다.
        # 처음부터 디코딩한 PCM을 자르면 30분 이후 문항도 정확한 시각에 잘린다.
        'source': str(wav),
        'silences': silences,
        'segments': segments,
        'items': aligned,
    }
    (base / 'align.json').write_text(json.dumps(align, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{args.test_id}: 음성 조각 {len(segments)}개, 반복 후보 {len(pairs)}개, 문항 40개 복구')
    print('  첫 문항:', questions[0]['text'][:60])
    print('  마지막 문항:', questions[-1]['text'][:60])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
