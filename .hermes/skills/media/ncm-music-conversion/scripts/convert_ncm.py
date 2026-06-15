#!/usr/bin/env python3
"""Batch convert .ncm files to .mp3 using ncmdump."""
import os, sys, shutil
from pathlib import Path

try:
    import ncmdump
    print('ncmdump module loaded')
except ImportError:
    print('ERROR: ncmdump not installed. Run: pip install ncmdump')
    sys.exit(1)

# === CONFIGURE THESE PATHS ===
src = Path(r'C:\Users\USERNAME\Desktop\vipmusic')
dst = Path(r'C:\Users\USERNAME\Desktop\mp3')
# ==============================

dst.mkdir(parents=True, exist_ok=True)
ncm_files = list(src.glob('*.ncm'))
print(f'Found {len(ncm_files)} ncm files')

success = 0
fail = 0
for i, f in enumerate(ncm_files):
    out_name = f.stem + '.mp3'
    out_path = dst / out_name
    if out_path.exists():
        print(f'[{i+1}] SKIP (exists): {out_name}')
        success += 1
        continue
    try:
        result = ncmdump.dump(str(f))
        if result and os.path.exists(result):
            shutil.move(result, str(out_path))
            print(f'[{i+1}] OK: {out_name}')
            success += 1
        else:
            expected = f.with_suffix('.mp3')
            if expected.exists():
                shutil.move(str(expected), str(out_path))
                print(f'[{i+1}] OK (moved): {out_name}')
                success += 1
            else:
                print(f'[{i+1}] FAIL: {f.name}')
                fail += 1
    except Exception as e:
        print(f'[{i+1}] ERROR: {f.name} -> {e}')
        fail += 1

print(f'\nDone! Success: {success}, Failed: {fail}')
