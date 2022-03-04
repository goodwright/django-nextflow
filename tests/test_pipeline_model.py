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
    

    def test_pipeline_order(self):
        p1 = mixer.blend(Pipeline, name="C")
        p2 = mixer.blend(Pipeline, name="A")
        p3 = mixer.blend(Pipeline, name="B")
        self.assertEqual(list(Pipeline.objects.all()), [p2, p3, p1])



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
        params, data, executions = pipeline.create_params({}, {}, {}, "10")
        self.assertEqual(params, {})
        self.assertEqual(data, [])
        self.assertEqual(executions, [])
    

    @patch("django_nextflow.models.Pipeline.create_data_params")
    @patch("django_nextflow.models.Pipeline.create_execution_params")
    def test_can_create_with_params(self, mock_ex, mock_data):
        pipeline = mixer.blend(Pipeline)
        params, data, executions = pipeline.create_params({"1": "2"}, "data", "executions", "10")
        self.assertEqual(params, {"1": "2"})
        self.assertEqual(data, mock_data.return_value)
        self.assertEqual(executions, mock_ex.return_value)
        mock_data.assert_called_with("data", "10", {"1": "2"})
        mock_ex.assert_called_with("executions", "10", {"1": "2"})



class DataPramCreationTests(TestCase):

    @patch("django_nextflow.models.Data.full_path", new_callable=PropertyMock)
    def test_can_create_params_from_data(self, mock_path):
        mock_path.side_effect = ["/path1", "/path2"]
        pipeline = mixer.blend(Pipeline)
        data1 = mixer.blend(Data, id=1)
        data2 = mixer.blend(Data, id=2)
        mixer.blend(Data, id=3)
        params = {}
        data = pipeline.create_data_params({"A": 1, "B": 2}, "10", params)
        self.assertEqual(params, {"A": "/path1", "B": "/path2"})
        self.assertEqual(data, [data1, data2])
    

    @patch("django_nextflow.models.Data.full_path", new_callable=PropertyMock)
    def test_can_create_params_from_data_when_missing(self, mock_path):
        mock_path.side_effect = ["/path1", "/path2"]
        pipeline = mixer.blend(Pipeline)
        data1 = mixer.blend(Data, id=1)
        mixer.blend(Data, id=3)
        params = {}
        data = pipeline.create_data_params({"A": 1, "B": 2}, "10", params)
        self.assertEqual(params, {"A": "/path1"})
        self.assertEqual(data, [data1])
    

    @override_settings(NEXTFLOW_DATA_ROOT="/data")
    @patch("django_nextflow.models.Data.full_path", new_callable=PropertyMock)
    @patch("os.symlink")
    def test_can_handle_list_of_data_params(self, mock_link, mock_path):
        mock_path.side_effect = ["/path1", "/path2", "/path4"]
        pipeline = mixer.blend(Pipeline)
        data1 = mixer.blend(Data, id=1, filename="file1")
        data2 = mixer.blend(Data, id=2, filename="file2")
        data4 = mixer.blend(Data, id=4, filename="file4")
        params = {}
        data = pipeline.create_data_params({"A": 1, "B": [2, 3, 4]}, "10", params)
        self.assertEqual(params, {"A": "/path1", "B": '"{file2,file4}"'})
        self.assertEqual(data, [data1, data2, data4])
        self.assertEqual(mock_link.call_count, 2)
        mock_link.assert_any_call("/path2", os.path.join("/data", "10", "file2"))
        mock_link.assert_any_call("/path4", os.path.join("/data", "10", "file4"))
    


class ExecutionParamCreationTests(TestCase):

    @override_settings(NEXTFLOW_DATA_ROOT="/data")
    @patch("os.makedirs")
    @patch("os.mkdir")
    @patch("django_nextflow.models.Data.full_path", new_callable=PropertyMock)
    @patch("os.symlink")
    def test_can_create_params_from_executions(self, mock_sym, mock_path, mock_mk, mock_mks):
        pipeline = mixer.blend(Pipeline)
        ex1 = mixer.blend(Execution, id=1)
        procex1 = mixer.blend(ProcessExecution, process_name="PROC1", execution=ex1)
        mixer.blend(Data, filename="file1.txt", upstream_process_execution=procex1)
        mixer.blend(Data, filename="file2.txt", upstream_process_execution=procex1)
        procex2 = mixer.blend(ProcessExecution, process_name="PROC2", execution=ex1)
        mixer.blend(Data, filename="file3.txt", upstream_process_execution=procex2)
        mixer.blend(Data, filename="file4.txt", upstream_process_execution=procex2)
        ex2 = mixer.blend(Execution, id=2)
        procex3 = mixer.blend(ProcessExecution, process_name="PROC3", execution=ex2)
        mixer.blend(Data, filename="file5.txt", upstream_process_execution=procex3)
        mixer.blend(Data, filename="file6.txt", upstream_process_execution=procex3)
        d7 = mixer.blend(Data, filename="file7.txt")
        d7.downstream_executions.add(ex2)
        mock_path.return_value = "path"
        params = {}
        executions = pipeline.create_execution_params({"A": 1, "B": 2, "C": 10}, "10", params)
        self.assertEqual(params, {
            "A": os.path.join("/data", "10", "executions", "A"),
            "B": os.path.join("/data", "10", "executions", "B"),
        })
        mock_mks.assert_any_call(os.path.join("/data", "10", "executions", "A"), exist_ok=True)
        mock_mks.assert_any_call(os.path.join("/data", "10", "executions", "B"), exist_ok=True)
        mock_mk.assert_any_call(os.path.join("/data", "10", "executions", "A", "PROC1"))
        mock_mk.assert_any_call(os.path.join("/data", "10", "executions", "A", "PROC2"))
        mock_mk.assert_any_call(os.path.join("/data", "10", "executions", "B", "PROC3"))
        mock_sym.assert_any_call("path", os.path.join("/data", "10", "executions", "A", "PROC1", "file1.txt"))
        mock_sym.assert_any_call("path", os.path.join("/data", "10", "executions", "A", "PROC1", "file2.txt"))
        mock_sym.assert_any_call("path", os.path.join("/data", "10", "executions", "A", "PROC2", "file3.txt"))
        mock_sym.assert_any_call("path", os.path.join("/data", "10", "executions", "A", "PROC2", "file4.txt"))
        mock_sym.assert_any_call("path", os.path.join("/data", "10", "executions", "B", "PROC3", "file5.txt"))
        mock_sym.assert_any_call("path", os.path.join("/data", "10", "executions", "B", "PROC3", "file6.txt"))
        mock_sym.assert_any_call("path", os.path.join("/data", "10", "executions", "B", "file7.txt"))
        self.assertEqual(executions, [ex1, ex2])



class PipelineRunningTests(TestCase):

    @override_settings(NEXTFLOW_DATA_ROOT="/data")
    @patch("django_nextflow.models.Pipeline.create_pipeline")
    @patch("django_nextflow.models.Execution.prepare_directory")
    @patch("django_nextflow.models.Pipeline.create_params")
    @patch("django_nextflow.models.Execution.create_from_object")
    @patch("django_nextflow.models.Execution.remove_symlinks")
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
        mocks[-3].return_value = {1: 2, 3: 4}, [mixer.blend(Data), mixer.blend(Data)], [mixer.blend(Execution), mixer.blend(Execution)]
        mocks[-4].return_value = execution
        mocks[-6].side_effect = [procex1, procex2]
        pipeline = mixer.blend(Pipeline)
        pipeline.run(execution_id=10, params={"param1": "X", "param2": "Y"}, data_params={"param3": 100}, execution_params={"param4": 50}, profile=["X"])
        mocks[-1].assert_called_with()
        mocks[-2].assert_called_with(execution_id=10)
        mocks[-3].assert_called_with({"param1": "X", "param2": "Y"}, {"param3": 100}, {"param4": 50}, "1000")
        nf_pipeline.run.assert_called_with(location="/data/1000", params={1: 2, 3: 4}, profile=["X"])
        mocks[-4].assert_called_with(nf_execution, "1000", pipeline)
        mocks[-5].assert_called_with()
        self.assertEqual(set(execution.upstream_data.all()), set(Data.objects.all()))
        mocks[-6].assert_any_call(nf_procex1, execution)
        self.assertEqual(mocks[-7].call_count, 2)
        self.assertEqual(mocks[-8].call_count, 2)



class PipelineRunningAndUpdatingTests(TestCase):

    @override_settings(NEXTFLOW_DATA_ROOT="/data")
    @patch("django_nextflow.models.Pipeline.create_pipeline")
    @patch("django_nextflow.models.Execution.prepare_directory")
    @patch("django_nextflow.models.Pipeline.create_params")
    @patch("django_nextflow.models.Execution.create_from_object")
    @patch("django_nextflow.models.Execution.remove_symlinks")
    @patch("django_nextflow.models.ProcessExecution.create_from_object")
    @patch("django_nextflow.models.ProcessExecution.create_downstream_data_objects")
    @patch("django_nextflow.models.ProcessExecution.create_upstream_data_objects")
    def test_can_run_and_update(self, *mocks):
        nf_pipeline = Mock()
        mocks[-1].return_value = nf_pipeline
        mocks[-2].return_value = "1000"
        mocks[-3].return_value = {1: 2, 3: 4}, [mixer.blend(Data), mixer.blend(Data)], [mixer.blend(Execution), mixer.blend(Execution)]
        pipeline = mixer.blend(Pipeline)
        execution1, execution2 = Mock(), Mock()
        procex1_1, procex1_2, procex2_1, procex2_2 = Mock(), Mock(), Mock(), Mock()
        execution1.process_executions = [procex1_1, procex1_2]
        execution2.process_executions = [procex2_1, procex2_2]
        execution = mixer.blend(Execution)
        procex1 = mixer.blend(ProcessExecution, execution=execution)
        procex2 = mixer.blend(ProcessExecution, execution=execution)
        mocks[-4].return_value = execution
        nf_pipeline.run_and_poll.return_value = [execution1, execution2]
        pipeline.run_and_update(execution_id=10, params={"param1": "X", "param2": "Y"}, data_params={"param3": 100}, execution_params={"param4": 50}, profile=["X"])
        mocks[-1].assert_called_with()
        mocks[-2].assert_called_with(execution_id=10)
        mocks[-3].assert_called_with({"param1": "X", "param2": "Y"}, {"param3": 100}, {"param4": 50}, "1000")
        nf_pipeline.run_and_poll.assert_called_with(location="/data/1000", params={1: 2, 3: 4}, profile=["X"])
        mocks[-4].assert_any_call(execution1, "1000", pipeline)
        mocks[-4].assert_any_call(execution2, "1000", pipeline)
        self.assertEqual(set(execution.upstream_data.all()), set(Data.objects.all()))
        mocks[-6].assert_any_call(procex1_1, execution)
        mocks[-6].assert_any_call(procex1_2, execution)
        mocks[-6].assert_any_call(procex2_1, execution)
        mocks[-6].assert_any_call(procex2_2, execution)