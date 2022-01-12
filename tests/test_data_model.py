import os
import time
from unittest.mock import PropertyMock, patch
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
        self.assertFalse(data.is_directory)
        self.assertLess(abs(data.created - time.time()), 1)
        self.assertEqual(data.downstream_executions.count(), 0)
        self.assertEqual(data.downstream_process_executions.count(), 0)



class DataCreationFromPathTests(TestCase):

    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads")
    @patch("django_nextflow.models.get_file_extension")
    @patch("os.path.getsize")
    @patch("os.path.isdir")
    @patch("os.mkdir")
    @patch("shutil.copy")
    def test_can_create_from_path(self, mock_copy, mock_mk, mock_dir, mock_size, mock_ext):
        mock_ext.return_value = "txt"
        mock_size.return_value = 100
        mock_dir.return_value = False
        data = Data.create_from_path("/path/to/file")
        self.assertEqual(data.filename, "file")
        self.assertEqual(data.filetype, "txt")
        self.assertEqual(data.size, 100)
        self.assertFalse(data.is_directory)
        self.assertLess(abs(data.created - time.time()), 1)
        self.assertIsNone(data.upstream_process_execution)
        mock_dir.assert_called_with("/path/to/file")
        mock_mk.assert_called_with(os.path.join("/uploads", str(data.id)))
        mock_copy.assert_called_with("/path/to/file", os.path.join(
            "/uploads", str(data.id), "file"
        ))
    

    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads")
    @patch("django_nextflow.models.get_file_extension")
    @patch("os.path.getsize")
    @patch("os.path.isdir")
    @patch("os.mkdir")
    @patch("shutil.copy")
    @patch("shutil.make_archive")
    def test_can_create_directory_from_path(self, mock_zip, mock_copy, mock_mk, mock_dir, mock_size, mock_ext):
        mock_ext.return_value = "txt"
        mock_size.return_value = 100
        mock_dir.return_value = True
        data = Data.create_from_path("/path/to/file")
        self.assertEqual(data.filename, "file")
        self.assertEqual(data.filetype, "txt")
        self.assertEqual(data.size, 100)
        self.assertTrue(data.is_directory)
        self.assertLess(abs(data.created - time.time()), 1)
        self.assertIsNone(data.upstream_process_execution)
        mock_dir.assert_called_with("/path/to/file")
        mock_mk.assert_called_with(os.path.join("/uploads", str(data.id)))
        mock_copy.assert_called_with("/path/to/file", os.path.join(
            "/uploads", str(data.id), "file"
        ))
        mock_zip.assert_called_with(
            os.path.join("/uploads", str(data.id), "file"),
            "zip", os.path.join("/uploads", str(data.id), "file"),
        )



class DataCreationFromUploadedFileTests(TestCase):

    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads")
    @patch("django_nextflow.models.get_file_extension")
    @patch("os.mkdir")
    @patch("builtins.open")
    def test_can_create_from_upload(self, mock_open, mock_mk, mock_ext):
        upload = SimpleUploadedFile(name="file.txt", content=b"abc")
        mock_ext.return_value = "txt"
        data = Data.create_from_upload(upload)
        self.assertEqual(data.filename, "file.txt")
        self.assertEqual(data.filetype, "txt")
        self.assertEqual(data.size, 3)
        self.assertFalse(data.is_directory)
        self.assertLess(abs(data.created - time.time()), 1)
        self.assertIsNone(data.upstream_process_execution)
        mock_ext.assert_called_with("file.txt")
        mock_mk.assert_called_with(os.path.join("/uploads", str(data.id)))
        mock_open.assert_called_with(os.path.join(
            "/uploads", str(data.id), "file.txt"
        ), "wb+")
        mock_open.return_value.__enter__.return_value.write.assert_called_with(b"abc")
    

    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads")
    @patch("django_nextflow.models.get_file_extension")
    @patch("os.mkdir")
    @patch("builtins.open")
    @patch("shutil.unpack_archive")
    def test_can_create_directory_from_upload(self, mock_unzip, mock_open, mock_mk, mock_ext):
        upload = SimpleUploadedFile(name="file.zip", content=b"abc")
        mock_ext.return_value = ""
        data = Data.create_from_upload(upload, is_directory=True)
        self.assertEqual(data.filename, "file")
        self.assertEqual(data.filetype, "")
        self.assertEqual(data.size, 3)
        self.assertTrue(data.is_directory)
        self.assertLess(abs(data.created - time.time()), 1)
        self.assertIsNone(data.upstream_process_execution)
        mock_ext.assert_called_with("file")
        mock_mk.assert_called_with(os.path.join("/uploads", str(data.id)))
        mock_open.assert_called_with(os.path.join(
            "/uploads", str(data.id), "file.zip"
        ), "wb+")
        mock_open.return_value.__enter__.return_value.write.assert_called_with(b"abc")
        mock_unzip.assert_called_with(
            os.path.join("/uploads", str(data.id), "file.zip"),
            os.path.join("/uploads", str(data.id)), "zip"
        )



class DataCreationFromOutputTests(TestCase):

    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads")
    @patch("os.path.isdir")
    @patch("django_nextflow.models.get_file_extension")
    @patch("os.path.getsize")
    def test_can_create_from_output(self, mock_size, mock_ext, mock_dir):
        process_execution = mixer.blend(ProcessExecution)
        mock_ext.return_value = "txt"
        mock_size.return_value = 200
        mock_dir.return_value = False
        data = Data.create_from_output("/path/to/file.txt", process_execution)
        self.assertEqual(data.filename, "file.txt")
        self.assertEqual(data.filetype, "txt")
        self.assertEqual(data.size, 200)
        self.assertFalse(data.is_directory)
        self.assertLess(abs(data.created - time.time()), 1)
        self.assertIs(data.upstream_process_execution, process_execution)
        mock_ext.assert_called_with("file.txt")
        mock_size.assert_called_with("/path/to/file.txt")
        mock_dir.assert_called_with("/path/to/file.txt")
    

    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads")
    @patch("os.path.isdir")
    @patch("django_nextflow.models.get_file_extension")
    @patch("os.path.getsize")
    @patch("shutil.make_archive")
    def test_can_create_directory_from_output(self, mock_zip, mock_size, mock_ext, mock_dir):
        process_execution = mixer.blend(ProcessExecution)
        mock_ext.return_value = ""
        mock_size.return_value = 200
        mock_dir.return_value = True
        data = Data.create_from_output("/path/to/file", process_execution)
        self.assertEqual(data.filename, "file")
        self.assertEqual(data.filetype, "")
        self.assertEqual(data.size, 200)
        self.assertTrue(data.is_directory)
        self.assertLess(abs(data.created - time.time()), 1)
        self.assertIs(data.upstream_process_execution, process_execution)
        mock_ext.assert_called_with("file")
        mock_size.assert_called_with("/path/to/file")
        mock_dir.assert_called_with("/path/to/file")
        mock_zip.assert_called_with("/path/to/file", "zip", "/path/to/file")



class DataFullPathTests(TestCase):

    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads")
    def test_can_get_full_path_of_uploaded_file(self):
        data = mixer.blend(Data, id=1, filename="reads.fastq", upstream_process_execution=None)
        self.assertEqual(data.full_path, os.path.join("/uploads", "1", "reads.fastq"))
    

    @override_settings(NEXTFLOW_DATA_ROOT="/data")
    @override_settings(NEXTFLOW_PUBLISH_DIR="results")
    @patch("django_nextflow.models.ProcessExecution.work_dir", new_callable=PropertyMock)
    def test_can_get_full_path_of_output_file(self, mock_workdir):
        mock_workdir.return_value = "/work/dir"
        data = mixer.blend(Data, filename="reads.fastq")
        self.assertEqual(data.full_path, os.path.join("/work/dir", "reads.fastq"))