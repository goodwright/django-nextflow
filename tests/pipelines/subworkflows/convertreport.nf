nextflow.enable.dsl=2

include { PDB_TO_MMCIF } from '../modules/pdb2mmcif'
include { MMCIF_REPORT } from '../modules/mmcifreport'

params.pdb = "*.pdb"

workflow {
    ch_cif = PDB_TO_MMCIF(params.pdb).cif
    MMCIF_REPORT(ch_cif)
}

workflow CONVERT_REPORT {
    take: pdb

    main:
    ch_cif = PDB_TO_MMCIF(params.pdb).cif
    MMCIF_REPORT(ch_cif)

    emit:
    cif = ch_cif
}