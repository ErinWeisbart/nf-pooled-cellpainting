#!/usr/bin/env python3
"""
QC Cycle Equality Check

This script checks if images from different cycles are mathematically equal,
which would indicate potential issues with cycle processing.

For each channel, it compares cycle 2 through N against cycle 1 to detect
if any images are identical (which shouldn't happen in normal processing).
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image


def parse_filename(filename):
    """
    Parse image filename to extract metadata.
    
    Expected format: Plate_X_Well_Y_Site_Z_CycleNN_CHANNEL.tiff
    
    Returns:
        dict: Metadata including plate, well, site, cycle, and channel
    """
    # Pattern: Plate_X_Well_Y_Site_Z_CycleNN_CHANNEL.tiff
    pattern = r'Plate_?(\d+)_Well_?([A-Z]\d+)_Site_?(\d+)_Cycle(\d+)_(.+)\.tiff?'
    match = re.match(pattern, filename, re.IGNORECASE)
    
    if not match:
        raise ValueError(f"Cannot parse filename: {filename}")
    
    return {
        'plate': match.group(1),
        'well': match.group(2),
        'site': match.group(3),
        'cycle': int(match.group(4)),
        'channel': match.group(5),
    }


def group_images_by_channel(image_files):
    """
    Group image files by channel, organizing by cycle within each channel.
    
    Args:
        image_files: List of Path objects
        
    Returns:
        dict: {channel: {cycle: filepath}}
    """
    channels = defaultdict(dict)
    
    for img_path in image_files:
        try:
            metadata = parse_filename(img_path.name)
            channel = metadata['channel']
            cycle = metadata['cycle']
            channels[channel][cycle] = img_path
        except ValueError as e:
            print(f"Warning: Skipping file - {e}", file=sys.stderr)
            continue
    
    return channels


def images_are_equal(img1_path, img2_path):
    """
    Check if two images are mathematically equal.
    
    Args:
        img1_path: Path to first image
        img2_path: Path to second image
        
    Returns:
        bool: True if images are identical, False otherwise
    """
    try:
        # Load images using PIL and convert to numpy arrays
        img1 = np.array(Image.open(img1_path))
        img2 = np.array(Image.open(img2_path))
        
        # Check if shapes match
        if img1.shape != img2.shape:
            return False
        
        # Check if all pixel values are equal
        return np.array_equal(img1, img2)
    
    except Exception as e:
        print(f"Error comparing {img1_path.name} and {img2_path.name}: {e}", file=sys.stderr)
        return False


def check_cycle_equality(image_files, stage):
    """
    Check if any cycle images are equal to cycle 1 for each channel.
    
    Args:
        image_files: List of image file paths
        stage: Processing stage ('illumapply' or 'preprocess')
        
    Returns:
        tuple: (passed: bool, results: dict, metadata: dict)
    """
    channels = group_images_by_channel(image_files)
    
    if not channels:
        return False, {}, {'error': 'No valid images found'}
    
    # Extract sample metadata from first image
    first_img = image_files[0]
    sample_meta = parse_filename(first_img.name)
    
    results = {}
    all_passed = True
    
    for channel, cycles_dict in sorted(channels.items()):
        # Skip if we don't have cycle 1 or only have one cycle
        if 1 not in cycles_dict or len(cycles_dict) < 2:
            results[channel] = {
                'status': 'SKIPPED',
                'reason': 'Missing cycle 1 or only one cycle present',
                'cycles_found': sorted(cycles_dict.keys())
            }
            continue
        
        cycle1_path = cycles_dict[1]
        equal_cycles = []
        
        # Compare cycle 2 through N to cycle 1
        for cycle in sorted(cycles_dict.keys()):
            if cycle == 1:
                continue
            
            cycle_n_path = cycles_dict[cycle]
            if images_are_equal(cycle1_path, cycle_n_path):
                equal_cycles.append(cycle)
                all_passed = False
        
        if equal_cycles:
            results[channel] = {
                'status': 'FAILED',
                'equal_cycles': equal_cycles,
                'total_cycles': len(cycles_dict),
                'message': f"Cycle(s) {equal_cycles} are identical to cycle 1"
            }
        else:
            results[channel] = {
                'status': 'PASSED',
                'total_cycles': len(cycles_dict),
                'message': 'All cycles are unique'
            }
    
    metadata = {
        'plate': sample_meta.get('plate', 'unknown'),
        'well': sample_meta.get('well', 'unknown'),
        'site': sample_meta.get('site', 'unknown'),
        'stage': stage,
        'total_images': len(image_files),
        'channels_tested': len(results)
    }
    
    return all_passed, results, metadata


def write_report(output_path, passed, results, metadata):
    """
    Write QC report to file.
    
    Args:
        output_path: Path to output report file
        passed: Overall QC pass/fail status
        results: Dictionary of results per channel
        metadata: Sample metadata
    """
    with open(output_path, 'w') as f:
        # Header
        f.write("=" * 80 + "\n")
        f.write("QC CYCLE EQUALITY CHECK REPORT\n")
        f.write("=" * 80 + "\n\n")
        
        # Metadata
        f.write("SAMPLE INFORMATION:\n")
        f.write(f"  Stage:          {metadata.get('stage', 'unknown')}\n")
        f.write(f"  Plate:          {metadata.get('plate', 'unknown')}\n")
        f.write(f"  Well:           {metadata.get('well', 'unknown')}\n")
        f.write(f"  Site:           {metadata.get('site', 'unknown')}\n")
        f.write(f"  Total Images:   {metadata.get('total_images', 0)}\n")
        f.write(f"  Channels Tested: {metadata.get('channels_tested', 0)}\n")
        f.write("\n")
        
        # Overall Status
        f.write("OVERALL QC STATUS: ")
        if passed:
            f.write("✓ PASSED\n")
            f.write("  No cycle images are identical to cycle 1.\n")
        else:
            f.write("✗ FAILED\n")
            f.write("  Some cycle images are identical to cycle 1 (see details below).\n")
        f.write("\n")
        
        # Per-channel results
        f.write("=" * 80 + "\n")
        f.write("DETAILED RESULTS BY CHANNEL:\n")
        f.write("=" * 80 + "\n\n")
        
        for channel, result in sorted(results.items()):
            f.write(f"Channel: {channel}\n")
            f.write(f"  Status: {result['status']}\n")
            
            if result['status'] == 'SKIPPED':
                f.write(f"  Reason: {result['reason']}\n")
                f.write(f"  Cycles Found: {result.get('cycles_found', [])}\n")
            elif result['status'] == 'FAILED':
                f.write(f"  Total Cycles: {result['total_cycles']}\n")
                f.write(f"  Equal Cycles: {result['equal_cycles']}\n")
                f.write(f"  Message: {result['message']}\n")
            else:  # PASSED
                f.write(f"  Total Cycles: {result['total_cycles']}\n")
                f.write(f"  Message: {result['message']}\n")
            
            f.write("\n")
        
        # Footer
        f.write("=" * 80 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 80 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Check if cycle images are mathematically equal'
    )
    parser.add_argument(
        '--images',
        nargs='+',
        required=True,
        help='Image files to check'
    )
    parser.add_argument(
        '--stage',
        required=True,
        choices=['illumapply', 'preprocess'],
        help='Processing stage'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output report file'
    )
    
    args = parser.parse_args()
    
    # Convert to Path objects
    image_files = [Path(img) for img in args.images]
    
    # Check cycle equality
    passed, results, metadata = check_cycle_equality(image_files, args.stage)
    
    # Write report
    write_report(args.output, passed, results, metadata)
    
    # Print summary to stdout
    print(f"QC Cycle Equality Check ({args.stage}): {'PASSED' if passed else 'FAILED'}")
    print(f"Report written to: {args.output}")
    
    # Exit with appropriate code
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
