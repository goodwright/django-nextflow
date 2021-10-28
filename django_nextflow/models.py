import os
import shutil
import nextflow
from random import randint
from django.db import models
from django.conf import settings
from .utils import get_file_extension, parse_datetime, parse_duration

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
            schema=os.path.join(settings.NEXTFLOW_PIPELINE_ROOT, self.schema_path) if self.schema_path else None,
        )
    

    @property
    def input_schema(self):
        return self.create_pipeline().input_schema
    

    def create_params(self, params, data_params):
        params = {**(params if params else {})}
        data_objects = []
        if data_params:
            for name, data_id in data_params.items():
                data = Data.objects.get(id=data_id)
                path = data.full_path
                params[name] = path
                data_objects.append(data)
        return params, data_objects


    def run(self, params=None, data_params=None):
        pipeline = self.create_pipeline()
        id = Execution.prepare_directory()
        params, data_objects = self.create_params(params or {}, data_params or {})
        execution = pipeline.run(
            location=os.path.join(settings.NEXTFLOW_DATA_ROOT, str(id)),
            params=params
        )
        execution_model = Execution.create_from_object(execution, id, self)
        for data in data_objects: execution_model.upstream.add(data)
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
                    filetype=get_file_extension(filename),
                    size=os.path.getsize(os.path.join(location, filename)),
                    process_execution=self
                )
        except FileNotFoundError: pass



class Data(models.Model):

    filename = models.CharField(max_length=200)
    filetype = models.CharField(max_length=20)
    size = models.IntegerField()
    process_execution = models.ForeignKey(ProcessExecution, null=True, related_name="data", on_delete=models.CASCADE)
    downstream = models.ManyToManyField(Execution, related_name="upstream")

    def __str__(self):
        return self.filename
    

    @staticmethod
    def create_from_path(path):
        filename = path.split(os.path.sep)[-1]
        data = Data.objects.create(
            filename=filename, filetype=get_file_extension(filename),
            size=os.path.getsize(path)
        )
        os.mkdir(os.path.join(settings.NEXTFLOW_UPLOADS_ROOT, str(data.id)))
        shutil.copy(path, os.path.join(
            settings.NEXTFLOW_UPLOADS_ROOT, str(data.id), filename
        ))
        return data
    

    @staticmethod
    def create_from_upload(upload):
        data = Data.objects.create(
            filename=upload.name, filetype=get_file_extension(upload.name),
            size=upload.size
        )
        os.mkdir(os.path.join(settings.NEXTFLOW_UPLOADS_ROOT, str(data.id)))
        with open(os.path.join(
            settings.NEXTFLOW_UPLOADS_ROOT, str(data.id), upload.name
        ), "wb+") as destination:
            for chunk in upload.chunks():
                destination.write(chunk)
        return data
    

    @property
    def full_path(self):
        """Gets the data's full path on the filesystem."""

        if self.process_execution:
            location = os.path.join(
                settings.NEXTFLOW_DATA_ROOT,
                str(self.process_execution.execution.id),
                settings.NEXTFLOW_PUBLISH_DIR, self.process_execution.name,
            )
        else:
            location = os.path.join(
                settings.NEXTFLOW_UPLOADS_ROOT, str(self.id),
            )
        return os.path.abspath(os.path.join(location, self.filename))
