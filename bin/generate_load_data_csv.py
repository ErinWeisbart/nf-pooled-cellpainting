#!/usr/bin/env python3
"""
generate_load_data_csv.py  -  Build CellProfiler load_data.csv files from image metadata.

Each JSON record has the fields:
    arm, batch, plate, well, site (int), cycle (int),
    channels (str), n_frames (int), filename (str)

Pipeline types: illumcalc, illumapply, segcheck, preprocess, combined
"""

import argparse, csv, json, sys
from collections import defaultdict
from itertools import product


def load_metadata_json(path):
    with open(path) as fh:
        raw = json.load(fh)
    records = []
    for r in raw:
        rec = dict(r)
        # Support both "channels" (multi-channel, comma-separated or list)
        # and "channel" (single-channel, one record per file)
        if "channels" in rec:
            ch_raw = rec["channels"]
            if isinstance(ch_raw, list):
                channels = [c.strip() for c in ch_raw]
            elif "," in str(ch_raw):
                channels = [c.strip() for c in str(ch_raw).split(",")]
            else:
                channels = [str(ch_raw).strip()]
        elif "channel" in rec:
            channels = [str(rec["channel"]).strip()]
        else:
            sys.exit(f"Record missing both 'channels' and 'channel' fields: {rec}")
        rec["_channels"] = channels
        rec["_site"]     = str(rec["site"])
        rec["_cycle"]    = int(rec["cycle"]) if "cycle" in rec else None
        rec["_frames"]   = list(range(int(rec.get("n_frames", len(channels)))))
        records.append(rec)
    return records


def load_staged_paths(path):
    """Load {basename: staged_relative_path} map from JSON (built by the NF shell script)."""
    if path is None:
        return {}
    with open(path) as fh:
        return json.load(fh)


def remap_filename(filename, staged_map):
    """Return the staged relative path for *filename* if available, else filename unchanged."""
    if not staged_map:
        return filename
    import os
    basename = os.path.basename(filename)
    return staged_map.get(basename, filename)


def painting_rows(rows):
    return [r for r in rows if r["arm"] == "painting"]

def barcoding_rows(rows):
    return [r for r in rows if r["arm"] == "barcoding"]

def group_by_site(rows):
    g = defaultdict(list)
    for r in rows:
        g[(r["plate"], r["well"], r["_site"])].append(r)
    return g

def group_by_cycle_site(rows):
    g = defaultdict(list)
    for r in rows:
        g[(r["plate"], r["well"], r["_site"], r["_cycle"])].append(r)
    return g

def unique_ordered(items):
    seen = []
    for v in items:
        if v not in seen:
            seen.append(v)
    return seen

def phenotyping_channels(paint_rows):
    return unique_ordered(ch for r in sorted(paint_rows, key=lambda r: r["_cycle"] or 0)
                          for ch in r["_channels"])

def barcoding_channels(barc_rows):
    return unique_ordered(ch for r in barc_rows for ch in r["_channels"])

def sorted_cycles(rows):
    return sorted({r["_cycle"] for r in rows})

def find_row(site_rows, channel, cycle=None):
    for r in site_rows:
        if cycle is not None and r["_cycle"] != cycle:
            continue
        if channel in r["_channels"]:
            return r
    return None

def get_file_and_frame(row, channel, staged_map=None):
    idx = row["_channels"].index(channel)
    fn  = remap_filename(row["filename"], staged_map)
    return fn, row["_frames"][idx]

def make_site_row(plate, well, site):
    return {"Metadata_Plate": plate, "Metadata_Well": well, "Metadata_Site": site}

def illum_filename(plate, channel, cycle=None):
    if cycle is not None:
        return f"{plate}_Cycle{cycle}_Illum{channel}.npy"
    return f"{plate}_Illum{channel}.npy"


def gen_illumcalc(rows, has_cycles, staged_map=None):
    if has_cycles:
        barc = barcoding_rows(rows) or rows
        channels = barcoding_channels(barc)
        if not channels:
            sys.exit("illumcalc (barcoding): no channels found")
        col_order = (["Metadata_Plate", "Metadata_Well", "Metadata_Site", "Metadata_Cycle"]
                     + [f"FileName_Orig{ch}" for ch in channels]
                     + [f"Frame_Orig{ch}" for ch in channels])
        out_rows = []
        for key, sr in sorted(group_by_cycle_site(barc).items()):
            plate, well, site, cycle = key
            row = make_site_row(plate, well, site)
            row["Metadata_Cycle"] = cycle
            for ch in channels:
                m = find_row(sr, ch)
                if m:
                    fn, fr = get_file_and_frame(m, ch, staged_map)
                    row[f"FileName_Orig{ch}"] = fn
                    row[f"Frame_Orig{ch}"] = fr
                else:
                    row[f"FileName_Orig{ch}"] = row[f"Frame_Orig{ch}"] = ""
            out_rows.append(row)
    else:
        paint = painting_rows(rows) or rows
        channels = phenotyping_channels(paint)
        if not channels:
            sys.exit("illumcalc (painting): no channels found")
        col_order = (["Metadata_Plate", "Metadata_Well", "Metadata_Site"]
                     + [f"FileName_Orig{ch}" for ch in channels]
                     + [f"Frame_Orig{ch}" for ch in channels])
        out_rows = []
        for key, sr in sorted(group_by_site(paint).items()):
            plate, well, site = key
            row = make_site_row(plate, well, site)
            for ch in channels:
                m = find_row(sr, ch)
                if m:
                    fn, fr = get_file_and_frame(m, ch, staged_map)
                    row[f"FileName_Orig{ch}"] = fn
                    row[f"Frame_Orig{ch}"] = fr
                else:
                    row[f"FileName_Orig{ch}"] = row[f"Frame_Orig{ch}"] = ""
            out_rows.append(row)
    return col_order, out_rows


def gen_illumapply(rows, has_cycles, staged_map=None):
    if has_cycles:
        barc = barcoding_rows(rows) or rows
        channels = barcoding_channels(barc)
        cycles = sorted_cycles(barc)
        if not channels or not cycles:
            sys.exit("illumapply (barcoding): no data found")
        col_order = ["Metadata_Plate", "Metadata_Well", "Metadata_Site"]
        for cyc, ch in product(cycles, channels):
            cyc_str = f"{cyc:02d}"
            col_order += [f"FileName_Cycle{cyc_str}_Orig{ch}", f"Frame_Cycle{cyc_str}_Orig{ch}",
                          f"FileName_Cycle{cyc_str}_Illum{ch}"]
        out_rows = []
        for key, sr in sorted(group_by_site(barc).items()):
            plate, well, site = key
            row = make_site_row(plate, well, site)
            for cyc, ch in product(cycles, channels):
                cyc_str = f"{cyc:02d}"
                m = find_row(sr, ch, cycle=cyc)
                if m:
                    fn, fr = get_file_and_frame(m, ch, staged_map)
                    row[f"FileName_Cycle{cyc_str}_Orig{ch}"] = fn
                    row[f"Frame_Cycle{cyc_str}_Orig{ch}"] = fr
                else:
                    row[f"FileName_Cycle{cyc_str}_Orig{ch}"] = row[f"Frame_Cycle{cyc_str}_Orig{ch}"] = ""
                # Use raw (non-padded) cycle int for filename to match illumcalc output
                row[f"FileName_Cycle{cyc_str}_Illum{ch}"] = illum_filename(plate, ch, cyc)
            out_rows.append(row)
    else:
        paint = painting_rows(rows) or rows
        channels = phenotyping_channels(paint)
        if not channels:
            sys.exit("illumapply (painting): no channels found")
        col_order = (["Metadata_Plate", "Metadata_Well", "Metadata_Site"]
                     + [f"FileName_Orig{ch}" for ch in channels]
                     + [f"Frame_Orig{ch}" for ch in channels]
                     + [f"FileName_Illum{ch}" for ch in channels])
        out_rows = []
        for key, sr in sorted(group_by_site(paint).items()):
            plate, well, site = key
            row = make_site_row(plate, well, site)
            for ch in channels:
                m = find_row(sr, ch)
                if m:
                    fn, fr = get_file_and_frame(m, ch, staged_map)
                    row[f"FileName_Orig{ch}"] = fn
                    row[f"Frame_Orig{ch}"] = fr
                else:
                    row[f"FileName_Orig{ch}"] = row[f"Frame_Orig{ch}"] = ""
                row[f"FileName_Illum{ch}"] = illum_filename(plate, ch)
            out_rows.append(row)
    return col_order, out_rows


def gen_segcheck(rows):
    paint = painting_rows(rows) or rows
    # Segcheck records are one-per-channel: each has a "channel" (singular) field
    # with the true channel name and a "filename" pointing to the corrected tiff.
    # Group by site and collect channels from the "channel" field directly.
    site_channel_file = defaultdict(dict)
    for r in paint:
        ch = r.get("channel") or (r["_channels"][0] if r["_channels"] else None)
        if ch:
            key = (r["plate"], r["well"], r["_site"])
            site_channel_file[key][ch] = r["filename"]
    if not site_channel_file:
        sys.exit("segcheck: no painting channels found")
    # Determine ordered channel list from first site
    first_key = sorted(site_channel_file.keys())[0]
    channels = list(site_channel_file[first_key].keys())
    col_order = (["Metadata_Plate", "Metadata_Well", "Metadata_Site"]
                 + [f"FileName_{ch}" for ch in channels])
    out_rows = []
    for key in sorted(site_channel_file.keys()):
        plate, well, site = key
        row = make_site_row(plate, well, site)
        for ch in channels:
            row[f"FileName_{ch}"] = site_channel_file[key].get(ch, "")
        out_rows.append(row)
    return col_order, out_rows


def gen_preprocess(rows):
    barc = barcoding_rows(rows) or rows
    channels = barcoding_channels(barc)
    cycles = sorted_cycles(barc)
    if not channels or not cycles:
        sys.exit("preprocess: no barcoding data found")
    col_order = ["Metadata_Plate", "Metadata_Well", "Metadata_Site"]
    for cyc, ch in product(cycles, channels):
        cyc_str = f"{cyc:02d}"
        col_order += [f"FileName_{ch}_Cycle{cyc_str}", f"Frame_{ch}_Cycle{cyc_str}"]
    out_rows = []
    for key, sr in sorted(group_by_site(barc).items()):
        plate, well, site = key
        row = make_site_row(plate, well, site)
        for cyc, ch in product(cycles, channels):
            cyc_str = f"{cyc:02d}"
            m = find_row(sr, ch, cycle=cyc)
            if m:
                fn, fr = get_file_and_frame(m, ch)
                row[f"FileName_{ch}_Cycle{cyc_str}"] = fn
                row[f"Frame_{ch}_Cycle{cyc_str}"] = fr
            else:
                row[f"FileName_{ch}_Cycle{cyc_str}"] = row[f"Frame_{ch}_Cycle{cyc_str}"] = ""
        out_rows.append(row)
    return col_order, out_rows


def gen_combined(rows):
    paint = painting_rows(rows)
    barc  = barcoding_rows(rows)
    ph_channels   = phenotyping_channels(paint)
    barc_channels = barcoding_channels(barc)
    barc_cycles   = sorted_cycles(barc)
    if not ph_channels:
        sys.exit("combined: no painting channels found")
    col_order = ["Metadata_Plate", "Metadata_Well", "Metadata_Site"]
    col_order += [f"FileName_Corr{ch}" for ch in ph_channels]
    for cyc, ch in product(barc_cycles, barc_channels):
        col_order.append(f"FileName_Cycle{cyc}_{ch}")
    paint_by_site = group_by_site(paint)
    barc_by_site  = group_by_site(barc)
    all_sites = sorted(set(paint_by_site) | set(barc_by_site))
    out_rows = []
    for (plate, well, site) in all_sites:
        row = make_site_row(plate, well, site)
        p_rows = paint_by_site.get((plate, well, site), [])
        for ch in ph_channels:
            m = find_row(p_rows, ch)
            row[f"FileName_Corr{ch}"] = m["filename"] if m else ""
        b_rows = barc_by_site.get((plate, well, site), [])
        for cyc, ch in product(barc_cycles, barc_channels):
            m = find_row(b_rows, ch, cycle=cyc)
            row[f"FileName_Cycle{cyc}_{ch}"] = m["filename"] if m else ""
        out_rows.append(row)
    return col_order, out_rows


def write_csv(col_order, out_rows, output):
    with open(output, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=col_order, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(out_rows)
    print(f"Wrote {len(out_rows)} rows -> {output}", file=sys.stderr)


def parse_args():
    p = argparse.ArgumentParser(description="Generate CellProfiler load_data.csv")
    p.add_argument("--metadata-json", required=True)
    p.add_argument("--pipeline-type", required=True,
                   choices=("illumcalc", "illumapply", "segcheck", "preprocess", "combined"))
    p.add_argument("--images-dir", default="./images")
    p.add_argument("--illum-dir", default=None)
    p.add_argument("-o", "--output", default="load_data.csv")
    p.add_argument("--channels", default=None)
    p.add_argument("--cycle-metadata-name", default="Cycle")
    p.add_argument("--has-cycles", action="store_true", default=False)
    p.add_argument("--range-skip", type=int, default=2)
    p.add_argument("--staged-paths-json", default=None,
                   help="JSON map of {basename: staged_relative_path} produced by the NF shell script")
    return p.parse_args()


def main():
    args = parse_args()
    rows = load_metadata_json(args.metadata_json)
    staged_map = load_staged_paths(args.staged_paths_json)
    ptype = args.pipeline_type
    if ptype == "illumcalc":
        col_order, out_rows = gen_illumcalc(rows, args.has_cycles, staged_map)
    elif ptype == "illumapply":
        col_order, out_rows = gen_illumapply(rows, args.has_cycles, staged_map)
    elif ptype == "segcheck":
        col_order, out_rows = gen_segcheck(rows)
    elif ptype == "preprocess":
        col_order, out_rows = gen_preprocess(rows)
    elif ptype == "combined":
        col_order, out_rows = gen_combined(rows)
    else:
        sys.exit(f"Unknown pipeline type: {ptype}")
    write_csv(col_order, out_rows, args.output)


if __name__ == "__main__":
    main()
