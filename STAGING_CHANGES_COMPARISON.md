# Staging Changes: Side-by-Side Comparison

## CELLPROFILER_ILLUMCALC Module

### Input Declaration

| Before | After |
|--------|-------|
| `path(images, stageAs: "images*/*")` | `path(images)` |

### Directory Structure

#### Before (Incremental Pattern)
```
work/task_xyz/
├── images1/
│   ├── image_file_001.tif
│   └── image_file_002.tif
├── images2/
│   ├── image_file_003.tif
│   └── image_file_004.tif
└── images3/
    └── image_file_005.tif
```

#### After (Metadata-Based Pattern)
```
work/task_xyz/
├── Plate1-A01-1/
│   ├── image_file_001.tif
│   └── image_file_002.tif
├── Plate1-A02-1/
│   ├── image_file_003.tif
│   └── image_file_004.tif
└── Plate1-B01-1/
    └── image_file_005.tif
```

### Staging Logic

#### Before
```python
python3 -c "
import json, os, glob
mapping = {}
for f in glob.glob('images*/*'):
    mapping[os.path.basename(f)] = f
print(json.dumps(mapping))
" > staged_paths.json
```

#### After
```python
python3 <<'ORGANIZE_FILES'
import json, os, shutil, glob

# Load metadata
with open('metadata.json') as f:
    metadata = json.load(f)

# Build filename -> metadata record mapping
meta_map = {}
for record in metadata:
    fname = os.path.basename(record['filename'])
    meta_map[fname] = record

# Create directories and move files based on metadata
staged_paths = {}
for img_file in glob.glob('*'):
    if not os.path.isfile(img_file) or img_file in ['metadata.json', 'staged_paths.json']:
        continue
    
    basename = os.path.basename(img_file)
    if basename in meta_map:
        rec = meta_map[basename]
        plate = rec['plate']
        well = rec['well']
        site = rec['site']
        
        # Create directory: {plate}-{well}-{site}
        dir_name = f"{plate}-{well}-{site}"
        os.makedirs(dir_name, exist_ok=True)
        
        # Move file into directory
        dest_path = os.path.join(dir_name, basename)
        shutil.move(img_file, dest_path)
        
        # Record staged path for CSV generation
        staged_paths[basename] = dest_path
    else:
        # File not in metadata - keep as-is
        staged_paths[basename] = basename

# Write staged paths mapping
with open('staged_paths.json', 'w') as f:
    json.dump(staged_paths, f)
ORGANIZE_FILES
```

---

## CELLPROFILER_ILLUMAPPLY Module

### Input Declaration

| Before | After |
|--------|-------|
| `path(images, stageAs: "images/img?/*")` | `path(images)` |

### Directory Structure

#### Before (Incremental Pattern)
```
work/task_xyz/
└── images/
    ├── img1/
    │   ├── image_file_001.tif
    │   └── image_file_002.tif
    ├── img2/
    │   ├── image_file_003.tif
    │   └── image_file_004.tif
    ├── img3/
    │   └── image_file_005.tif
    ├── Plate1_Illum_DNA.npy
    └── Plate1_Illum_ER.npy
```

#### After (Metadata-Based Pattern)
```
work/task_xyz/
└── images/
    ├── Plate1-A01-1/
    │   ├── image_file_001.tif
    │   └── image_file_002.tif
    ├── Plate1-A02-1/
    │   ├── image_file_003.tif
    │   └── image_file_004.tif
    ├── Plate1-B01-1/
    │   └── image_file_005.tif
    ├── Plate1_Illum_DNA.npy
    └── Plate1_Illum_ER.npy
```

### Staging Logic

#### Before
```python
python3 -c "
import json, os, glob
mapping = {}
for f in glob.glob('images/img*/*'):
    # strip the leading 'images/' prefix so CellProfiler resolves correctly
    mapping[os.path.basename(f)] = os.path.relpath(f, 'images')
print(json.dumps(mapping))
" > staged_paths.json
```

#### After
```python
python3 <<'ORGANIZE_FILES'
import json, os, shutil, glob

# Load metadata
with open('metadata.json') as f:
    metadata = json.load(f)

# Create images/ directory if it doesn't exist
os.makedirs('images', exist_ok=True)

# Build filename -> metadata record mapping
meta_map = {}
for record in metadata:
    fname = os.path.basename(record['filename'])
    meta_map[fname] = record

# Move image files into metadata-based directories under images/
staged_paths = {}
for img_file in glob.glob('*'):
    if not os.path.isfile(img_file) or img_file in ['metadata.json', 'staged_paths.json']:
        continue
    
    basename = os.path.basename(img_file)
    # Skip .npy files (illumination corrections - already in images/)
    if basename.endswith('.npy'):
        continue
        
    if basename in meta_map:
        rec = meta_map[basename]
        plate = rec['plate']
        well = rec['well']
        site = rec['site']
        
        # Create directory: images/{plate}-{well}-{site}
        dir_name = f"images/{plate}-{well}-{site}"
        os.makedirs(dir_name, exist_ok=True)
        
        # Move file into directory
        dest_path = os.path.join(dir_name, basename)
        shutil.move(img_file, dest_path)
        
        # Record path relative to images/ for CellProfiler
        # (CellProfiler uses --image-directory ./images/)
        staged_paths[basename] = f"{plate}-{well}-{site}/{basename}"
    else:
        # File not in metadata - keep as-is
        staged_paths[basename] = basename

# Write staged paths mapping
with open('staged_paths.json', 'w') as f:
    json.dump(staged_paths, f)
ORGANIZE_FILES
```

---

## Key Differences Summary

| Aspect | Before | After |
|--------|--------|-------|
| **Directory naming** | Incremental (images1, img2) | Metadata-based (Plate1-A01-1) |
| **Organization method** | Nextflow `stageAs` directive | Python script reading metadata |
| **Readability** | Low (arbitrary numbers) | High (meaningful names) |
| **Traceability** | Difficult (need to check logs) | Easy (name shows experimental context) |
| **Logic location** | Nextflow input directive | Explicit Python script in process |
| **Compatibility** | Via `staged_paths.json` | Via `staged_paths.json` |

Both approaches maintain compatibility with the existing `generate_load_data_csv.py` script through the `staged_paths.json` mapping file.
