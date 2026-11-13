#!/usr/bin/env python3
"""HSK 시험 원문에 병음·한국어 풀이를 붙여 기존 앱 데이터 형식으로 만든다.

공개 시험지의 원문만 번역하며, Google 번역 결과는 작업 폴더 밖 캐시에 보관해 다시
실행할 때 같은 문장을 재요청하지 않는다. 생성 결과는 기존 assemble.py 검사를 통과해야
실제 public 데이터로 들어간다.
"""
import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

import jieba
import jieba.posseg as posseg
from pypinyin import Style, lazy_pinyin

from vocab_fixes import (BANNED_PART, OUTLINE_LESSONS, VocabProblems, fix_vocab, fix_vocab_checked, has_hangul,  # noqa: F401
                         write_files_atomically)

sys.path.insert(0, str(Path(__file__).resolve().parent / 'listening'))
from script_fixes import apply_script_fixes  # noqa: E402  tools/listening/script_fixes.py


PUNCT = set('，。！？：；、“”‘’（）《》…—,.?!:;()[] ')
VOCAB_LIMIT = 8
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


class VocabCatalog:
    """프로젝트 단어장에서 급수별 신규 어휘와 검수된 뜻을 읽는다."""

    def __init__(self, path):
        entries = json.loads(Path(path).expanduser().read_text(encoding='utf-8'))
        self.entries = {}
        self.entry_scores = {}
        self.new_by_level = {}
        self.official_words = set()
        for entry in entries:
            word = entry.get('hanzi')
            level = entry.get('level')
            lesson = entry.get('lesson', '')
            if not word:
                continue
            score = self._score(entry)
            if score > self.entry_scores.get(word, -1):
                self.entries[word] = entry
                self.entry_scores[word] = score
            if level and (lesson.startswith(f'{level} 추가') or lesson in OUTLINE_LESSONS):
                self.new_by_level.setdefault(level, set()).add(word)
                self.official_words.add(word)
            if lesson == 'HSK1 150':
                self.official_words.add(word)

    @staticmethod
    def _score(entry):
        lesson = entry.get('lesson', '')
        level = entry.get('level', '')
        if level and (lesson.startswith(f'{level} 추가') or lesson == f'{level} 150' or lesson in OUTLINE_LESSONS):
            return 3
        if level.startswith('HSK') and not lesson.endswith(('듣기', '독해')):
            return 2
        return 1

    @staticmethod
    def level_for(test_id):
        match = re.match(r'^H([1-9])', test_id)
        return f'HSK{match.group(1)}' if match else None

    def priority_words(self, test_id):
        return self.new_by_level.get(self.level_for(test_id), set())

    def get(self, word):
        return self.entries.get(word, {})


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


def priority_words_in_text(text, priority_words, lexicon):
    """공식 어휘를 최장 일치로 나눠 복합 표현 안의 짧은 오인식을 막는다."""
    found = []
    index = 0
    while index < len(text):
        matches = [word for word in lexicon if text.startswith(word, index)]
        if not matches:
            index += 1
            continue
        word = max(matches, key=lambda candidate: (len(candidate), candidate))
        if word in priority_words and word not in found:
            found.append(word)
        index += len(word)
    return found


def content_words(texts, priority_words=None, limit=VOCAB_LIMIT, lexicon=None):
    """급수 신규 어휘를 먼저 담고, 남은 칸을 문항의 다른 핵심어로 채운다.

    신규 어휘가 제한보다 많으면 본문에 먼저 나온 어휘를 우선한다. 빈도가 같을 때도
    본문 등장 순서를 유지하므로 결과가 매번 같다.
    """
    priority_words = set(priority_words or ())
    lexicon = set(lexicon or priority_words)
    counts = Counter()
    flags = {}
    priority = []
    for text in texts:
        parsed = list(posseg.cut(text, HMM=False))
        for word in priority_words_in_text(text, priority_words, lexicon):
            if word not in priority:
                priority.append(word)

        for entry in parsed:
            word = entry.word.strip()
            if not word or any(char in PUNCT for char in word):
                continue
            if not re.search(r'[一-鿿]', word):
                continue
            flags[word] = entry.flag
            if word in STOPWORDS:
                continue
            if len(word) == 1 and entry.flag[:1] not in ('n', 'v', 'a'):
                continue
            counts[word] += 1
    chosen = priority[:limit]
    for word, _ in counts.most_common():
        if word not in chosen:
            chosen.append(word)
        if len(chosen) >= limit:
            break
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
    return [(word, POS_KO.get(flags.get(word, '')[:1], '')) for word in chosen[:limit]]


def vocab_for(texts, translations, catalog, test_id, where=None):
    """듣기·독해 공통 핵심 단어: 한자·병음·품사·뜻.

    뜻은 단어장의 한글 뜻, 없으면 번역의 한글 뜻을 쓴다. 둘 다 한글이 없으면 한자를 뜻 자리에 넣지 않고
    비워 둔다(예전에는 «뜻 = 한자»가 그대로 공개됐다). 품사를 못 정하면 «단어» 대신 비워 둔다.
    마지막에 보정 사전(tools/vocab_fixes.json)을 거친다. 그래도 빈 칸이 남으면 assemble.py 검사가 막으니,
    그 단어를 vocab_fixes.json에 더한다.
    """
    entries = []
    priority_words = catalog.priority_words(test_id)
    for word, detected_part in content_words(
            texts, priority_words=priority_words, lexicon=catalog.official_words):
        known = catalog.get(word)
        known_part = known.get('partOfSpeech') if known.get('partOfSpeech') != BANNED_PART else ''
        meaning = next((text for text in (known.get('meaningKo'), translations.get(word)) if has_hangul(text)), '')
        entry = {
            'hanzi': word,
            'pinyin': known.get('pinyin') or ''.join(lazy_pinyin(word, style=Style.TONE)),
            'partOfSpeech': known_part or detected_part,
            'meaningKo': meaning,
        }
        entries.append(entry)
    return fix_vocab(entries, where)


def grammar_for(text):
    """듣기·독해 공통 문장 구조: 패턴·설명."""
    matched = []
    for needles, pattern, meaning, note in GRAMMAR_RULES:
        if all(needle in text for needle in needles):
            matched.append((pattern, meaning, note))
        if len(matched) == 2:
            break
    if not matched:
        matched = [('기본 어순', '문맥에 맞게 문장 구성', '주어·술어·목적어와 수식어의 위치를 문맥 속에서 확인합니다.')]
    return [{'pattern': pattern, 'note': note} for pattern, _meaning, note in matched]


def listening_source_texts(item):
    texts = [line['text'] for line in item['lines']]
    texts.extend(option['text'] for option in item.get('options') or [])
    if item.get('paperStatement'):
        texts.append(item['paperStatement'])
    return texts


def annotated_text(entry):
    return ''.join(token for token, _ in entry.get('words', []))


def listening_note_texts(note):
    """복구 대본까지 반영된 enrich.json을 핵심 단어 선정 원문으로 쓴다."""
    texts = [annotated_text(line) for line in note.get('lines') or []]
    statement = note.get('statement')
    if statement:
        texts.append(annotated_text(statement))
    texts.extend(annotated_text(option) for option in note.get('options') or [])
    return [text for text in texts if text]


def collect_listening_strings(paper, catalog, test_id):
    texts = []
    for item in paper['items']:
        texts.extend(listening_source_texts(item))
    words = [word for item in paper['items'] for word, _ in content_words(
        listening_source_texts(item), priority_words=catalog.priority_words(test_id),
        lexicon=catalog.official_words,
    )]
    return texts + words


def write_listening(test_id, work, translator, catalog, vocab_only=False):
    base = Path(work).expanduser() / test_id
    paper = json.loads((base / 'paper.json').read_text(encoding='utf-8'))
    enrich_path = base / 'enrich.json'
    if vocab_only:
        data = json.loads(enrich_path.read_text(encoding='utf-8'))
        strings = []
        for note in data['items']:
            source_texts = listening_note_texts(note)
            strings.extend(source_texts)
            strings.extend(word for word, _ in content_words(
                source_texts,
                priority_words=catalog.priority_words(test_id),
                lexicon=catalog.official_words,
            ))
        translations = translator.translate(strings)
        for note in data['items']:
            note['vocab'] = vocab_for(
                listening_note_texts(note), translations,
                catalog=catalog, test_id=test_id, where=f'listening/{test_id}/{note["no"]}',
            )
        enrich_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
        print(f'{test_id}: 듣기 핵심 단어 {len(data["items"])}개 문항 갱신')
        return

    translations = translator.translate(collect_listening_strings(paper, catalog, test_id))
    items = []
    for item in paper['items']:
        source_texts = listening_source_texts(item)
        note = {
            'no': item['no'],
            'lines': [{'words': tokenize(line['text']), 'ko': translations.get(line['text'], '')}
                      for line in item['lines']],
            'statement': None,
            'options': [],
            'vocab': vocab_for(source_texts, translations, catalog=catalog, test_id=test_id,
                               where=f'listening/{test_id}/{item["no"]}'),
            'grammar': grammar_for(''.join(source_texts)),
        }
        if item['part'] == 2:
            text = item['paperStatement']
            note['statement'] = {'words': tokenize(text), 'ko': translations.get(text, '')}
        if item['part'] in (3, 4):
            note['options'] = [{'label': option['label'], 'words': tokenize(option['text']),
                                'ko': translations.get(option['text'], '')}
                               for option in item['options']]
        items.append(note)
    enrich_path.write_text(
        json.dumps({'id': test_id, 'items': items}, ensure_ascii=False, indent=1), encoding='utf-8'
    )
    print(f'{test_id}: 듣기 해설 {len(items)}개')


def prepare_public_listening_vocab(test_id, work, repo, problems):
    """작업 폴더 enrich.json의 핵심 단어를 보정해 공개 듣기 데이터에 넣을 내용을 만든다(쓰지 않는다)."""
    enrich = json.loads((Path(work).expanduser() / test_id / 'enrich.json').read_text(encoding='utf-8'))
    notes = {item['no']: item for item in enrich['items']}
    path = Path(repo).expanduser() / 'public/listening' / f'{test_id}.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    for item in data['items']:
        item['vocab'] = notes[item['no']]['vocab']
    apply_script_fixes(data, problems, test_id=test_id)  # 대본을 보정한 문항은 보정 파일의 단어를 쓴다(tools/listening/script_fixes.json)
    for item in data['items']:
        item['vocab'] = fix_vocab_checked(item['vocab'], f'listening/{test_id}/{item["no"]}', problems)
    return path, data


def sync_public_listening_vocab(test_id, work, repo):
    write_public_vocab([('listening', test_id, work, repo)])


def reading_vocab_texts(item, groups):
    texts = []
    for line in item['lines']:
        text = line['text']
        if item['part'] == 2 and '（）' in text:
            text = text.replace('（）', answer_word(item, groups))
        texts.append(text)
    if item.get('question'):
        texts.append(item['question'])
    if item['part'] == 3:
        texts.extend(option['text'] for option in item.get('options') or [])
    else:
        texts.append(answer_word(item, groups))
    return texts


def collect_reading_strings(paper, catalog, test_id):
    texts = []
    for group in paper['groups']:
        texts.extend(option['text'] for option in group['options'])
    groups = {group['id']: group for group in paper['groups']}
    for item in paper['items']:
        texts.extend(line['text'] for line in item['lines'])
        if item.get('question'):
            texts.append(item['question'])
        texts.extend(option['text'] for option in item.get('options') or [])
        for word, _ in content_words(
                reading_vocab_texts(item, groups),
                priority_words=catalog.priority_words(test_id),
                lexicon=catalog.official_words):
            texts.append(word)
    return texts


def answer_word(item, groups):
    group = groups[item['group']]
    return next(option['text'] for option in group['options'] if option['label'] == item['answer'])


def related_quote(passages, answer):
    best = max(passages, key=lambda text: len(set(text) & set(answer)))
    return best


def reading_item(item, groups, group_notes, translations, catalog, test_id):
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
    source_texts = list(display_texts)
    if item['part'] == 3:
        source_texts.extend(option['text'] for option in visible_options)
    else:
        source_texts.append(answer_word(item, groups))
    if item.get('question'):
        source_texts.append(item['question'])
    explain = {
        'basis': {'quote': quote, 'note': note},
        'distractors': [{'label': label, 'note': '정답 문장과 비교하면 문맥 연결이 맞지 않습니다.'}
                        for label in labels[:distractor_count]],
        'vocab': vocab_for(source_texts, translations, catalog=catalog, test_id=test_id,
                           where=f'reading/{test_id}/{item["no"]}'),
        'grammar': grammar_for(quote),
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


def update_reading_vocab(base, paper, translations, catalog, test_id):
    groups = {group['id']: group for group in paper['groups']}
    count = 0
    for path in sorted(base.glob('enrich-*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        for note in data.get('items', []):
            item = next(item for item in paper['items'] if item['no'] == note['no'])
            note['explain']['vocab'] = vocab_for(
                reading_vocab_texts(item, groups), translations,
                catalog=catalog, test_id=test_id, where=f'reading/{test_id}/{note["no"]}',
            )
            count += 1
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
    return count


def prepare_public_reading_vocab(test_id, work, repo, problems):
    """작업 폴더 enrich-*.json의 핵심 단어를 보정해 공개 독해 데이터에 넣을 내용을 만든다(쓰지 않는다)."""
    notes = {}
    for enrich_path in sorted((Path(work).expanduser() / test_id).glob('enrich-*.json')):
        data = json.loads(enrich_path.read_text(encoding='utf-8'))
        notes.update({item['no']: item for item in data.get('items', [])})
    path = Path(repo).expanduser() / 'public/reading' / f'{test_id}.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    for item in data['items']:
        item['explain']['vocab'] = fix_vocab_checked(
            notes[item['no']]['explain']['vocab'], f'reading/{test_id}/{item["no"]}', problems)
    return path, data


def sync_public_reading_vocab(test_id, work, repo):
    write_public_vocab([('reading', test_id, work, repo)])


def write_public_vocab(jobs):
    """공개 데이터 동기화: 모든 회차를 먼저 보정·검사하고, 문제가 하나도 없을 때만 한꺼번에 쓴다.

    jobs: [(kind, test_id, work, repo)]. 문제가 있으면 공개 파일을 하나도 쓰지 않고 VocabProblems를 낸다.
    """
    problems, files = [], {}
    for kind, test_id, work, repo in jobs:
        prepare = prepare_public_listening_vocab if kind == 'listening' else prepare_public_reading_vocab
        path, data = prepare(test_id, work, repo, problems)
        files[path] = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    if problems:
        raise VocabProblems(problems)
    write_files_atomically(files)
    return len(files)


def write_reading(test_id, work, translator, catalog, vocab_only=False):
    base = Path(work).expanduser() / test_id
    paper = json.loads((base / 'paper.json').read_text(encoding='utf-8'))
    strings = collect_reading_strings(paper, catalog, test_id)
    # 2부분은 번역할 때 정답을 채운 문장도 함께 보낸다.
    groups = {group['id']: group for group in paper['groups']}
    for item in paper['items']:
        if item['part'] == 2:
            strings.extend(line['text'].replace('（）', answer_word(item, groups)) for line in item['lines'])
        if item['part'] == 3:
            strings.extend(split_sentences(item['lines'][0]['text']))
    translations = translator.translate(strings)
    if vocab_only:
        count = update_reading_vocab(base, paper, translations, catalog, test_id)
        print(f'{test_id}: 독해 핵심 단어 {count}개 문항 갱신')
        return

    group_notes = {}
    for group in paper['groups']:
        group_notes[group['id']] = {
            'id': group['id'],
            'options': [{'label': option['label'], 'words': tokenize(option['text']),
                         'ko': translations.get(option['text'], '')} for option in group['options']],
        }
    items = [reading_item(item, groups, group_notes, translations, catalog, test_id)
             for item in paper['items']]
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
    parser.add_argument('--vocab', default=str(Path(__file__).resolve().parents[1] / 'src/data/vocab.json'))
    parser.add_argument('--vocab-only', action='store_true',
                        help='기존 병음·해석·문법은 유지하고 문항별 핵심 단어만 다시 만든다')
    parser.add_argument('--repo', help='--vocab-only 결과를 public 시험 데이터에도 동기화할 저장소')
    parser.add_argument('--mode', choices=('listening', 'reading', 'both'), default='both')
    args = parser.parse_args()
    translator = Translator(args.cache)
    catalog = VocabCatalog(args.vocab)
    jobs = enrich_all(args, translator, catalog)
    if not jobs:
        return 0
    try:
        count = write_public_vocab(jobs)
    except VocabProblems as error:
        for problem in error.problems:
            print('  ! ' + problem)
        print(f'단어 문제 {len(error.problems)}개가 남아 공개 데이터(public/)는 한 회차도 쓰지 않았습니다. '
              '작업 폴더의 해설 파일은 이미 새로 만들어졌습니다. tools/vocab_fixes.json에 보정을 더하고 다시 돌리세요.')
        return 1
    print(f'공개 데이터 {count}개 파일의 핵심 단어를 동기화했습니다.')
    from mine_refresh import refresh_after_write  # 내 단어장 갱신 색인(src/data/mine-refresh.json)
    results = [refresh_after_write(repo) for repo in sorted({job[3] for job in jobs})]
    return 0 if all(results) else 1  # 내 단어장 갱신 색인을 못 쓰면 1


def enrich_all(args, translator, catalog):
    """작업 폴더의 해설을 만들고, 공개 데이터 동기화가 필요한 회차 목록을 돌려준다(공개 파일은 여기서 쓰지 않는다)."""
    jobs = []
    for test_id in args.test_ids:
        if args.mode in ('listening', 'both'):
            write_listening(test_id, args.listening_work, translator, catalog, args.vocab_only)
            if args.vocab_only and args.repo:
                jobs.append(('listening', test_id, args.listening_work, args.repo))
        if args.mode in ('reading', 'both'):
            write_reading(test_id, args.reading_work, translator, catalog, args.vocab_only)
            if args.vocab_only and args.repo:
                jobs.append(('reading', test_id, args.reading_work, args.repo))
    return jobs


if __name__ == '__main__':
    raise SystemExit(main())
