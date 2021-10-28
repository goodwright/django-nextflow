nextflow.enable.dsl=2

include { PDB_TO_MMCIF } from '../modules/pdb2mmcif'

params.pdb = "*.pdb"
params.print_title = "yes"

workflow {
    PDB_TO_MMCIF(params.pdb, params.print_title)
}