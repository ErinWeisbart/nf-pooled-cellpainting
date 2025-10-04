# Staging Migration Status

## Migration Overview

This document tracks the migration from incremental staging patterns to metadata-based staging patterns across CellProfiler modules in the nf-pooled-cellpainting pipeline.

**Migration Date**: 2026-04-21  
**Status**: ✅ Code Complete, ⚠️ Testing Pending

---

## Module Status

### ✅ Migrated Modules

#### 1. CELLPROFILER_ILLUMCALC
- **File**: `modules/local/cellprofiler/illumcalc/main.nf`
- **Status**: ✅ Migrated
- **Pattern Before**: `stageAs: "images*/*"`
- **Pattern After**: `{plate}-{well}-{site}/`
- **Changes**:
  - Removed `stageAs` directive from input
  - Added Python script for metadata-based organization
  - Generates `staged_paths.json` for CSV compatibility
- **Testing Status**: ⚠️ Pending

#### 2. CELLPROFILER_ILLUMAPPLY
- **File**: `modules/local/cellprofiler/illumapply/main.nf`
- **Status**: ✅ Migrated
- **Pattern Before**: `stageAs: "images/img?/*"`
- **Pattern After**: `images/{plate}-{well}-{site}/`
- **Changes**:
  - Removed `stageAs` directive from input
  - Added Python script for metadata-based organization
  - Maintains `.npy` files in `images/` directory
  - Generates `staged_paths.json` for CSV compatibility
- **Testing Status**: ⚠️ Pending

### ℹ️ Other CellProfiler Modules (Not Migrated)

These modules don't use staging patterns that need migration:

#### 3. CELLPROFILER_SEGCHECK
- **File**: `modules/local/cellprofiler/segcheck/main.nf`
- **Staging**: No `stageAs` directive used
- **Action**: No changes needed

#### 4. CELLPROFILER_PREPROCESS
- **File**: `modules/local/cellprofiler/preprocess/main.nf`
- **Staging**: No `stageAs` directive used
- **Action**: No changes needed

#### 5. CELLPROFILER_COMBINEDANALYSIS
- **File**: `modules/local/cellprofiler/combinedanalysis/main.nf`
- **Staging**: No `stageAs` directive used
- **Action**: No changes needed

---

## Supporting Files

### ✅ Unchanged (Compatibility Maintained)

#### bin/generate_load_data_csv.py
- **Status**: ✅ No changes required
- **Reason**: Uses `staged_paths.json` mapping, works with both old and new patterns
- **Functions affected**: `load_staged_paths()`, `remap_filename()`

---

## Documentation Status

### ✅ Created Documentation

1. **CHANGES_QUICK_REFERENCE.md** - Quick overview of changes
2. **STAGING_CHANGES_COMPARISON.md** - Side-by-side before/after comparison
3. **STAGING_CHANGES_SUMMARY.md** - Comprehensive technical summary
4. **STAGING_MIGRATION_STATUS.md** - This document (migration status and testing plan)

---

## Testing Plan

### Phase 1: Unit Testing

#### Test 1: ILLUMCALC Staging Script
**Objective**: Verify metadata-based file organization works correctly

**Test Cases**:
1. **Single plate, multiple wells**
   - Metadata: Plate1, wells A01-A12, site 1
   - Expected: 12 directories (`Plate1-A01-1/`, ..., `Plate1-A12-1/`)
   
2. **Multiple sites per well**
   - Metadata: Plate1, well A01, sites 1-4
   - Expected: 4 directories (`Plate1-A01-1/`, ..., `Plate1-A01-4/`)

3. **Multiple plates**
   - Metadata: Plate1 and Plate2, various wells
   - Expected: Separate directories for each plate-well-site combination

4. **Missing metadata**
   - Input: File without metadata entry
   - Expected: File kept as-is (not moved)

5. **Special characters**
   - Metadata: Plate names with underscores, hyphens
   - Expected: Valid directory names created

**Validation**:
```bash
# Check directory structure
ls -R work/task_id/

# Verify staged_paths.json
cat work/task_id/staged_paths.json | jq .

# Confirm all files moved correctly
find work/task_id/ -name "*.tif" | wc -l
```

#### Test 2: ILLUMAPPLY Staging Script
**Objective**: Verify metadata-based organization under `images/` directory

**Test Cases**:
1. **Standard organization**
   - Metadata: Various plate-well-site combinations
   - Expected: Organized under `images/{plate}-{well}-{site}/`

2. **NPY file handling**
   - Input: Mix of image files and `.npy` illumination corrections
   - Expected: `.npy` files stay in `images/`, image files organized into subdirs

3. **Path relativity**
   - Check `staged_paths.json` contains paths relative to `images/`
   - Expected: Paths like `Plate1-A01-1/file.tif` (not `images/Plate1-A01-1/file.tif`)

**Validation**:
```bash
# Check images/ directory structure
ls -R work/task_id/images/

# Verify .npy files are in images/ root
find work/task_id/images/ -maxdepth 1 -name "*.npy"

# Check staged_paths.json relativity
cat work/task_id/staged_paths.json | jq .
```

### Phase 2: Integration Testing

#### Test 3: ILLUMCALC End-to-End
**Objective**: Verify complete ILLUMCALC process works with new staging

**Steps**:
1. Run ILLUMCALC module with test dataset
2. Check directory organization
3. Verify `load_data.csv` generation
4. Verify CellProfiler execution succeeds
5. Verify `.npy` output files created

**Test Data**:
- Small dataset: 2 plates, 4 wells, 2 sites = 16 image files
- Channels: DNA, ER, Mito (3 channels per site)
- Total files: 48 input images

**Success Criteria**:
- ✅ Directories created with correct naming
- ✅ `load_data.csv` has correct file paths
- ✅ CellProfiler runs without path errors
- ✅ Illumination correction `.npy` files generated
- ✅ Process completes without errors

#### Test 4: ILLUMAPPLY End-to-End
**Objective**: Verify complete ILLUMAPPLY process works with new staging

**Steps**:
1. Run ILLUMAPPLY module with test dataset and illumination corrections
2. Check `images/` directory organization
3. Verify `.npy` files in correct location
4. Verify `load_data.csv` generation
5. Verify CellProfiler execution succeeds
6. Verify corrected `.tiff` output files created

**Test Data**:
- Same dataset as ILLUMCALC test
- Plus: Illumination correction `.npy` files from ILLUMCALC

**Success Criteria**:
- ✅ Image files organized under `images/{plate}-{well}-{site}/`
- ✅ `.npy` files in `images/` root
- ✅ `load_data.csv` has correct relative paths
- ✅ CellProfiler runs without path errors
- ✅ Corrected `.tiff` files generated
- ✅ Process completes without errors

### Phase 3: Regression Testing

#### Test 5: Output Comparison
**Objective**: Verify outputs are functionally identical to previous version

**Method**:
1. Run old version on test dataset → capture outputs
2. Run new version on same test dataset → capture outputs
3. Compare:
   - Illumination correction `.npy` files (should be identical)
   - Corrected image statistics (should match)
   - CSV structure (may differ in paths, but data should be equivalent)

**Comparison Script**:
```python
import numpy as np
import pandas as pd

# Compare .npy files
old_illum = np.load('old/Plate1_IllumDNA.npy')
new_illum = np.load('new/Plate1_IllumDNA.npy')
assert np.allclose(old_illum, new_illum), "Illumination corrections differ!"

# Compare CSV row counts and metadata
old_csv = pd.read_csv('old/load_data.csv')
new_csv = pd.read_csv('new/load_data.csv')
assert len(old_csv) == len(new_csv), "Row count mismatch!"
assert set(old_csv.columns) == set(new_csv.columns), "Column mismatch!"
```

**Success Criteria**:
- ✅ Illumination corrections numerically identical
- ✅ Same number of rows in load_data.csv
- ✅ Same metadata values (plate, well, site, cycle)
- ✅ Corrected image statistics match (within numerical precision)

### Phase 4: Edge Case Testing

#### Test 6: Edge Cases
**Objective**: Verify robustness with unusual inputs

**Test Cases**:
1. **Empty metadata**: No image_metas provided
2. **Partial metadata**: Some files have metadata, others don't
3. **Duplicate filenames**: Same filename with different plate/well/site
4. **Very long names**: Plate names with 50+ characters
5. **Unicode characters**: Plate/well names with special Unicode
6. **Large datasets**: 1000+ images, 96 wells, 9 sites

**Success Criteria**:
- ✅ Graceful handling of missing/partial metadata
- ✅ No crashes on edge cases
- ✅ Clear error messages for invalid inputs
- ✅ Performance remains acceptable with large datasets

---

## Test Datasets

### Recommended Test Data Locations

1. **Test data repository**: `tests/data/staging_migration/`
2. **Real dataset (small)**: Use subset of actual experimental data
   - 2 plates, 8 wells, 2 sites = 32 images
   - All channels present
3. **Synthetic data**: Generate test images with controlled metadata

### Test Data Structure
```
tests/data/staging_migration/
├── illumcalc/
│   ├── metadata.json
│   ├── image_001.tif
│   ├── image_002.tif
│   └── ...
├── illumapply/
│   ├── metadata.json
│   ├── image_001.tif
│   ├── image_002.tif
│   ├── Plate1_IllumDNA.npy
│   ├── Plate1_IllumER.npy
│   └── ...
└── expected_outputs/
    ├── illumcalc/
    │   └── load_data.csv
    └── illumapply/
        └── load_data.csv
```

---

## Rollback Plan

If issues are discovered during testing:

### Immediate Rollback
```bash
# Revert the two module files
git checkout HEAD~1 -- modules/local/cellprofiler/illumcalc/main.nf
git checkout HEAD~1 -- modules/local/cellprofiler/illumapply/main.nf
```

### Gradual Rollback
1. Add feature flag to enable/disable new staging
2. Allow users to choose between old and new patterns
3. Deprecate old pattern after successful testing period

---

## Performance Benchmarks

### Expected Performance Impact

**File Organization Overhead**:
- Small datasets (< 100 images): < 1 second
- Medium datasets (100-1000 images): 1-5 seconds  
- Large datasets (1000+ images): 5-15 seconds

**Benefit**:
- Debugging time saved: Minutes to hours per issue
- Reduced troubleshooting complexity

**Net Impact**: Small upfront cost, significant long-term benefit

---

## Success Metrics

Migration will be considered successful when:

- ✅ All unit tests pass
- ✅ All integration tests pass  
- ✅ Regression tests show equivalent outputs
- ✅ Edge cases handled gracefully
- ✅ Performance impact < 5% of total runtime
- ✅ Documentation complete and reviewed
- ✅ Team sign-off obtained

---

## Timeline

| Phase | Tasks | Estimated Duration | Status |
|-------|-------|-------------------|--------|
| **Code Migration** | Modify ILLUMCALC and ILLUMAPPLY modules | 2-4 hours | ✅ Complete |
| **Documentation** | Create 4 documentation files | 2-3 hours | ✅ Complete |
| **Unit Testing** | Tests 1-2 | 4-6 hours | ⚠️ Pending |
| **Integration Testing** | Tests 3-4 | 6-8 hours | ⚠️ Pending |
| **Regression Testing** | Test 5 | 4-6 hours | ⚠️ Pending |
| **Edge Case Testing** | Test 6 | 2-4 hours | ⚠️ Pending |
| **Review & Sign-off** | Code review, team approval | 2-3 days | ⚠️ Pending |
| **Deployment** | Merge to main branch | 1 hour | ⚠️ Pending |

**Total Estimated Effort**: 20-30 hours of active work + review time

---

## Contact & Support

For questions about this migration:
- **Technical Lead**: [Your Name]
- **Code Review**: [Reviewer Name]
- **Testing Support**: [Tester Name]

---

## References

- **Code changes**: See git commit history
- **Technical details**: `STAGING_CHANGES_SUMMARY.md`
- **Quick reference**: `CHANGES_QUICK_REFERENCE.md`
- **Comparison**: `STAGING_CHANGES_COMPARISON.md`
