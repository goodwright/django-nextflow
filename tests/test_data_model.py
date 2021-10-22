import os
from django.test.utils import override_settings
from mixer.backend.django import mixer
from django.test import TestCase
from django_nextflow.models import Data, ProcessExecution

class DataCreationTests(TestCase):

    def test_data_creation(self):
        data = Data.objects.create(
            filename="reads.fastq", size=2048, path="/files",
            process_execution=mixer.blend(ProcessExecution)
        )
        data.full_clean()
        self.assertEqual(str(data), "reads.fastq")



class DataFullPathTests(TestCase):

    def test_can_get_full_path_without_settings(self):
        data = mixer.blend(Data, filename="reads.fastq", path="/files")
        self.assertEqual(data.full_path, f"/files{os.path.sep}reads.fastq")
    

    @override_settings(NEXTFLOW_DATA_ROOT="/home/data")
    def test_can_get_full_path_with_settings(self):
        data = mixer.blend(Data, filename="reads.fastq", path="/files")
        self.assertEqual(data.full_path, f"/home/data{os.path.sep}files{os.path.sep}reads.fastq")