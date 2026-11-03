#!/usr/bin/env python3
"""paper.json(대본·정답) + enrich.json(병음·해석·단어·문장 구조) + timings.json(음원 구간)을 합쳐
앱이 읽는 public/listening/<회차>.json을 만들고, 듣기 핵심 단어를 단어장(vocab.json)에 넣는다.

  assemble.py H31001 H31002 ... --work ~/hsk-listening-work --repo .
  assemble.py H31001 --work ~/hsk-listening-work --repo . --check   # 검사만, 파일을 쓰지 않음

먼저 해설을 기계적으로 검사한다. 단어 묶음의 한자를 이으면 원문과 같아야 하고,
pypinyin과 음절이 다른 단어는 목록으로 보여준다(다음자는 사람이 맞는지 본다).
핵심 단어는 tools/vocab_fixes.json 보정을 거친 뒤, 뜻에 한글이 있는지·품사가 «단어»가 아닌지 검사한다.
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

from pypinyin import Style, lazy_pinyin

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vocab_fixes import CardIds, fix_vocab, vocab_problems  # noqa: E402  tools/vocab_fixes.py
from script_fixes import apply_script_fixes  # noqa: E402  tools/listening/script_fixes.py

LESSON = 'HSK3 듣기'
PART_GUIDES = {
    1: '대화를 듣고 알맞은 사진 고르기',
    2: '듣고 ★ 문장이 맞는지 판단하기',
    3: '짧은 대화를 듣고 질문에 답하기',
    4: '긴 대화를 듣고 질문에 답하기',
}
DIGIT_READINGS = set('0123456789')


def toneless(pinyin):
    text = re.sub('[üǖǘǚǜ]', 'v', pinyin.lower())  # 성조 부호를 지우기 전에 ü를 v로 (pypinyin 표기)
    text = unicodedata.normalize('NFD', text)
    text = ''.join(ch for ch in text if unicodedata.category(ch) != 'Mn')
    return re.sub(r"[^a-z]", '', text)


def check_words(words, source, where, problems, reading_diffs):
    joined = ''.join(token for token, _ in words)
    if joined != source:
        problems.append(f'{where}: 한자 이어 붙이기가 원문과 다름\n    원문 {source}\n    결과 {joined}')
    for token, pinyin in words:
        hanzi = re.sub(r'[^一-鿿]', '', token)
        if not hanzi:
            if pinyin and not set(token) & DIGIT_READINGS:
                problems.append(f'{where}: 문장부호 "{token}"에 병음 "{pinyin}"')
            continue
        if not pinyin:
            problems.append(f'{where}: "{token}" 병음 없음')
            continue
        if hanzi != token:
            continue  # 숫자·기호가 섞인 토큰은 읽기를 사람이 정했다
        expected = ''.join(lazy_pinyin(token, style=Style.NORMAL))
        accepted = {expected}
        if len(token) > 1 and token.endswith('儿') and expected.endswith('er'):
            accepted.add(expected[:-2] + 'r')  # 儿화: pypinyin은 'dianer', 대본은 'diǎnr'
        if toneless(pinyin) not in accepted:
            reading_diffs.append(f'{where}: {token} {pinyin} (pypinyin: {"".join(lazy_pinyin(token, style=Style.TONE))})')


def build_test(test_id, work, problems, reading_diffs):
    base = work / test_id
    paper = json.loads((base / 'paper.json').read_text(encoding='utf-8'))
    enrich = {i['no']: i for i in json.loads((base / 'enrich.json').read_text(encoding='utf-8'))['items']}
    timings = {t['no']: t for t in json.loads((base / 'timings.json').read_text(encoding='utf-8'))}
    groups = {no: group for group in paper['pictureGroups'] for no in group['nos']}

    items = []
    for source in paper['items']:
        no = source['no']
        where = f'{test_id} {no}번'
        note = enrich.get(no)
        if not note:
            problems.append(f'{where}: 해설 없음')
            continue
        if len(note['lines']) != len(source['lines']):
            problems.append(f'{where}: 대본 줄 수가 다름 ({len(source["lines"])} vs {len(note["lines"])})')
            continue
        # 핵심 단어는 보정 사전(tools/vocab_fixes.json)을 거친다: 뜻에 한글 필수, 품사 «단어» 금지.
        vocab = fix_vocab(note.get('vocab'), f'listening/{test_id}/{no}')
        if not 3 <= len(vocab) <= 8:
            problems.append(f'{where}: 핵심 단어는 3~8개 ({len(vocab)}개)')
        for word in vocab:
            problems.extend(vocab_problems(word, where))

        script = []
        for index, (line, annotated) in enumerate(zip(source['lines'], note['lines'])):
            check_words(annotated['words'], line['text'], f'{where} {index + 1}줄', problems, reading_diffs)
            script.append({'speaker': line['speaker'], 'words': annotated['words'], 'ko': annotated['ko']})

        part = source['part']
        if part == 1:
            group = groups[no]
            choices = {'type': 'picture', 'image': group['image'], 'labels': group['labels']}
        elif part == 2:
            statement = note['statement']
            check_words(statement['words'], source['paperStatement'], f'{where} ★', problems, reading_diffs)
            choices = {'type': 'truefalse', 'statement': statement}
            # 2부분은 ★ 문장도 소리로 읽어 주므로 대본 끝에 붙인다.
            script.append({'speaker': '★', 'words': statement['words'], 'ko': statement['ko']})
        else:
            options = []
            for option, annotated in zip(source['options'], note['options']):
                check_words(annotated['words'], option['text'], f'{where} 보기 {option["label"]}', problems, reading_diffs)
                options.append({'label': option['label'], 'words': annotated['words'], 'ko': annotated['ko']})
            choices = {'type': 'text', 'options': options}

        timing = timings[no]
        items.append({
            'no': no,
            'part': part,
            'start': timing['start'],
            'end': timing['end'],
            'choices': choices,
            'answer': source['answer'],
            'script': script,
            'vocab': vocab,
            'grammar': note['grammar'],
        })

    test = {
        'id': test_id,
        'title': f'HSK 3급 {test_id}',
        'audio': f'{test_id}.mp3',
        'parts': [{'part': p, 'guide': g} for p, g in PART_GUIDES.items()],
        'items': items,
    }
    # 대본 인식 오류 보정(tools/listening/script_fixes.json). 단어를 바꾼 문항은 보정 사전·검사를 다시 거친다.
    for no in apply_script_fixes(test, problems):
        item = next(item for item in items if item['no'] == no)
        item['vocab'] = fix_vocab(item['vocab'], f'listening/{test_id}/{no}')
        for word in item['vocab']:
            problems.extend(vocab_problems(word, f'{test_id} {no}번'))
    return test


PUNCT_PINYIN = {'，': ',', '、': ',', '。': '.', '？': '?', '！': '!', '：': ':', '；': ';', '“': '"', '”': '"'}


def words_to_pinyin(words):
    """[['你','nǐ'],['，','']] → 'Nǐ,' 처럼 단어장 예문 병음 한 줄로 만든다."""
    out = ''
    for token, pinyin in words:
        if pinyin:
            out += (' ' if out and not out.endswith('"') else '') + pinyin
        elif token in PUNCT_PINYIN:
            out += PUNCT_PINYIN[token]
    return out[:1].upper() + out[1:]


def example_for(word, item):
    """단어가 처음 나온 대본 문장(없으면 보기)을 예문으로 쓴다."""
    sentences = item['script'] + item['choices'].get('options', [])
    for sentence in sentences:
        text = ''.join(token for token, _ in sentence['words'])
        if word in text:
            return text, words_to_pinyin(sentence['words']), sentence['ko']
    return '', '', ''


def update_vocab(tests, repo):
    path = repo / 'src' / 'data' / 'vocab.json'
    vocab = json.loads(path.read_text(encoding='utf-8'))
    # 다시 돌려도 같은 결과가 나오게 지난번에 넣은 듣기 단어는 지우고 새로 넣는다.
    # 오답노트가 카드 id로 기록되므로, 지난번에 있던 단어는 같은 id를 다시 쓰고 새 단어만 다음 번호를 받는다.
    # 사라진 카드의 id는 src/data/vocab-retired.json에 은퇴시켜 다시 쓰지 않는다(tools/vocab_fixes.py CardIds).
    ids = CardIds(repo, 'HSK3L', {entry['hanzi']: entry['id'] for entry in vocab if entry.get('lesson') == LESSON})
    vocab = [entry for entry in vocab if entry.get('lesson') != LESSON]
    known = {entry['hanzi'] for entry in vocab}
    added = []
    for test in tests:
        for item in test['items']:
            for word in item['vocab']:
                if word['hanzi'] in known:
                    continue
                known.add(word['hanzi'])
                zh, py, ko = example_for(word['hanzi'], item)
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
                    'source': f'HSK3 공식 모의고사 {test["id"]} 듣기 {item["no"]}번',
                    'tags': ['HSK3', '단어', LESSON, test['id']],
                })
    ids.write(path, vocab + added)  # 장부를 먼저 계산·검사하고 vocab.json과 함께 바꾼다
    return len(added)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('test_ids', nargs='+')
    parser.add_argument('--work', required=True)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--show-readings', action='store_true', help='pypinyin과 음절이 다른 단어를 모두 보여준다')
    parser.add_argument('--check', action='store_true', help='검사만 하고 파일을 쓰지 않는다')
    args = parser.parse_args()
    work, repo = Path(args.work).expanduser(), Path(args.repo)

    problems, reading_diffs, tests = [], [], []
    for test_id in args.test_ids:
        tests.append(build_test(test_id, work, problems, reading_diffs))

    print(f'pypinyin과 음절이 다른 단어 {len(reading_diffs)}개 (다음자는 맞을 수 있음)')
    if args.show_readings:
        for diff in reading_diffs:
            print('  ? ' + diff)
    if problems:
        for problem in problems:
            print('  ! ' + problem)
        print('문제가 있어 파일을 쓰지 않았습니다.')
        return 1
    if args.check:
        print('검사 통과 (--check라 파일은 쓰지 않았습니다).')
        return 0

    public = repo / 'public' / 'listening'
    for test in tests:
        (public / f'{test["id"]}.json').write_text(json.dumps(test, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    index = [{'id': t['id'], 'title': t['title'], 'count': len(t['items'])} for t in tests]
    (repo / 'src' / 'data' / 'listening-index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    added = update_vocab(tests, repo)
    print(f'회차 {len(tests)}개를 썼고, 단어장에 «{LESSON}» 단어 {added}개를 넣었습니다.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
