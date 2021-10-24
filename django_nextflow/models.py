import os
from django_nextflow.utils import parse_datetime, parse_duration
import nextflow
from random import randint
from django.db import models
from django.conf import settings
from .utils import parse_datetime, parse_duration

class Pipeline(models.Model):

    name = models.CharField(max_length=200)
    path = models.CharField(max_length=300)
    schema_path = models.CharField(max_length=300)
    config_path = models.CharField(max_length=300)

    def __str__(self):
        return self.name
    
    def run(self, basic_params=None, data_params=None):
        pipeline = nextflow.Pipeline(
            path=os.path.join(settings.NEXTFLOW_PIPELINE_ROOT, self.path),
            config=os.path.join(settings.NEXTFLOW_PIPELINE_ROOT, self.config_path) if self.config_path else None,
        )
        digits_length = 18
        id = randint(10 ** (digits_length - 1), 10 ** digits_length)

        os.mkdir(os.path.join(settings.NEXTFLOW_DATA_ROOT, str(id)))

        params = {**(basic_params if basic_params else {})}
        execution = pipeline.run(
            location=os.path.join(settings.NEXTFLOW_DATA_ROOT, str(id)),
            params=params
        )

        execution_model = Execution.objects.create(
            id=id,
            identifier=execution.id,
            stdout=execution.process.stdout,
            stderr=execution.process.stderr,
            exit_code=execution.process.returncode,
            status=execution.status,
            command=execution.command,
            started=parse_datetime(execution.datetime),
            duration=parse_duration(execution.duration),
            pipeline=self
        )

        for process_execution in execution.process_executions:
            ProcessExecution.objects.create(
                name=process_execution.name,
                process_name=process_execution.process,
                identifier=process_execution.hash,
                status=process_execution.status,
                stdout=process_execution.stdout,
                stderr=process_execution.stderr,
                execution=execution_model
            )

        return execution_model



class Execution(models.Model):

    identifier = models.CharField(max_length=100)
    stdout = models.TextField()
    stderr = models.TextField()
    exit_code = models.IntegerField()
    status = models.CharField(max_length=20)
    command = models.TextField()
    started = models.FloatField()
    duration = models.FloatField()
    pipeline = models.ForeignKey(Pipeline, related_name="executions", on_delete=models.CASCADE)
        

    def __str__(self):
        return self.identifier
    

    @property
    def finished(self):
        """The timestamp for when the execution stopped."""

        return self.started + self.duration
    

    def get_log_text(self):
        """Gets the text of the execution's nextflow log file. This requires a
        disk read, so is its own method."""

        execution = nextflow.Execution(
            location=os.path.join(settings.NEXTFLOW_DATA_ROOT, str(self.id)),
            id=self.identifier
        )
        return execution.log



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
