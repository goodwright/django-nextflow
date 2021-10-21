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



class ProcessExecution(models.Model):

    name = models.CharField(max_length=200)
    process_name = models.CharField(max_length=200)
    identifier = models.CharField(max_length=200)
    stdout = models.TextField()
    stderr = models.TextField()
    execution = models.ForeignKey(Execution, related_name="process_executions")

    def __str__(self):
        return self.name



class Data:

    filename = models.CharField(max_length=200)
    size = models.IntegerField()
    process_execution = models.ForeignKey(ProcessExecution, related_name="data")

    def __str__(self):
        return self.filename
