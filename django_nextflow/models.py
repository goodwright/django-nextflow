import os
import re
import time
import shutil
import nextflow
from random import randint
from django.db import models
from django.conf import settings
from .utils import get_file_extension, parse_datetime, parse_duration

class Pipeline(models.Model):
    """A Nextflow pipeline, representing some .nf file."""

    name = models.CharField(max_length=200)
    description = models.TextField()
    path = models.CharField(max_length=300)
    schema_path = models.CharField(max_length=300)
    config_path = models.CharField(max_length=300)

    def __str__(self):
        return self.name
    

    def create_pipeline(self):
        """Creates a nextflow.py pipeline from the model."""

        return nextflow.Pipeline(
            path=os.path.join(settings.NEXTFLOW_PIPELINE_ROOT, self.path),
            config=os.path.join(
                settings.NEXTFLOW_PIPELINE_ROOT, self.config_path
            ) if self.config_path else None,
            schema=os.path.join(
                settings.NEXTFLOW_PIPELINE_ROOT, self.schema_path
            ) if self.schema_path else None,
        )
    

    @property
    def input_schema(self):
        """Gets the pipeline's input requirements according to the schema
        file."""

        return self.create_pipeline().input_schema
    

    def create_params(self, params, data_params):
        """Creates param string for an execution."""

        params = {**(params if params else {})}
        data_objects = []
        if data_params:
            for name, value in data_params.items():
                if isinstance(value, list):
                    datas = [Data.objects.filter(id=id).first() for id in value]
                    paths = [d.full_path for d in datas if d]
                    params[name] = ",".join(paths)
                    data_objects += filter(bool, datas)
                else:
                    data = Data.objects.filter(id=value).first()
                    if not data: continue
                    path = data.full_path
                    params[name] = path
                    data_objects.append(data)
        return params, data_objects


    def run(self, params=None, data_params=None, profile=None):
        """Run the pipeline with a set of parameters."""
        
        pipeline = self.create_pipeline()
        id = Execution.prepare_directory()
        params, data_objects = self.create_params(params or {}, data_params or {})
        execution = pipeline.run(
            location=os.path.join(settings.NEXTFLOW_DATA_ROOT, str(id)),
            params=params, profile=profile
        )
        execution_model = Execution.create_from_object(execution, id, self)
        for data in data_objects: execution_model.upstream_data.add(data)
        for process_execution in execution.process_executions:
            process_execution_model = ProcessExecution.create_from_object(
                process_execution, execution_model
            )
            process_execution_model.create_downstream_data_objects()
        for process_execution_model in execution_model.process_executions.all():
            process_execution_model.create_upstream_data_objects()
        return execution_model



class Execution(models.Model):
    """A record of the running of some Nextflow file."""

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

        try:
            with open(os.path.join(
                settings.NEXTFLOW_DATA_ROOT, str(self.id), ".nextflow.log"
            )) as f:
                return f.read()
        except FileNotFoundError: return None
    

    @staticmethod
    def prepare_directory():
        """Generates a random 18-digit ID and creates a directory in the data
        root with that ID. The ID itself is returned."""

        digits_length = 18
        id = randint(10 ** (digits_length - 1), 10 ** digits_length)
        os.mkdir(os.path.join(settings.NEXTFLOW_DATA_ROOT, str(id)))
        return id
    

    @staticmethod
    def create_from_object(execution, id, pipeline):
        """Creates a Execution model object from a nextflow.py Execution."""

        return Execution.objects.create(
            id=id, identifier=execution.id, command=execution.command,
            stdout=execution.process.stdout, stderr=execution.process.stderr,
            exit_code=execution.process.returncode, status=execution.status,
            started=parse_datetime(execution.datetime),
            duration=parse_duration(execution.duration),
            pipeline=pipeline
        )



class ProcessExecution(models.Model):
    """A record of the execution of a process."""

    name = models.CharField(max_length=200)
    process_name = models.CharField(max_length=200)
    identifier = models.CharField(max_length=200)
    status = models.CharField(max_length=20)
    stdout = models.TextField()
    stderr = models.TextField()
    started = models.FloatField()
    duration = models.FloatField()
    execution = models.ForeignKey(Execution, related_name="process_executions", on_delete=models.CASCADE)

    def __str__(self):
        return self.name
    

    @staticmethod
    def create_from_object(process_execution, execution):
        """Creates a ProcessExecution model object from a nextflow.py
        ProcessExecution."""

        return ProcessExecution.objects.create(
            name=process_execution.name,
            process_name=process_execution.process,
            identifier=process_execution.hash,
            status=process_execution.status,
            stdout=process_execution.stdout,
            stderr=process_execution.stderr,
            started=parse_datetime(process_execution.start),
            duration=parse_duration(process_execution.duration),
            execution=execution
        )
    

    @property
    def finished(self):
        """The timestamp for when the execution stopped."""

        return self.started + self.duration


    @property
    def publish_dir(self):
        """The location where the process would have published its files."""

        results_dir = os.path.join(
            settings.NEXTFLOW_DATA_ROOT, str(self.execution.id),
            settings.NEXTFLOW_PUBLISH_DIR
        )
        if os.path.exists(results_dir):
            possibles = os.listdir(results_dir)
            work_dir_contents = set(os.listdir(self.work_dir))
            subsets = [d for d in possibles if set(os.listdir(os.path.join(
                results_dir, d
            ))).issubset(work_dir_contents)]
            if len(subsets) == 1:
                return os.path.join(results_dir, subsets[0])
            matches = [d for d in possibles if d.lower() == self.process_name.lower()]
            if len(matches) == 1:
                return os.path.join(results_dir, matches[0])
            matches = [d for d in possibles if d.lower() == self.name.lower()]
            if len(matches) == 1:
                return os.path.join(results_dir, matches[0])
    

    @property
    def work_dir(self):
        """The process execution's work directory."""

        components = self.identifier.split("/")
        work = os.path.join(
            settings.NEXTFLOW_DATA_ROOT, str(self.execution.id), "work", components[0]
        )
        subdir = [d for d in os.listdir(work) if d.startswith(components[1])][0]
        return os.path.join(work, subdir)


    def create_downstream_data_objects(self):
        """Looks at the files in its publish directory and makes Data objects
        from them."""

        published_files = []
        publish_dir = os.path.join(
            settings.NEXTFLOW_DATA_ROOT, str(self.execution.id),
            settings.NEXTFLOW_PUBLISH_DIR
        )
        if not os.path.exists(publish_dir): return
        for d in os.listdir(publish_dir):
            published_files += os.listdir(os.path.join(publish_dir, d))
        for filename in os.listdir(self.work_dir):
            if filename in published_files:
                if not os.path.islink(os.path.join(self.work_dir, filename)):
                    Data.objects.create(
                        filename=filename,
                        filetype=get_file_extension(filename),
                        size=os.path.getsize(os.path.join(self.work_dir, filename)),
                        upstream_process_execution=self
                    )
    

    def create_upstream_data_objects(self):
        """Looks at the files in its work directory and connects to Data objects
        from those which are symlinks."""

        try:
            with open(os.path.join(self.work_dir, ".command.run")) as f:
                run = f.read()
        except FileNotFoundError: return
        stage = re.search(r"nxf_stage\(\)((.|\n|\r)+?)}", run)
        if stage:
            contents = stage[1]
            tokens = contents.split()
            for token in tokens:
                if settings.NEXTFLOW_UPLOADS_ROOT in token:
                    data_id = token.split(os.path.sep)[-2]
                    self.upstream_data.add(Data.objects.get(id=data_id))
                elif settings.NEXTFLOW_DATA_ROOT in token:
                    components = token.split(os.path.sep)
                    execution_id = components[-5]
                    identifier = "/".join(components[-3:-1])[:9]
                    filename = components[-1]
                    self.upstream_data.add(
                        Execution.objects.get(id=execution_id).process_executions.get(
                            identifier=identifier
                        ).downstream_data.get(filename=filename)
                    )



class Data(models.Model):
    """A data file."""

    filename = models.CharField(max_length=200)
    filetype = models.CharField(max_length=20)
    size = models.IntegerField()
    created = models.IntegerField(default=time.time)
    upstream_process_execution = models.ForeignKey(ProcessExecution, null=True, related_name="downstream_data", on_delete=models.CASCADE)
    downstream_executions = models.ManyToManyField(Execution, related_name="upstream_data")
    downstream_process_executions = models.ManyToManyField(ProcessExecution, related_name="upstream_data")

    def __str__(self):
        return self.filename
    

    @staticmethod
    def create_from_path(path):
        """Creates a data object representing an uploaded file from a path."""

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
        """Creates a data object froma django UploadedFile."""

        data = Data.objects.create(
            filename=upload.name, filetype=get_file_extension(upload.name),
            size=upload.size
        )
        os.mkdir(os.path.join(settings.NEXTFLOW_UPLOADS_ROOT, str(data.id)))
        with open(os.path.join(
            settings.NEXTFLOW_UPLOADS_ROOT, str(data.id), upload.name
        ), "wb+") as f:
            for chunk in upload.chunks():
                f.write(chunk)
        return data
    

    @property
    def full_path(self):
        """Gets the data's full path on the filesystem."""

        if self.upstream_process_execution:
            location = self.upstream_process_execution.work_dir
        else:
            location = os.path.join(
                settings.NEXTFLOW_UPLOADS_ROOT, str(self.id),
            )
        return os.path.abspath(os.path.join(location, self.filename))
