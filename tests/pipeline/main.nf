nextflow.enable.dsl=2

include { CONVERT_REPORT } from './workflows/convertreport'
include { SPLIT_REPORT } from './workflows/splitreport'

params.pdb = "*.pdb"

workflow {
    ch_cif = CONVERT_REPORT(params.pdb).cif
    SPLIT_REPORT(ch_cif)
}