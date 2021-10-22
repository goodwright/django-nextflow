import os
from django.db import models
from django.conf import settings

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
    pipeline = models.ForeignKey(Pipeline, related_name="executions", on_delete=models.CASCADE)

    def __str__(self):
        return self.identifier



class ProcessExecution(models.Model):

    name = models.CharField(max_length=200)
    process_name = models.CharField(max_length=200)
    identifier = models.CharField(max_length=200)
    status = models.CharField(max_length=20)
    stdout = models.TextField()
    stderr = models.TextField()
    execution = models.ForeignKey(Execution, related_name="process_executions", on_delete=models.CASCADE)

    def __str__(self):
        return self.name



class Data(models.Model):

    filename = models.CharField(max_length=200)
    path = models.CharField(max_length=200)
    size = models.IntegerField()
    process_execution = models.ForeignKey(ProcessExecution, related_name="data", on_delete=models.CASCADE)

    def __str__(self):
        return self.filename
    
    @property
    def full_path(self):
        """Gets the data's full path on the filesystem."""

        if hasattr(settings, "NEXTFLOW_DATA_ROOT"):
            path = self.path[1:] if self.path[0] == os.path.sep else self.path
            return os.path.join(settings.NEXTFLOW_DATA_ROOT, path, self.filename)
        else:
            return os.path.join(self.path, self.filename)
