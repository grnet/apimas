import datetime
import unittest
import mock
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

        normalizer = ext.DateNormalizer(
            string_formats=['%Y-%m-%d %H:%M', '%Y-%m'],
            date_format='%Y-%m-%d %H:%M')
        self.assertEqual(normalizer(now), now_str)
        self.assertEqual(normalizer(now_date), now_date_str)

        self.assertEqual(normalizer(now_str), now_str)
        self.assertEqual(normalizer(now_date_str), now_date_str)

        self.assertRaises(ValueError, normalizer, 'invalid str')


class TestApimasValidator(unittest.TestCase):
    def setUp(self):
        self.validator = ext.ApimasValidator()

    def test_isfile(self):
        self.assertFalse(self.validator._validate_type_file('not a file'))
        self.assertTrue(self.validator._validate_type_file(
            mock.Mock(spec=file)))

    def test_isemail(self):
        email = 323
        self.assertFalse(self.validator._validate_type_email(email))

        email = 'invalid email'
        self.assertFalse(self.validator._validate_type_email(email))

        email = 'test@example.com'
        self.assertTrue(self.validator._validate_type_email(email))
