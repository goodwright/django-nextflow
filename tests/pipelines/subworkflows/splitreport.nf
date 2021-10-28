nextflow.enable.dsl=2

include { MMCIF_TO_CHAINS } from '../modules/mmcif2chains'
include { MMCIF_REPORT } from '../modules/mmcifreport'

params.mmcif = "*.cif"

workflow {
    ch_chains = MMCIF_TO_CHAINS(params.mmcif).cif.flatMap()
    MMCIF_REPORT( ch_chains )
}

workflow SPLIT_REPORT {

    take:
    mmcif

    main:
    ch_chains = MMCIF_TO_CHAINS(mmcif).cif.flatMap()
    MMCIF_REPORT( ch_chains )
}
