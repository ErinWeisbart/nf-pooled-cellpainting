# Illumination Correction QC Implementation Summary

## Overview
Successfully implemented a new QC step that generates before/after comparison reports showing raw images vs illumination-corrected images for visual quality assessment.

## Implementation Details

### 1. Python Script: `bin/qc_illum_compare.py`
**Purpose:** Generate side-by-side comparison montages of raw and corrected images

**Key Features:**
- Loads raw and corrected images using scikit-image
- Downsamples images by 4x to reduce file size
- Normalizes images to 0-1 range for consistent display
- Creates side-by-side montages with labeled columns (Raw | Corrected)
- Outputs PNG comparison images

**Usage:**
```bash
python qc_illum_compare.py \\
  --raw_images image1.tif image2.tif \\
  --corrected_images corr1.tif corr2.tif \\
  --channels DNA ER \\
  --output_dir ./qc_output \\
  --prefix batch1_plate1_A01_s1
```

**Dependencies:**
- numpy
- scikit-image (skimage)
- argparse
- pathlib

### 2. Nextflow Module: `modules/local/qc/illumcompare/main.nf`
**Purpose:** Nextflow wrapper for the QC script

**Inputs:**
- `tuple val(meta), path(raw_images), path(corrected_images)` - Raw and corrected images with metadata
- `val downsample_factor` - Downsample factor for image reduction (default: 4)

**Outputs:**
- `qc_reports` - PNG comparison images
- `versions` - Software version tracking

**Features:**
- Automatically extracts channel names from metadata
- Constructs output prefix from batch/plate/well/site
- Publishes reports to `{outdir}/qc/illum_compare/` directory
- Tracks Python version for reproducibility

### 3. Workflow Integration: `subworkflows/local/cellpainting/main.nf`
**Location:** Integrated before CELLPROFILER_SEGCHECK step

**Channel Logic:**
1. **Select First Raw Site:**
   - Takes `ch_images_by_site` channel
   - Creates deterministic sort key (batch_plate_well_site)
   - Sorts and selects first site
   - Preserves metadata and channel information

2. **Select First Corrected Site:**
   - Takes `CELLPROFILER_ILLUMAPPLY_PAINTING.out.corrected_images`
   - Creates matching sort key
   - Sorts and selects first site

3. **Combine Channels:**
   - Joins raw and corrected by site key (batch, plate, well, site)
   - Passes to QC_ILLUMCOMPARE module

**Why First Site Only?**
- Reduces QC overhead - one representative sample per run
- Sufficient for visual validation of correction quality
- Deterministic selection ensures reproducibility

## File Structure
```
nf-pooled-cellpainting/
├── bin/
│   └── qc_illum_compare.py              # QC script
├── modules/local/qc/illumcompare/
│   └── main.nf                          # Nextflow module
└── subworkflows/local/cellpainting/
    └── main.nf                          # Integration point (modified)
```

## Output Location
QC reports are published to:
```
{outdir}/qc/illum_compare/{batch}_{plate}_{well}_{site}_illum_compare_{channel}.png
```

Example:
```
results/qc/illum_compare/batch1_plate001_A01_s1_illum_compare_DNA.png
results/qc/illum_compare/batch1_plate001_A01_s1_illum_compare_ER.png
results/qc/illum_compare/batch1_plate001_A01_s1_illum_compare_Mito.png
```

## Testing Recommendations
1. **Test with minimal data:**
   - Run pipeline with 1 plate, 1 well, 1 site
   - Verify QC images are generated
   - Check that images show clear before/after differences

2. **Visual inspection:**
   - Verify montages show raw images (left) vs corrected images (right)
   - Confirm channel names match actual image content
   - Check that corrections remove illumination gradients

3. **Integration test:**
   - Confirm QC step runs before SEGCHECK
   - Verify no disruption to downstream processes
   - Check that versions are properly tracked

## Design Decisions

### Why Downsample by 4x?
- Original microscopy images can be 2000+ x 2000+ pixels
- 4x downsampling (500x500) maintains visual quality while reducing file size
- PNG outputs remain manageable for viewing and storage

### Why Select First Site Deterministically?
- Alphabetical/numerical sorting ensures same site is always selected
- Reproducible across pipeline runs
- Simplifies comparison between different pipeline versions

### Why Side-by-Side Layout?
- Easy visual comparison of correction effectiveness
- Clear labeling prevents confusion
- Standard format for before/after comparisons

## Potential Enhancements
1. **Add statistics overlay:**
   - Mean intensity before/after
   - Standard deviation reduction
   - Correlation coefficient

2. **Multi-site comparison:**
   - Add parameter to select N sites instead of just 1
   - Create grid layout for multiple sites

3. **Interactive HTML report:**
   - Use Plotly or similar for zoomable comparisons
   - Add image intensity histograms
   - Include metadata table

4. **Automated quality metrics:**
   - Calculate coefficient of variation reduction
   - Flag images with poor correction
   - Generate summary statistics table

## Code Quality
- ✅ Follows Nextflow DSL2 strict syntax
- ✅ Explicit closure parameters throughout
- ✅ Proper channel namespace usage
- ✅ No deprecated operators
- ✅ Clean map/join operations
- ✅ Comprehensive error handling in Python script
- ✅ Proper version tracking

## Dependencies Added
**Python packages** (already available in container):
- numpy
- scikit-image

**No new containers needed** - existing Python environment has all required packages.

## Next Steps for User
1. Test the implementation with a small dataset
2. Review generated QC images for quality
3. Consider adding to MultiQC report if desired
4. Adjust downsample factor if needed (parameter in module call)
5. Optionally expand to multiple sites if needed

## Contact/Support
This implementation follows the existing QC patterns in the pipeline (similar to QC_MONTAGEILLUM) and integrates seamlessly with the current workflow structure.
