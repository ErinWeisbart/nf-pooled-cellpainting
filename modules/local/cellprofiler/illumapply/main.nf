process CELLPROFILER_ILLUMAPPLY {
    tag "${meta.id}"
    label 'cellprofiler_basic'

    container "${workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container
        ? 'oras://community.wave.seqera.io/library/cellprofiler:4.2.8--7c1bd3a82764de92'
        : 'community.wave.seqera.io/library/cellprofiler:4.2.8--aff0a99749304a7f'}"

    input:
    tuple val(meta), val(channels), val(cycles), path(images, stageAs: "images/img?/*"), val(image_metas), path(npy_files, stageAs: "images/")
    path illumination_apply_cppipe
    val has_cycles

    output:
    tuple val(meta), path("*.tiff"), path("*.csv"), emit: corrected_images
    path "load_data.csv", emit: load_data_csv
    path "versions.yml", emit: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    // Serialize image metadata directly - it already contains all fields (plate, well, site, channels, filename, etc.)
    // Base64 encode to reduce log verbosity
    def metadata_json_content = groovy.json.JsonOutput.toJson(image_metas)
    def metadata_base64 = metadata_json_content.bytes.encodeBase64().toString()

    """
    # Create metadata JSON file from base64 (reduces log verbosity)
    echo '${metadata_base64}' | base64 -d > metadata.json

    # Build a JSON map of staged paths that handles duplicate filenames
    # Uses both basename and staging_index from metadata to create unique keys
    # CellProfiler uses --image-directory ./images/ so paths in load_data.csv must be
    # relative to that directory (e.g. img1/file.tiff, not images/img1/file.tiff)
    python3 -c "
import json, os, glob

# Read metadata to get staging indices
with open('metadata.json') as f:
    metadata = json.load(f)

# Create staging_index lookup: filename -> list of staging indices
filename_indices = {}
for record in metadata:
    filename = record['filename']
    staging_idx = record.get('staging_index', 0)
    if filename not in filename_indices:
        filename_indices[filename] = []
    filename_indices[filename].append(staging_idx)

# Build mapping from staged files
# Group staged files by basename
staged_by_basename = {}
for f in sorted(glob.glob('images/img*/*')):
    basename = os.path.basename(f)
    # Store path relative to 'images/' for CellProfiler
    relative_path = os.path.relpath(f, 'images')
    if basename not in staged_by_basename:
        staged_by_basename[basename] = []
    staged_by_basename[basename].append(relative_path)

# Create final mapping
mapping = {}
for basename, staged_paths in staged_by_basename.items():
    indices = filename_indices.get(basename, [])
    
    if len(staged_paths) == 1:
        # Only one file with this basename - simple mapping
        mapping[basename] = staged_paths[0]
        # Also create indexed keys for consistency
        for idx in indices:
            mapping[f'{basename}|{idx}'] = staged_paths[0]
    else:
        # Multiple files with same basename - use indexed keys
        for idx, path in zip(sorted(indices), sorted(staged_paths)):
            mapping[f'{basename}|{idx}'] = path
        # Also add a fallback simple key (points to first occurrence)
        mapping[basename] = sorted(staged_paths)[0]

print(json.dumps(mapping))
" > staged_paths.json

    # Generate load_data.csv
    generate_load_data_csv.py \\
        --pipeline-type illumapply \\
        --images-dir ./images \\
        --illum-dir ./images \\
        --output load_data.csv \\
        --metadata-json metadata.json \\
        --staged-paths-json staged_paths.json \\
        --channels "${channels}" \\
        --cycle-metadata-name "${params.cycle_metadata_name}" \\
        ${has_cycles ? '--has-cycles' : ''}

    # Patch Base image location to use Default Input Folder (staged images)
    # We need to copy the input file to a writable file first if it's a symlink or read-only
    cp -L ${illumination_apply_cppipe} illumination_apply_patched.cppipe
    sed -i 's/Base image location:None|/Base image location:Default Input Folder|/g' illumination_apply_patched.cppipe

    cellprofiler -c -r \\
        -p illumination_apply_patched.cppipe \\
        -o . \\
        --data-file=load_data.csv \\
        --image-directory ./images/

    cat <<-END_VERSIONS > versions.yml
	"${task.process}":
	    cellprofiler: \$(cellprofiler --version)
	END_VERSIONS
    """

    stub:
    // For barcoding (has_cycles=true): create files with _Cycle pattern that downstream regex expects
    // For painting (has_cycles=false): create painting-style files
    def stub_files = has_cycles ?
        """
        touch load_data.csv
        touch Plate_${meta.plate}_Well_${meta.well}_Site_${meta.site ?: 1}_Cycle01_DNA.tiff
        touch Plate_${meta.plate}_Well_${meta.well}_Site_${meta.site ?: 1}_Cycle01_A.tiff
        touch BarcodingIllumApplication_Cells.csv
        touch BarcodingIllumApplication_ConfluentRegions.csv
        touch BarcodingIllumApplication_Experiment.csv
        touch BarcodingIllumApplication_Image.csv
        touch BarcodingIllumApplication_Nuclei.csv
        """ :
        """
        touch load_data.csv
        touch Plate_${meta.plate}_Well_${meta.well}_Site_${meta.site ?: 1}_CorrPhalloidin.tiff
        touch PaintingIllumApplication_Cells.csv
        touch PaintingIllumApplication_ConfluentRegions.csv
        touch PaintingIllumApplication_Experiment.csv
        touch PaintingIllumApplication_Image.csv
        touch PaintingIllumApplication_Nuclei.csv
        """
    """
    ${stub_files}

    cat <<-END_VERSIONS > versions.yml
	"${task.process}":
	    cellprofiler: \$(cellprofiler --version)
	END_VERSIONS
    """
}
