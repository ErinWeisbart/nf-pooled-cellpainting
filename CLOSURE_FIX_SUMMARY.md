# Closure Parameter Fix Summary

## Problem
The workflow was failing with the error:
```
No signature of method: Script_4bb0d8c1e1eebd94$_runScript_closure1$_closure2$_closure29.call() 
is applicable for argument types: (LinkedList) values: [[[batch:2026_03_20_Batch1, plate:BR00149745, ...], ...]]
```

This error occurs when a closure expects multiple parameters (e.g., `meta, image`) but receives a single tuple (LinkedList) containing those elements.

## Root Cause
In Nextflow DSL2, when channels emit tuples, the closure receives the tuple as a single parameter rather than destructured parameters. This is especially true in strict syntax mode (v25.10+).

## Files Fixed

### workflows/nf-pooled-cellpainting.nf
Fixed 6 closure parameter destructuring issues:

1. **Line 29-34**: `ch_samplesheet.flatMap { meta, image ->` 
   - Changed to: `ch_samplesheet.flatMap { tuple ->`
   - Added explicit destructuring: `def meta = tuple[0]; def image = tuple[1]`

2. **Lines 37-41**: Filter for painting arm
   - Changed closure parameter from `{ meta, _image ->` to `{ tuple ->`
   - Added explicit destructuring

3. **Lines 43-47**: Map for painting arm
   - Changed closure parameter from `{ meta, image ->` to `{ tuple ->`
   - Added explicit destructuring

4. **Lines 48-52**: Filter for barcoding arm
   - Changed closure parameter from `{ meta, _image ->` to `{ tuple ->`
   - Added explicit destructuring

5. **Lines 54-58**: Map for barcoding arm
   - Changed closure parameter from `{ meta, image ->` to `{ tuple ->`
   - Added explicit destructuring

6. **Lines 128-148**: Combined analysis section
   - Fixed 4 closures in the combined analysis chain:
     - `.map { meta, images ->` → `.map { tuple ->`
     - `.flatMap { meta, images ->` → `.flatMap { tuple ->`
     - Nested `.map` in `.mix()` statement

## Pattern Used
**Before:**
```groovy
channel
    .map { meta, image ->
        // use meta and image directly
    }
```

**After:**
```groovy
channel
    .map { tuple ->
        def meta = tuple[0]
        def image = tuple[1]
        // use meta and image
    }
```

## Additional Files That May Need Fixes
The following files contain similar patterns that may also need fixing:
- `subworkflows/local/barcoding/main.nf` - 13+ instances
- `subworkflows/local/cellpainting/main.nf` - 10+ instances

These files should be reviewed and fixed if the workflow still fails after these initial fixes.

## Testing Recommendation
1. Test the workflow with the current fixes
2. If successful, no further changes needed
3. If errors persist in subworkflows, apply the same pattern to those files

## Next Steps
1. Commit these changes to a new branch
2. Test the workflow
3. If needed, fix additional subworkflow files
4. Run `nextflow lint` once SSL issues are resolved to catch any other syntax issues
