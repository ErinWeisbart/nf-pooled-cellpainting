# Using Your Own Data: Run

## Running the Pipeline with CLI

Once your inputs are ready, run the pipeline pointing to your files:

```bash
nextflow run broadinstitute/nf-pooled-cellpainting \
    --input samplesheet.csv \
    --barcodes barcodes.csv \
    --outdir results \
    --painting_illumcalc_cppipe your_painting_illumcalc_cppipe.cppipe \
    --painting_illumapply_cppipe your_painting_illumapply_cppipe.cppipe \
    --painting_segcheck_cppipe your_painting_segcheck_cppipe.cppipe \
    --barcoding_illumcalc_cppipe your_barcoding_illumcalc_cppipe.cppipe \
    --barcoding_illumapply_cppipe your_barcoding_illumapply_cppipe.cppipe \
    --barcoding_preprocess_cppipe your_barcoding_preprocess_cppipe.cppipe \
    --combinedanalysis_cppipe your_combinedanalysis_cppipe.cppipe \
    -profile docker
```

## Running the Pipeline with Seqera Platform

### Configuring the Pipeline in Seqera Platform

Navigate to **Launchpad** → **Add Pipeline**.

#### Pipeline Settings

| Setting | Value |
|---------|-------|
| **Name** | `nf-pooled-cellpainting` |
| **Pipeline to launch** | `https://github.com/broadinstitute/nf-pooled-cellpainting` |
| **Revision** | `dev` (or a specific tag) |
| **Compute environment** | Your AWS Batch environment |
| **Work directory** | `s3://your-bucket/work` |
| **Config profiles** | `test` (for testing) or leave empty |

#### Pipeline Parameters

For test runs, the `test` profile provides all necessary parameters. For custom data, provide parameters as JSON or YAML:

```yaml
input: "s3://your-bucket/samplesheet.csv"
barcodes: "s3://your-bucket/barcodes.csv"
outdir: "s3://your-bucket/results"
painting_illumcalc_cppipe: "s3://your-bucket/pipelines/painting_illumcalc.cppipe"
# ... other cppipe parameters
```

### Launching and Monitoring Runs

1. **Launch**: Click **Launch** from the pipeline page
2. **Monitor**: View real-time task execution in the **Runs** tab
3. **QC Review**: Check outputs in the S3 bucket or via the **Reports** tab
4. **Resume**: After QC review, click **Resume** (not Relaunch!) with updated parameters:

```yaml
qc_painting_passed: true
qc_barcoding_passed: true
```

:::{important} "Resume vs Relaunch"
**Resume** uses cached results; **Relaunch** starts from scratch. Always use Resume after QC review.
:::

### Cost Optimization Tips

1. **Use Spot Instances**: 60-90% cost savings for fault-tolerant workloads
2. **Enable Fusion Snapshots**: Automatically recover from spot interruptions
3. **Right-size Max CPUs**: Start with 500-1000, increase based on queue times
4. **Use Appropriate Instance Types**: Memory-optimized (`r6id`) for Combined Analysis; compute-optimized (`c6id`) for illumination steps
5. **Clean Up Work Directory**: Periodically delete old work directories from S3
6. **Route Long Tasks to On-Demand**: See below for avoiding spot reclaim losses on multi-hour tasks

### Routing Long-Running Tasks to On-Demand Instances

Long-running tasks like `FIJI_STITCHCROP` (up to 4-6 hours) and `CELLPROFILER_COMBINEDANALYSIS` risk losing hours of work if spot instances are reclaimed. To avoid this:

1. **Create an on-demand compute environment** in Seqera Platform (duplicate your spot environment, disable Fusion Snapshots since they're unnecessary for on-demand)

2. **Route specific processes** to the on-demand queue by adding to your Nextflow config:

```groovy
process {
    withName: 'FIJI_STITCHCROP' {
        queue = '<on-demand-queue-name>'
    }
    withName: 'CELLPROFILER_COMBINEDANALYSIS' {
        queue = '<on-demand-queue-name>'
    }
}
```

The queue name is visible in your Seqera Platform compute environment under "Manual config attributes".

:::{tip} When to use on-demand
Use on-demand for tasks that: (1) run longer than 1-2 hours, (2) have experienced repeated spot reclamations, or (3) are in the final stages of a critical run
:::

### Resource Requirements by Process

| Process | CPU | Memory | Notes |
|---------|-----|--------|-------|
| CELLPROFILER_ILLUMCALC | 1 | 2 GB | Per plate |
| CELLPROFILER_ILLUMAPPLY | 1-2 | 6 GB | Per well/site |
| CELLPROFILER_PREPROCESS | 4 | 8 GB | Per site |
| FIJI_STITCHCROP | 6 | 36 GB | Memory-intensive |
| CELLPROFILER_COMBINEDANALYSIS | 4 | 12-32 GB | Most demanding |

To override defaults, add to your Nextflow config:

```groovy
process {
    withName: 'CELLPROFILER_COMBINEDANALYSIS' {
        memory = '64.GB'
    }
}
```
