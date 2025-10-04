# Implementation Summary: Native S3 Paths in Final load_data.csv

## Objective
Replace staged file paths with native S3 paths ONLY in the final aggregated `load_data.csv` file (created by `collectFile`), while keeping intermediate `load_data.csv` files unchanged with staged paths for CellProfiler processing.

## Changes Made

### 1. New Module: `modules/local/replace_paths_in_loaddata.nf`
Created a new process `REPLACE_PATHS_IN_LOADDATA` that:
- Takes the aggregated `load_data.csv` from `collectFile`
- Takes metadata containing filename-to-native_path mappings from all samples
- Transforms the CSV by replacing staged file paths with native S3 paths in `FileName_*` fields
- Publishes the transformed CSV as `combined_analysis.load_data.csv` to the output directory

**Key Features:**
- Uses Python script embedded in the process
- Builds a mapping dictionary from metadata: `basename -> native_path`
- Processes each row and replaces paths in any field starting with `FileName_`
- Preserves all other CSV content unchanged
- Uses `publishDir` directive to automatically save to the correct location

### 2. Updated Workflow: `workflows/nf-pooled-cellpainting.nf`
Modified the combined analysis section to:
1. Include the new `REPLACE_PATHS_IN_LOADDATA` process
2. Collect all image metadata from `ch_cropped_images` channel
3. Apply path transformation after `collectFile` aggregation
4. Automatically publish the final CSV with native S3 paths

**Workflow Flow:**
```
ch_cropped_images (contains metadata_for_json with image_metadata)
  ↓
CELLPROFILER_COMBINEDANALYSIS (produces load_data.csv with staged paths)
  ↓
collectFile (aggregates all load_data.csv files)
  ↓
REPLACE_PATHS_IN_LOADDATA (transforms paths to native S3)
  ↓
Published to: ${params.outdir}/workspace/load_data_csv/combined_analysis.load_data.csv
```

**Code Changes:**
- Added `include { REPLACE_PATHS_IN_LOADDATA }` statement
- Collected metadata: `ch_all_metadata = ch_cropped_images.map { ..., metadata_for_json -> metadata_for_json.image_metadata }.flatten().collect()`
- Assigned collectFile output: `ch_aggregated_csv = CELLPROFILER_COMBINEDANALYSIS.out.load_data_csv.collectFile(...)`
- Called transformation process: `REPLACE_PATHS_IN_LOADDATA(ch_aggregated_csv, ch_all_metadata)`

## What Was NOT Changed
- **Intermediate load_data.csv files**: Still generated with staged paths by individual processes (illumcalc, illumapply, combinedanalysis)
- **CellProfiler processing**: Continues to use staged paths (as required for proper operation)
- **Other modules**: No changes to bin/generate_load_data_csv.py or any other processes

## Metadata Flow
The metadata containing native S3 paths flows through the workflow as follows:

1. **Input**: Created during image cropping/grouping in the workflow
   ```groovy
   image_metas = [
       [filename: "image1.tiff", native_path: "s3://bucket/path/image1.tiff", ...],
       [filename: "image2.tiff", native_path: "s3://bucket/path/image2.tiff", ...],
       ...
   ]
   ```

2. **Wrapped in metadata_for_json**: Passed to `CELLPROFILER_COMBINEDANALYSIS`
   ```groovy
   metadata_for_json = [
       plate: "plate1",
       batch: "batch1",
       image_metadata: image_metas
   ]
   ```

3. **Collected**: Extracted from all samples and flattened
   ```groovy
   ch_all_metadata = ch_cropped_images
       .map { meta, images, metadata_for_json -> metadata_for_json.image_metadata }
       .flatten()
       .collect()
   ```

4. **Used for transformation**: Passed to `REPLACE_PATHS_IN_LOADDATA` as a value channel

## Testing Recommendations

### 1. Verify Intermediate Files
Check that intermediate `load_data.csv` files still have staged paths:
```bash
# These should still have staged paths (e.g., "./images/filename.tiff")
cat work/**/illumcalc/load_data.csv
cat work/**/illumapply/load_data.csv
cat work/**/combinedanalysis/load_data.csv
```

### 2. Verify Final File
Check that the final aggregated file has native S3 paths:
```bash
# This should have native S3 paths (e.g., "s3://bucket/path/filename.tiff")
cat ${params.outdir}/workspace/load_data_csv/combined_analysis.load_data.csv
```

### 3. Verify CellProfiler Still Works
Ensure CellProfiler processes can still access staged files during execution:
```bash
# Check CellProfiler logs for successful image loading
cat .nextflow.log | grep -i "cellprofiler"
```

### 4. Check Metadata Propagation
Verify that all image metadata is correctly collected:
```bash
# Run with -with-trace to see channel operations
nextflow run ... -with-trace
```

## Expected Behavior

**Before this change:**
- Final `combined_analysis.load_data.csv` had staged paths (e.g., `./images/filename.tiff`)
- Downstream tools needed to resolve these paths or couldn't access the files

**After this change:**
- Intermediate `load_data.csv` files: Unchanged, still have staged paths (✓ CellProfiler works)
- Final `combined_analysis.load_data.csv`: Has native S3 paths (✓ Downstream tools can access)

## Troubleshooting

### If paths are not being replaced:
1. Check that metadata contains `filename` and `native_path` fields
2. Verify the basename matching logic (the script tries both basename and full filename)
3. Check the process log for "Transformed X rows" message

### If CellProfiler fails:
1. Verify intermediate `load_data.csv` files still have staged paths
2. Check that the transformation only affects the final aggregated CSV
3. Confirm the `REPLACE_PATHS_IN_LOADDATA` process is only called after `collectFile`

### If the final CSV is not published:
1. Check that `params.outdir` is correctly set
2. Verify the `publishDir` directive in the process definition
3. Confirm the process completed successfully (check `.nextflow.log`)

## Files Modified
- `workflows/nf-pooled-cellpainting.nf`: Added include, metadata collection, and process call
- `modules/local/replace_paths_in_loaddata.nf`: New file with transformation process

## Files NOT Modified
- `bin/generate_load_data_csv.py`: Unchanged (still generates staged paths)
- `modules/local/cellprofiler/illumcalc/main.nf`: Unchanged
- `modules/local/cellprofiler/illumapply/main.nf`: Unchanged
- `modules/local/cellprofiler/combinedanalysis/main.nf`: Unchanged
