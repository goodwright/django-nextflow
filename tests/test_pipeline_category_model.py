from django.test import TestCase
from django_nextflow.models import PipelineCategory

class PipelineCategoryCreationTests(TestCase):

    def test_pipeline_category_creation(self):
        category = PipelineCategory.objects.create(
            name="Good Pipelines",
            description="Pipelines which are useful",
        )
        self.assertEqual(str(category), "Good Pipelines")
        self.assertEqual(list(category.pipelines.all()), [])