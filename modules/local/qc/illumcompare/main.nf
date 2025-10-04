process QC_ILLUMCOMPARE {
    tag "${meta.plate}_${meta.well}_Site${meta.site}"
    label 'qc'

    container "community.wave.seqera.io/library/numpy_python_pip_pillow:74310e9b76ff61b6"

    input:
    tuple val(meta), path(raw_images, stageAs: "raw/*"), path(corrected_images, stageAs: "corrected/*")

    output:
    tuple val(meta), path("*.png"), emit: comparison
    path "versions.yml", emit: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def channels_list = meta.channels.join(',')
    """
    qc_illum_compare.py \\
        --raw-dir raw/ \\
        --corrected-dir corrected/ \\
        --output-dir . \\
        --batch ${meta.batch} \\
        --plate ${meta.plate} \\
        --well ${meta.well} \\
        --site ${meta.site} \\
        --channels "${channels_list}" \\
        --scale-factor 0.25

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        qc_illumcompare: 0.1.0
    END_VERSIONS
    """

    stub:
    """
    touch painting.${meta.batch}_${meta.plate}_${meta.well}_Site${meta.site}.illumcompare.png

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        qc_illumcompare: 0.1.0
    END_VERSIONS
    """
}
