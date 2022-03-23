import os
import re
import time
import shutil
from django.dispatch import receiver
import nextflow
from random import randint
from django.db import models
from django.conf import settings
from django.db.models.signals import post_delete
from django_random_id_model import RandomIDModel, generate_random_id
from .utils import get_file_extension, get_file_hash, parse_datetime, parse_duration
from .graphs import Graph

class Pipeline(RandomIDModel):
    """A Nextflow pipeline, representing some .nf file."""

    class Meta:
        ordering = ["name"]

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
    

    def create_params(self, params, data_params, execution_params, dir_name):
        """Creates param dict for an execution."""

        params = {**(params if params else {})}
        data_objects, execution_objects = [], []
        if data_params:
            data_objects = self.create_data_params(data_params, dir_name, params)
        if execution_params:
            execution_objects = self.create_execution_params(execution_params, dir_name, params)
        return params, data_objects, execution_objects
    

    def create_data_params(self, data_params, dir_name, params):
        """Creates a param dict for params which refer to django-nextflow data
        objects."""

        data_objects = []
        for name, value in data_params.items():
            if isinstance(value, list):
                datas = [Data.objects.filter(id=id).first() for id in value]
                paths = [d.filename for d in datas if d]
                params[name] = '"{' + ",".join(paths) + '}"'
                data_objects += filter(bool, datas)
                for data in filter(bool, datas):
                    os.symlink( data.full_path, os.path.join(
                        settings.NEXTFLOW_DATA_ROOT, dir_name, data.filename
                    ))
            else:
                data = Data.objects.filter(id=value).first()
                if not data: continue
                path = data.full_path
                params[name] = path
                data_objects.append(data)
        return data_objects
    

    def create_execution_params(self, execution_params, dir_name, params):
        """Creates a param dict for params which refer to django-nextflow
        execution objects."""

        execution_objects = []
        for name, value in execution_params.items():
            execution = Execution.objects.filter(id=value).first()
            if not execution: continue
            ex_dir_name = os.path.join(
                settings.NEXTFLOW_DATA_ROOT, dir_name, "executions", name
            )
            os.makedirs(ex_dir_name, exist_ok=True)
            for process in execution.process_executions.all():
                os.mkdir(os.path.join(ex_dir_name, process.process_name))
                for data in process.downstream_data.all():
                    os.symlink(data.full_path, os.path.join(
                        ex_dir_name, process.process_name, data.filename
                    ))
            for data in execution.upstream_data.all():
                os.symlink(data.full_path, os.path.join(
                    ex_dir_name, data.filename
                ))   
            params[name] = ex_dir_name
            execution_objects.append(execution)
        return execution_objects



    def run(self, params=None, data_params=None, execution_params=None, profile=None, execution_id=None, post_poll=None):
        """Run the pipeline with a set of parameters."""
        
        pipeline = self.create_pipeline()
        id = Execution.prepare_directory(execution_id=execution_id)
        params, data_objects, execution_objects = self.create_params(
            params or {}, data_params or {}, execution_params or {}, str(id)
        )
        execution = pipeline.run(
            location=os.path.join(settings.NEXTFLOW_DATA_ROOT, str(id)),
            params=params, profile=profile
        )
        execution_model = Execution.create_from_object(execution, id, self)
        execution_model.remove_symlinks()
        for data in data_objects: execution_model.upstream_data.add(data)
        for ex in execution_objects: execution_model.upstream_executions.add(ex)
        for process_execution in execution.process_executions:
            process_execution_model = ProcessExecution.create_from_object(
                process_execution, execution_model
            )
            process_execution_model.create_downstream_data_objects()
        for process_execution_model in execution_model.process_executions.all():
            process_execution_model.create_upstream_data_objects()
        execution_model.remove_symlinks()
        return execution_model


    def run_and_update(self, params=None, data_params=None, execution_params=None, profile=None, execution_id=None, post_poll=None):
        pipeline = self.create_pipeline()
        id = Execution.prepare_directory(execution_id=execution_id)
        params, data_objects, execution_objects = self.create_params(
            params or {}, data_params or {}, execution_params or {}, str(id)
        )
        for execution in pipeline.run_and_poll(
            location=os.path.join(settings.NEXTFLOW_DATA_ROOT, str(id)),
            params=params, profile=profile
        ):
            execution_model = Execution.create_from_object(execution, id, self)
            for data in data_objects:
                if not execution_model.upstream_data.filter(id=data.id):
                    execution_model.upstream_data.add(data)
            for ex in execution_objects:
                if not execution_model.upstream_executions.filter(id=ex.id):
                    execution_model.upstream_executions.add(ex)
            for process_execution in execution.process_executions:
                process_execution_model = ProcessExecution.create_from_object(
                    process_execution, execution_model
                )
                process_execution_model.create_downstream_data_objects()
            for process_execution_model in execution_model.process_executions.all():
                process_execution_model.create_upstream_data_objects()
            if post_poll:
                post_poll(execution_model)
        try:
            execution_model.remove_symlinks()
            return execution_model
        except: pass

class Execution(RandomIDModel):
    """A record of the running of some Nextflow file."""

    class Meta:
        ordering = ["started"]

    identifier = models.CharField(max_length=100)
    stdout = models.TextField()
    stderr = models.TextField()
    exit_code = models.IntegerField(null=True)
    status = models.CharField(max_length=20)
    command = models.TextField()
    started = models.FloatField(null=True)
    duration = models.FloatField(null=True)
    label = models.CharField(max_length=80, default="", blank=True)
    notes = models.TextField(default="", blank=True)
    pipeline = models.ForeignKey(Pipeline, related_name="executions", on_delete=models.CASCADE)
    upstream_executions = models.ManyToManyField("django_nextflow.Execution", related_name="downstream_executions")

    def __str__(self):
        return self.identifier
    

    @property
    def finished(self):
        """The timestamp for when the execution stopped."""

        if self.started is not None and self.duration is not None:
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
    def prepare_directory(execution_id=None):
        """Generates a random 18-digit ID and creates a directory in the data
        root with that ID. The ID itself is returned."""

        if not execution_id:
            execution_id = generate_random_id()
        os.mkdir(os.path.join(settings.NEXTFLOW_DATA_ROOT, str(execution_id)))
        return execution_id
    

    @staticmethod
    def create_from_object(execution, id, pipeline):
        """Creates a Execution model object from a nextflow.py Execution."""

        execution_model = Execution.objects.get_or_create(id=id, pipeline=pipeline)[0]
        execution_model.identifier = execution.id
        execution_model.stdout = execution.stdout
        execution_model.stderr = execution.stderr
        execution_model.status = execution.status
        execution_model.exit_code = execution.returncode
        execution_model.command = execution.command
        execution_model.started = parse_datetime(execution.datetime)
        execution_model.duration = parse_duration(execution.duration)
        execution_model.save()
        return execution_model
    

    def remove_symlinks(self):
        """As part of the preparation for running the execution, some symlinks
        might have been created. This tidies them away."""

        root = os.path.join(settings.NEXTFLOW_DATA_ROOT, str(self.id))
        for f in os.listdir(root):
            if os.path.islink(os.path.join(root, f)):
                 os.unlink(os.path.join(root, f))
        if os.path.exists(os.path.join(root, "executions")):
            shutil.rmtree(os.path.join(root, "executions"))
    

    def to_graph(self):
        """Creates a graph object from execution."""

        return Graph(self)



class ProcessExecution(RandomIDModel):
    """A record of the execution of a process."""
    
    class Meta:
        ordering = ["started"]

    name = models.CharField(max_length=200)
    process_name = models.CharField(max_length=200)
    identifier = models.CharField(max_length=200)
    status = models.CharField(max_length=20)
    stdout = models.TextField()
    stderr = models.TextField()
    started = models.FloatField(null=True)
    duration = models.FloatField(null=True)
    execution = models.ForeignKey(Execution, related_name="process_executions", on_delete=models.CASCADE)

    def __str__(self):
        return self.name
    

    @staticmethod
    def create_from_object(process_execution, execution):
        """Creates a ProcessExecution model object from a nextflow.py
        ProcessExecution."""

        proc_ex = ProcessExecution.objects.get_or_create(
            identifier=process_execution.hash,
            execution=execution
        )[0]
        proc_ex.name = process_execution.name
        proc_ex.process_name = process_execution.process
        proc_ex.status = process_execution.status
        proc_ex.stdout = process_execution.stdout
        proc_ex.stderr = process_execution.stderr
        proc_ex.started = parse_datetime(process_execution.start)
        proc_ex.duration = parse_duration(process_execution.duration)
        proc_ex.save()
        return proc_ex
    

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

        publish_dir = os.path.join(
            settings.NEXTFLOW_DATA_ROOT, str(self.execution.id),
            settings.NEXTFLOW_PUBLISH_DIR
        )
        if not os.path.exists(publish_dir): return
        results_files = {d: [
            os.readlink(os.path.join(publish_dir, d, f)) if
            os.path.islink(os.path.join(publish_dir, d, f)) else None
            for f in os.listdir(os.path.join(publish_dir, d))
        ] for d in os.listdir(publish_dir)}
        for filename in os.listdir(self.work_dir):
            path = os.path.join(self.work_dir, filename)
            if not os.path.islink(path):
                for d in results_files:
                    for f in results_files[d]:
                        if f == os.path.abspath(path):
                            Data.create_from_output(path, self)
    

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
                    try:
                        execution = Execution.objects.get(id=execution_id)
                        process_execution = execution.process_executions.get(identifier=identifier)
                        upstream = process_execution.downstream_data.filter(filename=filename).first()
                        if upstream:
                            self.upstream_data.add(upstream)
                        else:
                            path = os.path.join(process_execution.work_dir, filename)
                            self.upstream_data.add(
                                Data.create_from_output(path, process_execution)
                            )
                    except: pass



class Data(RandomIDModel):
    """A data file."""

    class Meta:
        ordering = ["filename"]

    filename = models.CharField(max_length=1000)
    filetype = models.CharField(max_length=50)
    size = models.BigIntegerField()
    created = models.IntegerField(default=time.time)
    is_directory = models.BooleanField(default=False)
    label = models.CharField(max_length=80, default="", blank=True)
    notes = models.TextField(default="", blank=True)
    is_ready = models.BooleanField(default=True)
    is_removed = models.BooleanField(default=False)
    md5 = models.CharField(max_length=64, default="")
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
            size=os.path.getsize(path), is_directory=os.path.isdir(path)
        )
        os.mkdir(os.path.join(settings.NEXTFLOW_UPLOADS_ROOT, str(data.id)))
        new_path = os.path.join(
            settings.NEXTFLOW_UPLOADS_ROOT, str(data.id), filename
        )
        shutil.copy(path, new_path)
        if data.is_directory:
            shutil.make_archive(new_path, "zip", new_path)
            data.md5 = get_file_hash(new_path + ".zip")
        else:
            data.md5 = get_file_hash(new_path)
        data.save()
        return data
    

    @staticmethod
    def create_from_upload(upload, is_directory=False):
        """Creates a data object froma django UploadedFile."""

        name = upload.name
        if is_directory and upload.name.endswith(".zip"):
            name = name[:-4]
        data = Data.objects.create(
            filename=name, filetype=get_file_extension(name),
            size=upload.size, is_directory=is_directory
        )
        location = os.path.join(settings.NEXTFLOW_UPLOADS_ROOT, str(data.id))
        os.mkdir(location)
        new_path = os.path.join(location, upload.name)
        with open(new_path, "wb+") as f:
            for chunk in upload.chunks():
                f.write(chunk)
        if data.is_directory:
            shutil.unpack_archive(new_path, new_path[:-4], "zip")
        data.md5 = get_file_hash(new_path)
        data.save()
        return data
    

    @staticmethod
    def create_from_partial_upload(blob, filename="blob", data=None, final=False, is_directory=False, filesize=None):
        """Updates a data object froma django UploadedFile."""

        if not data:
            filename_to_write_to, data_filename = filename, filename
            if is_directory and filename.endswith(".zip"):
                data_filename = data_filename[:-4]
            data = Data.objects.create(
                filename=data_filename, filetype=get_file_extension(data_filename),
                size=blob.size, is_ready=False, is_directory=is_directory
            )
            location = os.path.join(settings.NEXTFLOW_UPLOADS_ROOT, str(data.id))
            os.mkdir(location)
            full_path = os.path.join(location, filename_to_write_to)
            with open(full_path, "wb") as f: f.write(blob.read())
        else:
            if filesize is not None:
                if filesize < data.size: return data
                if filesize > data.size: raise ValueError("Missing chunk")
            filename_to_write_to, data_filename = data.filename, data.filename
            if data.is_directory: filename_to_write_to += ".zip"
            location = os.path.join(settings.NEXTFLOW_UPLOADS_ROOT, str(data.id))
            full_path = os.path.join(location, filename_to_write_to)
            with open(full_path, "ab") as f: f.write(blob.read())
            data.size = os.path.getsize(full_path)
            data.created = time.time()
        if final:
            data.is_ready = True
            if data.is_directory:
                shutil.unpack_archive(full_path, full_path[:-4], "zip")
            data.md5 = get_file_hash(full_path)
            data.size = os.path.getsize(full_path)
        data.save()
        return data


    @staticmethod
    def create_from_output(path, process_execution):
        """Takes the path to the output file of some process execution, and
        creates a Data object from it."""

        filename = path.split(os.path.sep)[-1]
        if process_execution.downstream_data.filter(filename=filename): return
        is_directory = os.path.isdir(path)
        if is_directory: shutil.make_archive(path, "zip", path)
        data = Data.objects.create(
            filename=filename,
            is_directory=is_directory,
            filetype=get_file_extension(filename),
            size=os.path.getsize(path + ".zip" if is_directory else path),
            upstream_process_execution=process_execution
        )
        if is_directory:
            data.md5 = get_file_hash(path + ".zip")
        else:
            data.md5 = get_file_hash(path)
        data.save()
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
    

    def upstream_within_execution(self):
        """Gets all data objects upstream of this one within the execution that
        produced it. If the data was not produced by an execution, there will be
        no upstream."""

        pe = self.upstream_process_execution
        data_ids = []
        if pe:
            graph = pe.execution.to_graph()
            self_in_graph = graph.data[self.id]
            upstream = [up for up in self_in_graph.up]
            while upstream:
                upstream = [up for node in upstream for up in node.up]
                for d in upstream: data_ids.append(d.id)
        return Data.objects.filter(id__in=data_ids)
    

    def downstream_within_execution(self):
        """Gets all data objects downstream of this one within the execution
        that produced it. If the data was not produced by an execution, there
        will be no downstream."""
        
        pe = self.upstream_process_execution
        data_ids = []
        if pe:
            graph = pe.execution.to_graph()
            self_in_graph = graph.data[self.id]
            downstream = [down for down in self_in_graph.down]
            while downstream:
                downstream = [down for node in downstream for down in (
                    node.down if "down" in dir(node) else []
                )]
                for d in downstream: data_ids.append(d.id)
        return Data.objects.filter(id__in=data_ids)
    

    def remove(self):
        """Removes the file on disk and sets is_removed to True."""

        try:
            os.remove(self.full_path)
        except FileNotFoundError: pass
        self.is_removed = True
        self.save()


@receiver(post_delete, sender=Data)
def data_post_delete(sender, **kwargs):
    """Delete the files on disk if data is deleted for real."""

    data = kwargs["instance"]
    try:
        if not data.upstream_process_execution:
            shutil.rmtree(os.path.join(settings.NEXTFLOW_UPLOADS_ROOT, str(data.id)))
        else:
            shutil.rmtree(kwargs["instance"].full_path)
            if data.is_directory:
                shutil.rmtree(kwargs["instance"].full_path + ".zip")
    except FileNotFoundError: pass
    except ProcessExecution.DoesNotExist: pass
