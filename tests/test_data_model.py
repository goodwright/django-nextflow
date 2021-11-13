import os
import time
from unittest.mock import patch
from django.test.utils import override_settings
from mixer.backend.django import mixer
from django.test import TestCase
from django_nextflow.models import Data, ProcessExecution, Execution
from django.core.files.uploadedfile import SimpleUploadedFile

class DataCreationTests(TestCase):

    def test_data_creation(self):
        data = Data.objects.create(
            filename="reads.fastq", size=2048, filetype="fastq",
            upstream_process_execution=mixer.blend(ProcessExecution)
        )
        data.full_clean()
        self.assertEqual(str(data), "reads.fastq")
        self.assertLess(abs(data.created - time.time()), 1)
        self.assertEqual(data.downstream_executions.count(), 0)
        self.assertEqual(data.downstream_process_executions.count(), 0)



class DataCreationFromPathTests(TestCase):

    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads")
    @patch("django_nextflow.models.get_file_extension")
    @patch("os.path.getsize")
    @patch("os.mkdir")
    @patch("shutil.copy")
    def test_can_create_from_path(self, mock_copy, mock_mk, mock_size, mock_ext):
        mock_ext.return_value = "txt"
        mock_size.return_value = 100
        data = Data.create_from_path("/path/to/file")
        self.assertEqual(data.filename, "file")
        self.assertEqual(data.filetype, "txt")
        self.assertEqual(data.size, 100)
        self.assertLess(abs(data.created - time.time()), 1)
        self.assertIsNone(data.upstream_process_execution)
        mock_mk.assert_called_with(os.path.join("/uploads", str(data.id)))
        mock_copy.assert_called_with("/path/to/file", os.path.join(
            "/uploads", str(data.id), "file"
        ))



class DataCreationFromUploadedFile(TestCase):

    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads")
    @patch("os.mkdir")
    @patch("builtins.open")
    def test_can_create_from_upload(self, mock_open, mock_mk):
        upload = SimpleUploadedFile(name="file.txt", content=b"abc")
        data = Data.create_from_upload(upload)
        self.assertEqual(data.filename, "file.txt")
        self.assertEqual(data.filetype, "txt")
        self.assertEqual(data.size, 3)
        self.assertLess(abs(data.created - time.time()), 1)
        self.assertIsNone(data.upstream_process_execution)
        mock_mk.assert_called_with(os.path.join("/uploads", str(data.id)))
        mock_open.assert_called_with(os.path.join(
            "/uploads", str(data.id), "file.txt"
        ), "wb+")
        mock_open.return_value.__enter__.return_value.write.assert_called_with(b"abc")



class DataFullPathTests(TestCase):

    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads")
    def test_can_get_full_path_of_uploaded_file(self):
        data = mixer.blend(Data, id=1, filename="reads.fastq", upstream_process_execution=None)
        self.assertEqual(data.full_path, os.path.join("/uploads", "1", "reads.fastq"))
    

    @override_settings(NEXTFLOW_DATA_ROOT="/data")
    @override_settings(NEXTFLOW_PUBLISH_DIR="results")
    def test_can_get_full_path_of_output_file(self):
        data = mixer.blend(Data, filename="reads.fastq", upstream_process_execution=mixer.blend(
            ProcessExecution, name="PROC", execution=mixer.blend(Execution, id=1)
        ))
        self.assertEqual(data.full_path, os.path.join("/data", "1", "results", "PROC", "reads.fastq"))