nextflow.enable.dsl = 2

process runIsoToAniso {
    debug true
    publishDir "results", mode:"copy"

    input:
    path x, stageAs: "input.cif"

    output:
    path "epoxide.cif"

    shell:
    '''
    /opt/qcrbox/venv/bin/qcb list applications
    /opt/qcrbox/venv/bin/qcb list commands
    /opt/qcrbox/venv/bin/qcb list containers
    echo "-----------------------------------------------------------------------------------------------"
    /opt/qcrbox/venv/bin/qcb invoke --command-id=1 --with-args='{"input_cif_file": "input.cif", "insert_anis_directive": "True"}'
    '''
}

workflow {
    def input_cif = Channel.fromPath("data/start.cif")

    main:
    runIsoToAniso(input_cif)

    emit:
    runIsoToAniso.out
}

