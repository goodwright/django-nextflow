import os
import shutil
from django.test import TestCase
from django.test.utils import override_settings
from django_nextflow.models import Data

class PdbToMmcifTests(TestCase):

    def setUp(self):
        self.data_dir = os.path.join("tests", "data")
        self.upload_dir = os.path.join("tests", "uploads")
        if os.path.exists(self.data_dir): shutil.rmtree(self.data_dir)
        if os.path.exists(self.upload_dir): shutil.rmtree(self.upload_dir)
        os.mkdir(self.data_dir)
        os.mkdir(self.upload_dir)
    

    def tearDown(self):
        shutil.rmtree(self.data_dir)
        shutil.rmtree(self.upload_dir)


    def files_path(self, path):
        return os.path.join("tests", "files", path)


    @override_settings(NEXTFLOW_PIPELINE_ROOT=os.path.join("tests", "pipelines"))
    @override_settings(NEXTFLOW_DATA_ROOT=os.path.join("tests", "data"))
    @override_settings(NEXTFLOW_UPLOADS_ROOT=os.path.join("tests", "uploads"))
    @override_settings(NEXTFLOW_PUBLISH_DIR=os.path.join("results"))
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