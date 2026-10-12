"""독해 도구가 같이 쓰는 글자 처리. tools/listening/의 같은 함수를 옮겨 왔다
(듣기 도구는 완성된 일회성 스크립트라 그대로 두고, 듣기 해설을 보강할 때 합친다)."""
import re
import unicodedata

from pypinyin import Style, lazy_pinyin

CJK = r'[一-鿿，。！？：；、“”‘’（）《》…—]'
DIGIT_READINGS = set('0123456789')
PUNCT_PINYIN = {'，': ',', '、': ',', '。': '.', '？': '?', '！': '!', '：': ':', '；': ';', '“': '"', '”': '"'}


def tidy(text):
    """pdftotext가 한자·문장부호 옆에 넣은 공백을 걷어낸다 ('才 5 点' → '才5点')."""
    text = re.sub(rf'(?<={CJK})\s+|\s+(?={CJK})', '', text.strip())
    return re.sub(r'\s{2,}', ' ', text)


def toneless(pinyin):
    text = re.sub('[üǖǘǚǜ]', 'v', pinyin.lower())  # 성조 부호를 지우기 전에 ü를 v로 (pypinyin 표기)
    text = unicodedata.normalize('NFD', text)
    text = ''.join(ch for ch in text if unicodedata.category(ch) != 'Mn')
    return re.sub(r'[^a-z]', '', text)


def join_words(words):
    return ''.join(token for token, _ in words)


def check_words(words, source, where, problems, reading_diffs):
    """한자를 이으면 원문과 같은지(problems), pypinyin과 음절이 다른지(reading_diffs) 본다."""
    joined = join_words(words)
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
            accepted.add(expected[:-2] + 'r')  # 儿화: pypinyin은 'zheer', 해설은 'zhèr'
        if toneless(pinyin) not in accepted:
            reading_diffs.append(f'{where}: {token} {pinyin} (pypinyin: {"".join(lazy_pinyin(token, style=Style.TONE))})')


def words_to_pinyin(words):
    """[['你','nǐ'],['，','']] → 'Nǐ,' 처럼 단어장 예문 병음 한 줄로 만든다."""
    out = ''
    for token, pinyin in words:
        if pinyin:
            out += (' ' if out and not out.endswith('"') else '') + pinyin
        elif token in PUNCT_PINYIN:
            out += PUNCT_PINYIN[token]
    return out[:1].upper() + out[1:]
