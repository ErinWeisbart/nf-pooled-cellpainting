# Fix for Closure Invocation Error

## Problem

The workflow was failing with the following error:

```
ERROR ~ Error executing process > 'POOLED_CELLPAINTING:CELLPROFILER_COMBINEDANALYSIS (2026_03_20_Batch1_BR00149745_E03_1)'

Caused by:
  Invalid method invocation `call` with arguments: [[batch:2026_03_20_Batch1, plate:BR00149745, well:E03, ...], [list of files...]]
  on Script_4bb0d8c1e1eebd94$_runScript_closure1$_closure2$_closure29 method

  Possible solutions: any(), any(groovy.lang.Closure), wait(), run(), run(), equals(java.lang.Object)
```

## Root Cause

In `workflows/nf-pooled-cellpainting.nf` around line 148, the closure was incorrectly structured after the `groupTuple` operator:

**BEFORE (Incorrect):**
```groovy
.groupTuple(by: 0)
.map { tuple ->
    // Explicitly destructure the grouped tuple
    def _group_key = tuple[0]
    def meta_list = tuple[1]
    def images_list = tuple[2]
    // ... rest of code
}
```

**Issue:** The closure parameter `tuple` was receiving the grouped tuple as a single object, but the closure signature didn't properly destructure it. When Nextflow tried to invoke this closure with the actual grouped data `[group_key, [metadata_list], [images_list]]`, it caused a method invocation mismatch.

## Solution

The fix changes the closure signature to explicitly destructure the three components of the grouped tuple:

**AFTER (Correct):**
```groovy
.groupTuple(by: 0)
.map { group_key, meta_list, images_list ->
    // Use first meta (they should all be identical for common fields like batch, plate, well, site)
    def common_meta = meta_list[0]
    // ... rest of code
}
```

**Why this works:** By explicitly declaring the three parameters in the closure signature, Groovy/Nextflow can properly destructure the tuple when invoking the closure. This matches the structure returned by `groupTuple(by: 0)`, which produces tuples of the form `[grouping_key, [list_of_metas], [list_of_images]]`.

## Technical Details

The `groupTuple(by: 0)` operator groups elements by the first element (index 0) and produces tuples where:
- Position 0: The grouping key (in this case, a string like "batch_plate_well_site")
- Position 1: A list of all metadata maps from the grouped elements
- Position 2: A list of all image files from the grouped elements

The closure must match this structure exactly for proper invocation.

## Changes Made

**File:** `workflows/nf-pooled-cellpainting.nf`
**Lines:** ~147-148
**Change:** Modified closure signature from `{ tuple ->` to `{ group_key, meta_list, images_list ->`
**Impact:** Fixes the method invocation error and allows the workflow to properly process combined cellpainting and barcoding images.

## Testing

After applying this fix:
1. The workflow should no longer fail with the "Invalid method invocation `call`" error
2. The CELLPROFILER_COMBINEDANALYSIS process should successfully receive the grouped images and metadata
3. Combined analysis should proceed normally when both `qc_painting_passed` and `qc_barcoding_passed` are true

## Recommendations

- Always use explicit parameter names in closures after operations like `groupTuple`, `join`, etc.
- Avoid generic parameter names like `tuple` when destructuring is needed
- Test channel operations with small datasets to catch signature mismatches early
