import os
import shutil
import time
from django.test import TestCase
from django.test.utils import override_settings
from mixer.backend.django import mixer
from django_nextflow.models import Pipeline

class IntegrationTest(TestCase):

    def setUp(self):
        self.data_dir = os.path.join("tests", "data")
        if os.path.exists(self.data_dir): shutil.rmtree(self.data_dir)
        os.mkdir(self.data_dir)
    

    def tearDown(self):
        shutil.rmtree(self.data_dir)
        if os.path.exists(".nextflow"): shutil.rmtree(".nextflow")



class Test(IntegrationTest):

    @override_settings(NEXTFLOW_PIPELINE_ROOT=os.path.join("tests", "pipelines"))
    @override_settings(NEXTFLOW_DATA_ROOT=os.path.join("tests", "data"))
    def test(self):
        # Create pipeline
        pipeline = Pipeline.objects.create(
            name="Hello World",
            path=os.path.join("hello-world", "main.nf"),
        )

        # Run pipeline
        start = time.time()
        execution = pipeline.run()
        end = time.time()

        # Execution is fine
        self.assertIn(str(execution.id), os.listdir(self.data_dir))
        self.assertEqual(execution.pipeline, pipeline)
        self.assertIn("_", execution.identifier)
        self.assertIn("N E X T F L O W", execution.stdout)
        self.assertFalse(execution.stderr)
        self.assertEqual(execution.exit_code, 0)
        self.assertEqual(
            execution.command,
            f"nextflow run {os.path.abspath(os.path.join('tests', 'pipelines', pipeline.path))}\n"
        )
        self.assertLess(abs(execution.started - start), 2)
        self.assertLess(
            abs(execution.finished - (execution.started + execution.duration)), 2
        )

        # Execution log
        log_text = execution.get_log_text()
        self.assertIn("N E X T F L O W", log_text)
        self.assertIn(f"[{execution.identifier}]", log_text)
        self.assertIn(f"DEBUG", log_text)

        # Execution processes
        self.assertEqual(execution.process_executions.count(), 4)
        for process_execution in execution.process_executions.all():
            self.assertEqual(process_execution.execution, execution)
            self.assertTrue(process_execution.name.startswith("sayHello ("))
            self.assertEqual(process_execution.process_name, "sayHello")
            self.assertEqual(process_execution.status, "COMPLETED")
            self.assertIn(process_execution.stdout, [
                "Hello world!\n", "Bonjour world!\n", "Ciao world!\n", "Hola world!\n"
            ])
            self.assertEqual(len(process_execution.identifier), 9)
            self.assertEqual(process_execution.data.count(), 0)

