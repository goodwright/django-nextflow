from unittest.mock import MagicMock, patch
from django.test import TestCase

from django_nextflow.utils import check_if_binary, get_file_extension, get_file_hash, parse_datetime, parse_duration

class DatetimeParsingTests(TestCase):

    def test_can_parse_datetime(self):
        self.assertEqual(parse_datetime("2020-01-01 12:00:00"), 1577901600)
    

    def test_can_parse_datetime_with_extra_stuff(self):
        self.assertEqual(parse_datetime("2020-01-01 12:00:00.234234"), 1577901600)



class DurationParsingTests(TestCase):

    def test_can_get_no_duration(self):
        self.assertEqual(parse_duration("-"), 0)
    

    def test_can_get_millisecond_duration(self):
        self.assertEqual(parse_duration("100ms"), 0.1)
    

    def test_can_get_second_duration(self):
        self.assertEqual(parse_duration("100s"), 100)
    

    def test_can_get_minute_duration(self):
        self.assertEqual(parse_duration("2m"), 120)
        self.assertEqual(parse_duration("2m 3s"), 123)
    

    def test_can_get_minute_duration(self):
        self.assertEqual(parse_duration("1h"), 3600)
        self.assertEqual(parse_duration("4h 2m 3s"), 14523)



class FileExtensionTests(TestCase):

    def test_can_get_extension(self):
        self.assertEqual(get_file_extension("file.txt"), "txt")
    

    def test_can_get_gz_extension(self):
        self.assertEqual(get_file_extension("file.txt.gz"), "txt.gz")
    

    def test_can_get_no_extension(self):
        self.assertEqual(get_file_extension("file"), "")



class FileHashTests(TestCase):

    @patch("builtins.open")
    def test_can_get_file_hash(self, mock_open):
        mock_open.return_value.__enter__.return_value.read.side_effect = [
            b"123", b"456"
        ]
        md5 = get_file_hash("/path")
        self.assertEqual(md5, "e10adc3949ba59abbe56e057f20f883e")
        mock_open.assert_called_with("/path", "rb")
        mock_open.return_value.__enter__.return_value.read.assert_called_with(4096)



class FileBinaryCheckTests(TestCase):

    @patch("builtins.open")
    def test_can_detect_binary(self, mock_open):
        mock_open.return_value.__enter__.return_value.read.return_value = ""
        mock_open.return_value.__enter__.return_value.read.side_effect = UnicodeDecodeError("1", b"", 3, 4, "5")
        self.assertTrue(check_if_binary("/path/to/file"))
        mock_open.assert_called_with("/path/to/file")
        mock_open.return_value.__enter__.return_value.read.assert_called_with(1024)
    

    @patch("builtins.open")
    def test_can_detect_not_binary(self, mock_open):
        self.assertFalse(check_if_binary("/path/to/file"))
        mock_open.assert_called_with("/path/to/file")
        mock_open.return_value.__enter__.return_value.read.assert_called_with(1024)