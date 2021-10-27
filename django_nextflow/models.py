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
    

    def create_pipeline(self):
        return nextflow.Pipeline(
            path=os.path.join(settings.NEXTFLOW_PIPELINE_ROOT, self.path),
            config=os.path.join(settings.NEXTFLOW_PIPELINE_ROOT, self.config_path) if self.config_path else None,
        )
    

    def create_params(self, params, data_params):
        params = {**(params if params else {})}
        if data_params:
            for name, data_id in data_params.items():
                data = Data.objects.get(id=data_id)
                path = data.full_path
                params[name] = path
        return params


    def run(self, params=None, data_params=None):
        pipeline = self.create_pipeline()
        id = Execution.prepare_directory()
        params = self.create_params(params or {}, data_params or {})
        execution = pipeline.run(
            location=os.path.join(settings.NEXTFLOW_DATA_ROOT, str(id)),
            params=params
        )
        execution_model = Execution.create_from_object(execution, id, self)
        for process_execution in execution.process_executions:
            process_execution_model = ProcessExecution.create_from_object(
                process_execution, execution_model
            )
            process_execution_model.create_data_objects()
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
    

    @staticmethod
    def prepare_directory():
        digits_length = 18
        id = randint(10 ** (digits_length - 1), 10 ** digits_length)
        os.mkdir(os.path.join(settings.NEXTFLOW_DATA_ROOT, str(id)))
        return id
    

    @staticmethod
    def create_from_object(execution, id, pipeline):
        return Execution.objects.create(
            id=id,
            identifier=execution.id,
            stdout=execution.process.stdout,
            stderr=execution.process.stderr,
            exit_code=execution.process.returncode,
            status=execution.status,
            command=execution.command,
            started=parse_datetime(execution.datetime),
            duration=parse_duration(execution.duration),
            pipeline=pipeline
        )




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
    

    @staticmethod
    def create_from_object(process_execution, execution):
        return ProcessExecution.objects.create(
            name=process_execution.name,
            process_name=process_execution.process,
            identifier=process_execution.hash,
            status=process_execution.status,
            stdout=process_execution.stdout,
            stderr=process_execution.stderr,
            execution=execution
        )
    

    @property
    def publish_dir(self):
        return os.path.join(
            settings.NEXTFLOW_DATA_ROOT,
            str(self.execution.id),
            settings.NEXTFLOW_PUBLISH_DIR,
            self.name
        )
    

    def create_data_objects(self):
        location = self.publish_dir
        try:
            for filename in os.listdir(location):
                Data.objects.create(
                    filename=filename,
                    path=location,
                    size=os.path.getsize(os.path.join(location, filename)),
                    process_execution=self
                )
        except FileNotFoundError: pass



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

        return os.path.abspath(os.path.join(
            settings.NEXTFLOW_DATA_ROOT,
            str(self.process_execution.execution.id),
            settings.NEXTFLOW_PUBLISH_DIR,
            self.process_execution.name,
            self.filename
        ))
