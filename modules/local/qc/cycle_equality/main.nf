process QC_CYCLE_EQUALITY {
    tag "${meta.id}_${stage}"
    label 'process_low'

    container 'wave.seqera.io/wt/3a135513c8da/library/numpy_python_pip_pillow:74310e9b76ff61b6'

    input:
    tuple val(meta), path(images)
    val stage  // 'illumapply' or 'preprocess'

    output:
    tuple val(meta), path("*_cycle_equality_report.txt"), emit: report
    path "versions.yml", emit: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    qc_cycle_equality.py \\
        --images ${images} \\
        --stage ${stage} \\
        --output ${prefix}_${stage}_cycle_equality_report.txt

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: \$(python3 --version | sed 's/Python //g')
        numpy: \$(python3 -c "import numpy; print(numpy.__version__)")
        skimage: \$(python3 -c "import skimage; print(skimage.__version__)")
    END_VERSIONS
    """
}
