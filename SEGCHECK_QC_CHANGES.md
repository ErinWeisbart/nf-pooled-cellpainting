# QC_MONTAGE_SEGCHECK Per-Well Changes

## Summary
Modified `QC_MONTAGE_SEGCHECK` to run on a **per-well basis** instead of per-plate basis in the `feature/single-channel` branch.

## Changes Made

### 1. Channel Reshaping (`subworkflows/local/cellpainting/main.nf`)

**Before:**
- SEGCHECK outputs were grouped by `batch` and `plate` only
- All wells from the same plate were combined into a single montage
- Required `.groupTuple()` to aggregate all wells

**After:**
- SEGCHECK outputs now include `well` in metadata
- Each well gets its own individual montage
- No `.groupTuple()` needed since SEGCHECK already outputs per-well

**Code change (lines ~220-223):**
```diff
-    // Reshape CELLPROFILER_SEGCHECK output for QC montage
+    // Reshape CELLPROFILER_SEGCHECK output for QC montage (per-well)
     ch_segcheck_qc = CELLPROFILER_SEGCHECK.out.segcheck_res
-        .map { meta, _ch_versionscsv_files, png_files ->
-            [meta.subMap(['batch', 'plate']) + [arm: "painting"], png_files]
-        }
-        .groupTuple()
-        .map { meta, png_files_list ->
-            [meta, png_files_list.flatten().sort { it -> it.name }]
+        .map { meta, _csv_files, png_files ->
+            // Keep well in metadata for per-well montages
+            [meta.subMap(['batch', 'plate', 'well']) + [arm: "painting"], png_files]
         }
```

### 2. Process Tag Update (`modules/local/qc/montageillum/main.nf`)

**Before:**
- Tag only showed plate ID

**After:**
- Tag conditionally shows plate and well when well is present
- Maintains backward compatibility for plate-only montages

**Code change (line 2):**
```diff
-    tag "${meta.plate}"
+    tag "${meta.well ? meta.plate + '_' + meta.well : meta.plate}"
```

### 3. Output Filename Update (`modules/local/qc/montageillum/main.nf`)

**Before:**
- Output: `painting.{batch}_{plate}.montage.png`

**After:**
- Output: `painting.{batch}_{plate}_{well}.montage.png` (when well present)
- Falls back to plate-only format for backward compatibility

**Code change (lines 19-21):**
```diff
     script:
-    def output_name = "${meta.arm}.${meta.batch}_${meta.plate}.montage.png"
+    def output_name = meta.well 
+        ? "${meta.arm}.${meta.batch}_${meta.plate}_${meta.well}.montage.png"
+        : "${meta.arm}.${meta.batch}_${meta.plate}.montage.png"
```

## Impact

### Benefits:
✅ Individual QC montages per well enable easier quality assessment  
✅ Issues can be identified at well-level granularity  
✅ Reduced file size per montage (fewer images combined)  
✅ Parallel QC montage creation per well (no groupTuple barrier)  
✅ Backward compatible - module works for both plate and well-level montages  

### Behavior:
- **Before:** 1 montage per plate (all wells combined)
- **After:** N montages per plate (1 per well)

### File naming examples:
- **Before:** `painting.Batch1_Plate1.montage.png`
- **After:** `painting.Batch1_Plate1_A01.montage.png`, `painting.Batch1_Plate1_A02.montage.png`, etc.

## Files Modified
1. `subworkflows/local/cellpainting/main.nf` - Channel reshaping logic
2. `modules/local/qc/montageillum/main.nf` - Tag and output filename logic

## Testing Recommendations
1. Verify montage files are created per well in output directory
2. Check file naming includes well identifier
3. Confirm each montage contains only images from its respective well
4. Validate that all wells produce their own montage
5. Ensure synchronization barrier still works correctly for downstream FIJI_STITCHCROP

## Notes
- The `QC_MONTAGEILLUM` module remains generic and can still be used for plate-level montages
- Other uses of `QC_MONTAGEILLUM` (illumination and stitchcrop QC) are unaffected
- The synchronization barrier for FIJI_STITCHCROP continues to work as before
