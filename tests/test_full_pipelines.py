import os
import time
import shutil
from django.test import TestCase
from django.test.utils import override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django_nextflow.models import Data, Pipeline, ProcessExecution

@override_settings(NEXTFLOW_PIPELINE_ROOT=os.path.join("tests", "pipeline"))
@override_settings(NEXTFLOW_DATA_ROOT=os.path.join("tests", "data"))
@override_settings(NEXTFLOW_UPLOADS_ROOT=os.path.join("tests", "uploads"))
@override_settings(NEXTFLOW_PUBLISH_DIR=os.path.join("results"))
class PipelineTest(TestCase):

    def setUp(self):
        self.data_dir = os.path.join("tests", "data")
        self.upload_dir = os.path.join("tests", "uploads")
        self.pipe_dir = os.path.join("tests", "pipeline")
        self.files_dir = os.path.join("tests", "files")
        if os.path.exists(self.data_dir): shutil.rmtree(self.data_dir)
        if os.path.exists(self.upload_dir): shutil.rmtree(self.upload_dir)
        os.mkdir(self.data_dir)
        os.mkdir(self.upload_dir)
    

    def tearDown(self):
        shutil.rmtree(self.data_dir)
        shutil.rmtree(self.upload_dir)


    def files_path(self, path):
        return os.path.join(self.files_dir, path)


class PdbToMmcifTests(PipelineTest):

    def test_can_run_pipeline(self):
        # Upload PDB file
        pdb_data = Data.create_from_path(self.files_path("1lol.pdb"))
        self.assertEqual(pdb_data.filename, "1lol.pdb")
        self.assertEqual(pdb_data.size, 322623)
        self.assertIsNone(pdb_data.process_execution)
        self.assertEqual(
            pdb_data.full_path,
            os.path.abspath(os.path.join(self.upload_dir, str(pdb_data.id), "1lol.pdb"))
        )
        self.assertTrue(os.path.exists(pdb_data.full_path))

        # Create and run pipeline object
        pipeline = Pipeline.objects.create(
            name="Convert to mmCIF",
            path=os.path.join("subworkflows", "pdb2mmcif.nf")
        )
        start = time.time()
        execution = pipeline.run(data_params={"pdb": pdb_data.id})

        # Execution is fine
        self.assertIn(str(execution.id), os.listdir(self.data_dir))
        self.assertEqual(execution.pipeline, pipeline)
        self.assertIn("_", execution.identifier)
        self.assertIn("N E X T F L O W", execution.stdout)
        self.assertFalse(execution.stderr)
        self.assertEqual(execution.exit_code, 0)
        command = "nextflow run " +\
            os.path.abspath(os.path.join(self.pipe_dir,  pipeline.path)) +\
            " --pdb=" +\
            os.path.abspath(os.path.join(self.upload_dir, str(pdb_data.id), "1lol.pdb\n"))
        self.assertEqual(execution.command, command)
        self.assertLess(abs(execution.started - start), 2)
        self.assertLess(
            abs(execution.finished - (execution.started + execution.duration)), 2
        )

        # Process execution is fine
        self.assertEqual(execution.process_executions.count(), 1)
        process_execution = execution.process_executions.first()
        self.assertEqual(process_execution.execution, execution)
        self.assertEqual(process_execution.name, "PDB_TO_MMCIF")
        self.assertEqual(process_execution.process_name, "PDB_TO_MMCIF")
        self.assertEqual(process_execution.status, "COMPLETED")
        self.assertEqual(
            process_execution.stdout,
            "CRYSTAL STRUCTURE OF OROTIDINE MONOPHOSPHATE DECARBOXYLASE COMPLEX WITH XMP\n"
        )
        self.assertEqual(len(process_execution.identifier), 9)

        # Data output is fine
        self.assertEqual(process_execution.data.count(), 1)
        data = process_execution.data.first()
        self.assertEqual(data.filename, "1lol.cif")
        self.assertGreater(data.size, 200_000)
        self.assertEqual(data.process_execution, process_execution)
        self.assertTrue(os.path.exists(data.full_path))
    

    def test_can_get_mmtf_with_param(self):
        # Upload PDB file
        pdb_data = Data.create_from_path(self.files_path("1lol.pdb"))
        self.assertEqual(pdb_data.filename, "1lol.pdb")
        self.assertEqual(pdb_data.size, 322623)
        self.assertIsNone(pdb_data.process_execution)
        self.assertEqual(
            pdb_data.full_path,
            os.path.abspath(os.path.join(self.upload_dir, str(pdb_data.id), "1lol.pdb"))
        )
        self.assertTrue(os.path.exists(pdb_data.full_path))

        # Create and run pipeline object
        pipeline = Pipeline.objects.create(
            name="Convert to mmCIF",
            path=os.path.join("subworkflows", "pdb2mmcif.nf")
        )
        start = time.time()
        execution = pipeline.run(params={"print_title": "no"}, data_params={"pdb": pdb_data.id})

        # Execution is fine
        self.assertIn(str(execution.id), os.listdir(self.data_dir))
        self.assertEqual(execution.pipeline, pipeline)
        self.assertIn("_", execution.identifier)
        self.assertIn("N E X T F L O W", execution.stdout)
        self.assertFalse(execution.stderr)
        self.assertEqual(execution.exit_code, 0)
        command = "nextflow run " +\
            os.path.abspath(os.path.join(self.pipe_dir,  pipeline.path)) +\
            " --print_title=no --pdb=" +\
            os.path.abspath(os.path.join(self.upload_dir, str(pdb_data.id), "1lol.pdb\n"))
        self.assertEqual(execution.command, command)
        self.assertLess(abs(execution.started - start), 2)
        self.assertLess(
            abs(execution.finished - (execution.started + execution.duration)), 2
        )

        # Process execution is fine
        self.assertEqual(execution.process_executions.count(), 1)
        process_execution = execution.process_executions.first()
        self.assertEqual(process_execution.execution, execution)
        self.assertEqual(process_execution.name, "PDB_TO_MMCIF")
        self.assertEqual(process_execution.process_name, "PDB_TO_MMCIF")
        self.assertEqual(process_execution.status, "COMPLETED")
        self.assertEqual(process_execution.stdout, "-")
        self.assertEqual(len(process_execution.identifier), 9)

        # Data output is fine
        self.assertEqual(process_execution.data.count(), 1)
        data = process_execution.data.first()
        self.assertEqual(data.filename, "1lol.cif")
        self.assertGreater(data.size, 200_000)
        self.assertEqual(data.process_execution, process_execution)
        self.assertTrue(os.path.exists(data.full_path))
    

    def test_can_get_pipeline_input_schema(self):
        pipeline = Pipeline.objects.create(
            name="Convert to mmCIF",
            path=os.path.join("subworkflows", "pdb2mmcif.nf"),
            schema_path=os.path.join("subworkflows", "pdb2mmcif.json"),
        )
        self.assertEqual(pipeline.input_schema, {
            "file_options": {
                "title": "File options",
                "type": "object",
                "fa_icon": "fas fa-terminal",
                "description": "File options.",
                "properties": {
                    "input": {
                        "type": "string",
                        "format": "file-path",
                        "mimetype": "text/plain",
                        "pattern": "^\\S+\\.pdb$",
                        "description": "Path to PDB file.",
                        "help_text": "Needs to be standard format.",
                        "fa_icon": "fas fa-file-csv"
                    }
                }
            },
            "display_options": {
                "title": "Display options",
                "type": "object",
                "description": "Options for what to print",
                "default": "",
                "properties": {
                    "print_title": {
                        "type": "boolean",
                        "fa_icon": "fas fa-barcode",
                        "description": "Print PDB title."
                    }
                },
                "fa_icon": "fas fa-barcode"
            }
        })



class MmcifReportTests(PipelineTest):

    def test_can_run_pipeline(self):
        # Upload MMCIF file
        with open(self.files_path("1lol.cif")) as f:
            upload = SimpleUploadedFile("1lol.cif", f.read().encode(), content_type="text/plain")
        cif_data = Data.create_from_upload(upload)
        self.assertEqual(cif_data.filename, "1lol.cif")
        self.assertEqual(cif_data.size, 383351)
        self.assertIsNone(cif_data.process_execution)
        self.assertEqual(
            cif_data.full_path,
            os.path.abspath(os.path.join(self.upload_dir, str(cif_data.id), "1lol.cif"))
        )
        self.assertTrue(os.path.exists(cif_data.full_path))

        # Create and run pipeline object
        pipeline = Pipeline.objects.create(
            name="Report on mmCIF",
            path=os.path.join("subworkflows", "mmcifreport.nf")
        )
        start = time.time()
        execution = pipeline.run(data_params={"mmcif": cif_data.id})

        # Execution is fine
        self.assertIn(str(execution.id), os.listdir(self.data_dir))
        self.assertEqual(execution.pipeline, pipeline)
        self.assertIn("_", execution.identifier)
        self.assertIn("N E X T F L O W", execution.stdout)
        self.assertFalse(execution.stderr)
        self.assertEqual(execution.exit_code, 0)
        command = "nextflow run " +\
            os.path.abspath(os.path.join(self.pipe_dir,  pipeline.path)) +\
            " --mmcif=" +\
            os.path.abspath(os.path.join(self.upload_dir, str(cif_data.id), "1lol.cif\n"))
        self.assertEqual(execution.command, command)
        self.assertLess(abs(execution.started - start), 2)
        self.assertLess(
            abs(execution.finished - (execution.started + execution.duration)), 2
        )

        # Process execution is fine
        self.assertEqual(execution.process_executions.count(), 1)
        process_execution = execution.process_executions.first()
        self.assertEqual(process_execution.execution, execution)
        self.assertEqual(process_execution.name, "MMCIF_REPORT")
        self.assertEqual(process_execution.process_name, "MMCIF_REPORT")
        self.assertEqual(process_execution.status, "COMPLETED")
        self.assertEqual(process_execution.stdout, "Saved!\n")
        self.assertEqual(len(process_execution.identifier), 9)

        # Data output is fine
        self.assertEqual(process_execution.data.count(), 1)
        data = process_execution.data.first()
        self.assertEqual(data.filename, "report.txt")
        self.assertGreater(data.size, 50)
        self.assertEqual(data.process_execution, process_execution)
        self.assertTrue(os.path.exists(data.full_path))



class MmcifToChainsTests(PipelineTest):

    def test_can_run_pipeline(self):
        # Upload MMCIF file
        with open(self.files_path("1lol.cif")) as f:
            upload = SimpleUploadedFile("1lol.cif", f.read().encode(), content_type="text/plain")
        cif_data = Data.create_from_upload(upload)
        self.assertEqual(cif_data.filename, "1lol.cif")
        self.assertEqual(cif_data.size, 383351)
        self.assertIsNone(cif_data.process_execution)
        self.assertEqual(
            cif_data.full_path,
            os.path.abspath(os.path.join(self.upload_dir, str(cif_data.id), "1lol.cif"))
        )
        self.assertTrue(os.path.exists(cif_data.full_path))

        # Create and run pipeline object
        pipeline = Pipeline.objects.create(
            name="Split mmCIF",
            path=os.path.join("subworkflows", "mmcif2chains.nf")
        )
        start = time.time()
        execution = pipeline.run(data_params={"mmcif": cif_data.id})

        # Execution is fine
        self.assertIn(str(execution.id), os.listdir(self.data_dir))
        self.assertEqual(execution.pipeline, pipeline)
        self.assertIn("_", execution.identifier)
        self.assertIn("N E X T F L O W", execution.stdout)
        self.assertFalse(execution.stderr)
        self.assertEqual(execution.exit_code, 0)
        command = "nextflow run " +\
            os.path.abspath(os.path.join(self.pipe_dir,  pipeline.path)) +\
            " --mmcif=" +\
            os.path.abspath(os.path.join(self.upload_dir, str(cif_data.id), "1lol.cif\n"))
        self.assertEqual(execution.command, command)
        self.assertLess(abs(execution.started - start), 2)
        self.assertLess(
            abs(execution.finished - (execution.started + execution.duration)), 2
        )

        # Process execution is fine
        self.assertEqual(execution.process_executions.count(), 1)
        process_execution = execution.process_executions.first()
        self.assertEqual(process_execution.execution, execution)
        self.assertEqual(process_execution.name, "MMCIF_TO_CHAINS")
        self.assertEqual(process_execution.process_name, "MMCIF_TO_CHAINS")
        self.assertEqual(process_execution.status, "COMPLETED")
        self.assertEqual(process_execution.stdout, "<Chain A (204 residues)>\n<Chain B (214 residues)>\n")
        self.assertEqual(len(process_execution.identifier), 9)

        # Data outputs are fine
        self.assertEqual(process_execution.data.count(), 2)
        for data in process_execution.data.all():
            self.assertIn(data.filename, ["chain_A.cif", "chain_B.cif"])
            self.assertGreater(data.size, 100_000)
            self.assertEqual(data.process_execution, process_execution)
            self.assertTrue(os.path.exists(data.full_path))



class ConvertAndReportTests(PipelineTest):

    def test_can_run_pipeline(self):
        # Upload PDB file
        pdb_data = Data.create_from_path(self.files_path("1lol.pdb"))
        self.assertEqual(pdb_data.filename, "1lol.pdb")
        self.assertEqual(pdb_data.size, 322623)
        self.assertIsNone(pdb_data.process_execution)
        self.assertEqual(
            pdb_data.full_path,
            os.path.abspath(os.path.join(self.upload_dir, str(pdb_data.id), "1lol.pdb"))
        )
        self.assertTrue(os.path.exists(pdb_data.full_path))

        # Create and run pipeline object
        pipeline = Pipeline.objects.create(
            name="Convert and report",
            path=os.path.join("workflows", "convertreport.nf")
        )
        start = time.time()
        execution = pipeline.run(data_params={"pdb": pdb_data.id})

        # Execution is fine
        self.assertIn(str(execution.id), os.listdir(self.data_dir))
        self.assertEqual(execution.pipeline, pipeline)
        self.assertIn("_", execution.identifier)
        self.assertIn("N E X T F L O W", execution.stdout)
        self.assertFalse(execution.stderr)
        self.assertEqual(execution.exit_code, 0)
        command = "nextflow run " +\
            os.path.abspath(os.path.join(self.pipe_dir,  pipeline.path)) +\
            " --pdb=" +\
            os.path.abspath(os.path.join(self.upload_dir, str(pdb_data.id), "1lol.pdb\n"))
        self.assertEqual(execution.command, command)
        self.assertLess(abs(execution.started - start), 2)
        self.assertLess(
            abs(execution.finished - (execution.started + execution.duration)), 2
        )
        self.assertEqual(execution.process_executions.count(), 2)

        # Process execution 1 is fine
        process_execution = execution.process_executions.first()
        self.assertEqual(process_execution.execution, execution)
        self.assertEqual(process_execution.name, "PDB_TO_MMCIF")
        self.assertEqual(process_execution.process_name, "PDB_TO_MMCIF")
        self.assertEqual(process_execution.status, "COMPLETED")
        self.assertEqual(
            process_execution.stdout,
            "CRYSTAL STRUCTURE OF OROTIDINE MONOPHOSPHATE DECARBOXYLASE COMPLEX WITH XMP\n"
        )
        self.assertEqual(len(process_execution.identifier), 9)

        # Data output 1 is fine
        self.assertEqual(process_execution.data.count(), 1)
        data = process_execution.data.first()
        self.assertEqual(data.filename, "1lol.cif")
        self.assertGreater(data.size, 200_000)
        self.assertEqual(data.process_execution, process_execution)
        self.assertTrue(os.path.exists(data.full_path))

        # Process execution 2 is fine
        process_execution = execution.process_executions.last()
        self.assertEqual(process_execution.execution, execution)
        self.assertEqual(process_execution.name, "MMCIF_REPORT")
        self.assertEqual(process_execution.process_name, "MMCIF_REPORT")
        self.assertEqual(process_execution.status, "COMPLETED")
        self.assertEqual(process_execution.stdout, "Saved!\n")
        self.assertEqual(len(process_execution.identifier), 9)

        # Data output 2 is fine
        self.assertEqual(process_execution.data.count(), 1)
        data = process_execution.data.first()
        self.assertEqual(data.filename, "report.txt")
        self.assertGreater(data.size, 20)
        self.assertEqual(data.process_execution, process_execution)
        self.assertTrue(os.path.exists(data.full_path))



class SplitAndReportTests(PipelineTest):

    def test_basic_pipeline(self):
        # Upload MMCIF file
        with open(self.files_path("1lol.cif")) as f:
            upload = SimpleUploadedFile("1lol.cif", f.read().encode(), content_type="text/plain")
        cif_data = Data.create_from_upload(upload)
        self.assertEqual(cif_data.filename, "1lol.cif")
        self.assertEqual(cif_data.size, 383351)
        self.assertIsNone(cif_data.process_execution)
        self.assertEqual(
            cif_data.full_path,
            os.path.abspath(os.path.join(self.upload_dir, str(cif_data.id), "1lol.cif"))
        )
        self.assertTrue(os.path.exists(cif_data.full_path))

        # Create and run pipeline object
        pipeline = Pipeline.objects.create(
            name="Split and Report",
            path=os.path.join("workflows", "splitreport.nf")
        )
        start = time.time()
        execution = pipeline.run(data_params={"mmcif": cif_data.id})

        # Execution is fine
        self.assertIn(str(execution.id), os.listdir(self.data_dir))
        self.assertEqual(execution.pipeline, pipeline)
        self.assertIn("_", execution.identifier)
        self.assertIn("N E X T F L O W", execution.stdout)
        self.assertFalse(execution.stderr)
        self.assertEqual(execution.exit_code, 0)
        command = "nextflow run " +\
            os.path.abspath(os.path.join(self.pipe_dir,  pipeline.path)) +\
            " --mmcif=" +\
            os.path.abspath(os.path.join(self.upload_dir, str(cif_data.id), "1lol.cif\n"))
        self.assertEqual(execution.command, command)
        self.assertLess(abs(execution.started - start), 2)
        self.assertLess(
            abs(execution.finished - (execution.started + execution.duration)), 2
        )
        self.assertEqual(execution.process_executions.count(), 3)

        # Process execution 1 is fine
        process_execution = execution.process_executions.first()
        self.assertEqual(process_execution.execution, execution)
        self.assertEqual(process_execution.name, "MMCIF_TO_CHAINS")
        self.assertEqual(process_execution.process_name, "MMCIF_TO_CHAINS")
        self.assertEqual(process_execution.status, "COMPLETED")
        self.assertEqual(process_execution.stdout, "<Chain A (204 residues)>\n<Chain B (214 residues)>\n")
        self.assertEqual(len(process_execution.identifier), 9)

        # Data output 1/2 is fine
        self.assertEqual(process_execution.data.count(), 2)
        for data in process_execution.data.all():
            self.assertIn(data.filename, ["chain_A.cif", "chain_B.cif"])
            self.assertGreater(data.size, 100_000)
            self.assertEqual(data.process_execution, process_execution)
            self.assertTrue(os.path.exists(data.full_path))
        

        # Process execution 2 is fine
        process_execution = execution.process_executions.all()[1]
        self.assertEqual(process_execution.execution, execution)
        self.assertIn(process_execution.name, ["MMCIF_REPORT (1)", "MMCIF_REPORT (2)"])
        self.assertEqual(process_execution.process_name, "MMCIF_REPORT")
        self.assertEqual(process_execution.status, "COMPLETED")
        self.assertEqual(process_execution.stdout, "Saved!\n")
        self.assertEqual(len(process_execution.identifier), 9)

        # Data output 3 is fine
        self.assertEqual(process_execution.data.count(), 1)
        data = process_execution.data.first()
        self.assertEqual(data.filename, "report.txt")
        self.assertGreater(data.size, 20)
        self.assertEqual(data.process_execution, process_execution)
        self.assertTrue(os.path.exists(data.full_path))

        # Process execution 3 is fine
        process_execution = execution.process_executions.last()
        self.assertEqual(process_execution.execution, execution)
        self.assertIn(process_execution.name, ["MMCIF_REPORT (1)", "MMCIF_REPORT (2)"])
        self.assertEqual(process_execution.process_name, "MMCIF_REPORT")
        self.assertEqual(process_execution.status, "COMPLETED")
        self.assertEqual(process_execution.stdout, "Saved!\n")
        self.assertEqual(len(process_execution.identifier), 9)

        # Data output 4 is fine
        self.assertEqual(process_execution.data.count(), 1)
        data = process_execution.data.first()
        self.assertEqual(data.filename, "report.txt")
        self.assertGreater(data.size, 20)
        self.assertEqual(data.process_execution, process_execution)
        self.assertTrue(os.path.exists(data.full_path))



class FullWorkflowTests(PipelineTest):

    def test_basic_pipeline(self):
        # Upload PDB file
        pdb_data = Data.create_from_path(self.files_path("1lol.pdb"))
        self.assertEqual(pdb_data.filename, "1lol.pdb")
        self.assertEqual(pdb_data.size, 322623)
        self.assertIsNone(pdb_data.process_execution)
        self.assertEqual(
            pdb_data.full_path,
            os.path.abspath(os.path.join(self.upload_dir, str(pdb_data.id), "1lol.pdb"))
        )
        self.assertTrue(os.path.exists(pdb_data.full_path))

        # Create and run pipeline object
        pipeline = Pipeline.objects.create(
            name="Analyse PDB",
            path=os.path.join("main.nf")
        )
        start = time.time()
        execution = pipeline.run(data_params={"pdb": pdb_data.id})

        # Execution is fine
        self.assertIn(str(execution.id), os.listdir(self.data_dir))
        self.assertEqual(execution.pipeline, pipeline)
        self.assertIn("_", execution.identifier)
        self.assertIn("N E X T F L O W", execution.stdout)
        self.assertFalse(execution.stderr)
        self.assertEqual(execution.exit_code, 0)
        command = "nextflow run " +\
            os.path.abspath(os.path.join(self.pipe_dir,  pipeline.path)) +\
            " --pdb=" +\
            os.path.abspath(os.path.join(self.upload_dir, str(pdb_data.id), "1lol.pdb\n"))
        self.assertEqual(execution.command, command)
        self.assertLess(abs(execution.started - start), 2)
        self.assertLess(
            abs(execution.finished - (execution.started + execution.duration)), 2
        )

        # The correct number of processes and data were created
        self.assertEqual(ProcessExecution.objects.count(), 5)
        self.assertEqual(Data.objects.count(), 7)

        # Process executions are ok
        for process_execution in execution.process_executions.all():
            self.assertEqual(process_execution.execution, execution)
            self.assertIn(process_execution.name, [
                "CONVERT_REPORT:PDB_TO_MMCIF",
                "CONVERT_REPORT:MMCIF_REPORT",
                "SPLIT_REPORT:MMCIF_TO_CHAINS",
                "SPLIT_REPORT:MMCIF_REPORT (1)",
                "SPLIT_REPORT:MMCIF_REPORT (2)",
            ])
            self.assertIn(process_execution.process_name, [
                "CONVERT_REPORT:PDB_TO_MMCIF",
                "CONVERT_REPORT:MMCIF_REPORT",
                "SPLIT_REPORT:MMCIF_TO_CHAINS",
                "SPLIT_REPORT:MMCIF_REPORT"
            ])
            self.assertEqual(process_execution.status, "COMPLETED")
            self.assertEqual(len(process_execution.identifier), 9)
        
            # Data objects are ok
            for data in process_execution.data.all():
                self.assertEqual(data.process_execution, process_execution)
                self.assertIn(data.filename, [
                    "report.txt", "1lol.cif", "chain_A.cif", "chain_B.cif"
                ])
                self.assertGreater(data.size, 20)
                self.assertTrue(os.path.exists(data.full_path))