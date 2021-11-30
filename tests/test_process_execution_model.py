import os
from unittest.mock import Mock, PropertyMock, patch
from django.test.utils import override_settings
from mixer.backend.django import mixer
from django.test import TestCase
from django_nextflow.models import ProcessExecution, Execution, Data

class ProcessExecutionCreationTests(TestCase):

    def test_process_execution_creation(self):
        execution = ProcessExecution.objects.create(
            name="FASTQC (1)", process_name="FASTQC", identifier="abc123",
            stdout="all good", stderr="no problems", status="OK",
            execution=mixer.blend(Execution)
        )
        execution.full_clean()
        self.assertEqual(str(execution), "FASTQC (1)")
        self.assertEqual(list(execution.downstream_data.all()), [])
        self.assertEqual(list(execution.upstream_data.all()), [])



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



@override_settings(NEXTFLOW_DATA_ROOT="/data")
@override_settings(NEXTFLOW_PUBLISH_DIR="results")
class PublishDirTests(TestCase):

    def setUp(self):
        self.execution = mixer.blend(
            ProcessExecution, name="PROC (2)", process_name="PROC",
            execution=mixer.blend(Execution, id=1)
        )
        self.patch1 = patch("os.path.exists")
        self.mock_exists = self.patch1.start()
        self.mock_exists.return_value = True
        self.patch2 = patch("os.listdir")
        self.mock_listdir = self.patch2.start()
        self.patch3 = patch("django_nextflow.models.ProcessExecution.work_dir", new_callable=PropertyMock)
        self.mock_work = self.patch3.start()
        self.mock_work.return_value = "/work"

    

    def tearDown(self):
        self.patch1.stop()
        self.patch2.stop()
        self.patch3.stop()


    def test_can_get_publish_dir_via_file_match(self):
        self.mock_listdir.side_effect = [
            ["PROC1", "PROC2", "PROC3"],
            ["myfile1.txt", "myfile2.txt", "myfile3.txt"],
            ["myfile1.txt", "myfile4.txt"],
            ["myfile2.txt", "myfile3.txt"],
            ["myfile5.txt"],
        ]
        self.assertEqual(self.execution.publish_dir, os.path.join(
            "/data", "1", "results", "PROC2"
        ))
        self.mock_exists.assert_called_with(os.path.join("/data", "1", "results"))
        self.assertEqual([c[0][0] for c in self.mock_listdir.call_args_list], [
            os.path.join("/data", "1", "results"),
            "/work",
            os.path.join("/data", "1", "results", "PROC1"),
            os.path.join("/data", "1", "results", "PROC2"),
            os.path.join("/data", "1", "results", "PROC3"),
        ])
    

    def test_can_get_publish_dir_via_process_name_match(self):
        self.mock_listdir.side_effect = [
            ["PROC (1)", "PROC (2)", "PROC (3)"],
            ["myfile1.txt", "myfile2.txt", "myfile3.txt"],
            ["myfile1.txt", "myfile4.txt"],
            ["myfile2.txt", "myfile3.txt"],
            ["myfile2.txt"],
        ]
        self.assertEqual(self.execution.publish_dir, os.path.join(
            "/data", "1", "results", "PROC (2)"
        ))
        self.mock_exists.assert_called_with(os.path.join("/data", "1", "results"))
        self.assertEqual([c[0][0] for c in self.mock_listdir.call_args_list], [
            os.path.join("/data", "1", "results"),
            "/work",
            os.path.join("/data", "1", "results", "PROC (1)"),
            os.path.join("/data", "1", "results", "PROC (2)"),
            os.path.join("/data", "1", "results", "PROC (3)"),
        ])
    

    def test_can_get_publish_dir_via_name_match(self):
        self.mock_listdir.side_effect = [
            ["PROC1", "PROC2", "PROC3"],
            ["myfile1.txt", "myfile2.txt", "myfile3.txt"],
            ["myfile8.txt", "myfile4.txt"],
            ["myfile2.txt", "myfile3.txt"],
            ["myfile9.txt"],
        ]
        self.assertEqual(self.execution.publish_dir, os.path.join(
            "/data", "1", "results", "PROC2"
        ))
        self.mock_exists.assert_called_with(os.path.join("/data", "1", "results"))
        self.assertEqual([c[0][0] for c in self.mock_listdir.call_args_list], [
            os.path.join("/data", "1", "results"),
            "/work",
            os.path.join("/data", "1", "results", "PROC1"),
            os.path.join("/data", "1", "results", "PROC2"),
            os.path.join("/data", "1", "results", "PROC3"),
        ])
    

    def test_can_handle_no_match(self):
        self.mock_exists.return_value = False
        self.assertIsNone(self.execution.publish_dir)



class WorkDirTests(TestCase):
    
    @patch("os.listdir")
    @override_settings(NEXTFLOW_DATA_ROOT="/data")
    def test_can_get_workdir(self, mock_listdir):
        mock_listdir.return_value = ["34567346753", "1234567890"]
        execution = mixer.blend(ProcessExecution, identifier="ab/123456", execution=mixer.blend(
            Execution, id=1
        ))
        self.assertEqual(execution.work_dir, os.path.join(
            "/data", "1", "work", "ab", "1234567890"
        ))



class DownstreamDataCreationTests(TestCase):

    @override_settings(NEXTFLOW_DATA_ROOT="/data")
    @patch("django_nextflow.models.ProcessExecution.publish_dir", new_callable=PropertyMock())
    @patch("os.listdir")
    @patch("django_nextflow.models.get_file_extension")
    @patch("os.path.getsize")
    def test_can_create_downstream_data_objects(self, mock_size, mock_ext, mock_list, mock_dir):
        mock_dir.return_value = "/path/results"
        mock_list.return_value = ["file1.txt", "file2.txt"]
        mock_ext.return_value = "txt"
        mock_size.side_effect = [20, 30]
        execution = mixer.blend(ProcessExecution)
        execution.create_downstream_data_objects()
        self.assertEqual(execution.downstream_data.count(), 2)
        for d in execution.downstream_data.all():
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
        execution.create_downstream_data_objects()
        self.assertEqual(execution.downstream_data.count(), 0)
    

    @override_settings(NEXTFLOW_DATA_ROOT="/data")
    @patch("django_nextflow.models.ProcessExecution.publish_dir", new_callable=PropertyMock())
    @patch("os.listdir")
    def test_can_handle_no_publish_dir(self, mock_list, mock_dir):
        mock_dir.return_value = None
        execution = mixer.blend(ProcessExecution)
        execution.create_downstream_data_objects()
        self.assertEqual(execution.downstream_data.count(), 0)



class UpstreamDataCreationTests(TestCase):

    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads")
    @override_settings(NEXTFLOW_DATA_ROOT="/data")
    @patch("os.listdir")
    @patch("django_nextflow.models.ProcessExecution.work_dir", new_callable=PropertyMock())
    @patch("os.readlink")
    def test_can_assign_upstream_data(self, mock_readlink, mock_workdir, mock_listdir):
        path = lambda s: s.replace("/", os.path.sep)
        mock_listdir.return_value = ["file1.txt", "file2.txt", "file3.txt"]
        mock_readlink.side_effect = [path("/uploads/10/file1.txt"), OSError, path("/data/20/work/ab/123456789/file3.txt")]
        upload1 = mixer.blend(Data, id=10)
        mixer.blend(Data, id=11)
        ex1 = mixer.blend(Execution, id=20)
        proc_ex = mixer.blend(ProcessExecution, identifier="ab/123456", execution=ex1)
        data1 = mixer.blend(Data, upstream_process_execution=proc_ex, filename="file3.txt")
        mixer.blend(Data, upstream_process_execution=proc_ex, filename="file5.txt")
        execution = mixer.blend(ProcessExecution)
        execution.create_upstream_data_objects()
        self.assertEqual(set(execution.upstream_data.all()), {data1, upload1})
        mock_listdir.assert_called_with(mock_workdir)
        for f in mock_listdir.return_value:
            mock_readlink.assert_any_call(os.path.join(mock_workdir, f))


