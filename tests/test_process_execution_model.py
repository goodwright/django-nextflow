import os
from unittest.mock import Mock, PropertyMock, patch, mock_open
from django.test.utils import override_settings
from mixer.backend.django import mixer
from django.test import TestCase
from django_nextflow.models import ProcessExecution, Execution, Data

class ProcessExecutionCreationTests(TestCase):

    def test_process_execution_creation(self):
        execution = ProcessExecution.objects.create(
            name="FASTQC (1)", process_name="FASTQC", identifier="abc123",
            stdout="all good", stderr="no problems", status="OK",
            started=2000, duration=5,
            execution=mixer.blend(Execution)
        )
        execution.full_clean()
        self.assertEqual(str(execution), "FASTQC (1)")
        self.assertEqual(list(execution.downstream_data.all()), [])
        self.assertEqual(list(execution.upstream_data.all()), [])
    

    def test_process_execution_order(self):
        p1 = mixer.blend(ProcessExecution, started=200)
        p2 = mixer.blend(ProcessExecution, started=None)
        p3 = mixer.blend(ProcessExecution, started=100)
        self.assertEqual(list(ProcessExecution.objects.all()), [p2, p3, p1])



class ProcessExecutionCreationFromObject(TestCase):

    def test_can_create_from_object(self):
        mock_pe = Mock(
            name="PROC (1)", process="PROC", hash="ab/123", started=2000,
            status="OK", stdout="out", stderr="err", start="123", duration=10
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
        self.assertEqual(execution.started, 2000)
        self.assertEqual(execution.duration, 10)
        self.assertEqual(execution.execution, ex)
    

    def test_can_update_from_object(self):
        mock_pe = Mock(
            name="PROC (1)", process="PROC", hash="ab/123", started=2000,
            status="OK", stdout="out", stderr="err", start="123", duration=10
        )
        ex = mixer.blend(Execution)
        mock_pe.name = "PROC (1)"
        pe = mixer.blend(ProcessExecution, identifier="ab/123", execution=ex)
        execution = ProcessExecution.create_from_object(mock_pe, ex)
        self.assertEqual(pe, execution)
        self.assertEqual(execution.name, "PROC (1)")
        self.assertEqual(execution.process_name, "PROC")
        self.assertEqual(execution.identifier, "ab/123")
        self.assertEqual(execution.status, "OK")
        self.assertEqual(execution.stdout, "out")
        self.assertEqual(execution.stderr, "err")
        self.assertEqual(execution.started, 2000)
        self.assertEqual(execution.duration, 10)
        self.assertEqual(execution.execution, ex)
        self.assertEqual(ProcessExecution.objects.count(), 1)


class ExecutionFinishedTests(TestCase):

    def test_can_get_finish_time(self):
        execution = mixer.blend(ProcessExecution, started=1000, duration=60)
        self.assertEqual(execution.finished, 1060)



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
    @override_settings(NEXTFLOW_PUBLISH_DIR="results")
    @patch("os.path.exists")
    def test_can_handle_no_publish_dir(self, mock_exists):
        proc_ex = mixer.blend(ProcessExecution, execution=mixer.blend(Execution, id=10))
        mock_exists.return_value = False
        proc_ex.create_downstream_data_objects()
        self.assertEqual(proc_ex.downstream_data.count(), 0)
        mock_exists.assert_called_with(os.path.join("/data", "10", "results"))
    

    @override_settings(NEXTFLOW_DATA_ROOT="/data")
    @override_settings(NEXTFLOW_PUBLISH_DIR="results")
    @patch("os.path.exists")
    @patch("os.listdir")
    @patch("django_nextflow.models.ProcessExecution.work_dir", new_callable=PropertyMock())
    @patch("os.path.islink")
    @patch("os.readlink")
    @patch("django_nextflow.models.Data.create_from_output")
    def test_can_get_downstream_data(self, mock_create, mock_read, mock_islink, mock_work, mock_listdir, mock_exists):
        mock_listdir.side_effect = [
            ["PROC1", "PROC2"],
            ["result1.txt", "outfile2.txt"],
            ["outfile1.txt", "outfile3.txt", "outfile5.txt"],
            [".command.sh", "outfile1.txt", "infile.txt", "outfile2.txt", "outfile3.txt"],
        ]
        mock_islink.side_effect = [
            True, True, True, True, True,
            False, False, True, False, False
        ]
        mock_read.side_effect = [
            "/other/result1.txt", "/other/outfile2.txt",
            "/workdir/outfile1.txt", "/workdir/outfile3.txt", "/workdir/outfile5.txt"
        ]
        proc_ex = mixer.blend(ProcessExecution, work_dir="/workdir")
        proc_ex.create_downstream_data_objects()
        self.assertEqual(mock_create.call_count, 2)
        mock_create.assert_any_call(os.path.join("/workdir", "outfile1.txt"), proc_ex)
        mock_create.assert_any_call(os.path.join("/workdir", "outfile3.txt"), proc_ex)



class UpstreamDataCreationTests(TestCase):

    @patch("django_nextflow.models.ProcessExecution.work_dir", new_callable=PropertyMock())
    @patch("builtins.open", new_callable=mock_open)
    def test_can_handle_missing_run_file(self, mock_open, mock_work):
        mock_open.side_effect = FileNotFoundError
        proc_ex = mixer.blend(ProcessExecution)
        proc_ex.create_upstream_data_objects()
        self.assertEqual(proc_ex.upstream_data.count(), 0)
    

    @patch("django_nextflow.models.ProcessExecution.work_dir", new_callable=PropertyMock())
    @patch("builtins.open", new_callable=mock_open)
    def test_can_handle_no_stage(self, mock_open, mock_work):
        mock_open.return_value.__enter__.return_value.read.return_value = "..."
        proc_ex = mixer.blend(ProcessExecution)
        proc_ex.create_upstream_data_objects()
        self.assertEqual(proc_ex.upstream_data.count(), 0)
    

    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads".replace("/", os.path.sep))
    @override_settings(NEXTFLOW_DATA_ROOT="/data".replace("/", os.path.sep))
    @patch("django_nextflow.models.ProcessExecution.work_dir", new_callable=PropertyMock())
    @patch("builtins.open", new_callable=mock_open)
    def test_can_get_upstream_uploads(self, mock_open, mock_work):
        run = "... ... nxf_stage() { token1 token2 /uploads/123/file.txt token4 /uploads/456/file.txt }".replace("/", os.path.sep)
        mock_open.return_value.__enter__.return_value.read.return_value = run
        upload1 = mixer.blend(Data, id=123)
        upload2 = mixer.blend(Data, id=456)
        upload3 = mixer.blend(Data, id=789)
        proc_ex = mixer.blend(ProcessExecution)
        proc_ex.create_upstream_data_objects()
        self.assertEqual(proc_ex.upstream_data.count(), 2)
        self.assertEqual(set(proc_ex.upstream_data.all()), {upload1, upload2})
    

    @override_settings(NEXTFLOW_UPLOADS_ROOT="/uploads".replace("/", os.path.sep))
    @override_settings(NEXTFLOW_DATA_ROOT="/data".replace("/", os.path.sep))
    @patch("django_nextflow.models.ProcessExecution.work_dir", new_callable=PropertyMock())
    @patch("builtins.open", new_callable=mock_open)
    @patch("django_nextflow.models.Data.create_from_output")
    def test_can_get_upstream_data_objects(self, mock_create, mock_open, mock_work):
        run = "... ... nxf_stage() { token1 token2 /data/123/work/12/345/file.txt token4 /data/456/work/02/345/file.txt }".replace("/", os.path.sep)
        mock_open.return_value.__enter__.return_value.read.return_value = run
        ex1 = mixer.blend(Execution, id=123)
        pe1 = mixer.blend(ProcessExecution, execution=ex1, identifier="12/345")
        mixer.blend(Data, upstream_process_execution=pe1, filename="file.txt")
        pe2 = mixer.blend(ProcessExecution, execution=ex1)
        ex2 = mixer.blend(Execution, id=456)
        pe3 = mixer.blend(ProcessExecution, execution=ex2, identifier="02/345", work_dir="111")
        pe3.work_dir = "/workdir3"
        pe4 = mixer.blend(ProcessExecution, execution=ex2)
        ex3 = mixer.blend(Execution, id=789)
        proc_ex = mixer.blend(ProcessExecution)
        mock_create.return_value = mixer.blend(Data)
        proc_ex.create_upstream_data_objects()
        self.assertEqual(proc_ex.upstream_data.count(), 2)
        self.assertEqual(mock_create.call_count, 1)
        self.assertEqual(set(proc_ex.upstream_data.all()), set(Data.objects.all()))



