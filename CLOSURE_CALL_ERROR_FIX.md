# Fix for Closure Call Error in Combined Analysis

## Problem Summary

**Error Message:**
```
No signature of method: Script_4bb0d8c1e1eebd94$_runScript_closure1$_closure2$_closure29.call() 
is applicable for argument types: (LinkedList) 
values: [[[batch:2026_03_20_Batch1, plate:BR00149745, well:E03, channels:Brightfield, arm:painting, ...], ...]]
```

**Location:** `workflows/nf-pooled-cellpainting.nf`, line 147

**Root Cause:** 
The closure after `.groupTuple(by: 0)` was using implicit tuple destructuring with multiple parameters:
```groovy
.map { group_key, meta_list, images_list ->
```

In Nextflow's strict syntax mode (v25.10+), when `groupTuple` returns a tuple, attempting to destructure it implicitly in the closure parameter list causes a method signature mismatch. The closure receives a **LinkedList** (the entire tuple), but the parameter pattern expects individual arguments.

## The Fix

**Before (BROKEN):**
```groovy
.groupTuple(by: 0)
.map { group_key, meta_list, images_list ->
    // Use first meta (they should all be identical for common fields like batch, plate, well, site)
    def common_meta = meta_list[0]
```

**After (FIXED):**
```groovy
.groupTuple(by: 0)
.map { tuple ->
    // Extract grouped values from tuple
    def group_key = tuple[0]
    def meta_list = tuple[1]
    def images_list = tuple[2]
    
    // Use first meta (they should all be identical for common fields like batch, plate, well, site)
    def common_meta = meta_list[0]
```

## Why This Works

1. **Explicit tuple handling**: The closure now accepts a single parameter `tuple` containing the full tuple
2. **Manual destructuring**: Values are extracted using array indexing (`tuple[0]`, `tuple[1]`, `tuple[2]`)
3. **Compatible with strict syntax**: This pattern is fully compatible with Nextflow v25.10+ strict syntax requirements

## Changes Made

- **File**: `workflows/nf-pooled-cellpainting.nf`
- **Lines**: 147-151 (added explicit tuple extraction)
- **Impact**: Resolves the method signature error in combined analysis section

## Testing Recommendation

After applying this fix, test the workflow with:
```bash
nextflow run main.nf -profile <your_profile> --input <samplesheet> \
  --qc_painting_passed true --qc_barcoding_passed true
```

The combined analysis section should now execute without the closure call error.

## Related Issues

This fix follows the same pattern used in the previous fix documented in `FIX_CLOSURE_INVOCATION_ERROR.md`, ensuring consistency across the codebase with Nextflow strict syntax compliance.
