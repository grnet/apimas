import datetime
import unittest
from apimas.modeling.clients import extensions as ext


class TestExtensions(unittest.TestCase):
    def test_ref_normalizer(self):
        normalizer = ext.RefNormalizer('http://root.com')
        url = normalizer('value')
        self.assertEqual(url, 'http://root.com/value/')

        self.assertIsNone(normalizer(None))

    def test_datetime_normalizer(self):
        now = datetime.datetime.now()
        now_date = now.date()

        now_str = '%s-%s-%s %s:%s' % (
            now.year, str(now.month).zfill(2), str(now.day).zfill(2),
            str(now.hour).zfill(2), str(now.minute).zfill(2))
        now_date_str = '%s-%s-%s 00:00' % (
            now.year, str(now.month).zfill(2), str(now.day).zfill(2))

        normalizer = ext.DateNormalizer('%Y-%m-%d %H:%M')
        self.assertEqual(normalizer(now), now_str)
        self.assertEqual(normalizer(now_date), now_date_str)

        self.assertEqual(normalizer(now_str), now_str)
        self.assertEqual(normalizer(now_date_str), now_date_str)

        self.assertRaises(ValueError, normalizer, 'invalid str')
