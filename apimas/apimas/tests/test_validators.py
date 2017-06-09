import unittest
import mock
from apimas.validators import CerberusValidator


class TestApimasValidator(unittest.TestCase):
    def setUp(self):
        self.validator = CerberusValidator()

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
