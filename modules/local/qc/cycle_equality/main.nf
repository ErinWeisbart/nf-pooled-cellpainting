process QC_CYCLE_EQUALITY {
    tag "${meta.id}_${stage}"
    label 'process_low'

    container "${workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container
        ? 'oras://community.wave.seqera.io/library/pip_numpy_scikit-image:56e0d6a8df025890'
        : 'community.wave.seqera.io/library/pip_numpy_scikit-image:9c9207913d10b50f'}"

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
