# Troubleshooting

## Load Data CSV Errors

**Symptom**: CellProfiler fails with "Unable to load image"

**Solution**: Validate CSV paths are accessible:

```bash
# Check CSV format
head load_data.csv

# Verify image paths exist
cat load_data.csv | cut -d',' -f5 | xargs -I {} test -f {} && echo "OK"
```

## Plugin Not Found

**Symptom**: "Plugin 'callbarcodes' not found"

**Solution**: Ensure plugin URL is accessible and pipeline has access to the internet if plugin is loaded from an online source.

## Memory Errors

**Symptom**: CellProfiler crashes with out-of-memory

**Solution**: Increase process memory or reduce image size:

```groovy
process {
    withName: 'CELLPROFILER_.*' {
        memory = { task.attempt == 1 ? 32.GB : 64.GB }
        errorStrategy = 'retry'
    }
}
```

## Missing Images

**Symptom**: CSV has fewer rows than expected

**Solution**: Check filename patterns match exactly:

```bash
ls test_images/ | grep -E "P[0-9]+_[A-Z][0-9]+_[0-9]+_[0-9]+_.*\.tif"
```

## Metadata Mismatches

**Symptom**: CellProfiler can't group images properly

**Solution**: Ensure metadata columns are populated correctly:

```python
df[['Metadata_Plate', 'Metadata_Well', 'Metadata_Site']].drop_duplicates()
```
