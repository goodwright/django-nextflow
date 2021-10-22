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