from django.test import TestCase

from django_nextflow.utils import get_file_extension, parse_datetime, parse_duration

class DatetimeParsingTests(TestCase):

    def test_can_parse_datetime(self):
        self.assertEqual(parse_datetime("2020-01-01 12:00:00"), 1577901600)



class DurationParsingTests(TestCase):

    def test_can_get_no_duration(self):
        self.assertEqual(parse_duration("-"), 0)
    

    def test_can_get_millisecond_duration(self):
        self.assertEqual(parse_duration("100ms"), 0.1)
    

    def test_can_get_second_duration(self):
        self.assertEqual(parse_duration("100s"), 100)



class FileExtensionTests(TestCase):

    def test_can_get_extension(self):
        self.assertEqual(get_file_extension("file.txt"), "txt")
    

    def test_can_get_no_extension(self):
        self.assertEqual(get_file_extension("file"), "")