import os
from unittest.mock import Mock, PropertyMock, patch
from django.test.utils import override_settings
from mixer.backend.django import mixer
from django.test import TestCase
from django_nextflow.models import ProcessExecution, Execution

class ProcessExecutionCreationTests(TestCase):

    def test_process_execution_creation(self):
        execution = ProcessExecution.objects.create(
            name="FASTQC (1)", process_name="FASTQC", identifier="abc123",
            stdout="all good", stderr="no problems", status="OK",
            execution=mixer.blend(Execution)
        )
        execution.full_clean()
        self.assertEqual(str(execution), "FASTQC (1)")
        self.assertEqual(list(execution.data.all()), [])



class ProcessExecutionCreationFromObject(TestCase):

    def test_can_create_from_object(self):
        mock_pe = Mock(
            name="PROC (1)", process="PROC", hash="ab/123",
            status="OK", stdout="out", stderr="err"
        )
        ex = mixer.blend(Execution)
        mock_pe.name = "PROC (1)"
        execution = ProcessExecution.create_from_object(mock_pe, ex)
        self.assertEqual(execution.name, "PROC (1)")
        self.assertEqual(execution.process_name, "PROC")
        self.assertEqual(execution.identifier, "ab/123")
        self.assertEqual(execution.status, "OK")
        self.assertEqual(execution.stdout, "out")
        self.assertEqual(execution.stderr, "err")
        self.assertEqual(execution.execution, ex)



class PublishDirTests(TestCase):

    @override_settings(NEXTFLOW_DATA_ROOT="/data")
    @override_settings(NEXTFLOW_PUBLISH_DIR="results")
    def test_can_get_publish_dir(self):
        execution = mixer.blend(ProcessExecution, name="PROC", execution=mixer.blend(
            Execution, id=1
        ))
        self.assertEqual(execution.publish_dir, os.path.join(
            "/data", "1", "results", "PROC"
        ))



class DataCreationTests(TestCase):

    @override_settings(NEXTFLOW_DATA_ROOT="/data")
    @patch("django_nextflow.models.ProcessExecution.publish_dir", new_callable=PropertyMock())
    @patch("os.listdir")
    @patch("django_nextflow.models.get_file_extension")
    @patch("os.path.getsize")
    def test_can_create_data_objects(self, mock_size, mock_ext, mock_list, mock_dir):
        mock_dir.return_value = "/path/results"
        mock_list.return_value = ["file1.txt", "file2.txt"]
        mock_ext.return_value = "txt"
        mock_size.side_effect = [20, 30]
        execution = mixer.blend(ProcessExecution)
        execution.create_data_objects()
        self.assertEqual(execution.data.count(), 2)
        for d in execution.data.all():
            self.assertIn(d.filename, ["file1.txt", "file2.txt"])
            self.assertEqual(d.filetype, "txt")
            self.assertIn(d.size, [20, 30])
    

    @override_settings(NEXTFLOW_DATA_ROOT="/data")
    @patch("django_nextflow.models.ProcessExecution.publish_dir", new_callable=PropertyMock())
    @patch("os.listdir")
    def test_can_handle_missing_location(self, mock_list, mock_dir):
        mock_dir.return_value = "/path/results"
        mock_list.side_effect = FileNotFoundError
        execution = mixer.blend(ProcessExecution)
        execution.create_data_objects()
        self.assertEqual(execution.data.count(), 0)

