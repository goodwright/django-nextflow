from django.test import TestCase
from django.test.utils import override_settings
from mixer.backend.django import mixer
from django_nextflow.models import Pipeline

class IntegrationTest(TestCase):

    def setUp(self):
        pass



class Test(IntegrationTest):

    def test(self):
        pipeline = Pipeline.objects.create(
            path="",
            config_path="",
            schema_path=""
        )

