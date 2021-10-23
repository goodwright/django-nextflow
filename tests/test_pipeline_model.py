
from django.test import TestCase
from django.test.utils import override_settings
from mixer.backend.django import mixer
from django_nextflow.models import Pipeline

class PipelineCreationTests(TestCase):

    def test_pipeline_creation(self):
        pipeline = Pipeline.objects.create(
            name="Run analysis",
            path="runanalysis.nf",
            config_path="nextflow.config",
            schema_path="schema.json"
        )
        self.assertEqual(str(pipeline), "Run analysis")
        self.assertEqual(list(pipeline.executions.all()), [])



class RunTests(TestCase):

    @override_settings(NEXTFLOW_PIPELINE_ROOT="/home/nf")
    @override_settings(NEXTFLOW_DATA_ROOT="/home/data")
    def test_can_run(self):
        pipeline = mixer.blend(Pipeline, path="main.nf", config_path="conf/nextflow.config")
        execution = pipeline.run()
