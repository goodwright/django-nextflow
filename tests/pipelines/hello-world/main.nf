#!/usr/bin/env nextflow

params.worldname = "world"

cheers = Channel.from 'Bonjour', 'Ciao', 'Hello', 'Hola'

process sayHello {
  echo true
  input: 
    val x from cheers
  script:
    """
    echo '$x $params.worldname!'
    """
}