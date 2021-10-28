nextflow.enable.dsl=2

include { PDB_TO_MMCIF } from './modules/pdb2mmcif'
include { MMCIF_REPORT } from './modules/mmcifreport'
include { MMCIF_TO_CHAINS } from './modules/mmcif2chains'

include { CONVERT_REPORT } from './subworkflows/convertreport'
include { SPLIT_REPORT } from './subworkflows/splitreport'

params.pdb = "*.pdb"

workflow {
    ch_cif = CONVERT_REPORT(params.pdb).cif
    SPLIT_REPORT(ch_cif)
}