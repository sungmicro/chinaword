#!/usr/bin/env python3
"""검증 음성에서 더 완전하게 들린 문장으로 임시 Whisper 대본을 보완한다."""
import argparse
import json
from pathlib import Path

from bootstrap import clean_text, split_sentences


KNOWN_ASR_FIXES = {
    '相交多少钱一斤?6.5。': '香蕉多少钱一斤？六块五。',
}


def refine_item(item, heard):
    text = clean_text(heard)
    for source, replacement in KNOWN_ASR_FIXES.items():
        text = text.replace(source, replacement)
    sentences = split_sentences(text)
    if item['part'] == 2 and len(sentences) > 1:
        sentences = sentences[:-1]
    item['lines'] = [
        {
            'speaker': '问' if item['part'] in (3, 4) and index == len(sentences) - 1 else None,
            'text': sentence,
        }
        for index, sentence in enumerate(sentences)
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('test_id')
    parser.add_argument('--work', required=True)
    args = parser.parse_args()

    base = Path(args.work).expanduser() / args.test_id
    paper_path = base / 'paper.json'
    paper = json.loads(paper_path.read_text(encoding='utf-8'))
    reports = json.loads((base / 'verify.json').read_text(encoding='utf-8'))
    items = {item['no']: item for item in paper['items']}

    changed = []
    for report in reports:
        if report['coverage'] < 0.5 or report['lengthRatio'] <= 1.5:
            continue
        refine_item(items[report['no']], report['heard'])
        changed.append(report['no'])

    paper_path.write_text(json.dumps(paper, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"{args.test_id}: 검증 음성으로 대본 {len(changed)}개 보완 ({', '.join(map(str, changed)) or '없음'})")


if __name__ == '__main__':
    main()
