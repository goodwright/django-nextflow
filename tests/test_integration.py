import os
import shutil
import time
from django.test import TestCase
from django.test.utils import override_settings
from django_nextflow.models import Pipeline, Execution, Data, ProcessExecution

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
    @override_settings(NEXTFLOW_PUBLISH_DIR=os.path.join("results"))
    def test_basic_pipeline(self):
        # Create pipeline
        pipeline = Pipeline.objects.create(
            name="Hello World",
            path=os.path.join("hello-world", "main.nf"),
        )

        # Run pipeline
        start = time.time()
        execution = pipeline.run()

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
    

    @override_settings(NEXTFLOW_PIPELINE_ROOT=os.path.join("tests", "pipelines"))
    @override_settings(NEXTFLOW_DATA_ROOT=os.path.join("tests", "data"))
    @override_settings(NEXTFLOW_PUBLISH_DIR=os.path.join("results"))
    def test_basic_pipeline_with_inputs(self):
        # Create pipeline
        pipeline = Pipeline.objects.create(
            name="Hello World",
            path=os.path.join("hello-world", "main.nf"),
        )

        # Run pipeline
        execution = pipeline.run(params={"worldname": "Earth"})

        # Execution is fine
        self.assertIn(str(execution.id), os.listdir(self.data_dir))
        self.assertEqual(execution.pipeline, pipeline)
        self.assertIn("_", execution.identifier)
        self.assertIn("N E X T F L O W", execution.stdout)
        self.assertFalse(execution.stderr)
        self.assertEqual(execution.exit_code, 0)
        self.assertEqual(
            execution.command,
            f"nextflow run {os.path.abspath(os.path.join('tests', 'pipelines', pipeline.path))} --worldname=Earth\n"
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
                "Hello Earth!\n", "Bonjour Earth!\n", "Ciao Earth!\n", "Hola Earth!\n"
            ])
            self.assertEqual(len(process_execution.identifier), 9)
            self.assertEqual(process_execution.data.count(), 0)
    

    @override_settings(NEXTFLOW_PIPELINE_ROOT=os.path.join("tests", "pipelines"))
    @override_settings(NEXTFLOW_DATA_ROOT=os.path.join("tests", "data"))
    @override_settings(NEXTFLOW_PUBLISH_DIR=os.path.join("results"))
    def test_basic_pipeline_with_data_inputs(self):
        # Create data object
        pipeline = Pipeline.objects.create(
            name="Hello World (0)",
            path=os.path.join("data-input", "main.nf"),
        )
        execution = Execution.objects.create(
            id=50,
            pipeline=pipeline,
            exit_code=0,
            started=100, duration=20
        )
        process_execution = ProcessExecution.objects.create(
            execution=execution,
            name="Hello World (0)"
        )
        Data.objects.create(
            id=200,
            size=100,
            filename="test-file.txt",
            process_execution=process_execution
        )
        os.mkdir(os.path.join("tests", "data", "50"))
        os.mkdir(os.path.join("tests", "data", "50", "results"))
        os.mkdir(os.path.join("tests", "data", "50", "results", "Hello World (0)"))
        with open(os.path.join("tests", "data", "50", "results", "Hello World (0)", "test-file.txt"), "w") as f:
            f.write("content")

        # Create pipeline
        pipeline = Pipeline.objects.create(
            name="Hello World",
            path=os.path.join("data-input", "main.nf"),
        )

        # Run pipeline
        execution = pipeline.run(params={"worldname": "Earth"}, data_params={"filename": 200})

        # Execution is fine
        self.assertIn(str(execution.id), os.listdir(self.data_dir))
        self.assertEqual(execution.pipeline, pipeline)
        self.assertIn("_", execution.identifier)
        self.assertIn("N E X T F L O W", execution.stdout)
        self.assertFalse(execution.stderr)
        self.assertEqual(execution.exit_code, 0)
        self.assertEqual(
            execution.command,
            f"nextflow run {os.path.abspath(os.path.join('tests', 'pipelines', pipeline.path))}"
            f" --worldname=Earth '--filename={os.path.abspath(os.path.join('tests', 'data', '50', 'results', 'Hello World (0)', 'test-file.txt'))}'\n"
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
                "contentHello Earth!\n", "contentBonjour Earth!\n",
                "contentCiao Earth!\n", "contentHola Earth!\n"
            ])
            self.assertEqual(len(process_execution.identifier), 9)
            self.assertEqual(process_execution.data.count(), 0)
    

    @override_settings(NEXTFLOW_PIPELINE_ROOT=os.path.join("tests", "pipelines"))
    @override_settings(NEXTFLOW_DATA_ROOT=os.path.join("tests", "data"))
    @override_settings(NEXTFLOW_PUBLISH_DIR=os.path.join("results"))
    def test_pipeline_with_data_outputs(self):
        # Create pipeline
        pipeline = Pipeline.objects.create(
            name="Hello World",
            path=os.path.join("data-hello-world", "main.nf"),
            config_path=os.path.join("data-hello-world", "nextflow.config"),
        )

        # Run pipeline
        start = time.time()
        execution = pipeline.run()

        # Execution is fine
        self.assertIn(str(execution.id), os.listdir(self.data_dir))
        self.assertEqual(execution.pipeline, pipeline)
        self.assertIn("_", execution.identifier)
        self.assertIn("N E X T F L O W", execution.stdout)
        self.assertFalse(execution.stderr)
        self.assertEqual(execution.exit_code, 0)
        self.assertEqual(
            execution.command,
            f"nextflow -C {os.path.abspath(os.path.join('tests', 'pipelines', pipeline.config_path))} run {os.path.abspath(os.path.join('tests', 'pipelines', pipeline.path))}\n"
        )
        self.assertLess(abs(execution.started - start), 5)
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
            self.assertEqual(process_execution.stdout, "-")
            self.assertEqual(len(process_execution.identifier), 9)

            # Data objects
            self.assertEqual(process_execution.data.count(), 2)
            for data in process_execution.data.all():
                self.assertIn(data.filename, ["message.txt", "output.txt"])
                self.assertIn(data.size, [7, 12, 13, 15])
                self.assertEqual(data.process_execution, process_execution)