nextflow.enable.dsl=2

process MMCIF_TO_CHAINS {
    publishDir "results", saveAs: { filename -> task.name + '/' + filename }

    input:
    path mmcif

    output:
    path "chain_*.cif", emit: cif

    script:
    """
    #!/usr/bin/env python

    import atomium
    pdb = atomium.open("$mmcif")

    # Remove this bit once atomium is fixed
    if not pdb.model.chains():
        pdb = atomium.fetch("$mmcif".split("/")[-1].split(".")[0])

    for chain in sorted(pdb.model.chains(), key=lambda c: c.id):
        print(chain)
        chain.save(f"chain_{chain.id}.cif")
    """
}