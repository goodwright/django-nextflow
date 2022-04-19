# django-nextflow

![](https://github.com/goodwright/django-nextflow/actions/workflows/main.yml/badge.svg)
[![](https://img.shields.io/pypi/pyversions/django-nextflow.svg?color=3776AB&logo=python&logoColor=white)](https://www.python.org/)
[![](https://img.shields.io/pypi/djversions/django-nextflow?color=0C4B33&logo=django&logoColor=white&label=django)](https://www.djangoproject.com/)
[![](https://img.shields.io/pypi/l/django-nextflow.svg?color=blue)](https://github.com/goodwright/django-nextflow/blob/master/LICENSE)

django-nextflow is Django app for running Nextflow pipelines and storing their
results in a database within a Django web app.

## Installation

nextflow.py is available through PyPI:

```bash
pip install django-nextflow
```

You must install the Nextflow executable itself separately: see the
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
NEXTFLOW_PUBLISH_DIR/process_name for output files for that process. These files
*must* be published as symlinks, not copies, otherwise django-nextflow will not
recognise them.

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
    description="Some useful pipeline.",
    schema_path="main.json",
    config_path="nextflow.config"
)
print(pipeline.input_schema) # Returns inputs as dict
```

These can be assigned to `PipelineCategory` objects for organisation.

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
execution = pipeline.run(
    params={"param1": "xxx"},
    data_params={"param2": 23, "param3": [24, 25]}
)
```

...where 23, 24 and 25 are the IDs of `Data` objects.

You can also supply entire executions as inputs, in which case they will be
provided to the pipeline as a directory of symlinked files:

```python
execution = pipeline.run(
    params={"param1": "xxx"},
    execution_params={"genome1": 23, "genome2": 24}
)
```

The above `run` method will run the entire pipeline and create the database
objects at the end. To create the Execution object straight away and update it
as execution proceeds, use `run_and_update`. This can take a `post_poll`
function which will execute every time the Execution updates.

The `Data` objects above were created by running some pipeline, but you might
want to create one from scratch without running a pipeline. You can do so either
from a path string, or from a Django `UploadedFile` object:

```python
data1 = Data.create_from_path("/path/to/file.txt")
data2 = Data.create_from_upload(django_upload_object)
```

The file will be copied to `NEXTFLOW_UPLOADS_ROOT` in this case.

You can also create a Data object in chunks using:

```python
data = Data.create_from_partial_upload(django_upload_object1, filename="large-file.txt")
data = Data.create_from_partial_upload(django_upload_object2, data=data)
data = Data.create_from_partial_upload(django_upload_object3, data=data, final=True)
```


You can determine all the downstream data of a data object within its generating
execution using the `downstream_within_execution` method. Likewise the
`upstream_within_execution` method will return all upstream data within the
execution.

## Changelog

### 0.10

*19th April, 2022*

- Pipelines can now be organised into categories with a new `PipelineCatgeory` model.
- Pipelines now have an `order` field for ordering within categories.

### 0.9.3

*23rd March, 2022*

- Fixed data post-delete hook handling of missing upstream objects.

### 0.9.2

*21st March, 2022*

- Added data post-delete behavior.
- Fixed up/downstream within execution lookups.

### 0.9.1

*7th March, 2022*

- Partial data upload will now optionally verify filesize matches expected.

### 0.9

*6th March, 2022*

- Data objects can now be created from upload objects blob by blob.
- `is_ready`field added to Data to denote those in process of being created.
- Models now have default ordering.
- Executions can now be manually created with very minimal information.
- Fixed missing MD5 hash for pipeline output files.
- Fixed issue with generating finished time when values were missing.

### 0.8

*27th February, 2022*

- Execution objects now have label and notes fields.
- Data objects now have label and notes fields.
- Added method to 'remove' data objects rather than delete them entirely.
- Data objects now have MD5 hash upon creation.

### 0.7

*19th February, 2022*

- Executions can now generate a graph representation of themselves.
- Data objects can now detect all their up/downstream data within an execution.

### 0.6

*14th February, 2022*

- Pipelines now have a `run_and_update` method, for constant Execution updating.
- Better Execution ID generation.


### 0.5

*3rd February, 2022*

- Pipelines can now take execution inputs.
- Fixed method for detecting downstream data products.

### 0.4

*12th January, 2022*

- Better support for multiple data objects.
- Data objects can now be directories, which will be automatically zipped.
- When creating upstream data connections, data objects will be created if needed.

### 0.3.2

*26th December, 2021*

- Allow IDs to be big ints.

### 0.3.1

*24th December, 2021*

- Data file sizes can now be more than 2<sup>32</sup>.
- Data file names can now be 1000 characters long.

### 0.3

*21st December, 2021*

- Pipelines can now take multiple data inputs per param.
- Profiles can now be specified when running a pipeline.
- Compression extension .gz now ignored when detecting filetype.
- Process executions start and end times are now recorded.
- Improved system for identifying upstream data inputs.
- Improved publish_dir identification.
- Improved log file reading.

### 0.2

*14th November, 2021*

- Pipelines now have description fields.
- Data objects now have creation time fields.
- Added upstream data objects as well as downstream to process executions. 

### 0.1.1

*3rd November, 2021*

- Fixed duration string parsing.

### 0.1

*29th October, 2021*

- Initial models for pipelines, execution, process executions and data.
