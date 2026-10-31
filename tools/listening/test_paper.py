import unittest

from paper import picture_right


class PictureCropTest(unittest.TestCase):
    def test_clips_before_right_side_watermark(self):
        words = [
            {'text': 'A', 'x0': 90},
            {'text': 'Hancai', 'x0': 506.1},
            {'text': 'Chinese', 'x0': 506.1},
        ]
        self.assertAlmostEqual(picture_right(words), 500.1)

    def test_keeps_original_right_edge_without_watermark(self):
        self.assertEqual(picture_right([{'text': 'A', 'x0': 90}]), 540)


if __name__ == '__main__':
    unittest.main()
