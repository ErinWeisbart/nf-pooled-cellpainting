# Staging Changes Quick Reference

## What Changed?

The CellProfiler ILLUMCALC and ILLUMAPPLY modules have been migrated from **incremental staging patterns** to **metadata-based staging patterns**.

## Before vs After

### ILLUMCALC Module
- **Before**: `stageAs: "images*/*"` → Files scattered in `images1/`, `images2/`, etc.
- **After**: Files organized in `{plate}-{well}-{site}/` directories
  - Example: `Plate1-A01-1/`, `Plate1-A01-2/`, `Plate1-B02-1/`

### ILLUMAPPLY Module
- **Before**: `stageAs: "images/img?/*"` → Files in `images/img1/`, `images/img2/`, etc.
- **After**: Files organized in `images/{plate}-{well}-{site}/` directories
  - Example: `images/Plate1-A01-1/`, `images/Plate1-A01-2/`, `images/Plate1-B02-1/`

## Benefits

✅ **Human-readable directories** - Know exactly which plate/well/site each directory contains  
✅ **Easier debugging** - Trace files back to experimental conditions instantly  
✅ **Metadata-driven** - Organization reflects your experimental design  
✅ **No breaking changes** - Downstream processes use `staged_paths.json` mapping  

## Technical Details

Both modules now:
1. Read `metadata.json` containing plate, well, site information for each image
2. Organize files into named directories based on this metadata
3. Generate `staged_paths.json` mapping for the CSV generator
4. Maintain compatibility with existing `generate_load_data_csv.py` script

## Files Modified

- `modules/local/cellprofiler/illumcalc/main.nf`
- `modules/local/cellprofiler/illumapply/main.nf`

## Testing Status

⚠️ **Requires testing** - See `STAGING_MIGRATION_STATUS.md` for complete testing plan.
