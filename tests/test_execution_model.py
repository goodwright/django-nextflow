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