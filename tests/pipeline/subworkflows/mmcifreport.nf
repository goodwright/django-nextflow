nextflow.enable.dsl=2

include { MMCIF_REPORT } from '../modules/mmcifreport'

params.mmcif = "*.cif"

workflow {
    MMCIF_REPORT(params.mmcif)
}