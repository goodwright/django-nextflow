# Generated by Django 3.2.8 on 2021-12-03 05:47

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
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('identifier', models.CharField(max_length=100)),
                ('stdout', models.TextField()),
                ('stderr', models.TextField()),
                ('exit_code', models.IntegerField()),
                ('status', models.CharField(max_length=20)),
                ('command', models.TextField()),
                ('started', models.FloatField()),
                ('duration', models.FloatField()),
            ],
        ),
        migrations.CreateModel(
            name='Pipeline',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('path', models.CharField(max_length=300)),
                ('schema_path', models.CharField(max_length=300)),
                ('config_path', models.CharField(max_length=300)),
            ],
        ),
        migrations.CreateModel(
            name='ProcessExecution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('process_name', models.CharField(max_length=200)),
                ('identifier', models.CharField(max_length=200)),
                ('status', models.CharField(max_length=20)),
                ('stdout', models.TextField()),
                ('stderr', models.TextField()),
                ('started', models.FloatField()),
                ('duration', models.FloatField()),
                ('execution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='process_executions', to='django_nextflow.execution')),
            ],
        ),
        migrations.AddField(
            model_name='execution',
            name='pipeline',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='executions', to='django_nextflow.pipeline'),
        ),
        migrations.CreateModel(
            name='Data',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filename', models.CharField(max_length=200)),
                ('filetype', models.CharField(max_length=20)),
                ('size', models.IntegerField()),
                ('created', models.IntegerField(default=time.time)),
                ('downstream_executions', models.ManyToManyField(related_name='upstream_data', to='django_nextflow.Execution')),
                ('downstream_process_executions', models.ManyToManyField(related_name='upstream_data', to='django_nextflow.ProcessExecution')),
                ('upstream_process_execution', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='downstream_data', to='django_nextflow.processexecution')),
            ],
        ),
    ]
