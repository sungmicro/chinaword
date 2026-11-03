#!/usr/bin/env python3
"""문장 words의 붙은 토큰 나누기 (예문·대본·보기 병음 «bǐjiàománg» → «bǐjiào máng»).

해설 핵심 단어는 tools/vocab_fixes.json split으로 이미 나눴지만(比较忙 → 比较·忙), 같은 토큰이 문장 words의
[한자, 병음] 쌍에는 붙은 채 남아 있었다. 그래서 대본·지문의 병음과 단어장 예문 병음(examplePinyin)이
«bǐjiàománg»처럼 보였다. 여기서는 나누기 표의 토큰을 문장에서도 조각으로 나눈다.

  나누기 표: tools/vocab_fixes.json split(비어 있지 않은 것) + tools/mine_moves.json split
  조각: 표의 조각 한자를 토큰 안에서 차례로 찾고, 그 사이에 남는 글자는 한 글자씩 따로 둔다
        (很多 → 很 + 多, 这段话 → 这 + 段 + 话, 一个班 → 一 + 个 + 班). 조각이 토큰 안에 차례로 없으면(三四年 → 年级,
        见过面 → 见面) 한 글자씩 나눈다.
  병음: 원래 병음을 글자마다 음절로 맞춰(pypinyin 다음자 후보, 성조 무시) 조각 경계에서 자른다. 성조·대문자는 원래 것을 쓴다.
        맞출 수 없으면 그 토큰은 그대로 둔다.

적용 경로
  - tools/vocab_fixes.py --apply-listening, tools/listening/assemble.py, tools/reading/assemble.py: 회차를 쓰기 전에 나눈다.
  - tools/vocab_fixes.py --repo . --apply-sentences: 공개 독해·듣기 회차를 그 자리에서 나누고, src/data/vocab.json의 예문 병음
    (examplePinyin)과 문장 카드 병음에서 붙은 병음을 나눈 병음으로 바꾼다. 몇 번 돌려도 같다.
  - 바꾼 병음(붙은 → 나눈)은 tools/sentence_splits.json에 쌓는다(지우지 않는다). 내 단어장에 예전에 담은 예문 병음도
    이 표로 바꾼다(tools/mine_refresh.py → src/data/mine-refresh.json pinyin).
"""
import json
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPLITS_PATH = HERE / 'sentence_splits.json'
TONE_MARKS = {'̀', '́', '̄', '̌'}
SEPARATORS = {' ', "'", '’', '-'}


def sentence_table(fixes=None, moves=None):
    """{토큰: [조각 한자, ...]} — vocab_fixes split(빈 목록 제외)과 mine_moves split."""
    if fixes is None:
        fixes = json.loads((HERE / 'vocab_fixes.json').read_text(encoding='utf-8'))
    if moves is None:
        moves = json.loads((HERE / 'mine_moves.json').read_text(encoding='utf-8'))
    table = {}
    for source in (fixes.get('split', {}), moves.get('split', {})):
        for token, parts in source.items():
            pieces = [part.split('#', 1)[0] for part in parts]
            if pieces:
                table[token] = pieces
    return table


def toneless(char):
    decomposed = unicodedata.normalize('NFD', char.lower())
    return unicodedata.normalize('NFC', ''.join(c for c in decomposed if c not in TONE_MARKS))


_READINGS = {}


def readings(char):
    """그 글자의 성조 없는 병음 후보(다음자 포함)."""
    if char not in _READINGS:
        from pypinyin import Style, pinyin  # 필요할 때만(앱 테스트 환경에는 없어도 된다)
        found = pinyin(char, style=Style.NORMAL, heteronym=True, v_to_u=True)[0]
        candidates = {toneless(reading) for reading in found}
        candidates |= {reading.replace('ü', 'v') for reading in candidates}  # 'lv'처럼 적은 병음도 맞춘다
        _READINGS[char] = sorted(candidates, key=lambda reading: (-len(reading), reading))
    return _READINGS[char]


def syllables(hanzi, pinyin):
    """병음을 글자마다 한 음절로 나눈다. 맞출 수 없으면 None."""
    letters = [c for c in unicodedata.normalize('NFC', pinyin) if c not in SEPARATORS]
    flat = [toneless(c) for c in letters]
    text = ''.join(flat)
    if len(text) != len(flat):
        return None

    def walk(index, pos):
        if index == len(hanzi):
            return [] if pos == len(text) else None
        for reading in readings(hanzi[index]):
            if text.startswith(reading, pos):
                rest = walk(index + 1, pos + len(reading))
                if rest is not None:
                    return [''.join(letters[pos:pos + len(reading)])] + rest
        return None

    return walk(0, 0)


def token_pieces(token, pieces):
    """조각 한자를 토큰 안에서 차례로 찾아, 사이에 남는 글자까지 포함한 토큰 목록. 맞지 않으면 None."""
    out, cursor = [], 0
    for piece in pieces:
        found = token.find(piece, cursor)
        if found < 0:
            return None
        out.extend(token[cursor:found])  # 사이에 남는 글자는 한 글자씩(喜不喜欢 → 喜 + 不 + 喜欢, 带我去 → 带 + 我 + 去)
        out.append(piece)
        cursor = found + len(piece)
    out.extend(token[cursor:])
    return out if len(out) > 1 else None


def split_token(token, pinyin, table):
    """[[조각, 병음], ...] 또는 None(나누지 않음). 조각이 토큰 안에 차례로 없으면(三四年 → 年级, 见过面 → 见面) 한 글자씩 나눈다."""
    if token not in table:
        return None
    pieces = token_pieces(token, table[token]) or (list(token) if len(token) > 1 else None)
    if not pieces or not pinyin:
        return None
    per_char = syllables(token, pinyin)
    if per_char is None:
        return None
    out, start = [], 0
    for piece in pieces:
        out.append([piece, ''.join(per_char[start:start + len(piece)])])
        start += len(piece)
    return out


def split_words(words, table, log=None, skipped=None):
    """문장 words 하나를 나눈 새 목록. log: {토큰: {붙은 병음: 나눈 병음}}에 바꾼 것을 모은다."""
    out = []
    for pair in words:
        token, pinyin = pair[0], pair[1]
        pieces = split_token(token, pinyin, table) if token in table else None
        if pieces is None:
            if token in table and skipped is not None and pinyin:
                skipped.add((token, pinyin))
            out.append(pair)
            continue
        out.extend(pieces)
        spaced = ' '.join(py for _, py in pieces)
        if log is not None and spaced != pinyin:  # 이미 띄어 쓴 병음(Lǎo Lǐ)은 토큰만 나누고 기록하지 않는다
            log.setdefault(token, {})[pinyin] = spaced
    return out


def split_test_sentences(test, table=None, log=None, skipped=None):
    """회차 dict 안의 모든 문장 words(핵심 단어 vocab 제외)를 그 자리에서 나눈다. 나눈 토큰 수를 돌려준다."""
    table = sentence_table() if table is None else table
    count = 0

    def walk(node):
        nonlocal count
        if isinstance(node, dict):
            for key, value in node.items():
                if key == 'vocab':
                    continue
                if key == 'words' and isinstance(value, list) and all(isinstance(p, list) and len(p) == 2 for p in value):
                    new = split_words(value, table, log, skipped)
                    if len(new) != len(value):
                        count += len(new) - len(value)
                        node[key] = new
                else:
                    walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(test)
    return count


def _is_letter(char):
    return bool(char) and unicodedata.category(char).startswith('L')


def _variants(table):
    """[(붙은 병음, 나눈 병음)] — 원래 표기와, 문장 첫머리에 올 때의 첫 글자 대문자 표기. 원래 표기가 이긴다."""
    pairs = {}
    for glued, spaced in sorted(table.items()):
        pairs.setdefault(glued, spaced)
    for glued, spaced in sorted(table.items()):
        pairs.setdefault(glued[:1].upper() + glued[1:], spaced[:1].upper() + spaced[1:])
    return sorted(pairs.items(), key=lambda pair: (-len(pair[0]), pair[0]))


def fix_pinyin_text(text, zh, fixes):
    """문장 병음 text에서, 한자 문장 zh에 있는 토큰의 붙은 병음을 나눈 병음으로 바꾼다(앞뒤가 글자가 아닐 때만).
    대소문자는 그대로 맞추고, 문장 첫머리처럼 첫 글자만 대문자인 것도 바꾼다.
    fixes: {토큰: {붙은: 나눈}}. src/mineRefresh.js fixPinyinText와 같은 규칙."""
    if not text or not zh:
        return text
    for token, table in sorted(fixes.items()):
        if token not in zh:
            continue
        for glued, spaced in _variants(table):
            out, pos = [], 0
            while True:
                found = text.find(glued, pos)
                if found < 0:
                    break
                end = found + len(glued)
                if _is_letter(text[found - 1] if found else '') or _is_letter(text[end] if end < len(text) else ''):
                    out.append(text[pos:end])
                else:
                    out.append(text[pos:found] + spaced)
                pos = end
            out.append(text[pos:])
            text = ''.join(out)
    return text


def load_splits(path=None):
    path = SPLITS_PATH if path is None else path
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))['pinyin']
    return {}


def splits_text(pinyin):
    data = {
        '_about': '문장 words에서 나눈 붙은 토큰의 병음(붙은 → 나눈). tools/sentence_split.py가 나눌 때마다 더하고 지우지 않는다. '
                  'vocab.json 예문 병음과 내 단어장에 담아 둔 예문 병음을 이 표로 바꾼다.',
        'pinyin': {token: dict(sorted(table.items())) for token, table in sorted(pinyin.items())},
    }
    return json.dumps(data, ensure_ascii=False, indent=1) + '\n'


def merge_splits(log, path=None):
    """이번에 나눈 병음을 기록 표에 더한 내용(텍스트)을 돌려준다."""
    merged = load_splits(path)
    for token, table in log.items():
        merged.setdefault(token, {}).update(table)
    return splits_text(merged)


def fix_vocab_pinyin(vocab, fixes):
    """vocab.json 카드의 예문 병음과 문장·패턴 카드의 병음을 고친다. 바꾼 카드 수."""
    changed = 0
    for card in vocab:
        before = (card.get('examplePinyin'), card.get('pinyin'))
        card['examplePinyin'] = fix_pinyin_text(card.get('examplePinyin', ''), card.get('exampleZh', ''), fixes)
        if card.get('itemType') != '단어':
            card['pinyin'] = fix_pinyin_text(card.get('pinyin', ''), card.get('hanzi', ''), fixes)
        if (card.get('examplePinyin'), card.get('pinyin')) != before:
            changed += 1
    return changed
