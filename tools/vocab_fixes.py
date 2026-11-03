#!/usr/bin/env python3
"""듣기·독해 핵심 단어 보정과 검사.

auto_enrich는 사전에서 한글 뜻을 못 찾은 토큰을 예전에 «뜻 = 한자»로, 품사를 못 정한 토큰을 «단어»로 채웠고,
jieba가 두 단어를 붙이거나(比较忙) 잘못 끊은(铅笔画) 토큰도 그대로 담았다. 원본 작업 폴더(~/hsk-*-work)는
고치지 않고, 이 보정 사전(vocab_fixes.json)을 조립 단계에서 적용한다.

  - tools/reading/assemble.py: 해설 단어를 조립할 때 fix_vocab을 거치고, vocab_problems로 검사한다.
  - tools/listening/assemble.py: 같은 방식.
  - tools/auto_enrich.py: 새로 만드는 단어에도 fix_vocab을 거치고, 한글 뜻이 없으면 한자로 채우지 않는다.

듣기 공개 데이터는 H31006 이후 회차를 assemble.py로 다시 만들 수 없어(대본 손질 이력), 아래 명령으로
public/listening/*.json의 대본 보정(tools/listening/script_fixes.json)과 단어, 단어장 «HSK3 듣기» 단원만
보정한다. 몇 번 돌려도 결과가 같다.

  vocab_fixes.py --repo . --apply-listening   # 듣기 공개 데이터·단어장 보정
  vocab_fixes.py --repo .                     # 듣기·독해 공개 데이터에 남은 문제 개수만 보기
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

FIXES_PATH = Path(__file__).with_name('vocab_fixes.json')
HANGUL = re.compile('[가-힣]')
VOCAB_KEYS = ('hanzi', 'pinyin', 'partOfSpeech', 'meaningKo')
VOCAB_LIMIT = 8
BANNED_PART = '단어'
READING_LESSON = 'HSK3 독해'


def has_hangul(text):
    return bool(HANGUL.search(text or ''))


def load_fixes(path=FIXES_PATH):
    return json.loads(Path(path).read_text(encoding='utf-8'))


_FIXES = None


def fixes():
    global _FIXES
    if _FIXES is None:
        _FIXES = load_fixes()
    return _FIXES


def _part(part_id, table):
    """split·items가 가리키는 단어. '多#남짓'처럼 # 뒤는 같은 한자의 다른 뜻 구분이다."""
    fields = table['parts'].get(part_id) or table['words'].get(part_id)
    if fields is None:
        raise KeyError(f'vocab_fixes.json: parts·words에 없는 단어 {part_id}')
    return {'hanzi': part_id.split('#', 1)[0], **{key: fields[key] for key in VOCAB_KEYS[1:]}}


def fix_vocab(vocab, where=None, table=None):
    """핵심 단어 목록에 보정 사전을 적용한다. where: 'reading/H31006/52' 같은 문항 주소.

    같은 한자는 하나만 남긴다(앞의 것). 나눠서 8개를 넘으면 나눠 생긴 단어를 뒤에서부터 뺀다
    (원래 고른 단어는 남긴다).
    """
    table = table or fixes()
    local = table.get('items', {}).get(where or '', {})
    out, seen = [], set()
    for entry in vocab or []:
        hanzi = entry.get('hanzi', '')
        if hanzi in local:
            replaced, derived = [_part(part, table) for part in local[hanzi]], True
        elif hanzi in table['split']:
            replaced, derived = [_part(part, table) for part in table['split'][hanzi]], True
        elif hanzi in table['words']:
            replaced, derived = [{**entry, **{key: table['words'][hanzi][key] for key in VOCAB_KEYS[1:]}}], False
        else:
            replaced, derived = [entry], False
        for word in replaced:
            if word['hanzi'] in seen:
                continue
            seen.add(word['hanzi'])
            out.append((word, derived))
    while len(out) > VOCAB_LIMIT:
        index = max((i for i, (_, derived) in enumerate(out) if derived), default=len(out) - 1)
        out.pop(index)
    return [word for word, _ in out]


def vocab_problems(entry, where):
    """한자·병음이 있어야 하고, 뜻에 한글이 있어야 하며, 품사 «단어»는 쓰지 않는다."""
    problems = []
    here = f'{where} 단어 {entry.get("hanzi")}'
    for key, name in (('hanzi', '한자'), ('pinyin', '병음')):
        if not (entry.get(key) or '').strip():
            problems.append(f'{here}: {name}({key}) 없음')
    if not has_hangul(entry.get('meaningKo')):
        problems.append(f'{here}: 뜻(meaningKo)에 한글이 없음 ({entry.get("meaningKo")!r}) → tools/vocab_fixes.json에 보정을 더한다')
    if entry.get('partOfSpeech') == BANNED_PART:
        problems.append(f'{here}: 품사 «{BANNED_PART}»는 쓰지 않음 → tools/vocab_fixes.json에 보정을 더한다')
    return problems


class VocabProblems(Exception):
    """보정 뒤에도 문제가 남은 단어. 공개 데이터를 쓰기 전에 멈춘다."""

    def __init__(self, problems):
        super().__init__(f'단어 문제 {len(problems)}개')
        self.problems = problems


def fix_vocab_checked(vocab, where, problems):
    """fix_vocab을 적용하고 남은 문제를 problems에 모은다."""
    fixed = fix_vocab(vocab, where)
    for entry in fixed:
        problems.extend(vocab_problems(entry, where))
    return fixed


# --- 단어장 카드 id 장부 ---
# 오답노트(시험보기)는 카드 id로 기록된다. 다시 만들 때 사라진 카드의 id는 은퇴시켜 다시 쓰지 않는다.
# 뜻이 같은 카드가 남아 있을 때만 movedTo에 그 한자를 적고, 앱이 오답노트를 불러올 때 그 카드로 옮긴다.
# movedTo 기준: 같은 단어가 남아 있거나, 나머지 조각이 수사·양사·지시/인칭대명사·정도부사·조사·방향보어처럼
# 문법 요소뿐일 때 그 핵심 단어(很多→多, 一斤→斤, 欢迎您→欢迎). 내용어끼리 붙은 것(足球比赛, 坐地铁),
# 잘못 끊긴 것(个人, 三四年), 남은 카드의 뜻이 다른 것(一米→米 '쌀', 一张→张 '장씨')은 null.
# 사람이 정한 값은 vocab_fixes.json의 movedTo에 둔다(같은 단어가 남은 경우 말고는 이 표에 없으면 null).
ID_REGISTRY = Path('src') / 'data' / 'vocab-retired.json'


def load_id_registry(repo):
    path = Path(repo) / ID_REGISTRY
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    return {'lastNo': {}, 'retired': {}}  # 장부가 없으면 지난번 카드 번호에서 이어 간다


def registry_text(registry):
    registry = {**registry, 'retired': dict(sorted(registry['retired'].items()))}
    return json.dumps(registry, ensure_ascii=False, indent=1) + '\n'


def write_files_atomically(contents):
    """{경로: 내용}을 모두 임시 파일에 쓴 뒤 os.replace로 한꺼번에 바꾼다(중간에 실패하면 원본은 그대로)."""
    staged = []
    try:
        for path, text in contents.items():
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(f'.{path.name}.tmp')
            tmp.write_text(text, encoding='utf-8')
            staged.append((tmp, path))
    except Exception:
        for tmp, _ in staged:
            tmp.unlink(missing_ok=True)
        raise
    for tmp, path in staged:
        os.replace(tmp, path)


def id_number(entry_id):
    return int(str(entry_id).rsplit('-', 1)[1])


def moved_to(hanzi, hanzi_alive, table=None):
    """은퇴한 카드의 기록을 이어받을 한자. 같은 단어가 남아 있으면 그 단어, 아니면 vocab_fixes.json movedTo의 값."""
    if hanzi in hanzi_alive:
        return hanzi
    target = (table or fixes()).get('movedTo', {}).get(hanzi)
    return target if target in hanzi_alive else None


class CardIds:
    """한 단원(접두사 'HSK3L'·'HSK3R')의 카드 id를 정한다. 같은 단어는 같은 id, 새 단어는
    은퇴한 번호까지 포함한 최댓값 다음 번호."""

    def __init__(self, repo, prefix, previous):
        self.repo, self.prefix = repo, prefix
        self.registry = load_id_registry(repo)
        self.previous = previous  # 지난번 이 단원 카드 {hanzi: id}
        used = [id_number(i) for i in previous.values()]
        used += [id_number(i) for i in self.registry['retired'] if i.startswith(prefix + '-')]
        self.last_no = max(used + [self.registry['lastNo'].get(prefix, 0)])

    def id_for(self, hanzi):
        if hanzi in self.previous:
            return self.previous[hanzi]
        self.last_no += 1
        return f'{self.prefix}-{self.last_no:03d}'

    def plan(self, final_vocab):
        """새 vocab.json(전체)에 맞는 장부를 계산하고 검사한다. 파일은 쓰지 않는다."""
        ids = [entry['id'] for entry in final_vocab]
        if len(ids) != len(set(ids)):
            raise ValueError('vocab.json에 같은 id가 둘 이상 있다')
        alive, hanzi_alive = set(ids), {entry['hanzi'] for entry in final_vocab}
        retired = {key: dict(value) for key, value in self.registry['retired'].items()}
        for hanzi, entry_id in self.previous.items():
            if entry_id not in alive:
                retired[entry_id] = {'hanzi': hanzi}
        for value in retired.values():  # 이전 은퇴 항목도 지금 기준으로 다시 정한다(사람이 고친 표를 따른다)
            value['movedTo'] = moved_to(value['hanzi'], hanzi_alive)
        reused = alive & set(retired)
        if reused:
            raise ValueError(f'은퇴한 id를 다시 썼다: {sorted(reused)}')
        last_no = {**self.registry['lastNo'], self.prefix: self.last_no}
        return {**self.registry, 'lastNo': last_no, 'retired': retired}

    def write(self, vocab_path, final_vocab):
        """장부를 먼저 계산·검사한 뒤 vocab.json과 장부를 함께 바꾼다."""
        registry = self.plan(final_vocab)
        write_files_atomically({
            vocab_path: json.dumps(final_vocab, ensure_ascii=False, indent=2) + '\n',
            Path(self.repo) / ID_REGISTRY: registry_text(registry),
        })
        self.registry = registry


def count_problems(repo):
    """공개 데이터에서 뜻에 한글이 없는 항목, 품사가 «단어»인 항목을 센다."""
    result = {}
    for kind in ('reading', 'listening'):
        no_hangul = banned = 0
        items = set()
        for path in sorted((Path(repo) / 'public' / kind).glob('H*.json')):
            data = json.loads(path.read_text(encoding='utf-8'))
            for item in data['items']:
                vocab = item['explain']['vocab'] if kind == 'reading' else item['vocab']
                for word in vocab:
                    bad = bool(vocab_problems(word, ''))
                    if not has_hangul(word.get('meaningKo')):
                        no_hangul += 1
                        bad = True
                    if word.get('partOfSpeech') == BANNED_PART:
                        banned += 1
                        bad = True
                    if bad:
                        items.add((data['id'], item['no']))
        result[kind] = {'meaningKo에 한글 없음': no_hangul, "partOfSpeech=='단어'": banned, '문항': len(items)}
    return result


def apply_listening(repo):
    """public/listening/*.json의 단어를 보정하고, 단어장 «HSK3 듣기» 단원을 assemble.py와 같은 규칙으로 다시 넣는다.

    보정 뒤에도 문제가 남으면 아무 파일도 쓰지 않고 VocabProblems를 낸다. 단어장·장부를 바꾼 뒤에
    공개 듣기 파일을 한꺼번에 바꾼다.
    """
    sys.path.insert(0, str(Path(__file__).parent / 'listening'))
    from assemble import update_vocab  # tools/listening/assemble.py
    from script_fixes import apply_script_fixes  # tools/listening/script_fixes.py
    from sentence_split import merge_splits, split_test_sentences, SPLITS_PATH

    tests, problems, log = [], [], {}
    for path in sorted((Path(repo) / 'public' / 'listening').glob('H*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        apply_script_fixes(data, problems)  # 대본 인식 오류 보정(문항 단어를 바꾸면 아래 보정도 거친다)
        split_test_sentences(data, log=log)  # 문장 words의 붙은 토큰(比较忙)도 나눈다(tools/sentence_split.py)
        for item in data['items']:
            item['vocab'] = fix_vocab_checked(item['vocab'], f'listening/{data["id"]}/{item["no"]}', problems)
        tests.append((path, data))
    if problems:
        raise VocabProblems(problems)
    files = {path: json.dumps(data, ensure_ascii=False, separators=(',', ':')) for path, data in tests}
    tests = [data for _, data in tests]
    index = json.loads((Path(repo) / 'src' / 'data' / 'listening-index.json').read_text(encoding='utf-8'))
    order = {entry['id']: position for position, entry in enumerate(index)}
    tests.sort(key=lambda test: order.get(test['id'], len(order)))
    # assemble.py와 똑같이 다시 넣는다(다른 단원에 있는 단어는 빼고 «HSK3 듣기» 단원을 뒤에 붙인다).
    # 파일 안 순서는 원래대로 듣기 → 독해로 둔다. 독해 단원은 이어서 tools/reading/assemble.py가 다시 만든다.
    added = update_vocab(tests, Path(repo))
    path = Path(repo) / 'src' / 'data' / 'vocab.json'
    vocab = json.loads(path.read_text(encoding='utf-8'))
    vocab = [e for e in vocab if e.get('lesson') != READING_LESSON] + [e for e in vocab if e.get('lesson') == READING_LESSON]
    files[path] = json.dumps(vocab, ensure_ascii=False, indent=2) + '\n'
    if log:
        files[SPLITS_PATH] = merge_splits(log)
    write_files_atomically(files)  # 단어장 장부 검사가 끝난 뒤에야 공개 듣기 파일을 바꾼다
    return len(tests), added


def apply_sentences(repo):
    """공개 독해·듣기 회차의 문장 words에서 붙은 토큰을 나누고(tools/sentence_split.py), src/data/vocab.json의
    예문 병음·문장 카드 병음도 같은 표로 고친다. 몇 번 돌려도 같다. (나눈 토큰 수, 고친 카드 수, 못 나눈 토큰)을 돌려준다."""
    from sentence_split import fix_vocab_pinyin, load_splits, merge_splits, split_test_sentences

    repo = Path(repo)
    files, log, skipped, count = {}, {}, set(), 0
    for kind in ('reading', 'listening'):
        for path in sorted((repo / 'public' / kind).glob('H*.json')):
            text = path.read_text(encoding='utf-8')
            data = json.loads(text)
            if split_test_sentences(data, log=log, skipped=skipped):
                count += 1
                files[path] = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    fixes = load_splits()
    for token, table in log.items():
        fixes.setdefault(token, {}).update(table)
    vocab_path = repo / 'src' / 'data' / 'vocab.json'
    vocab = json.loads(vocab_path.read_text(encoding='utf-8'))
    cards = fix_vocab_pinyin(vocab, fixes)
    if cards:
        files[vocab_path] = json.dumps(vocab, ensure_ascii=False, indent=2) + '\n'
    import sentence_split  # SPLITS_PATH는 부를 때 읽는다(테스트에서 바꿀 수 있게)
    splits_path = sentence_split.SPLITS_PATH
    splits = merge_splits(log)
    if not splits_path.exists() or splits_path.read_text(encoding='utf-8') != splits:
        files[splits_path] = splits
    if files:
        write_files_atomically(files)
    return sum(len(table) for table in log.values()), count, cards, sorted(skipped)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', required=True)
    parser.add_argument('--apply-listening', action='store_true', help='듣기 공개 데이터와 단어장 «HSK3 듣기» 단원을 보정한다')
    parser.add_argument('--apply-sentences', action='store_true',
                        help='독해·듣기 문장 words의 붙은 토큰을 나누고 vocab.json 예문 병음을 고친다(tools/sentence_split.py)')
    args = parser.parse_args(argv)
    # 고른 데이터 작업을 모두 끝낸 뒤 마지막에 내 단어장 갱신 색인을 한 번만 다시 쓴다(못 쓰면 1).
    if args.apply_listening:
        try:
            tests, added = apply_listening(args.repo)
        except VocabProblems as error:
            for problem in error.problems:
                print('  ! ' + problem)
            print(f'문제 {len(error.problems)}개. 파일을 쓰지 않았습니다.')
            return 1
        print(f'듣기 회차 {tests}개의 단어를 보정했고, 단어장에 «HSK3 듣기» 단어 {added}개를 다시 넣었습니다.')
    if args.apply_sentences:
        pairs, files, cards, skipped = apply_sentences(args.repo)
        print(f'문장의 붙은 토큰 {pairs}종을 나눴습니다(회차 파일 {files}개, vocab.json 카드 {cards}개).')
        for token, pinyin in skipped:
            print(f'  ? 나누지 못함: {token} {pinyin}')
    if args.apply_listening or args.apply_sentences:
        import mine_refresh  # 순환 import라 여기서 가져온다(mine_refresh가 이 파일을 불러온다)
        if not mine_refresh.refresh_after_write(args.repo):
            return 1  # 데이터는 썼지만 내 단어장 갱신 색인을 쓰지 못했다
    counts = count_problems(args.repo)
    for kind, count in counts.items():
        print(kind, json.dumps(count, ensure_ascii=False))
    return 1 if any(count['문항'] for count in counts.values()) else 0


if __name__ == '__main__':
    raise SystemExit(main())
