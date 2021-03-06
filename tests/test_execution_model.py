import os
from unittest.mock import mock_open, patch, Mock
from mixer.backend.django import mixer
from django.test import TestCase
from django.test.utils import override_settings
from django_nextflow.models import Execution, Pipeline

class ExecutionCreationTests(TestCase):

    def test_execution_creation(self):
        execution = Execution.objects.create(
            identifier="good_run", command="nextflow run pipeline.nf",
            stdout="all good", stderr="no problems", exit_code=0, status="OK",
            started=1000000000, duration=200, pipeline=mixer.blend(Pipeline)
        )
        execution.full_clean()
        self.assertEqual(str(execution), "good_run")
        self.assertEqual(execution.label, "")
        self.assertEqual(execution.notes, "")
        self.assertEqual(execution.params, "{}")
        self.assertEqual(execution.data_params, "{}")
        self.assertEqual(execution.execution_params, "{}")
        self.assertEqual(list(execution.process_executions.all()), [])
        self.assertEqual(list(execution.upstream_data.all()), [])
    

    def test_execution_order(self):
        e1 = mixer.blend(Execution, started=200)
        e2 = mixer.blend(Execution, started=None)
        e3 = mixer.blend(Execution, started=100)
        self.assertEqual(list(Execution.objects.all()), [e2, e3, e1])


class ExecutionFinishedTests(TestCase):

    def test_can_get_finish_time(self):
        execution = mixer.blend(Execution, started=1000, duration=60)
        self.assertEqual(execution.finished, 1060)
    

    def test_can_handle_missing_values(self):
        execution = mixer.blend(Execution, started=None, duration=60)
        self.assertIsNone(execution.finished)
        execution = mixer.blend(Execution, started=1000, duration=None)
        self.assertIsNone(execution.finished)
        execution = mixer.blend(Execution, started=None, duration=None)
        self.assertIsNone(execution.finished)



class ExecutionLogTests(TestCase):

    @override_settings(NEXTFLOW_DATA_ROOT="/home/data")
    @patch("builtins.open", new_callable=mock_open)
    def test_can_get_log(self, mock_open):
        mock_open.return_value.__enter__.return_value.read.return_value = "logtext"
        execution = mixer.blend(Execution)
        log = execution.get_log_text()
        self.assertEqual(log, "logtext")
        mock_open.assert_called_with(
            os.path.join("/home/data", str(execution.id), ".nextflow.log"),
        )



class DirectoryPreparationTests(TestCase):

    @override_settings(NEXTFLOW_DATA_ROOT="/data")
    @patch("os.mkdir")
    def test_can_prepare_directory(self, mock_mk):
        id = Execution.prepare_directory()
        self.assertEqual(len(str(id)), 12)
        mock_mk.assert_called_with(os.path.join("/data", str(id)))



class CreationFromObjectTests(TestCase):

    def test_can_create_from_object(self):
        execution = Mock(
            id="x_y", status="OK", command="nextflow run", started=2021,
            stdout="out", stderr="err", returncode=0, duration=10
        )
        pipeline = mixer.blend(Pipeline)
        execution = Execution.create_from_object(
            execution, 1234, pipeline, {1: 2}, {3: 4}, {5: 6}
        )
        self.assertEqual(execution.id, 1234)
        self.assertEqual(execution.params, '{"1": 2}')
        self.assertEqual(execution.data_params, '{"3": 4}')
        self.assertEqual(execution.execution_params, '{"5": 6}')
        self.assertEqual(execution.identifier, "x_y")
        self.assertEqual(execution.stdout, "out")
        self.assertEqual(execution.stderr, "err")
        self.assertEqual(execution.exit_code, 0)
        self.assertEqual(execution.status, "OK")
        self.assertEqual(execution.command, "nextflow run")
        self.assertEqual(execution.started, 2021)
        self.assertEqual(execution.duration, 10)
        self.assertEqual(execution.pipeline, pipeline)
    

    def test_can_update_from_object(self):
        execution = Mock(
            id="x_y", status="OK", command="nextflow run", started=2021,
            stdout="out", stderr="err", returncode=0, duration=10
        )
        pipeline = mixer.blend(Pipeline)
        ex = mixer.blend(Execution, id=1234, pipeline=pipeline)
        execution = Execution.create_from_object(execution, 1234, pipeline)
        self.assertEqual(ex, execution)
        self.assertEqual(execution.id, 1234)
        self.assertEqual(execution.identifier, "x_y")
        self.assertEqual(execution.stdout, "out")
        self.assertEqual(execution.stderr, "err")
        self.assertEqual(execution.exit_code, 0)
        self.assertEqual(execution.status, "OK")
        self.assertEqual(execution.command, "nextflow run")
        self.assertEqual(execution.started, 2021)
        self.assertEqual(execution.duration, 10)
        self.assertEqual(execution.pipeline, pipeline)
        self.assertEqual(Execution.objects.count(), 1)



class SymlinkRemovalTests(TestCase):

    @override_settings(NEXTFLOW_DATA_ROOT="/data")
    @patch("os.listdir")
    @patch("os.path.islink")
    @patch("os.unlink")
    def test_can_remove_symlinks(self, mock_unlink, mock_islink, mock_listdir):
        execution = mixer.blend(Execution, id=20)
        mock_listdir.return_value = ["work", "results", "file1", "file2", "file3"]
        mock_islink.side_effect = [False, False, True, False, True]
        execution.remove_symlinks()
        mock_listdir.assert_called_with(os.path.join("/data", "20"))
        for f in mock_listdir.return_value:
            mock_islink.assert_any_call(os.path.join("/data", "20", f))
        self.assertEqual(mock_unlink.call_count, 2)
        mock_unlink.assert_any_call(os.path.join("/data", "20", "file1"))
        mock_unlink.assert_any_call(os.path.join("/data", "20", "file3"))



class ExecutionGraphTests(TestCase):

    @patch("django_nextflow.models.Graph")
    def test_can_get_graph(self, mock_graph):
        execution = mixer.blend(Execution)
        graph = execution.to_graph()
        mock_graph.assert_called_with(execution)
        self.assertIs(graph, mock_graph.return_value)