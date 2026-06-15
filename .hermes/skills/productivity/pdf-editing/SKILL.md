---
name: pdf-editing
description: "Structural PDF editing: page numbers, splitting, merging, redaction, watermarking via pymupdf."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [PDF, Editing, PageNumbers, Split, Merge, Redaction, pymupdf]
    related_skills: [ocr-and-documents, document-editing, nano-pdf, powerpoint]
---

# PDF Structural Editing

Manipulate PDF structure — page numbers, splitting, merging, redaction, watermarking. Uses **pymupdf** (lightweight, no OCR models needed).

For **text extraction** → use `ocr-and-documents` skill.
For **.docx editing** → use `document-editing` skill.
For **PDF text typo fixes** → use `nano-pdf` skill.

## Prerequisites

```bash
pip3 install pymupdf
```

## Core Patterns

### 1. Find Page Numbers by Pattern

Chinese academic PDFs commonly use `- N -` (with spaces) or `-N-` (no spaces) format.

```python
import pymupdf, re

doc = pymupdf.open('input.pdf')
for i, page in enumerate(doc):
    instances = page.get_text('dict')
    for block in instances['blocks']:
        if 'lines' not in block:
            continue
        for line in block['lines']:
            for span in line['spans']:
                text = span['text'].strip()
                # Match both "- 1 -" and "-1-" formats
                if re.match(r'^-\s*\d+\s*-$', text):
                    rect = pymupdf.Rect(span['bbox'])
                    print(f'Page {i+1}: "{text}" at {rect}')
```

### 2. Redact (Remove) Text

Two-step: mark redactions, then apply. Order matters — mark ALL first, then apply.

```python
# Step 1: Mark all redactions
for page_num in target_pages:
    page = doc[page_num]
    for block in page.get_text('dict')['blocks']:
        if 'lines' not in block:
            continue
        for line in block['lines']:
            for span in line['spans']:
                if should_redact(span['text']):
                    rect = pymupdf.Rect(span['bbox'])
                    annot = page.add_redact_annot(rect, fill=(1, 1, 1))  # white fill

# Step 2: Apply all redactions (separate loop!)
for page_num in target_pages:
    doc[page_num].apply_redactions()
```

### 3. Add Page Number Text

```python
import pymupdf

page = doc[page_num]
rect = page.rect

text = '-1-'
fontsize = 10
fontname = 'helv'  # Helvetica (built-in, always available)

# Right-aligned bottom
tw = pymupdf.get_text_length(text, fontsize=fontsize, fontname=fontname)
x = rect.width - 50   # 50pt from right edge
y = rect.height - 20  # 20pt from bottom
page.insert_text(pymupdf.Point(x, y), text, fontsize=fontsize, fontname=fontname)

# Centered bottom
tw = pymupdf.get_text_length(text, fontsize=fontsize, fontname=fontname)
x = (rect.width - tw) / 2
y = rect.height - 20
page.insert_text(pymupdf.Point(x, y), text, fontsize=fontsize, fontname=fontname)
```

### 4. Roman Numerals

```python
roman_map = {1:'i', 2:'ii', 3:'iii', 4:'iv', 5:'v', 6:'vi', 7:'vii', 8:'viii', 9:'ix', 10:'x'}
# For arbitrary numbers, use: pip3 install roman → import roman; roman.toRoman(n).lower()
```

### 5. Split PDF (Extract Pages)

```python
import pymupdf

src = pymupdf.open('full.pdf')
dst = pymupdf.open()

# Extract pages 8-24 (0-indexed: 7-23)
dst.insert_pdf(src, from_page=7, to_page=23)
dst.save('extracted.pdf')
```

### 6. Merge PDFs

```python
import pymupdf

result = pymupdf.open()
for path in ['part1.pdf', 'part2.pdf', 'part3.pdf']:
    result.insert_pdf(pymupdf.open(path))
result.save('merged.pdf')
```

### 7. Analyze Page Structure

```python
import pymupdf

doc = pymupdf.open('input.pdf')
for i, page in enumerate(doc):
    rect = page.rect
    # Bottom 15% of page
    bottom = pymupdf.Rect(rect.x0, rect.y1 * 0.85, rect.x1, rect.y1)
    text = page.get_text('text', clip=bottom).strip()
    first_line = page.get_text()[:300].split('\n')[0]
    print(f'Page {i+1}: title=[{first_line[:50]}] bottom=[{text[:50]}]')
```

## Common Workflows

### Chinese Academic Thesis Page Numbers

Standard layout:
- Cover (no number)
- Front matter: abstract, TOC → Roman numerals (i, ii, iii)
- Body: introduction through references → `-1-`, `-2-`, etc.
- Appendix/tables → no page numbers or separate numbering

Steps:
1. Analyze page structure to identify sections
2. Redact old page numbers (mark all, then apply all)
3. Insert new page numbers at correct positions
4. For split output: extract pages and re-number

### Remove Page Headers (Text + Horizontal Lines)

Chinese academic thesis headers typically contain a title (e.g., "江苏警官学院本科毕业论文（设计）") and a thin horizontal line below it.

```python
import pymupdf

doc = pymupdf.open('input.pdf')
HEADER_ZONE = 0.10  # top 10% of page

for page_num in range(start_page, len(doc)):
    page = doc[page_num]
    rect = page.rect

    # Step 1: Redact header text (small font in top zone)
    for block in page.get_text('dict')['blocks']:
        if 'lines' not in block:
            continue
        for line in block['lines']:
            for span in line['spans']:
                text = span['text'].strip()
                y_pos = span['bbox'][1]
                if y_pos < rect.y1 * HEADER_ZONE and text and span['size'] < 12:
                    annot = page.add_redact_annot(
                        pymupdf.Rect(span['bbox']), fill=(1, 1, 1))
    page.apply_redactions()

    # Step 2: Cover header horizontal lines
    # ⚠️ CRITICAL: See Pitfall #8 — must filter carefully!
    for d in page.get_drawings():
        r = d['rect']
        is_in_header = r.y0 < rect.y1 * HEADER_ZONE
        is_horizontal_line = r.width > 100 and r.height < 3
        if is_in_header and is_horizontal_line:
            shape = page.new_shape()
            shape.draw_rect(r)
            shape.finish(color=(1, 1, 1), fill=(1, 1, 1))
            shape.commit()
```

### Detect and Remove Blank Pages

```python
import pymupdf

doc = pymupdf.open('input.pdf')
blank_pages = []

for i, page in enumerate(doc):
    text = page.get_text().strip()
    # Also check for pages with only whitespace or very few visible chars
    if len(text) < 50:
        blank_pages.append(i)

# Delete from back to front to preserve indices
for idx in reversed(blank_pages):
    doc.delete_page(idx)

doc.save('output.pdf')
```

### Replace Damaged Pages from Original

If a processing step accidentally damages specific pages (e.g., removes table borders), restore them from the original:

```python
original = pymupdf.open('original.pdf')
modified = pymupdf.open('modified.pdf')

# Replace last 3 pages from original
for i in range(3):
    orig_idx = len(original) - 3 + i
    mod_idx = len(modified) - 3 + i
    modified.delete_page(mod_idx)
    modified.insert_pdf(original, from_page=orig_idx, to_page=orig_idx,
                        start_at=mod_idx)
modified.save('fixed.pdf')
```

## Pitfalls

1. **Redaction order**: Always mark ALL redactions first, then apply in a separate loop. Marking and applying in the same loop can skip elements.

2. **Font availability**: Only `helv` (Helvetica), `tiro`, `cour`, `symb`, `zadb` are guaranteed built-in. For Chinese text, you need a CJK font — use `page.insert_text()` with a loaded font file or fall back to roman/ASCII only.

3. **Page coordinate system**: pymupdf uses 72 DPI. A4 = 595×842 points. Origin (0,0) is top-left.

4. **Whitespace in page numbers**: Chinese PDFs often use `- 1 -` (with spaces). Your regex must handle both: `r'^-\\s*\\d+\\s*-$'`

5. **`get_text_length` accuracy**: Returns width for the specified font/size. Use for positioning calculations but verify visually.

6. **Large PDFs**: For PDFs >100 pages, process in batches to avoid memory issues. pymupdf loads pages on demand but redaction markers accumulate in memory.

7. **pip vs pip3**: On many Linux systems, `pip` is not in PATH — use `pip3` explicitly.

8. **⚠️ CRITICAL — `get_drawings()` returns ALL drawing objects**: This includes table borders, cell dividers, and form lines — NOT just page header lines. Using a simple "top zone + horizontal" filter WILL destroy table borders on pages where tables extend near the top. **Safe approach**: Only remove lines where `width > 100 AND height < 3` AND the line is clearly a page header separator (check if header text was found on the same page at the same Y level). Better yet: if the page has tables in the header zone, skip line removal entirely and only remove text. **Always verify**: After removing headers, check the last few pages of the output to confirm table borders are intact.
