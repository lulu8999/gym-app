---
name: pdf-structure-editing
description: Edit PDF structural elements — page numbers, headers, footers, watermarks — while preserving all other content. Uses PyMuPDF (fitz). Covers find/replace/remove operations on positional text and vector drawings.
triggers:
  - "修改PDF页码"
  - "删除PDF页眉/页脚"
  - "PDF页码格式修改"
  - "remove PDF headers/footers"
  - "edit page numbers in PDF"
  - "PDF结构修改"
---

# PDF Structural Editing

Edit PDF structural elements (page numbers, headers, footers, lines) using PyMuPDF while preserving all other content.

## Prerequisites

```bash
pip3 install pymupdf
```

Import: `import pymupdf`

## Core Patterns

### 1. Analyzing Page Structure

```python
doc = pymupdf.open("input.pdf")
for i, page in enumerate(doc):
    rect = page.rect
    # Top 15% = header zone
    top_area = pymupdf.Rect(rect.x0, rect.y0, rect.x1, rect.y1 * 0.15)
    text = page.get_text("text", clip=top_area).strip()
    print(f"Page {i+1} header zone: [{text}]")
```

### 2. Finding Text by Position and Size

```python
text_instances = page.get_text("dict")
for block in text_instances["blocks"]:
    if "lines" in block:
        for line in block["lines"]:
            for span in line["spans"]:
                text = span["text"].strip()
                bbox = span["bbox"]  # (x0, y0, x1, y1)
                font_size = span["size"]
                # Filter by position and size
                if bbox[1] < rect.y1 * 0.1 and font_size < 12:
                    # This is likely a header, not body content
                    pass
```

### 3. Finding and Removing Page Numbers

Page numbers typically match pattern `- 数字 -` with optional spaces:

```python
import re
for span in all_spans:
    text = span["text"].strip()
    if re.match(r"^-\s*\d+\s*-$", text):
        # Found a page number — redact it
        annot = page.add_redact_annot(pymupdf.Rect(span["bbox"]), fill=(1, 1, 1))
page.apply_redactions()
```

### 4. Adding New Page Numbers

```python
new_text = f"-{page_num}-"
text_width = pymupdf.get_text_length(new_text, fontsize=10, fontname="helv")
# Right-aligned at bottom
right_x = rect.width - 50
bottom_y = rect.height - 20
page.insert_text(pymupdf.Point(right_x, bottom_y), new_text, fontsize=10, fontname="helv")
# Centered at bottom
center_x = rect.width / 2 - text_width / 2
page.insert_text(pymupdf.Point(center_x, bottom_y), new_text, fontsize=10, fontname="helv")
```

### 5. Removing Header Text and Lines

```python
# Remove header text (small font in top 10% of page)
for block in text_instances["blocks"]:
    if "lines" in block:
        for line in block["lines"]:
            for span in line["spans"]:
                if span["bbox"][1] < rect.y1 * 0.1 and span["size"] < 12:
                    annot = page.add_redact_annot(
                        pymupdf.Rect(span["bbox"]), fill=(1, 1, 1)
                    )

# Remove header horizontal lines — use REDACTION, not white overlay
# (white overlay causes "double line" artifacts when original drawings remain)
drawings = page.get_drawings()
for d in drawings:
    if (d["rect"].y0 < rect.y1 * 0.1 and
        d["rect"].width > 100 and    # Wide line
        d["rect"].height < 5):       # Thin line (horizontal)
        # Expand rect slightly to fully cover thin lines
        cover = pymupdf.Rect(
            d["rect"].x0 - 0.5,
            d["rect"].y0 - 0.5,
            d["rect"].x1 + 0.5,
            d["rect"].y1 + 0.5,
        )
        annot = page.add_redact_annot(cover, fill=(1, 1, 1))

page.apply_redactions()
```

### 6. Splitting PDFs

```python
# Extract pages 8-24 (0-indexed: 7-23)
new_doc = pymupdf.open()
new_doc.insert_pdf(source_doc, from_page=7, to_page=23)
new_doc.save("output.pdf")
```

## Pitfalls

1. **Redact vs White Overlay (for ALL elements, not just text)**: `add_redact_annot()` + `apply_redactions()` actually removes content from the PDF object model. Drawing white rectangles with `new_shape()` only visually covers — the original drawing object **still exists** underneath. This causes **double-line artifacts**: the original line and the white overlay can both be detected by drawing analysis tools, and some renderers show faint ghost lines. **Always use redaction for both text AND vector lines.**

2. **Don't use `annot.apply()`**: The Annot object has no `.apply()` method. Use `page.apply_redactions()` after adding all redaction annotations.

3. **Table border lines**: When removing header lines by drawing dimensions, check `width > 100` and `height < 5` to avoid removing table borders. Table borders typically form vertical lines (narrow width) or are part of grid structures.

4. **Header vs Title distinction**: The chapter title (e.g., "参考文献") may appear both as a small header (font ~9pt, top 10%) and as a body title (font ~16pt, lower position). Use font size + position to distinguish. Only remove the header instance.

5. **Regex for page numbers**: The pattern `r"^-\s*\d+\s*-$"` handles variations like `- 1 -`, `-1-`, `- 10 -`. Avoid matching too broadly — check that the number part is actually a digit.

6. **White overlay causes ghost lines**: When you draw a white rectangle over a line, `get_drawings()` returns BOTH the original line AND the white rectangle. This is invisible to the eye but causes: (a) false positives in drawing-count comparisons, (b) re-detection bugs when you try to selectively restore content, (c) subtle rendering artifacts in some PDF viewers. **Use redaction instead.**

7. **Comparing original vs modified PDFs**: When modifying PDFs with tables, always compare `get_drawings()` output between original and modified versions on affected pages. Focus on: drawing count per page (should not increase), lines at the same Y coordinate (detect duplicates), `type='f'` vs `'s'` vs `'fs'` (ensure no new filled rectangles appeared).
   ```python
   for page_num in range(len(doc)):
       orig_count = len(original[page_num].get_drawings())
       mod_count = len(doc[page_num].get_drawings())
       if mod_count > orig_count:
           print(f"⚠️ Page {page_num+1}: {mod_count - orig_count} extra drawings!")
   ```

8. **Restoring accidentally removed table borders**: If a modification accidentally removed table lines, the safest fix is to copy the affected pages from the original PDF, then re-apply only the intended modifications. Use `insert_pdf()` with `from_page`/`to_page`:
   ```python
   new_doc = pymupdf.open()
   new_doc.insert_pdf(modified_doc, from_page=0, to_page=-4)  # all except last 3
   new_doc.insert_pdf(original_doc, from_page=len(original_doc)-3, to_page=len(original_doc)-1)
   ```

## Workflow for Common Tasks

### "Change page numbers from page X to page Y"
1. Analyze existing page number format and positions
2. Redact old page numbers
3. Apply redactions
4. Insert new page numbers at desired position/format

### "Remove headers from page N onwards"
1. Identify header text (small font, top zone)
2. Identify header lines (wide, thin drawings, top zone)
3. Redact BOTH text and lines with `add_redact_annot()` + `apply_redactions()` (never white overlay)
4. **Verify no table borders were accidentally caught** — compare drawing counts against original
5. Verify table borders are preserved
