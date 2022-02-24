# Generated by Django 4.0 on 2022-02-24 14:19

from django.db import migrations, models
import django.db.models.deletion
import time


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Execution',
            fields=[
                ('id', models.BigIntegerField(primary_key=True, serialize=False)),
                ('identifier', models.CharField(max_length=100)),
                ('stdout', models.TextField()),
                ('stderr', models.TextField()),
                ('exit_code', models.IntegerField(null=True)),
                ('status', models.CharField(max_length=20)),
                ('command', models.TextField()),
                ('started', models.FloatField(null=True)),
                ('duration', models.FloatField(null=True)),
                ('alias', models.CharField(blank=True, default='', max_length=80)),
                ('notes', models.TextField(blank=True, default='')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Pipeline',
            fields=[
                ('id', models.BigIntegerField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('path', models.CharField(max_length=300)),
                ('schema_path', models.CharField(max_length=300)),
                ('config_path', models.CharField(max_length=300)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ProcessExecution',
            fields=[
                ('id', models.BigIntegerField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('process_name', models.CharField(max_length=200)),
                ('identifier', models.CharField(max_length=200)),
                ('status', models.CharField(max_length=20)),
                ('stdout', models.TextField()),
                ('stderr', models.TextField()),
                ('started', models.FloatField(null=True)),
                ('duration', models.FloatField(null=True)),
                ('execution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='process_executions', to='django_nextflow.execution')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='execution',
            name='pipeline',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='executions', to='django_nextflow.pipeline'),
        ),
        migrations.AddField(
            model_name='execution',
            name='upstream_executions',
            field=models.ManyToManyField(related_name='downstream_executions', to='django_nextflow.Execution'),
        ),
        migrations.CreateModel(
            name='Data',
            fields=[
                ('id', models.BigIntegerField(primary_key=True, serialize=False)),
                ('filename', models.CharField(max_length=1000)),
                ('filetype', models.CharField(max_length=50)),
                ('size', models.BigIntegerField()),
                ('created', models.IntegerField(default=time.time)),
                ('is_directory', models.BooleanField(default=False)),
                ('notes', models.TextField(blank=True, default='')),
                ('downstream_executions', models.ManyToManyField(related_name='upstream_data', to='django_nextflow.Execution')),
                ('downstream_process_executions', models.ManyToManyField(related_name='upstream_data', to='django_nextflow.ProcessExecution')),
                ('upstream_process_execution', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='downstream_data', to='django_nextflow.processexecution')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
