#!/usr/bin/env python3
"""HSK 시험 원문에 병음·한국어 풀이를 붙여 기존 앱 데이터 형식으로 만든다.

공개 시험지의 원문만 번역하며, Google 번역 결과는 작업 폴더 밖 캐시에 보관해 다시
실행할 때 같은 문장을 재요청하지 않는다. 생성 결과는 기존 assemble.py 검사를 통과해야
실제 public 데이터로 들어간다.
"""
import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

import jieba
import jieba.posseg as posseg
from pypinyin import Style, lazy_pinyin


PUNCT = set('，。！？：；、“”‘’（）《》…—,.?!:;()[] ')
STOPWORDS = set('''
的 是 了 在 我 你 他 她 它 们 和 也 都 就 很 有 不 这 那 一 个
我们 你们 他们 什么 吗 呢 吧 啊 着 过 把 被 给 到 对 从 为 与 而 但
又 还 让 使 才 再 只 会 能 要 想 去 来 上 下来 里 外 中 后 前 时 地 得
第 每 各 某 其 于 及 或 并 所 因为 所以 如果 虽然 但是 然后 已经 正在
可以 应该 没有 不是 怎么 怎样 多少 哪里 哪儿 谁
'''.split())
POS_KO = {
    'n': '명사', 'v': '동사', 'a': '형용사', 'd': '부사', 'r': '대명사', 'm': '수사',
    'q': '양사', 'p': '개사', 'c': '접속사', 't': '시간사', 's': '장소사', 'f': '방위사',
}
GRAMMAR_RULES = [
    (('虽然', '但是'), '虽然 A，但是 B', 'A이지만 B', '앞내용과 대비되는 핵심 내용을 뒤에서 말합니다.'),
    (('因为', '所以'), '因为 A，所以 B', 'A이기 때문에 B', '원인과 결과를 이어 줍니다.'),
    (('如果',), '如果 A，就 B', '만약 A라면 B', '조건과 그 결과를 나타냅니다.'),
    (('一边',), '一边 A，一边 B', 'A하면서 B하다', '두 동작이 동시에 진행됨을 나타냅니다.'),
    (('除了',), '除了 A，还 B', 'A 말고도 B', 'A에 B를 더하는 표현입니다.'),
    (('越来越',), '越来越 + 형용사', '점점 더 ~하다', '시간에 따른 변화의 정도를 나타냅니다.'),
    (('把',), '把 + 목적어 + 동사', '목적어를 ~하다', '처리하거나 변화시키는 대상을 동사 앞에 둡니다.'),
    (('被',), '주어 + 被 + 행위자 + 동사', '~에 의해 ~되다', '동작을 받는 대상을 주어로 세우는 피동문입니다.'),
    (('比',), 'A 比 B + 형용사', 'A가 B보다 더 ~하다', '두 대상을 비교합니다.'),
    (('正在',), '正在 + 동사', '~하고 있는 중이다', '현재 진행 중인 동작을 나타냅니다.'),
    (('过',), '동사 + 过', '~해 본 적이 있다', '과거의 경험을 나타냅니다.'),
    (('得',), '동사 + 得 + 정도', '~하게 동작하다', '동작의 정도나 상태를 설명합니다.'),
    (('了',), '동사/형용사 + 了', '~했다, ~해졌다', '완료나 상태 변화를 나타냅니다.'),
]


class Translator:
    def __init__(self, cache_path):
        self.cache_path = Path(cache_path).expanduser()
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache = json.loads(self.cache_path.read_text(encoding='utf-8')) if self.cache_path.exists() else {}

    def request(self, texts):
        joined = '\n'.join(texts)
        data = urllib.parse.urlencode({
            'client': 'gtx', 'sl': 'zh-CN', 'tl': 'ko', 'dt': 't', 'q': joined,
        }).encode()
        request = urllib.request.Request(
            'https://translate.googleapis.com/translate_a/single',
            data=data,
            headers={'User-Agent': 'Mozilla/5.0'},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.load(response)
        translated = ''.join(chunk[0] for chunk in result[0]).split('\n')
        if len(translated) != len(texts):
            if len(texts) == 1:
                return [''.join(chunk[0] for chunk in result[0])]
            translated = []
            for text in texts:
                translated.extend(self.request([text]))
                time.sleep(0.08)
        return translated

    def translate(self, texts):
        unique = list(dict.fromkeys(text for text in texts if text and text.strip()))
        pending = [text for text in unique if text not in self.cache]
        batch = []
        size = 0
        for text in pending + [None]:
            if text is None or (batch and size + len(text) > 2800):
                for source, translated in zip(batch, self.request(batch)):
                    self.cache[source] = translated.strip()
                self.cache_path.write_text(json.dumps(self.cache, ensure_ascii=False, indent=1), encoding='utf-8')
                batch, size = [], 0
                time.sleep(0.12)
            if text is not None:
                batch.append(text)
                size += len(text)
        return {text: self.cache.get(text, '') for text in unique}


def tokenize(text):
    words = []
    for token in jieba.lcut(text, HMM=False):
        if not token:
            continue
        if token.isspace():
            words.append([token, ''])
            continue
        if all(char in PUNCT for char in token):
            words.extend([[char, ''] for char in token if not char.isspace()])
            continue
        pinyin = (
            ''.join(lazy_pinyin(token, style=Style.TONE, neutral_tone_with_five=False))
            if re.search(r'[一-鿿]', token) else ''
        )
        words.append([token, pinyin])
    return words


def tokenize_blank(text, answer):
    before, after = text.split('（）', 1)
    words = tokenize(before) + [[answer, ''.join(lazy_pinyin(answer, style=Style.TONE))]] + tokenize(after)
    return words, len(tokenize(before))


def split_sentences(text):
    sentences = [part for part in re.findall(r'.+?(?:[。！？?!]|$)', text) if part]
    return sentences or [text]


def content_words(texts, limit=5):
    counts = Counter()
    flags = {}
    for text in texts:
        for entry in posseg.cut(text, HMM=False):
            word = entry.word.strip()
            if not word or any(char in PUNCT for char in word) or word in STOPWORDS:
                continue
            if not re.search(r'[一-鿿]', word):
                continue
            if len(word) == 1 and entry.flag[:1] not in ('n', 'v', 'a'):
                continue
            counts[word] += 1
            flags[word] = entry.flag
    chosen = [word for word, _ in counts.most_common(limit)]
    if len(chosen) < 3:
        for text in texts:
            for token, _ in tokenize(text):
                if re.fullmatch(r'[一-鿿]{1,}', token) and token not in STOPWORDS and token not in chosen:
                    chosen.append(token)
                    flags[token] = 'n'
                if len(chosen) >= 3:
                    break
            if len(chosen) >= 3:
                break
    return [(word, POS_KO.get(flags.get(word, '')[:1], '단어')) for word in chosen[:limit]]


def example_for(word, texts, translations):
    text = next((text for text in texts if word in text), texts[0])
    return {'zh': text, 'words': tokenize(text), 'ko': translations.get(text, '')}


def vocab_for(texts, translations, detailed):
    entries = []
    for word, part in content_words(texts):
        entry = {
            'hanzi': word,
            'pinyin': ''.join(lazy_pinyin(word, style=Style.TONE)),
            'partOfSpeech': part,
            'meaningKo': translations.get(word, word),
        }
        if detailed:
            entry['usage'] = f'{word}가 쓰인 문장을 함께 확인'
            entry['example'] = example_for(word, texts, translations)
        entries.append(entry)
    return entries


def grammar_for(text, translations, detailed):
    matched = []
    for needles, pattern, meaning, note in GRAMMAR_RULES:
        if all(needle in text for needle in needles):
            matched.append((pattern, meaning, note))
        if len(matched) == 2:
            break
    if not matched:
        matched = [('기본 어순', '문맥에 맞게 문장 구성', '주어·술어·목적어와 수식어의 위치를 문맥 속에서 확인합니다.')]
    entries = []
    for pattern, meaning, note in matched:
        entry = {'pattern': pattern, 'note': note}
        if detailed:
            entry['meaningKo'] = meaning
            entry['example'] = {'zh': text, 'words': tokenize(text), 'ko': translations.get(text, '')}
        entries.append(entry)
    return entries


def breakdown_for(quote):
    if '，' in quote:
        head, tail = quote.split('，', 1)
        chunks = [{'text': head + '，', 'role': '부사어'}, {'text': tail, 'role': '술어'}]
    else:
        chunks = [{'text': quote, 'role': '술어'}]
    return [{'chunks': chunks, 'note': '정답 판단에 필요한 핵심 문장 구조를 확인합니다.'}]


def collect_listening_strings(paper):
    texts = []
    for item in paper['items']:
        texts.extend(line['text'] for line in item['lines'])
        if item.get('paperStatement'):
            texts.append(item['paperStatement'])
        texts.extend(option['text'] for option in item.get('options') or [])
    words = [word for item in paper['items'] for word, _ in content_words(
        [line['text'] for line in item['lines']] + [option['text'] for option in item.get('options') or []]
    )]
    return texts + words


def write_listening(test_id, work, translator):
    base = Path(work).expanduser() / test_id
    paper = json.loads((base / 'paper.json').read_text(encoding='utf-8'))
    translations = translator.translate(collect_listening_strings(paper))
    items = []
    for item in paper['items']:
        source_texts = [line['text'] for line in item['lines']]
        source_texts += [option['text'] for option in item.get('options') or []]
        if item.get('paperStatement'):
            source_texts.append(item['paperStatement'])
        note = {
            'no': item['no'],
            'lines': [{'words': tokenize(line['text']), 'ko': translations.get(line['text'], '')}
                      for line in item['lines']],
            'statement': None,
            'options': [],
            'vocab': vocab_for(source_texts, translations, detailed=False),
            'grammar': grammar_for(''.join(source_texts), translations, detailed=False),
        }
        if item['part'] == 2:
            text = item['paperStatement']
            note['statement'] = {'words': tokenize(text), 'ko': translations.get(text, '')}
        if item['part'] in (3, 4):
            note['options'] = [{'label': option['label'], 'words': tokenize(option['text']),
                                'ko': translations.get(option['text'], '')}
                               for option in item['options']]
        items.append(note)
    (base / 'enrich.json').write_text(
        json.dumps({'id': test_id, 'items': items}, ensure_ascii=False, indent=1), encoding='utf-8'
    )
    print(f'{test_id}: 듣기 해설 {len(items)}개')


def collect_reading_strings(paper):
    texts = []
    for group in paper['groups']:
        texts.extend(option['text'] for option in group['options'])
    for item in paper['items']:
        texts.extend(line['text'] for line in item['lines'])
        if item.get('question'):
            texts.append(item['question'])
        texts.extend(option['text'] for option in item.get('options') or [])
        for word, _ in content_words(texts[-6:]):
            texts.append(word)
    return texts


def answer_word(item, groups):
    group = groups[item['group']]
    return next(option['text'] for option in group['options'] if option['label'] == item['answer'])


def related_quote(passages, answer):
    best = max(passages, key=lambda text: len(set(text) & set(answer)))
    return best


def reading_item(item, groups, group_notes, translations):
    annotated_lines = []
    display_texts = []
    if item['part'] == 3:
        for sentence in split_sentences(item['lines'][0]['text']):
            annotated_lines.append({'words': tokenize(sentence), 'ko': translations.get(sentence, translations.get(item['lines'][0]['text'], ''))})
            display_texts.append(sentence)
    else:
        for line in item['lines']:
            if item['part'] == 2 and '（）' in line['text']:
                answer = answer_word(item, groups)
                words, blank = tokenize_blank(line['text'], answer)
                filled = line['text'].replace('（）', answer)
                annotated_lines.append({'words': words, 'ko': translations.get(filled, translations.get(line['text'], '')), 'blank': blank})
                display_texts.append(filled)
            else:
                annotated_lines.append({'words': tokenize(line['text']), 'ko': translations.get(line['text'], '')})
                display_texts.append(line['text'])

    question = None
    options = None
    if item['part'] == 3:
        question = {'words': tokenize(item['question']), 'ko': translations.get(item['question'], '')}
        options = [{'label': option['label'], 'words': tokenize(option['text']), 'ko': translations.get(option['text'], '')}
                   for option in item['options']]
        visible_options = item['options']
        quote = related_quote(display_texts, next(o['text'] for o in item['options'] if o['label'] == item['answer']))
        note = f'지문의 내용과 가장 잘 맞는 {item["answer"]}를 고릅니다.'
    elif item['part'] == 2:
        visible_options = groups[item['group']]['options']
        quote = display_texts[0]
        note = f'빈칸에 {answer_word(item, groups)}를 넣으면 문맥과 문장 구조가 자연스럽습니다.'
    else:
        visible_options = groups[item['group']]['options']
        quote = display_texts[0]
        note = f'{item["answer"]} 보기와 이어 읽으면 자연스러운 대화가 됩니다.'

    labels = [option['label'] for option in visible_options
              if option['label'] not in (item['answer'], groups.get(item.get('group'), {}).get('example'))]
    distractor_count = 2 if item['part'] == 3 else min(2, len(labels))
    source_texts = display_texts + [option['text'] for option in visible_options]
    if item.get('question'):
        source_texts.append(item['question'])
    explain = {
        'basis': {'quote': quote, 'note': note},
        'distractors': [{'label': label, 'note': '정답 문장과 비교하면 문맥 연결이 맞지 않습니다.'}
                        for label in labels[:distractor_count]],
        'breakdown': breakdown_for(quote),
        'vocab': vocab_for(source_texts, translations, detailed=True),
        'grammar': grammar_for(quote, translations, detailed=True),
    }

    pair = None
    if item['part'] == 1:
        own = item['lines'][0]['text']
        partner = next(option['text'] for option in visible_options if option['label'] == item['answer'])
        pair = 'option-first' if re.search(r'[？?]$', partner) and not re.search(r'[？?]$', own) else 'item-first'
    return {
        'no': item['no'], 'lines': annotated_lines, 'question': question, 'options': options,
        'pair': pair, 'explain': explain,
    }


def write_reading(test_id, work, translator):
    base = Path(work).expanduser() / test_id
    paper = json.loads((base / 'paper.json').read_text(encoding='utf-8'))
    strings = collect_reading_strings(paper)
    # 2부분은 번역할 때 정답을 채운 문장도 함께 보낸다.
    groups = {group['id']: group for group in paper['groups']}
    for item in paper['items']:
        if item['part'] == 2:
            strings.extend(line['text'].replace('（）', answer_word(item, groups)) for line in item['lines'])
        if item['part'] == 3:
            strings.extend(split_sentences(item['lines'][0]['text']))
    translations = translator.translate(strings)
    group_notes = {}
    for group in paper['groups']:
        group_notes[group['id']] = {
            'id': group['id'],
            'options': [{'label': option['label'], 'words': tokenize(option['text']),
                         'ko': translations.get(option['text'], '')} for option in group['options']],
        }
    items = [reading_item(item, groups, group_notes, translations) for item in paper['items']]
    ranges = [(41, 50), (51, 60), (61, 70)]
    for first, last in ranges:
        group_ids = {item['group'] for item in paper['items'] if first <= item['no'] <= last and item['group']}
        data = {
            'groups': [group_notes[group_id] for group_id in sorted(group_ids)],
            'items': [item for item in items if first <= item['no'] <= last],
        }
        (base / f'enrich-{first}-{last}.json').write_text(
            json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8'
        )
    print(f'{test_id}: 독해 해설 {len(items)}개')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('test_ids', nargs='+')
    parser.add_argument('--listening-work', required=True)
    parser.add_argument('--reading-work', required=True)
    parser.add_argument('--cache', default='~/hsk-enrich-work/translations-zh-ko.json')
    parser.add_argument('--mode', choices=('listening', 'reading', 'both'), default='both')
    args = parser.parse_args()
    translator = Translator(args.cache)
    for test_id in args.test_ids:
        if args.mode in ('listening', 'both'):
            write_listening(test_id, args.listening_work, translator)
        if args.mode in ('reading', 'both'):
            write_reading(test_id, args.reading_work, translator)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
