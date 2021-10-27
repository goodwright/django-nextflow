nextflow.enable.dsl=2

process MMCIF_REPORT {
    publishDir "results", saveAs: { filename -> task.name + '/' + filename }

    input:
    path mmcif

    output:
    path "*.txt", emit: txt

    script:
    """
    #!/usr/bin/env python

    import atomium
    pdb = atomium.open("$mmcif")

    data = {
        "title": pdb.title,
        "atoms": len(pdb.model.atoms())
    }
    with open("report.txt", "w") as f:
        f.write("\\n".join([
            f"{key}: {value}" for key, value in data.items()
        ]))
    print("Saved!")
    """
}