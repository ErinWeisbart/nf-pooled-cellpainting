#!/usr/bin/env python
"""
QC script for comparing raw vs illumination-corrected images.

Creates a visual comparison report showing before/after illumination correction
for the first plate/well/site across all channels.

Usage:
    python qc_illum_compare.py \\
        --raw-dir raw_images/ \\
        --corrected-dir corrected_images/ \\
        --output-dir . \\
        --batch Batch1 \\
        --plate Plate1 \\
        --well A01 \\
        --site 1 \\
        --channels DNA,ER,RNA,AGP,Mito
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def natural_sort_key(s: str) -> List:
    """Natural sorting key that handles numbers properly."""
    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split("([0-9]+)", s)
    ]


def find_image_for_channel(
    image_dir: Path,
    batch: str,
    plate: str,
    well: str,
    site: str,
    channel: str,
    channel_index: int,
    all_channels: List[str],
) -> Optional[Path]:
    """
    Find the image file for a specific channel in the given directory.
    
    Since Nextflow has already staged the correct images for this plate/well/site,
    we just need to find the file containing the target channel name or number.
    
    Handles two naming conventions:
    1. Descriptive names (corrected images): filename contains channel name (e.g., "CorrDNA.tiff")
    2. Numbered channels (raw images): filename contains "chN" where N is the channel index (e.g., "ch1" for first channel)
    
    Args:
        image_dir: Directory containing images (already filtered by Nextflow)
        batch: Batch identifier (for reference, not used in matching)
        plate: Plate identifier (for reference, not used in matching)
        well: Well identifier (for reference, not used in matching)
        site: Site number (for reference, not used in matching)
        channel: Channel name to find in the filename
        channel_index: 0-based index of this channel in the channels list
        all_channels: Full list of channel names (for context)
    
    Returns:
        Path to the image file, or None if not found
    """
    # List all TIFF files in the directory
    tiff_files = list(image_dir.glob("*.tif")) + list(image_dir.glob("*.tiff")) + \
                 list(image_dir.glob("*.ome.tif")) + list(image_dir.glob("*.ome.tiff"))
    
    if not tiff_files:
        return None
    
    # Find files that match this channel
    matching_files = []
    
    for tiff_file in tiff_files:
        filename = tiff_file.name
        filename_lower = filename.lower()
        
        # Strategy 1: Look for channel name in filename (for corrected images)
        # Example: "Plate_BR00149745_pCFB_Well_D06_Site_1_CorrDNA.tiff"
        if channel.lower() in filename_lower:
            matching_files.append(tiff_file)
            continue
        
        # Strategy 2: Look for "chN" pattern where N is channel_index + 1 (for raw images)
        # Example: "r04c06f01p01-ch1sk1fk1fl1.tiff" where ch1 is the first channel (index 0)
        channel_number = channel_index + 1  # Convert 0-based index to 1-based channel number
        
        # Look for patterns like "ch1", "-ch1-", "-ch1s", "ch1.", etc.
        # Match: (non-digit or start)ch(N)(non-digit or end)
        # This avoids matching "ch10" when looking for "ch1"
        import re
        pattern = rf'(?:^|[^0-9])ch{channel_number}(?:[^0-9]|$)'
        if re.search(pattern, filename_lower):
            matching_files.append(tiff_file)
            continue
    
    if matching_files:
        # Return the first match (sorted for determinism)
        return sorted(matching_files, key=lambda p: natural_sort_key(p.name))[0]
    
    return None


def load_and_downsample_image(image_path: Path, scale_factor: float = 0.25) -> Image.Image:
    """
    Load a TIFF image and downsample it.
    
    Args:
        image_path: Path to the image file
        scale_factor: Factor to scale down the image (default: 0.25 for 1/4 size)
    
    Returns:
        PIL Image object (downsampled and normalized)
    """
    # Load the image
    img = Image.open(image_path)
    
    # Convert to numpy array for processing
    img_array = np.array(img)
    
    # Normalize to 0-255 range (assuming 16-bit input)
    if img_array.dtype == np.uint16:
        # Simple min-max normalization
        img_min = img_array.min()
        img_max = img_array.max()
        if img_max > img_min:
            img_array = ((img_array - img_min) / (img_max - img_min) * 255).astype(np.uint8)
        else:
            img_array = np.zeros_like(img_array, dtype=np.uint8)
    
    # Convert back to PIL Image
    img_normalized = Image.fromarray(img_array)
    
    # Downsample
    new_size = (int(img_normalized.width * scale_factor), int(img_normalized.height * scale_factor))
    img_downsampled = img_normalized.resize(new_size, Image.Resampling.LANCZOS)
    
    return img_downsampled


def create_comparison_montage(
    raw_images: List[Tuple[str, Image.Image]],
    corrected_images: List[Tuple[str, Image.Image]],
    output_path: Path,
    title: str,
) -> None:
    """
    Create a comparison montage showing raw and corrected images side by side.
    
    Args:
        raw_images: List of (channel_name, image) tuples for raw images
        corrected_images: List of (channel_name, image) tuples for corrected images
        output_path: Path to save the output montage
        title: Title for the montage
    """
    if not raw_images and not corrected_images:
        print("Warning: No images to create montage")
        return
    
    # Get image dimensions (assume all images are the same size after downsampling)
    sample_img = raw_images[0][1] if raw_images else corrected_images[0][1]
    img_width, img_height = sample_img.size
    
    # Layout parameters
    padding = 10
    label_height = 30
    title_height = 50
    num_channels = max(len(raw_images), len(corrected_images))
    
    # Calculate montage dimensions
    # Layout: Title at top, then rows of [Raw | Corrected] for each channel
    montage_width = 2 * img_width + 3 * padding  # Two images side by side with padding
    montage_height = (
        title_height +
        num_channels * (img_height + label_height + padding) +
        padding
    )
    
    # Create the montage canvas
    montage = Image.new('RGB', (montage_width, montage_height), color='white')
    draw = ImageDraw.Draw(montage)
    
    # Try to use a font, fall back to default if not available
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except:
        title_font = ImageFont.load_default()
        label_font = ImageFont.load_default()
    
    # Draw title
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (montage_width - title_width) // 2
    draw.text((title_x, 10), title, fill='black', font=title_font)
    
    # Draw column headers
    y_offset = title_height
    draw.text((padding + img_width // 2 - 20, y_offset), "Raw", fill='black', font=label_font)
    draw.text((2 * padding + img_width + img_width // 2 - 40, y_offset), "Corrected", fill='black', font=label_font)
    
    y_offset += label_height
    
    # Create a mapping of channels to images
    raw_dict = {ch: img for ch, img in raw_images}
    corrected_dict = {ch: img for ch, img in corrected_images}
    
    # Get all unique channels
    all_channels = sorted(set(list(raw_dict.keys()) + list(corrected_dict.keys())))
    
    # Draw each channel comparison
    for channel in all_channels:
        # Draw channel label
        draw.text((padding, y_offset), channel, fill='black', font=label_font)
        
        row_y = y_offset + label_height
        
        # Draw raw image
        if channel in raw_dict:
            raw_img_rgb = raw_dict[channel].convert('RGB')
            montage.paste(raw_img_rgb, (padding, row_y))
        else:
            # Draw placeholder
            draw.rectangle(
                [(padding, row_y), (padding + img_width, row_y + img_height)],
                outline='red',
                width=2
            )
            draw.text(
                (padding + img_width // 2 - 30, row_y + img_height // 2),
                "Missing",
                fill='red',
                font=label_font
            )
        
        # Draw corrected image
        if channel in corrected_dict:
            corrected_img_rgb = corrected_dict[channel].convert('RGB')
            montage.paste(corrected_img_rgb, (2 * padding + img_width, row_y))
        else:
            # Draw placeholder
            draw.rectangle(
                [(2 * padding + img_width, row_y),
                 (2 * padding + 2 * img_width, row_y + img_height)],
                outline='red',
                width=2
            )
            draw.text(
                (2 * padding + img_width + img_width // 2 - 30, row_y + img_height // 2),
                "Missing",
                fill='red',
                font=label_font
            )
        
        y_offset += img_height + label_height + padding
    
    # Save the montage
    montage.save(output_path)
    print(f"Saved comparison montage to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate QC report comparing raw vs illumination-corrected images"
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        required=True,
        help="Directory containing raw images"
    )
    parser.add_argument(
        "--corrected-dir",
        type=Path,
        required=True,
        help="Directory containing illumination-corrected images"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("."),
        help="Output directory for the QC report"
    )
    parser.add_argument(
        "--batch",
        type=str,
        required=True,
        help="Batch identifier"
    )
    parser.add_argument(
        "--plate",
        type=str,
        required=True,
        help="Plate identifier"
    )
    parser.add_argument(
        "--well",
        type=str,
        required=True,
        help="Well identifier (e.g., A01)"
    )
    parser.add_argument(
        "--site",
        type=str,
        required=True,
        help="Site number"
    )
    parser.add_argument(
        "--channels",
        type=str,
        required=True,
        help="Comma-separated list of channel names"
    )
    parser.add_argument(
        "--scale-factor",
        type=float,
        default=0.25,
        help="Downsample factor (default: 0.25 for 1/4 size)"
    )
    
    args = parser.parse_args()
    
    # Parse channels
    channels = [ch.strip() for ch in args.channels.split(',')]
    
    print(f"Generating illumination correction QC report for {args.plate}_{args.well}_Site{args.site}")
    print(f"Channels: {', '.join(channels)}")
    
    # Load raw images
    raw_images = []
    for channel_index, channel in enumerate(channels):
        img_path = find_image_for_channel(
            args.raw_dir, args.batch, args.plate, args.well, args.site, channel,
            channel_index, channels
        )
        if img_path:
            print(f"Found raw image for {channel}: {img_path.name}")
            img = load_and_downsample_image(img_path, args.scale_factor)
            raw_images.append((channel, img))
        else:
            print(f"Warning: Could not find raw image for {channel}")
    
    # Load corrected images
    corrected_images = []
    for channel_index, channel in enumerate(channels):
        img_path = find_image_for_channel(
            args.corrected_dir, args.batch, args.plate, args.well, args.site, channel,
            channel_index, channels
        )
        if img_path:
            print(f"Found corrected image for {channel}: {img_path.name}")
            img = load_and_downsample_image(img_path, args.scale_factor)
            corrected_images.append((channel, img))
        else:
            print(f"Warning: Could not find corrected image for {channel}")
    
    # Create the comparison montage
    output_path = args.output_dir / f"painting.{args.batch}_{args.plate}_{args.well}_Site{args.site}.illumcompare.png"
    title = f"Illumination Correction QC: {args.plate}_{args.well}_Site{args.site}"
    
    create_comparison_montage(raw_images, corrected_images, output_path, title)
    
    print("QC report generation complete!")


if __name__ == "__main__":
    main()
