process REPLACE_PATHS_IN_LOADDATA {
    tag "load_data_csv"
    label 'process_single'
    publishDir "${params.outdir}/workspace/load_data_csv", mode: 'copy', saveAs: { "combined_analysis.load_data.csv" }

    input:
    path load_data_csv
    val metadata

    output:
    path "load_data_with_native_paths.csv", emit: csv

    script:
    def metadata_json = groovy.json.JsonOutput.toJson(metadata)
    """
    python3 <<'EOF'
import csv
import json
import sys
import os

# Load metadata
metadata = json.loads('''${metadata_json}''')

# Build mapping from filename to native_path
filename_to_native = {}
for record in metadata:
    filename = record.get('filename', '')
    native_path = record.get('native_path', '')
    if filename and native_path:
        # Store by basename in case paths are relative
        basename = os.path.basename(filename)
        filename_to_native[basename] = native_path
        # Also store with full filename
        filename_to_native[filename] = native_path

# Read input CSV and transform paths
with open('${load_data_csv}', 'r') as infile:
    reader = csv.DictReader(infile)
    fieldnames = reader.fieldnames
    rows = []
    
    for row in reader:
        # Process each field that starts with 'FileName_'
        for field in fieldnames:
            if field.startswith('FileName_') and row.get(field):
                original_path = row[field]
                basename = os.path.basename(original_path)
                
                # Replace with native path if found
                if basename in filename_to_native:
                    row[field] = filename_to_native[basename]
        
        rows.append(row)

# Write output CSV
with open('load_data_with_native_paths.csv', 'w', newline='') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"Transformed {len(rows)} rows", file=sys.stderr)
EOF
    """
}
