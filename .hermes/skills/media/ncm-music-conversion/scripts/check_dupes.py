#!/usr/bin/env python3
"""Check for duplicate song titles and remove duplicates (keep larger file)."""
from pathlib import Path
from collections import Counter

# === CONFIGURE ===
folders = [Path(r'F:\中文'), Path(r'F:\外文')]
# ==================

def extract_title(filename):
    name = filename.stem
    idx = name.rfind(' - ')
    if idx >= 0:
        return name[idx + 3:].strip()
    return name.strip()

for folder in folders:
    files = list(folder.glob('*.mp3'))
    titles = [extract_title(f) for f in files]
    dupes = {t: c for t, c in Counter(titles).items() if c > 1}
    print(f'{folder}: {len(files)} files')
    if dupes:
        print(f'  Duplicates: {len(dupes)}')
        for t, c in dupes.items():
            print(f'    {t} x{c}')
    else:
        print('  No duplicates!')

# Cross-folder check
cn_titles = set(extract_title(f) for f in folders[0].glob('*.mp3'))
en_titles = set(extract_title(f) for f in folders[1].glob('*.mp3'))
cross = cn_titles & en_titles
if cross:
    print(f'\nCross-folder duplicates: {len(cross)}')
    for t in cross:
        print(f'  {t}')
else:
    print('\nNo cross-folder duplicates!')
