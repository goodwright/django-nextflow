nextflow.enable.dsl=2

include { PDB_TO_MMCIF } from '../modules/pdb2mmcif'

params.pdb = "*.pdb"

workflow {
    PDB_TO_MMCIF(params.pdb)
}