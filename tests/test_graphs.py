import os
import time
from unittest.mock import PropertyMock, patch
from django.test.utils import override_settings
from mixer.backend.django import mixer
from django.test import TestCase
from django_nextflow.models import Data, ProcessExecution, Execution
from django_nextflow.graphs import Graph

class GraphCreationTests(TestCase):

    def test_no_content(self):
        graph = Graph(mixer.blend(Execution))
        self.assertEqual(graph.data, {})
        self.assertEqual(graph.process_executions, {})
        self.assertEqual(str(graph), "<Graph (0 nodes)>")
    

    def test_1_process_execution_no_data(self):
        ex = mixer.blend(Execution)
        pe = mixer.blend(ProcessExecution, id=1, execution=ex)
        graph = Graph(ex)
        self.assertEqual(graph.data, {})
        self.assertEqual(graph.process_executions, {1: pe})
        self.assertEqual(str(graph), "<Graph (1 node)>")
        self.assertEqual(graph.process_executions[1].up, set())
        self.assertEqual(graph.process_executions[1].down, set())
    

    def test_1_process_execution_with_data(self):
        ex = mixer.blend(Execution)
        pe = mixer.blend(ProcessExecution, id=1, execution=ex)
        d1, d2, d3, d4 = (mixer.blend(Data, id=n) for n in range(1, 5))
        pe.upstream_data.add(d1)
        pe.upstream_data.add(d2)
        pe.downstream_data.add(d3)
        pe.downstream_data.add(d4)
        graph = Graph(ex)
        self.assertEqual(graph.data, {1: d1, 2: d2, 3: d3, 4: d4})
        self.assertEqual(graph.process_executions, {1: pe})
        self.assertEqual(str(graph), "<Graph (5 nodes)>")
        self.assertEqual(graph.process_executions[1].up, {d1, d2})
        self.assertEqual(graph.process_executions[1].down, {d3, d4})
        self.assertEqual(graph.data[1].up, set())
        self.assertEqual(graph.data[1].down, {pe})
        self.assertEqual(graph.data[2].up, set())
        self.assertEqual(graph.data[2].down, {pe})
        self.assertEqual(graph.data[3].up, {pe})
        self.assertEqual(graph.data[3].down, set())
        self.assertEqual(graph.data[4].up, {pe})
        self.assertEqual(graph.data[4].down, set())
    

    def test_complex_graph(self):
        # There's a previous execution which shouldn't be in graph
        prev_ex = mixer.blend(Execution)
        mult_gen = mixer.blend(ProcessExecution, id=0, execution=prev_ex)
        mult_pre = mixer.blend(Data, id=0, upstream_process_execution=None)
        mult_gen.upstream_data.add(mult_pre)

        # An execution with 6 processes
        ex = mixer.blend(Execution)
        barcode_gen = mixer.blend(ProcessExecution, id=1, execution=ex)
        ultra = mixer.blend(ProcessExecution, id=2, execution=ex)
        fastqc1 = mixer.blend(ProcessExecution, id=3, execution=ex)
        fastqc2 = mixer.blend(ProcessExecution, id=4, execution=ex)
        trim1 = mixer.blend(ProcessExecution, id=5, execution=ex)
        trim2 = mixer.blend(ProcessExecution, id=6, execution=ex)

        # Data and the processes which make them
        multiplexed = mixer.blend(Data, id=1, upstream_process_execution=mult_gen)
        sheet = mixer.blend(Data, id=2, upstream_process_execution=None)
        barcode = mixer.blend(Data, id=3, upstream_process_execution=barcode_gen)
        fastq1 = mixer.blend(Data, id=4, upstream_process_execution=ultra)
        fastq2 = mixer.blend(Data, id=5, upstream_process_execution=ultra)
        html1 = mixer.blend(Data, id=6, upstream_process_execution=fastqc1)
        html2 = mixer.blend(Data, id=7, upstream_process_execution=fastqc2)
        zip1 = mixer.blend(Data, id=8, upstream_process_execution=fastqc1)
        zip2 = mixer.blend(Data, id=9, upstream_process_execution=fastqc2)
        trimmed1 = mixer.blend(Data, id=10, upstream_process_execution=trim1)
        trimmed2 = mixer.blend(Data, id=11, upstream_process_execution=trim2)

        # Define inputs to process executions
        barcode_gen.upstream_data.add(sheet)
        ultra.upstream_data.add(multiplexed)
        ultra.upstream_data.add(barcode)
        fastqc1.upstream_data.add(fastq1)
        fastqc2.upstream_data.add(fastq2)
        trim1.upstream_data.add(fastq1)
        trim2.upstream_data.add(fastq2)

        # A later execution which shouldn't be in graph
        later_ex = mixer.blend(Execution)
        read_zip = mixer.blend(ProcessExecution, id=7)
        read_html = mixer.blend(ProcessExecution, id=8)
        read_zip.upstream_data.add(zip1)
        read_html.upstream_data.add(zip2)
        read_zip.downstream_data.add(mixer.blend(Data))
        read_html.downstream_data.add(mixer.blend(Data))

        # Make graph
        with self.assertNumQueries(3):
            graph = Graph(ex)

        # Graph is correct
        self.assertEqual(len(graph.process_executions), 6)
        self.assertEqual(len(graph.data), 11)
        self.assertEqual(graph.data[1], multiplexed)
        self.assertEqual(graph.data[1].up, set())
        self.assertEqual(graph.data[1].down, {ultra})
        self.assertEqual(graph.process_executions[2], ultra)
        self.assertEqual(graph.process_executions[2].up, {multiplexed, barcode})
        self.assertEqual(graph.process_executions[2].down, {fastq1, fastq2})
        




