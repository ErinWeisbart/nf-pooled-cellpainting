process QC_DUP_CHECK {
    tag "${meta.id}"
    label 'qc'

    container 'community.wave.seqera.io/library/ipykernel_jupytext_nbconvert_pandas_pruned:c397cee54f4ab064'

    input:
    tuple val(meta), path(csv_files)

    output:
    tuple val(meta), path("qc_dup_check_report_*.txt"), emit: report
    path "versions.yml", emit: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def mode = meta.containsKey('mode') ? meta.mode : 'illumapply'
    def report_name = "qc_dup_check_report_${meta.batch}_${meta.plate}_${mode}.txt"
    """
    # Create a directory to hold all CSV files
    mkdir -p csv_input
    
    # Copy all CSV files that end with Image.csv to the input directory
    # Use a counter to ensure unique filenames and avoid name collisions
    counter=0
    for file in ${csv_files}; do
        if [[ "\$file" == *Image.csv ]]; then
            # Create unique filename: counter_originalname
            basename=\$(basename "\$file")
            cp "\$file" "csv_input/\${counter}_\${basename}"
            counter=\$((counter + 1))
        fi
    done

    qc_dup_check.py \\
        ${mode} \\
        --input-dir ./csv_input \\
        --output-report ${report_name} \\
        --threshold 0.99 \\
        --batch ${meta.batch} \\
        --plate ${meta.plate}

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: \$(python --version | sed 's/Python //')
        pandas: \$(python -c "import pandas; print(pandas.__version__)")
    END_VERSIONS
    """

    stub:
    def mode = meta.containsKey('mode') ? meta.mode : 'illumapply'
    def report_name = "qc_dup_check_report_${meta.batch}_${meta.plate}_${mode}.txt"
    """
    touch ${report_name}

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: 3.11.0
        pandas: 2.0.0
    END_VERSIONS
    """
}
