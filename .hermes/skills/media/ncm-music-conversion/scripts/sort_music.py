#!/usr/bin/env python3
"""Sort mp3 files by language (Chinese/Foreign), dedup by title."""
import os, re, shutil
from pathlib import Path

# === CONFIGURE THESE PATHS ===
SRC_MP3 = Path(r'C:\Users\USERNAME\Desktop\mp3')
DEST_CN = Path(r'F:\中文')
DEST_EN = Path(r'F:\外文')
# ==============================

DEST_CN.mkdir(parents=True, exist_ok=True)
DEST_EN.mkdir(parents=True, exist_ok=True)

def extract_title(filename):
    """Extract song title from 'Artist - Title.mp3'."""
    name = filename.stem
    idx = name.rfind(' - ')
    if idx >= 0:
        return name[idx + 3:].strip()
    return name.strip()

def has_chinese(text):
    """Check if text contains CJK characters."""
    return bool(re.search(r'[\u4e00-\u9fff\u3400-\u4dbf]', text))

all_files = []
for f in SRC_MP3.glob('*.mp3'):
    title = extract_title(f)
    all_files.append({
        'path': f,
        'title': title,
        'is_chinese': has_chinese(title),
    })

print(f'Found {len(all_files)} mp3 files')

# Dedup by title (keep first occurrence)
seen_titles = {}
duplicates = []
for item in all_files:
    t = item['title']
    if t in seen_titles:
        duplicates.append(item['path'].name)
    else:
        seen_titles[t] = item

if duplicates:
    print(f'\nDuplicates ({len(duplicates)}):')
    for d in duplicates:
        print(f'  Skipped: {d}')

deduped = list(seen_titles.values())
print(f'\nAfter dedup: {len(deduped)} files')

cn_count = 0
en_count = 0
for item in deduped:
    dest_dir = DEST_CN if item['is_chinese'] else DEST_EN
    dest_path = dest_dir / item['path'].name
    if not dest_path.exists():
        shutil.copy2(item['path'], dest_path)
    if item['is_chinese']:
        cn_count += 1
    else:
        en_count += 1

print(f'\n========== Report ==========')
print(f'Chinese: {cn_count} -> {DEST_CN}')
print(f'Foreign: {en_count} -> {DEST_EN}')
print(f'Skipped (dupes): {len(all_files) - len(deduped)}')
print(f'=============================')
