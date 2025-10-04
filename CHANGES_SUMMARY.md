# QC_ILLUMCOMPARE Report Publishing Configuration

## Summary
Added publishing configuration for the `QC_ILLUMCOMPARE` process to output reports to the `qc_reports` directory so they appear in the Seqera Platform Reports tab.

## Changes Made

### File: `conf/modules.config`

Added a new `publishDir` configuration for the `QC_ILLUMCOMPARE` process:

```groovy
withName: QC_ILLUMCOMPARE {
    publishDir = [
        path: { "${params.outdir}/workspace/qc_reports/2_illumination_comparison/${meta.plate}" },
        pattern: "*.{png}",
        mode: params.publish_dir_mode,
        saveAs: { filename -> filename.equals('versions.yml') ? null : filename },
    ]
}
```

## Output Location
The illumination comparison PNG reports will now be published to:
```
<outdir>/workspace/qc_reports/2_illumination_comparison/<plate_id>/
```

This follows the existing QC report structure:
- `1_illumination_painting/` - Illumination correction profiles (painting)
- **`2_illumination_comparison/`** - ⭐ NEW: Raw vs corrected image comparison
- `3_segmentation/` - Segmentation check montages
- `4_stitching_painting/` - Stitching results (painting)
- `5_illumination_barcoding/` - Illumination correction profiles (barcoding)
- `6_alignment/` - Barcode alignment reports
- `7_preprocessing/` - Preprocessing reports
- `8_stitching_barcoding/` - Stitching results (barcoding)

## Process Details
- **Process**: `POOLED_CELLPAINTING:CELLPAINTING:QC_ILLUMCOMPARE`
- **Output**: PNG images comparing raw and illumination-corrected images
- **Metadata**: Organized by plate ID
- **Pattern**: All `*.png` files (excludes `versions.yml`)

## Testing
After this change, when the workflow runs:
1. The `QC_ILLUMCOMPARE` process will generate comparison PNG files
2. These will be published to `qc_reports/2_illumination_comparison/<plate>/`
3. The reports will automatically appear in the Seqera Platform Reports tab

## Next Steps
Commit and push these changes to the `feature/single-channel` branch, then re-run the workflow to see the reports in the Seqera Platform.
