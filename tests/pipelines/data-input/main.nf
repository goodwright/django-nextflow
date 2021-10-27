#!/usr/bin/env nextflow

params.worldname = "world"
params.filename = ""

cheers = Channel.from 'Bonjour', 'Ciao', 'Hello', 'Hola'

process sayHello {
  echo true
  input: 
    val x from cheers
  script:
    """
    echo | cat "$params.filename"
    echo '$x $params.worldname!'
    """
}