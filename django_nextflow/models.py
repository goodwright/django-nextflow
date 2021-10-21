from django.db import models

class Pipeline(models.Model):

    name = models.CharField(max_length=200)
    path = models.CharField(max_length=300)
    schema_path = models.CharField(max_length=300)
    config_path = models.CharField(max_length=300)

    def __str__(self):
        return self.name



class Execution(models.Model):

    identifier = models.CharField(max_length=100)
    stdout = models.TextField()
    stderr = models.TextField()
    exit_code = models.IntegerField()
    command = models.TextField()
    pipeline = models.ForeignKey(Pipeline, related_name="executions")

    def __str__(self):
        return self.identifier