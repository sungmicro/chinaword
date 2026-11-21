"""audio30.py 순수 함수 테스트 (ffmpeg·whisper 없이).

  ~/venv-store/hsk-listening/bin/python -m unittest discover -s tools/hsk30
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audio30  # noqa: E402


def seg(i, start, end, text):
    return {'i': i, 'start': start, 'end': end, 'large': text}


def paper(level, n, groups=()):
    return {'level': level, 'listening': {'groups': list(groups), 'items': [{'no': k} for k in range(1, n + 1)]}}


class NumberTest(unittest.TestCase):
    def test_cn_to_int(self):
        self.assertEqual([audio30.cn_to_int(x) for x in ('一', '十', '十五', '二十', '二十一', '32', '甲')],
                         [1, 10, 15, 20, 21, 32, None])

    def test_speech_spans_split_on_gap(self):
        silences = [(1.0, 1.2), (2.0, 3.5)]
        spans = audio30.speech_spans(silences, 5.0, 1.0)
        self.assertEqual(spans, [{'start': 0.0, 'end': 2.0}, {'start': 3.5, 'end': 5.0}])


class ProposeTest(unittest.TestCase):
    def test_level3_keeps_first_reading_only(self):
        blocks = [
            seg(0, 0, 3, '现在开始第一到五题。'),
            seg(1, 6, 6.4, 'R'),                       # 번호(받아쓰기 틀림), 앞 쉼 2.6초
            seg(2, 7.5, 12, '姐姐，这是你的新耳机吗？对，我买来听音乐的。'),
            seg(3, 14.2, 18.7, '姐姐，这是你的新耳机吗？对，我买来听音乐的。'),  # 두 번째 낭독
            seg(4, 25, 25.4, '哦。'),
            seg(5, 26.5, 30, '哥哥，下午去看电影吗？我发烧了。'),
            seg(6, 32, 35.5, '哥哥，下午去看电影吗？我发烧了。'),
            seg(7, 40, 42, '听力考试现在结束。'),
        ]
        cuts, notes = audio30.propose_cuts({'id': 'T', 'blocks': blocks}, paper(3, 2))
        self.assertEqual(notes, [])
        self.assertEqual([c['ranges'] for c in cuts['items']], [[[6, 12]], [[25, 30]]])

    def test_group_passage_plus_own_question(self):
        fine = [
            seg(0, 0, 3, '每题听一次，现在开始第一题。'),
            seg(1, 5, 9, '第一到二题是根据下面一段话。'),
            seg(2, 9.5, 12, '你要是去成都，可以尝尝甜水面。'),
            seg(3, 12.5, 15, '特别香。'),
            seg(4, 17.2, 17.9, '一'),
            seg(5, 19, 21, '甜水面是哪里的美食？'),
            seg(6, 37, 37.8, '二'),
            seg(7, 39, 41, '甜水面的味道怎么样？'),
        ]
        cuts, notes = audio30.propose_cuts({'id': 'T', 'fine': fine}, paper(4, 2, ['1-2']), 'fine')
        self.assertEqual(notes, [])
        self.assertEqual(cuts['items'][0]['ranges'], [[9.5, 15], [17.2, 21]])
        self.assertEqual(cuts['items'][1]['ranges'], [[9.5, 15], [37, 41]])
        self.assertEqual(cuts['items'][1]['group'], '1-2')

    def test_short_reply_inside_dialogue_is_not_a_number(self):
        fine = [
            seg(0, 0, 3, '现在开始第一题。'),
            seg(1, 5, 5.5, '一'),
            seg(2, 6.6, 9, '姐姐，这是你的新耳机吗？'),
            seg(3, 9.4, 9.8, '对。'),          # 앞 쉼 0.4초: 대화 속 짧은 대답
            seg(4, 10.1, 12, '我买来听音乐的。'),
        ]
        cuts, notes = audio30.propose_cuts({'id': 'T', 'fine': fine}, paper(4, 1), 'fine')
        self.assertEqual(notes, [])
        self.assertEqual(cuts['items'][0]['ranges'], [[5, 12]])


class SnapTest(unittest.TestCase):
    def test_snap_stays_inside_silence_midpoints(self):
        silences = [(9.0, 9.2), (12.0, 12.2)]
        self.assertEqual(audio30.snap(10.0, 11.5, silences), (9.7, 11.8))
        self.assertEqual(audio30.snap(9.3, 11.9, silences), (9.1, 12.1))


if __name__ == '__main__':
    unittest.main()
