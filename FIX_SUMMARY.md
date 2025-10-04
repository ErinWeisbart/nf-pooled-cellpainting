# Fix Summary: load_data.csv Duplicate File Path Issue

## Problem Description

In the POOLED_CELLPAINTING:BARCODING:CELLPROFILER_ILLUMAPPLY_BARCODING workflow, the `load_data.csv` file was being generated incorrectly. The same staged file path was being entered in multiple columns (e.g., FileName_Cycle01_OrigDAPI, FileName_Cycle02_OrigDAPI, FileName_Cycle03_OrigDAPI, etc.) even though these should reference different files.

This occurred because files from different source directories had identical filenames (filename collision). After staging with Nextflow's `stageAs`, they were placed in different subdirectories (`images/img0/`, `images/img1/`, etc.), but the code was not properly distinguishing between them.

## Root Cause

The issue was in two places:

1. **Missing `staging_index` in ILLUMAPPLY metadata** (`subworkflows/local/barcoding/main.nf`):
   - ILLUMCALC properly added a `staging_index` to each image's metadata to handle duplicate filenames
   - ILLUMAPPLY did NOT add this index, so all files with the same basename were treated as identical

2. **Inadequate staged path mapping** (`modules/local/cellprofiler/illumapply/main.nf`):
   - The Python script that built `staged_paths.json` only mapped `{basename: path}`
   - When multiple files had the same basename, only the last one was kept in the mapping
   - The script didn't use the `staging_index` to create unique keys like `{basename|index: path}`

## Solution

### Change 1: Add staging_index to ILLUMAPPLY metadata

In `subworkflows/local/barcoding/main.nf` (around line 137-147), modified the channel mapping that prepares input for ILLUMAPPLY:

```groovy
// Before:
[group_meta, all_channels, unique_cycles, images_list, images_meta_list]

// After:
// Add staging_index to each image metadata to handle duplicate filenames
def indexed_metas = images_meta_list.withIndex().collect { img_meta, idx ->
    img_meta + [staging_index: idx]
}

[group_meta, all_channels, unique_cycles, images_list, indexed_metas]
```

This ensures each image metadata has a unique `staging_index` field that corresponds to its position in the staged file list.

### Change 2: Update staged_paths.json generation

In `modules/local/cellprofiler/illumapply/main.nf` (around line 30-42), replaced the simple mapping script with a more sophisticated one that:

1. Reads the metadata JSON to get staging indices for each file
2. Groups staged files by basename
3. Creates BOTH indexed keys (`basename|staging_index`) AND simple fallback keys (`basename`)
4. Properly maps each unique file to its correct staged path

```python
# Key logic:
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
```

## How It Works Together

1. When ILLUMAPPLY receives images, each image metadata now has a `staging_index` (0, 1, 2, ...)
2. The shell script reads this metadata and creates a mapping with indexed keys
3. The `generate_load_data_csv.py` script calls `remap_filename()` which:
   - First tries to look up `{basename}|{staging_index}` (exact match)
   - Falls back to `{basename}` if no indexed key exists
4. This ensures each file reference in the load_data.csv points to the correct staged path

## Files Modified

1. `subworkflows/local/barcoding/main.nf` - Added staging_index to ILLUMAPPLY metadata
2. `modules/local/cellprofiler/illumapply/main.nf` - Enhanced staged_paths.json generation script

## Testing Recommendation

After applying this fix, verify that the generated `load_data.csv` contains different file paths for each cycle:

```csv
Metadata_Plate,Metadata_Well,Metadata_Site,FileName_Cycle01_OrigDAPI,FileName_Cycle02_OrigDAPI,...
Plate1,A01,1,img0/file.tiff,img1/file.tiff,...
```

Instead of the incorrect output:
```csv
Metadata_Plate,Metadata_Well,Metadata_Site,FileName_Cycle01_OrigDAPI,FileName_Cycle02_OrigDAPI,...
Plate1,A01,1,img0/file.tiff,img0/file.tiff,...  # WRONG - same path repeated
```

## Note

This fix aligns ILLUMAPPLY with the pattern already used in ILLUMCALC, which has handled duplicate filenames correctly since the staging_index feature was implemented.
