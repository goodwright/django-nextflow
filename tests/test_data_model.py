import os
import time
from unittest.mock import Mock, PropertyMock, patch
from django.test.utils import override_settings
from mixer.backend.django import mixer
from django.test import TestCase
from django_nextflow.models import Data, ProcessExecution, Execution
from django.core.files.uploadedfile import SimpleUploadedFile

class DataCreationTests(TestCase):

    def test_data_creation(self):
        data = Data.objects.create(
            filename="reads.fastq", size=2048, filetype="fastq", md5="x",
            upstream_process_execution=mixer.blend(ProcessExecution)
        )
        data.full_clean()
        self.assertEqual(str(data), "reads.fastq")
        self.assertFalse(data.is_directory)
        self.assertEqual(data.label, "")
        self.assertEqual(data.notes, "")
        self.assertTrue(data.is_ready)
        self.assertTrue(data.is_binary)
        self.assertFalse(data.is_removed)
        self.assertLess(abs(data.created - time.time()), 1)
        self.assertEqual(data.downstream_executions.count(), 0)
        self.assertEqual(data.downstream_process_executions.count(), 0)
    

    def test_data_order(self):
        d1 = mixer.blend(Data, filename="C")
        d2 = mixer.blend(Data, filename="A")
        d3 = mixer.blend(Data, filename="B")
        self.assertEqual(list(Data.objects.all()), [d2, d3, d1])



class DataCreationFromPathTests(TestCase):

    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads")
    @patch("django_nextflow.models.get_file_extension")
    @patch("os.path.getsize")
    @patch("os.path.isdir")
    @patch("os.mkdir")
    @patch("shutil.copy")
    @patch("django_nextflow.models.get_file_hash")
    @patch("django_nextflow.models.check_if_binary")
    def test_can_create_from_path(self, mock_bin, mock_md5, mock_copy, mock_mk, mock_dir, mock_size, mock_ext):
        mock_ext.return_value = "txt"
        mock_size.return_value = 100
        mock_dir.return_value = False
        mock_md5.return_value = "X"
        mock_bin.return_value = False
        data = Data.create_from_path("/path/to/file")
        self.assertEqual(data.filename, "file")
        self.assertEqual(data.filetype, "txt")
        self.assertEqual(data.md5, "X")
        self.assertEqual(data.size, 100)
        self.assertFalse(data.is_directory)
        self.assertFalse(data.is_binary)
        self.assertLess(abs(data.created - time.time()), 1)
        self.assertIsNone(data.upstream_process_execution)
        mock_dir.assert_called_with("/path/to/file")
        mock_mk.assert_called_with(os.path.join("/uploads", str(data.id)))
        mock_copy.assert_called_with("/path/to/file", os.path.join(
            "/uploads", str(data.id), "file"
        ))
        mock_md5.assert_called_with(os.path.join(os.path.join("/uploads", str(data.id), "file")))
        mock_bin.assert_called_with("/path/to/file")
    

    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads")
    @patch("django_nextflow.models.get_file_extension")
    @patch("os.path.getsize")
    @patch("os.path.isdir")
    @patch("os.mkdir")
    @patch("shutil.copy")
    @patch("shutil.make_archive")
    @patch("django_nextflow.models.get_file_hash")
    @patch("django_nextflow.models.check_if_binary")
    def test_can_create_directory_from_path(self, mock_bin, mock_md5, mock_zip, mock_copy, mock_mk, mock_dir, mock_size, mock_ext):
        mock_ext.return_value = "txt"
        mock_size.return_value = 100
        mock_dir.return_value = True
        mock_md5.return_value = "X"
        data = Data.create_from_path("/path/to/file")
        self.assertEqual(data.filename, "file")
        self.assertEqual(data.filetype, "txt")
        self.assertEqual(data.md5, "X")
        self.assertEqual(data.size, 100)
        self.assertTrue(data.is_directory)
        self.assertFalse(data.is_binary)
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
        mock_md5.assert_called_with(os.path.join(os.path.join("/uploads", str(data.id), "file.zip")))
        self.assertFalse(mock_bin.called)



class DataCreationFromUploadedFileTests(TestCase):

    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads")
    @patch("django_nextflow.models.get_file_extension")
    @patch("os.mkdir")
    @patch("builtins.open")
    @patch("django_nextflow.models.get_file_hash")
    @patch("django_nextflow.models.check_if_binary")
    def test_can_create_from_upload(self, mock_bin, mock_md5, mock_open, mock_mk, mock_ext):
        upload = SimpleUploadedFile(name="file.txt", content=b"abc")
        mock_ext.return_value = "txt"
        mock_md5.return_value = "X"
        mock_bin.return_value = False
        data = Data.create_from_upload(upload)
        self.assertEqual(data.filename, "file.txt")
        self.assertEqual(data.filetype, "txt")
        self.assertEqual(data.md5, "X")
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
        mock_md5.assert_called_with(os.path.join("/uploads", str(data.id), "file.txt"))
        mock_bin.assert_called_with(os.path.join("/uploads", str(data.id), "file.txt"))

    

    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads")
    @patch("django_nextflow.models.get_file_extension")
    @patch("os.mkdir")
    @patch("builtins.open")
    @patch("shutil.unpack_archive")
    @patch("django_nextflow.models.get_file_hash")
    @patch("django_nextflow.models.check_if_binary")
    def test_can_create_directory_from_upload(self, mock_bin, mock_md5, mock_unzip, mock_open, mock_mk, mock_ext):
        upload = SimpleUploadedFile(name="file.zip", content=b"abc")
        mock_ext.return_value = ""
        mock_md5.return_value = "X"
        data = Data.create_from_upload(upload, is_directory=True)
        self.assertEqual(data.filename, "file")
        self.assertEqual(data.filetype, "")
        self.assertEqual(data.md5, "X")
        self.assertEqual(data.size, 3)
        self.assertTrue(data.is_directory)
        self.assertFalse(data.is_binary)
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
            os.path.join("/uploads", str(data.id), "file"), "zip"
        )
        mock_md5.assert_called_with(os.path.join("/uploads", str(data.id), "file.zip"))
        self.assertFalse(mock_bin.called)



class DataCreationFromMultiUploadedFileTests(TestCase):

    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads")
    @patch("django_nextflow.models.get_file_extension")
    @patch("os.mkdir")
    @patch("builtins.open")
    @patch("django_nextflow.models.check_if_binary")
    def test_can_create_first_blob(self, mock_bin, mock_open, mock_mk, mock_ext):
        upload = SimpleUploadedFile(name="blob", content=b"abc")
        mock_ext.return_value = "txt"
        mock_bin.return_value = False
        data = Data.create_from_partial_upload(upload, filename="file.txt")
        self.assertEqual(data.filename, "file.txt")
        self.assertEqual(data.filetype, "txt")
        self.assertEqual(data.size, 3)
        self.assertLess(abs(data.created - time.time()), 1)
        self.assertFalse(data.is_directory)
        self.assertTrue(data.is_binary)
        self.assertFalse(data.is_removed)
        self.assertFalse(data.is_ready)
        self.assertEqual(data.md5, "")
        mock_ext.assert_called_with("file.txt")
        mock_mk.assert_called_with(os.path.join("/uploads", str(data.id)))
        mock_open.assert_called_with(os.path.join(
            "/uploads", str(data.id), "file.txt"
        ), "wb")
        mock_open.return_value.__enter__.return_value.write.assert_called_with(b"abc")
        self.assertFalse(mock_bin.called)
    

    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads")
    @patch("builtins.open")
    @patch("os.path.getsize")
    def test_can_add_middle_blob(self, mock_size, mock_open):
        data = mixer.blend(
            Data, filename="file.txt", filetype="txt", size=0, created=100,
            is_directory=False, is_ready=False, md5=""
        )
        mock_size.return_value = 6
        upload = SimpleUploadedFile(name="blob", content=b"def")
        data = Data.create_from_partial_upload(upload, data=data)
        self.assertEqual(data.filename, "file.txt")
        self.assertEqual(data.filetype, "txt")
        self.assertEqual(data.size, 6)
        self.assertLess(abs(data.created - time.time()), 1)
        self.assertFalse(data.is_directory)
        self.assertFalse(data.is_removed)
        self.assertFalse(data.is_ready)
        self.assertEqual(data.md5, "")
        mock_open.assert_called_with(os.path.join("/uploads", str(data.id), "file.txt"), "ab")
        mock_open.return_value.__enter__.return_value.write.assert_called_with(b"def")
    

    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads")
    @patch("builtins.open")
    @patch("os.path.getsize")
    def test_can_add_middle_blob_and_validate_size(self, mock_size, mock_open):
        data = mixer.blend(
            Data, filename="file.txt", filetype="txt", size=3, created=100,
            is_directory=False, is_ready=False, md5=""
        )
        mock_size.return_value = 6
        upload = SimpleUploadedFile(name="blob", content=b"def")
        data = Data.create_from_partial_upload(upload, data=data, filesize=3)
        self.assertEqual(data.filename, "file.txt")
        self.assertEqual(data.filetype, "txt")
        self.assertEqual(data.size, 6)
        self.assertLess(abs(data.created - time.time()), 1)
        self.assertFalse(data.is_directory)
        self.assertFalse(data.is_removed)
        self.assertFalse(data.is_ready)
        self.assertEqual(data.md5, "")
        mock_open.assert_called_with(os.path.join("/uploads", str(data.id), "file.txt"), "ab")
        mock_open.return_value.__enter__.return_value.write.assert_called_with(b"def")
    

    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads")
    @patch("builtins.open")
    @patch("os.path.getsize")
    def test_can_add_middle_blob_and_ignore_small_size(self, mock_size, mock_open):
        data = mixer.blend(
            Data, filename="file.txt", filetype="txt", size=6, created=100,
            is_directory=False, is_ready=False, md5=""
        )
        mock_size.return_value = 6
        upload = SimpleUploadedFile(name="blob", content=b"def")
        data = Data.create_from_partial_upload(upload, data=data, filesize=3)
        self.assertEqual(data.filename, "file.txt")
        self.assertEqual(data.filetype, "txt")
        self.assertEqual(data.size, 6)
        self.assertFalse(data.is_directory)
        self.assertFalse(data.is_removed)
        self.assertFalse(data.is_ready)
        self.assertEqual(data.md5, "")
        self.assertFalse(mock_open.called)
    

    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads")
    @patch("builtins.open")
    @patch("os.path.getsize")
    def test_can_add_middle_blob_and_fail_large_size(self, mock_size, mock_open):
        data = mixer.blend(
            Data, filename="file.txt", filetype="txt", size=0, created=100,
            is_directory=False, is_ready=False, md5=""
        )
        mock_size.return_value = 6
        upload = SimpleUploadedFile(name="blob", content=b"def")
        with self.assertRaises(ValueError):
            data = Data.create_from_partial_upload(upload, data=data, filesize=3)
    

    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads")
    @patch("builtins.open")
    @patch("os.path.getsize")
    @patch("django_nextflow.models.get_file_hash")
    @patch("django_nextflow.models.check_if_binary")
    def test_can_add_final_blob(self, mock_bin, mock_md5, mock_size, mock_open):
        data = mixer.blend(
            Data, filename="file.txt", filetype="txt", size=0, created=100,
            is_directory=False, is_ready=False, md5=""
        )
        mock_bin.return_value = False
        mock_size.return_value = 9
        mock_md5.return_value = "hash"
        upload = SimpleUploadedFile(name="blob", content=b"ghi")
        data = Data.create_from_partial_upload(upload, data=data, final=True)
        self.assertEqual(data.filename, "file.txt")
        self.assertEqual(data.filetype, "txt")
        self.assertEqual(data.size, 9)
        self.assertLess(abs(data.created - time.time()), 1)
        self.assertFalse(data.is_directory)
        self.assertFalse(data.is_directory)
        self.assertFalse(data.is_removed)
        self.assertTrue(data.is_ready)
        self.assertEqual(data.md5, "hash")
        mock_open.assert_called_with(os.path.join("/uploads", str(data.id), "file.txt"), "ab")
        mock_open.return_value.__enter__.return_value.write.assert_called_with(b"ghi")
        mock_md5.assert_called_with(os.path.join("/uploads", str(data.id), "file.txt"))
        mock_size.assert_called_with(os.path.join("/uploads", str(data.id), "file.txt"))
        mock_bin.assert_called_with(os.path.join("/uploads", str(data.id), "file.txt"))
    

    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads")
    @patch("django_nextflow.models.get_file_extension")
    @patch("os.mkdir")
    @patch("builtins.open")
    def test_can_create_first_directory_blob(self, mock_open, mock_mk, mock_ext):
        upload = SimpleUploadedFile(name="blob", content=b"abc")
        mock_ext.return_value = ""
        data = Data.create_from_partial_upload(upload, filename="file.zip", is_directory=True)
        self.assertEqual(data.filename, "file")
        self.assertEqual(data.filetype, "")
        self.assertEqual(data.size, 3)
        self.assertLess(abs(data.created - time.time()), 1)
        self.assertTrue(data.is_directory)
        self.assertTrue(data.is_binary)
        self.assertFalse(data.is_removed)
        self.assertFalse(data.is_ready)
        self.assertEqual(data.md5, "")
        mock_ext.assert_called_with("file")
        mock_mk.assert_called_with(os.path.join("/uploads", str(data.id)))
        mock_open.assert_called_with(os.path.join(
            "/uploads", str(data.id), "file.zip"
        ), "wb")
        mock_open.return_value.__enter__.return_value.write.assert_called_with(b"abc")
    

    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads")
    @patch("builtins.open")
    @patch("os.path.getsize")
    @patch("django_nextflow.models.get_file_hash")
    @patch("shutil.unpack_archive")
    def test_can_add_final_directory_blob(self, mock_unpack, mock_md5, mock_size, mock_open):
        data = mixer.blend(
            Data, filename="file", filetype="", size=0, created=100,
            is_directory=True, is_ready=False, md5=""
        )
        mock_size.return_value = 9
        mock_md5.return_value = "hash"
        upload = SimpleUploadedFile(name="blob", content=b"ghi")
        data = Data.create_from_partial_upload(upload, data=data, final=True)
        self.assertEqual(data.filename, "file")
        self.assertEqual(data.filetype, "")
        self.assertEqual(data.size, 9)
        self.assertLess(abs(data.created - time.time()), 1)
        self.assertTrue(data.is_directory)
        self.assertFalse(data.is_binary)
        self.assertFalse(data.is_removed)
        self.assertTrue(data.is_ready)
        self.assertEqual(data.md5, "hash")
        mock_unpack.assert_called_with(
            os.path.join("/uploads", str(data.id), "file.zip"),
            os.path.join("/uploads", str(data.id), "file"), "zip"
        )
        mock_open.assert_called_with(os.path.join("/uploads", str(data.id), "file.zip"), "ab")
        mock_open.return_value.__enter__.return_value.write.assert_called_with(b"ghi")
        mock_md5.assert_called_with(os.path.join("/uploads", str(data.id), "file.zip"))
        mock_size.assert_called_with(os.path.join("/uploads", str(data.id), "file.zip"))



class DataCreationFromOutputTests(TestCase):

    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads")
    @patch("os.path.isdir")
    @patch("django_nextflow.models.get_file_extension")
    @patch("os.path.getsize")
    @patch("django_nextflow.models.get_file_hash")
    @patch("django_nextflow.models.check_if_binary")
    def test_can_create_from_output(self, mock_bin, mock_md5, mock_size, mock_ext, mock_dir):
        process_execution = mixer.blend(ProcessExecution)
        mock_ext.return_value = "txt"
        mock_size.return_value = 200
        mock_md5.return_value = "X"
        mock_dir.return_value = False
        mock_bin.return_value = False
        data = Data.create_from_output("/path/to/file.txt", process_execution)
        self.assertEqual(data.filename, "file.txt")
        self.assertEqual(data.filetype, "txt")
        self.assertEqual(data.size, 200)
        self.assertEqual(data.md5, "X")
        self.assertFalse(data.is_directory)
        self.assertFalse(data.is_binary)
        self.assertLess(abs(data.created - time.time()), 1)
        self.assertIs(data.upstream_process_execution, process_execution)
        mock_ext.assert_called_with("file.txt")
        mock_size.assert_called_with("/path/to/file.txt")
        mock_dir.assert_called_with("/path/to/file.txt")
        mock_md5.assert_called_with(os.path.join("/path/to/file.txt"))
        mock_bin.assert_called_with(os.path.join("/path/to/file.txt"))
    

    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads")
    @patch("os.path.isdir")
    @patch("django_nextflow.models.get_file_extension")
    @patch("os.path.getsize")
    @patch("shutil.make_archive")
    @patch("django_nextflow.models.get_file_hash")
    @patch("django_nextflow.models.check_if_binary")
    def test_can_create_directory_from_output(self, mock_bin, mock_md5, mock_zip, mock_size, mock_ext, mock_dir):
        process_execution = mixer.blend(ProcessExecution)
        mock_ext.return_value = ""
        mock_size.return_value = 200
        mock_md5.return_value = "X"
        mock_dir.return_value = True
        data = Data.create_from_output("/path/to/file", process_execution)
        self.assertEqual(data.filename, "file")
        self.assertEqual(data.filetype, "")
        self.assertEqual(data.size, 200)
        self.assertEqual(data.md5, "X")
        self.assertFalse(data.is_binary)
        self.assertTrue(data.is_directory)
        self.assertLess(abs(data.created - time.time()), 1)
        self.assertIs(data.upstream_process_execution, process_execution)
        mock_ext.assert_called_with("file")
        mock_size.assert_called_with("/path/to/file.zip")
        mock_dir.assert_called_with("/path/to/file")
        mock_zip.assert_called_with("/path/to/file", "zip", "/path/to/file")
        mock_md5.assert_called_with(os.path.join("/path/to/file.zip"))
        self.assertFalse(mock_bin.called)
    

    def test_can_ignore_if_already_exists(self):
        process_execution = mixer.blend(ProcessExecution)
        mixer.blend(Data, upstream_process_execution=process_execution, filename="file.txt")
        data = Data.create_from_output("/path/to/file.txt", process_execution)
        self.assertIsNone(data)



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



class UpstreamWithinExecutionTests(TestCase):

    def test_no_execution(self):
        data = mixer.blend(Data, upstream_process_execution=None)
        self.assertFalse(data.upstream_within_execution())
    

    @patch("django_nextflow.models.Execution.to_graph")
    def test_can_get_upstream(self, mock_graph):
        ex = mixer.blend(Execution)
        pe1 = mixer.blend(ProcessExecution)
        pe2 = mixer.blend(ProcessExecution)
        pe3 = mixer.blend(ProcessExecution)
        pe4 = mixer.blend(ProcessExecution)
        pe5 = mixer.blend(ProcessExecution)
        d1 = mixer.blend(Data)
        d2 = mixer.blend(Data)
        d3 = mixer.blend(Data)
        d4 = mixer.blend(Data)
        d5 = mixer.blend(Data)
        d6 = mixer.blend(Data)
        d7 = mixer.blend(Data)
        graph = Mock()
        mock_graph.return_value = graph
        data = mixer.blend(Data, id=1, upstream_process_execution=pe2)
        data.up = {pe2}
        pe2.up = {d4, d5}
        d4.up = {pe1}
        d5.up = {pe3}
        pe1.up = {d1, d2}
        pe3.up = {d7}
        d1.up, d2.up, d7.up = set(), set(), set()
        graph.data = {1: data}
        self.assertEqual(set(data.upstream_within_execution()), {d4, d5, d1, d2, d7})



class DownstreamWithinExecutionTests(TestCase):

    def test_no_execution(self):
        data = mixer.blend(Data, upstream_process_execution=None)
        self.assertFalse(data.downstream_within_execution())
    

    @patch("django_nextflow.models.Execution.to_graph")
    def test_can_get_downstream(self, mock_graph):
        ex = mixer.blend(Execution)
        pe1 = mixer.blend(ProcessExecution)
        pe2 = mixer.blend(ProcessExecution)
        pe3 = mixer.blend(ProcessExecution)
        pe4 = mixer.blend(ProcessExecution)
        pe5 = mixer.blend(ProcessExecution)
        d1 = mixer.blend(Data)
        d2 = mixer.blend(Data)
        d3 = mixer.blend(Data)
        d4 = mixer.blend(Data)
        d5 = mixer.blend(Data)
        d6 = mixer.blend(Data)
        d7 = mixer.blend(Data)
        graph = Mock()
        mock_graph.return_value = graph
        data = mixer.blend(Data, id=1, upstream_process_execution=pe2)
        data.down = {pe1, pe2}
        pe1.down = {d4}
        pe2.down = {d6, d5}
        d4.down = set()
        d5.down = {pe3}
        pe3.down = {d1, d2}
        d1.down, d2.down, d6.down = set(), set(), set()
        graph.data = {1: data}
        self.assertEqual(set(data.downstream_within_execution()), {d4, d6, d5, d1, d2})



class DataContentsTests(TestCase):

    def test_binary_contents(self):
        data = mixer.blend(Data, is_binary=True, is_directory=False, is_ready=True)
        self.assertIsNone(data.contents())
    

    def test_directory_contents(self):
        data = mixer.blend(Data, is_binary=False, is_directory=True, is_ready=True)
        self.assertIsNone(data.contents())
    

    def test_unready_contents(self):
        data = mixer.blend(Data, is_binary=False, is_directory=False, is_ready=False)
        self.assertIsNone(data.contents())
    

    @patch("django_nextflow.models.Data.full_path", new_callable=PropertyMock)
    @patch("builtins.open")
    def test_can_get_contents(self, mock_open, mock_path):
        mock_path.return_value = "/path"
        data = mixer.blend(Data, is_binary=False)
        data.full_path = "/path"
        mock_open.return_value.__enter__.return_value.read.return_value = "X"
        self.assertEqual(data.contents(), "X")
        mock_open.assert_called_with("/path")
        mock_open.return_value.__enter__.return_value.seek.assert_called_with(0)
        mock_open.return_value.__enter__.return_value.read.assert_called_with(1024)
    

    @patch("django_nextflow.models.Data.full_path", new_callable=PropertyMock)
    @patch("builtins.open")
    def test_can_get_specific_contents(self, mock_open, mock_path):
        mock_path.return_value = "/path"
        data = mixer.blend(Data, is_binary=False)
        data.full_path = "/path"
        mock_open.return_value.__enter__.return_value.read.return_value = "X"
        self.assertEqual(data.contents(4, 500), "X")
        mock_open.assert_called_with("/path")
        mock_open.return_value.__enter__.return_value.seek.assert_called_with(2000)
        mock_open.return_value.__enter__.return_value.read.assert_called_with(500)



class DataRemovalTests(TestCase):

    @override_settings(NEXTFLOW_DATA_ROOT="/data")
    @patch("django_nextflow.models.Data.full_path", new_callable=PropertyMock)
    @patch("os.remove")
    def test_can_remove_file(self, mock_remove, mock_path):
        data = mixer.blend(Data)
        self.assertFalse(data.is_removed)
        data.remove()
        self.assertTrue(data.is_removed)
        mock_remove.assert_called_with(mock_path.return_value)
    

    @override_settings(NEXTFLOW_DATA_ROOT="/data")
    @patch("django_nextflow.models.Data.full_path", new_callable=PropertyMock)
    @patch("os.remove")
    def test_can_remove_file_again(self, mock_remove, mock_path):
        data = mixer.blend(Data)
        mock_remove.side_effect = FileNotFoundError
        self.assertFalse(data.is_removed)
        data.remove()
        self.assertTrue(data.is_removed)
        mock_remove.assert_called_with(mock_path.return_value)



class DataDeletionTests(TestCase):

    @override_settings(NEXTFLOW_DATA_ROOT="/data")
    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads")
    @patch("shutil.rmtree")
    def test_can_delete_upload(self, mock_rm):
        data = mixer.blend(Data, id=1, upstream_process_execution=None)
        data.delete()
        mock_rm.assert_called_with(os.path.join("/uploads", "1"))
    

    @override_settings(NEXTFLOW_DATA_ROOT="/data")
    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads")
    @patch("shutil.rmtree")
    @patch("django_nextflow.models.Data.full_path", new_callable=PropertyMock)
    def test_can_delete_produced_file(self, mock_path, mock_rm):
        mock_path.return_value = "/data/proc/data.txt"
        data = mixer.blend(Data, id=1)
        data.delete()
        mock_rm.assert_called_with(os.path.join("/data/proc/data.txt"))
    

    @override_settings(NEXTFLOW_DATA_ROOT="/data")
    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads")
    @patch("shutil.rmtree")
    @patch("django_nextflow.models.Data.full_path", new_callable=PropertyMock)
    def test_can_delete_produced_directory(self, mock_path, mock_rm):
        mock_path.return_value = "/data/proc/data"
        data = mixer.blend(Data, id=1, is_directory=True)
        data.delete()
        mock_rm.assert_any_call(os.path.join("/data/proc/data"))
        mock_rm.assert_any_call(os.path.join("/data/proc/data.zip"))