import os
from unittest.mock import patch, Mock
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
        self.assertEqual(list(execution.process_executions.all()), [])
        self.assertEqual(list(execution.upstream.all()), [])


class ExecutionFinishedTests(TestCase):

    def test_can_get_finish_time(self):
        execution = mixer.blend(Execution, started=1000, duration=60)
        self.assertEqual(execution.finished, 1060)



class ExecutionLogTests(TestCase):

    @override_settings(NEXTFLOW_DATA_ROOT="/home/data")
    @patch("nextflow.Execution")
    @patch("nextflow.Execution.log")
    def test_can_get_log(self, mock_log, mock_Execution):
        mock_Execution.return_value = Mock(log="logtext")
        mock_log.return_value = "logtext"
        execution = mixer.blend(Execution, identifier="good_run")
        log = execution.get_log_text()
        self.assertEqual(log, "logtext")
        mock_Execution.assert_called_with(
            location=os.path.join("/home/data", str(execution.id)),
            id="good_run"
        )



class DirectoryPreparationTests(TestCase):

    @override_settings(NEXTFLOW_DATA_ROOT="/data")
    @patch("os.mkdir")
    def test_can_prepare_directory(self, mock_mk):
        id = Execution.prepare_directory()
        self.assertEqual(len(str(id)), 18)
        mock_mk.assert_called_with(os.path.join("/data", str(id)))



class CreationFromObjectTests(TestCase):

    @patch("django_nextflow.models.parse_datetime")
    @patch("django_nextflow.models.parse_duration")
    def test_can_create_from_object(self, mock_dur, mock_dt):
        mock_dt.return_value = 2021
        mock_dur.return_value = 10
        execution = Mock(
            id="x_y", status="OK", command="nextflow run", datetime="now",
            process=Mock(stdout="out", stderr="err", returncode=0), duration="1s"
        )
        pipeline = mixer.blend(Pipeline)
        execution = Execution.create_from_object(execution, 1234, pipeline)
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
        mock_dur.assert_called_with("1s")
        mock_dt.assert_called_with("now")