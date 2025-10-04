# QC Cycle Equality Check Implementation

## Overview
A new QC step that checks if images from different cycles are mathematically equal, running **before** the existing QC_PREPROCESS step.

## Purpose
Detects potential issues where cycle images are identical (which shouldn't happen in normal processing). This helps catch problems early in the pipeline.

## What It Does

### For ILLUMAPPLY Stage:
- Selects the **first plate/well/site** (sorted alphabetically)
- Loads all cycles and channels for that site
- For each channel: compares cycle 2, 3, ..., N against cycle 1
- Reports if any cycles are mathematically identical

### For PREPROCESS Stage:
- Selects the **first plate/well/site** (sorted alphabetically)  
- Loads all cycles and channels for that site
- For each channel: compares cycle 2, 3, ..., N against cycle 1
- Reports if any cycles are mathematically identical

## Implementation Details

### New Files Created:

1. **`modules/local/qc/cycle_equality/main.nf`**
   - Nextflow process module
   - Runs the Python QC script
   - Outputs: report text file and versions

2. **`bin/qc_cycle_equality.py`**
   - Python script using numpy and scikit-image
   - Compares images pixel-by-pixel using `np.array_equal()`
   - Generates human-readable QC reports

### Modified Files:

1. **`subworkflows/local/barcoding/main.nf`**
   - Added two `QC_CYCLE_EQUALITY` includes (one for ILLUMAPPLY, one for PREPROCESS)
   - Integrated cycle equality checks after each stage
   - Selection logic: sorts by plate_well_site and takes first entry

## Report Format

The QC generates a text report with:

```
================================================================================
QC CYCLE EQUALITY CHECK REPORT
================================================================================

SAMPLE INFORMATION:
  Stage:          illumapply
  Plate:          1
  Well:           A01
  Site:           1
  Total Images:   20
  Channels Tested: 5

OVERALL QC STATUS: ✓ PASSED
  No cycle images are identical to cycle 1.

================================================================================
DETAILED RESULTS BY CHANNEL:
================================================================================

Channel: DNA
  Status: PASSED
  Total Cycles: 4
  Message: All cycles are unique

Channel: ProteinA
  Status: PASSED
  Total Cycles: 4
  Message: All cycles are unique

...
```

If cycles ARE equal:
```
Channel: DNA
  Status: FAILED
  Total Cycles: 4
  Equal Cycles: [2, 3]
  Message: Cycle(s) [2, 3] are identical to cycle 1
```

## Integration Points

### ILLUMAPPLY Stage:
```groovy
CELLPROFILER_ILLUMAPPLY_BARCODING (...)
↓
QC_CYCLE_EQUALITY_ILLUMAPPLY (first plate/well/site, 'illumapply')
↓
QC_CYCLEDUP_ILLUMAPPLY (all sites)
```

### PREPROCESS Stage:
```groovy
CELLPROFILER_PREPROCESS (...)
↓
QC_CYCLE_EQUALITY_PREPROCESS (first plate/well/site, 'preprocess')
↓
QC_CYCLEDUP_PREPROCESS (all sites)
↓
QC_PREPROCESS (...)
```

## Channel Operations

### ILLUMAPPLY:
```groovy
ch_illumapply_qc_equality = CELLPROFILER_ILLUMAPPLY_BARCODING.out.corrected_images
    .map { group_meta, images, _csv ->
        def sort_key = "${group_meta.plate}_${group_meta.well}_${group_meta.site ?: '0'}"
        [sort_key, group_meta, images]
    }
    .toSortedList { a, b -> a[0] <=> b[0] }
    .flatMap { sorted_list ->
        sorted_list.isEmpty() ? [] : [[sorted_list[0][1], sorted_list[0][2]]]
    }
```

### PREPROCESS:
```groovy
ch_preprocess_qc_equality = CELLPROFILER_PREPROCESS.out.preprocessed_images
    .map { meta, images ->
        def sort_key = "${meta.plate}_${meta.well}_${meta.site ?: '0'}"
        [sort_key, meta, images]
    }
    .toSortedList { a, b -> a[0] <=> b[0] }
    .flatMap { sorted_list ->
        sorted_list.isEmpty() ? [] : [[sorted_list[0][1], sorted_list[0][2]]]
    }
```

## Key Features

1. **Early Detection**: Runs before QC_PREPROCESS to catch issues early
2. **Sample Selection**: Uses first plate/well/site (alphabetically sorted) for consistent testing
3. **Mathematical Comparison**: Uses `np.array_equal()` for exact pixel-by-pixel comparison
4. **Comprehensive Reporting**: Clear pass/fail status with detailed per-channel results
5. **Non-blocking**: Reports issues but doesn't stop pipeline execution

## Technical Notes

- **Container**: Uses Wave container with numpy and scikit-image
- **Memory**: Low memory footprint (only loads first site)
- **Performance**: Fast comparison using numpy's optimized array operations
- **Exit codes**: Returns 1 if QC fails, 0 if passes (for potential downstream conditional logic)

## Example Workflow

For a plate with:
- Plate: 1, 2
- Wells: A01, A02, B01
- Sites: 1, 2, 3
- Cycles: 1, 2, 3, 4
- Channels: DNA, ProteinA, ProteinB

The QC will test:
- **Selected sample**: Plate 1, Well A01, Site 1 (first alphabetically)
- **Images tested**: All cycles (1-4) × all channels (DNA, ProteinA, ProteinB)
- **Comparisons**: For each channel, compare cycles 2, 3, 4 against cycle 1

## Dependencies

- Python 3
- numpy
- scikit-image
- Nextflow DSL2

## Output Location

Reports are published according to the workflow's output configuration, typically:
- `{outdir}/qc/cycle_equality/illumapply/`
- `{outdir}/qc/cycle_equality/preprocess/`

---

**Status**: ✅ Implementation complete and verified
**Date**: 2026-04-20
