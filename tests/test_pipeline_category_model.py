from django.test import TestCase
from mixer.backend.django import mixer
from django_nextflow.models import PipelineCategory

class PipelineCategoryCreationTests(TestCase):

    def test_pipeline_category_creation(self):
        category = PipelineCategory.objects.create(
            name="Good Pipelines",
            description="Pipelines which are useful",
        )
        self.assertEqual(str(category), "Good Pipelines")
        self.assertEqual(category.order, 1)
        self.assertEqual(list(category.pipelines.all()), [])
    

    def test_pipeline_order(self):
        p1 = mixer.blend(PipelineCategory, order=3)
        p2 = mixer.blend(PipelineCategory, order=1)
        p3 = mixer.blend(PipelineCategory, order=2)
        self.assertEqual(list(PipelineCategory.objects.all()), [p2, p3, p1])