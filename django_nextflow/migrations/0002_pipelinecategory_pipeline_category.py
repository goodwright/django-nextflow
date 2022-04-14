# Generated by Django 4.0 on 2022-04-14 07:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('django_nextflow', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PipelineCategory',
            fields=[
                ('id', models.BigIntegerField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField()),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='pipeline',
            name='category',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pipelines', to='django_nextflow.pipelinecategory'),
        ),
    ]