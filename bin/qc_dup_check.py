#!/usr/bin/env python3
"""
QC script to check for duplicate images by analyzing correlation columns in CellProfiler Image.csv files.

This script looks for columns with "Correlation_Correlation" in the name and reports any values > 0.99,
which may indicate duplicate images in the dataset.
"""

import argparse
import glob
import os
import sys
from pathlib import Path

import pandas as pd


def find_image_csv_files(input_dir: str, mode: str) -> list:
    """
    Find all Image.csv files from the appropriate CellProfiler output.

    Args:
        input_dir: Base directory to search for CSV files
        mode: Either 'illumapply' or 'preprocess' to determine which files to search

    Returns:
        List of paths to Image.csv files
    """
    if mode == "illumapply":
        # Look for any CSV files ending in Image.csv from IllumApplication output
        # Pattern matches files like: BarcodingIllumApplication_Image.csv, *IllumApplication_Image.csv
        pattern = os.path.join(input_dir, "**", "*IllumApplication*Image.csv")
    elif mode == "preprocess":
        # Look for Image.csv files from BarcodePreprocessing output
        # Pattern matches files like: BarcodePreprocessing_Image.csv
        pattern = os.path.join(input_dir, "**", "*Preprocessing*Image.csv")
    else:
        raise ValueError(f"Invalid mode: {mode}. Must be 'illumapply' or 'preprocess'")

    csv_files = glob.glob(pattern, recursive=True)
    
    # Filter to only include files that actually end with "Image.csv"
    csv_files = [f for f in csv_files if f.endswith("Image.csv")]
    
    return sorted(csv_files)


def check_correlation_columns(csv_file: Path, threshold: float = 0.99) -> dict:
    """
    Check correlation columns in a CSV file for high values.

    Args:
        csv_file: Path to the CSV file
        threshold: Threshold above which correlations are considered high (default: 0.99)

    Returns:
        Dictionary with check results
    """
    try:
        df = pd.read_csv(csv_file)
    except Exception as e:
        return {
            "file": str(csv_file),
            "error": f"Failed to read CSV: {e}",
            "has_high_correlations": False,
            "correlation_columns": [],
            "high_correlation_count": 0,
        }

    # Find all columns with "Correlation_Correlation" in the name
    corr_columns = [col for col in df.columns if "Correlation_Correlation" in col]

    if not corr_columns:
        return {
            "file": str(csv_file),
            "error": None,
            "has_high_correlations": False,
            "correlation_columns": [],
            "high_correlation_count": 0,
            "message": "No correlation columns found",
        }

    # Check for high correlations
    high_corr_results = {}
    total_high_corr = 0

    for col in corr_columns:
        high_values = df[df[col] > threshold][col]
        if len(high_values) > 0:
            high_corr_results[col] = {
                "count": len(high_values),
                "max_value": float(high_values.max()),
                "mean_value": float(high_values.mean()),
            }
            total_high_corr += len(high_values)

    has_high_correlations = total_high_corr > 0

    return {
        "file": str(csv_file),
        "error": None,
        "has_high_correlations": has_high_correlations,
        "correlation_columns": corr_columns,
        "high_correlation_count": total_high_corr,
        "high_correlation_details": high_corr_results if has_high_correlations else {},
        "total_rows": len(df),
    }


def generate_report(results: list, output_file: str, mode: str, threshold: float) -> None:
    """
    Generate a text report summarizing the correlation check results.

    Args:
        results: List of result dictionaries from check_correlation_columns
        output_file: Path to output report file
        mode: The mode used ('illumapply' or 'preprocess')
        threshold: The correlation threshold used
    """
    with open(output_file, "w") as f:
        f.write("=" * 80 + "\n")
        f.write(f"QC Duplication Check Report - Mode: {mode.upper()}\n")
        f.write(f"Correlation Threshold: {threshold}\n")
        f.write("=" * 80 + "\n\n")

        files_with_issues = [r for r in results if r["has_high_correlations"]]
        files_with_errors = [r for r in results if r.get("error")]

        f.write(f"Total files analyzed: {len(results)}\n")
        f.write(f"Files with high correlations (>{threshold}): {len(files_with_issues)}\n")
        f.write(f"Files with errors: {len(files_with_errors)}\n\n")

        if files_with_errors:
            f.write("-" * 80 + "\n")
            f.write("FILES WITH ERRORS:\n")
            f.write("-" * 80 + "\n")
            for result in files_with_errors:
                f.write(f"\nFile: {result['file']}\n")
                f.write(f"Error: {result['error']}\n")

        if files_with_issues:
            f.write("-" * 80 + "\n")
            f.write("FILES WITH HIGH CORRELATIONS:\n")
            f.write("-" * 80 + "\n")
            for result in files_with_issues:
                f.write(f"\nFile: {result['file']}\n")
                f.write(f"Total rows: {result['total_rows']}\n")
                f.write(f"High correlation instances: {result['high_correlation_count']}\n")
                f.write("\nDetails by column:\n")
                for col, details in result["high_correlation_details"].items():
                    f.write(f"  {col}:\n")
                    f.write(f"    Count: {details['count']}\n")
                    f.write(f"    Max value: {details['max_value']:.4f}\n")
                    f.write(f"    Mean value: {details['mean_value']:.4f}\n")
        else:
            f.write("-" * 80 + "\n")
            f.write("RESULT: No high correlations detected!\n")
            f.write("-" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Check CellProfiler Image.csv files for high correlation values that may indicate duplicates"
    )
    parser.add_argument(
        "mode",
        choices=["illumapply", "preprocess"],
        help="Mode to determine which CSV files to check",
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        required=True,
        help="Base directory containing CellProfiler output CSV files",
    )
    parser.add_argument(
        "--output-report",
        type=str,
        default="qc_dup_check_report.txt",
        help="Output report file path",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.99,
        help="Correlation threshold above which to report (default: 0.99)",
    )

    args = parser.parse_args()

    print(f"QC Duplication Check - Mode: {args.mode}")
    print(f"Input directory: {args.input_dir}")
    print(f"Correlation threshold: {args.threshold}")

    # Find CSV files
    csv_files = find_image_csv_files(args.input_dir, args.mode)

    if not csv_files:
        print(f"WARNING: No Image.csv files found for mode '{args.mode}' in {args.input_dir}")
        print("Creating empty report...")
        with open(args.output_report, "w") as f:
            f.write("=" * 80 + "\n")
            f.write(f"QC Duplication Check Report - Mode: {args.mode.upper()}\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"No Image.csv files found in {args.input_dir}\n")
            f.write("This may be expected if this step has not been run yet.\n")
        sys.exit(0)

    print(f"Found {len(csv_files)} Image.csv file(s) to analyze")

    # Analyze each file
    results = []
    for csv_file in csv_files:
        print(f"Analyzing: {csv_file}")
        result = check_correlation_columns(csv_file, args.threshold)
        results.append(result)

        if result.get("error"):
            print(f"  ERROR: {result['error']}")
        elif result["has_high_correlations"]:
            print(f"  WARNING: Found {result['high_correlation_count']} high correlation(s)")
        else:
            print(f"  OK: No high correlations detected")

    # Generate report
    generate_report(results, args.output_report, args.mode, args.threshold)
    print(f"\nReport written to: {args.output_report}")

    # Determine exit status
    files_with_issues = [r for r in results if r["has_high_correlations"]]
    if files_with_issues:
        print(f"\nWARNING: {len(files_with_issues)} file(s) have high correlations!")
        sys.exit(0)  # Still exit 0 since this is a warning, not an error
    else:
        print("\nSUCCESS: No high correlations detected in any files.")
        sys.exit(0)


if __name__ == "__main__":
    main()
