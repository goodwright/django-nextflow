import os
from unittest.mock import MagicMock, Mock, PropertyMock, patch
from django.test import TestCase
from django.test.utils import override_settings
from mixer.backend.django import mixer
from django_nextflow.models import Execution, Pipeline, Data, ProcessExecution

class PipelineCreationTests(TestCase):

    def test_pipeline_creation(self):
        pipeline = Pipeline.objects.create(
            name="Run analysis",
            description="Run some analysis",
            path="runanalysis.nf",
            config_path="nextflow.config",
            schema_path="schema.json"
        )
        self.assertEqual(str(pipeline), "Run analysis")
        self.assertEqual(list(pipeline.executions.all()), [])



class PipelineNextflowCreationTests(TestCase):

    @override_settings(NEXTFLOW_PIPELINE_ROOT="/pipelines")
    def test_can_create_nextflow_pipeline(self):
        pipeline = mixer.blend(Pipeline, path="path", config_path="config", schema_path="schema")
        pipeline = pipeline.create_pipeline()
        self.assertEqual(pipeline.path, os.path.join("/pipelines", "path"))
        self.assertEqual(pipeline.config, os.path.join("/pipelines", "config"))
        self.assertEqual(pipeline.schema, os.path.join("/pipelines", "schema"))
    

    @override_settings(NEXTFLOW_PIPELINE_ROOT="/pipelines")
    def test_can_create_nextflow_pipeline_without_values(self):
        pipeline = mixer.blend(Pipeline, path="path", config_path="", schema_path="")
        pipeline = pipeline.create_pipeline()
        self.assertEqual(pipeline.path, os.path.join("/pipelines", "path"))
        self.assertIsNone(pipeline.config)
        self.assertIsNone(pipeline.schema)



class InputSchemaTests(TestCase):

    @patch("django_nextflow.models.Pipeline.create_pipeline")
    def test_can_get_input_schema(self, mock_create):
        pipeline = mixer.blend(Pipeline)
        mock_create.return_value = Mock(input_schema = {1: "schema"})
        self.assertEqual(pipeline.input_schema, {1: "schema"})



class ParamCreationTests(TestCase):

    def test_can_create_no_params(self):
        pipeline = mixer.blend(Pipeline)
        params, data = pipeline.create_params({}, {})
        self.assertEqual(params, {})
        self.assertEqual(data, [])
    

    def test_can_create_params_from_basic(self):
        pipeline = mixer.blend(Pipeline)
        params, data = pipeline.create_params({"1": "2"}, {})
        self.assertEqual(params, {"1": "2"})
        self.assertEqual(data, [])
    

    @patch("django_nextflow.models.Data.full_path", new_callable=PropertyMock)
    def test_can_create_params_from_data(self, mock_path):
        mock_path.side_effect = ["/path1", "/path2"]
        pipeline = mixer.blend(Pipeline)
        data1 = mixer.blend(Data, id=1)
        data2 = mixer.blend(Data, id=2)
        mixer.blend(Data, id=3)
        params, data = pipeline.create_params({"1": "2"}, {"A": 1, "B": 2})
        self.assertEqual(params, {"1": "2", "A": "/path1", "B": "/path2"})
        self.assertEqual(data, [data1, data2])
    

    @patch("django_nextflow.models.Data.full_path", new_callable=PropertyMock)
    def test_can_create_params_from_data_when_missing(self, mock_path):
        mock_path.side_effect = ["/path1", "/path2"]
        pipeline = mixer.blend(Pipeline)
        data1 = mixer.blend(Data, id=1)
        mixer.blend(Data, id=3)
        params, data = pipeline.create_params({"1": "2"}, {"A": 1, "B": 2})
        self.assertEqual(params, {"1": "2", "A": "/path1"})
        self.assertEqual(data, [data1])
    

    @patch("django_nextflow.models.Data.full_path", new_callable=PropertyMock)
    def test_can_handle_list_of_data_params(self, mock_path):
        mock_path.side_effect = ["/path1", "/path2", "/path4"]
        pipeline = mixer.blend(Pipeline)
        data1 = mixer.blend(Data, id=1)
        data2 = mixer.blend(Data, id=2)
        data4 = mixer.blend(Data, id=4)
        params, data = pipeline.create_params({"1": "2"}, {"A": 1, "B": [2, 3, 4]})
        self.assertEqual(params, {"1": "2", "A": "/path1", "B": "/path2,/path4"})
        self.assertEqual(data, [data1, data2, data4])



class PipelineRunningTests(TestCase):

    @override_settings(NEXTFLOW_DATA_ROOT="/data")
    @patch("django_nextflow.models.Pipeline.create_pipeline")
    @patch("django_nextflow.models.Execution.prepare_directory")
    @patch("django_nextflow.models.Pipeline.create_params")
    @patch("django_nextflow.models.Execution.create_from_object")
    @patch("django_nextflow.models.ProcessExecution.create_from_object")
    @patch("django_nextflow.models.ProcessExecution.create_downstream_data_objects")
    @patch("django_nextflow.models.ProcessExecution.create_upstream_data_objects")
    def test_can_run(self, *mocks):
        nf_pipeline = Mock()
        nf_execution = Mock()
        nf_procex1, nf_procex2 = Mock(), Mock()
        execution = mixer.blend(Execution)
        procex1 = mixer.blend(ProcessExecution, execution=execution)
        procex2 = mixer.blend(ProcessExecution, execution=execution)
        nf_execution.process_executions = [nf_procex1, nf_procex2]
        nf_pipeline.run.return_value = nf_execution
        mocks[-1].return_value = nf_pipeline
        mocks[-2].return_value = "1000"
        mocks[-3].return_value = {1: 2, 3: 4}, [mixer.blend(Data), mixer.blend(Data)]
        mocks[-4].return_value = execution
        mocks[-5].side_effect = [procex1, procex2]
        pipeline = mixer.blend(Pipeline)
        pipeline.run(params={"param1": "X", "param2": "Y"}, data_params={"param3": 100}, profile=["X"])
        mocks[-1].assert_called_with()
        mocks[-2].assert_called_with()
        mocks[-3].assert_called_with({"param1": "X", "param2": "Y"}, {"param3": 100})
        nf_pipeline.run.assert_called_with(location="/data/1000", params={1: 2, 3: 4}, profile=["X"])
        mocks[-4].assert_called_with(nf_execution, "1000", pipeline)
        self.assertEqual(set(execution.upstream_data.all()), set(Data.objects.all()))
        mocks[-5].assert_any_call(nf_procex1, execution)
        self.assertEqual(mocks[-6].call_count, 2)
        self.assertEqual(mocks[-7].call_count, 2)