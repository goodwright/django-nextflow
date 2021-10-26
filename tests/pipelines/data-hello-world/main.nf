#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.worldname = "world"

cheers = Channel.from 'Bonjour', 'Ciao', 'Hello', 'Hola'

process sayHello {
  echo true
  publishDir "${params.outdir}", mode: params.publish_dir_mode, saveAs: { filename -> task.name + '/' + filename }


  input: 
    val x
  output:
    file 'message.txt'
    file 'output.txt'
  script:
    """
    echo '$x $params.worldname!' > message.txt
    echo "non-output" > non-output.txt
    echo "output" > output.txt
    """
}

workflow {
  sayHello(cheers)
}