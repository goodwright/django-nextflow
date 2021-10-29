# django-nextflow

![](https://github.com/goodwright/django-nextflow/actions/workflows/main.yml/badge.svg)
[![](https://img.shields.io/pypi/pyversions/django-nextflow.svg?color=3776AB&logo=python&logoColor=white)](https://www.python.org/)
[![](https://img.shields.io/pypi/djversions/django-nextflow?color=0C4B33&logo=django&logoColor=white&label=django)](https://www.djangoproject.com/)
[![](https://img.shields.io/pypi/l/django-nextflow.svg?color=blue)](https://github.com/goodwright/django-nextflow/blob/master/LICENSE)

django-nextflow is Django app for runnign Nextflow pipelines and storing their
results in a database within a Django web app.

## Installation

nextflow.py is available through PyPI:

```bash
pip install django-nextflow
```

You must install Nextflow itself separately: see the
[Nextflow Documentation](https://www.nextflow.io/docs/latest/getstarted.html#installation)
for help with this.

## Setup

To use the app within Django, add `django-nextflow` to your list of
`INSTALLED_APPS`.

You must define four values in your `settings.py`:

- `NEXTFLOW_PIPELINE_ROOT` - the location on disk where the Nextflow pipelines
are stored. All references to pipeline files will use this as the root.

- `NEXTFLOW_DATA_ROOT` - the location on disk to store execution records.

- `NEXTFLOW_UPLOADS_ROOT` - the location on disk to store uploaded data.

- `NEXTFLOW_PUBLISH_DIR` - the name of the folder published files will be saved
to. Within an execution directory, django-nextflow will look in
NEXTFLOW_PUBLISH_DIR/process_name for output files for that process.

## Usage

Begin by defining one or more Pipelines. These are .nf files somewhere within
the `NEXTFLOW_PIPELINE_ROOT` you defined:

```python
from django_nextflow.models import Pipeline

pipeline = Pipeline.objects.create(path="workflows/main.nf")
```

You can also provide paths to a JSON input schema file (structured using the
nf-core style) and a config file to use when running it:

```python
pipeline = Pipeline.objects.create(
    path="workflows/main.nf",
    schema_path="main.json",
    config_path="nextflow.config"
)
print(pipeline.input_schema) # Returns inputs as dict
```

To run the pipeline:

```python
execution = pipeline.run(params={"param1": "xxx"})
```

This will run the pipeline using Nextflow, and save database entries for three
different models:

- The `Execution` that is returned represents the running of this pipeline on
this occasion. It stores the stdout and stderr of the command, and has a
`get_log_text()` method for reading the full log file from disk. A directory
will be created in `NEXTFLOW_DATA_ROOT` for the execution to take place in.

- `ProcessExecution` records for each process that execution within the running
of the pipeline. These also have their own stdout and stderr, as well as status
information etc.

- `Data` records for each file published by the processes in the pipeline. Note
that this is not every file produced - but specifically those output by the
process via its output channel. For this to work the processes must be
configured to publish these files to a particular directory name (the one that
`NEXTFLOW_PUBLISH_DIR` is set to), and to a subdirectory within that directory
with the process's name.

If you want to supply a file for which there is a `Data` object as the input to
a pipeline, you can do so as follows:

```python
execution = pipeline.run(params={"param1": "xxx"}, data_params={"param2": 23})
```

...where 23 is the ID of the `Data` object.

The `Data` objects above were created by running some pipeline, but you might
want to create one from scratch without running a pipeline. You can do so either
from a path string, or from a Django `UploadedFile` object:

```python
data1 = Data.create_from_path("/path/to/file.txt")
data2 = Data.create_from_upload(django_upload_object)
```

The file will be copied to `NEXTFLOW_UPLOADS_ROOT` in this case.

### 0.1

*29th October, 2021*

- Initial models for pipelines, execution, process executions and data.
