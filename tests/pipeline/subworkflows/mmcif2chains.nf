nextflow.enable.dsl=2

include { MMCIF_TO_CHAINS } from '../modules/mmcif2chains'

params.mmcif = "*.cif"

workflow {
    MMCIF_TO_CHAINS(params.mmcif)
}