nextflow.enable.dsl=2

process PDB_TO_MMCIF {
    publishDir "${params.outdir}",
        mode: params.publish_dir_mode,
        saveAs: { filename -> filename }

    publishDir "results", saveAs: { filename -> task.name + '/' + filename }

    input:
    path pdb

    output:
    path "*.cif", emit: cif

    script:
    """
    #!/usr/bin/env python

    import atomium
    pdb = atomium.open("$pdb")
    print(pdb.title)
    filename = "$pdb"
    filename = ".".join(filename.split(".")[:-1]) + ".cif"
    pdb.model.save(filename)
    """
}