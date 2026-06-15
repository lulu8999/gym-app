# Header Removal Pitfalls — Lessons from Thesis Processing

## Problem: Table Borders Destroyed During Header Removal

When removing page headers (text + horizontal lines) from a Chinese academic thesis, the `get_drawings()` approach for removing header separator lines accidentally removed table borders on appendix pages.

### Root Cause

`page.get_drawings()` returns **ALL** drawing objects on a page — including:
- Page header separator lines (what we want to remove)
- Table cell borders (what we must preserve)
- Form field lines, underlines, decorative elements

The naive filter `width > 100 AND height < 3 AND y < 10% of page height` matches BOTH header lines AND table borders on pages where tables start near the top.

### Safe Approaches

**Approach A: Text-conditional line removal**
Only remove a horizontal line if header text was ALSO found at a similar Y position on the same page. If no header text exists, skip line removal.

```python
# Find header text first
header_text_found = False
header_y = None
for block in page.get_text('dict')['blocks']:
    for line in block.get('lines', []):
        for span in line['spans']:
            if span['bbox'][1] < rect.y1 * 0.1 and span['size'] < 12:
                header_text_found = True
                header_y = span['bbox'][1]

# Only remove lines if header text was found
if header_text_found:
    for d in page.get_drawings():
        r = d['rect']
        if r.y0 < rect.y1 * 0.1 and r.width > 100 and r.height < 3:
            # Additional: check line is near header text Y position
            if header_y and abs(r.y0 - header_y) < 30:
                # This is likely a header separator, safe to remove
                ...
```

**Approach B: Page-type classification**
Classify pages by type (header page vs. table-only page) before processing. Appendix/table pages often have NO header text — only remove lines on pages where header text was detected.

**Approach C: Skip line removal, only remove text**
The safest approach: only redact the header TEXT, leave all lines untouched. The thin header separator line is usually barely noticeable.

### Verification Checklist

After any header removal operation:
1. Check the last 3-5 pages of the output — these are most likely to have tables
2. Compare drawing counts before/after for those pages
3. If counts differ, restore the original pages from the source PDF

### Recovery: Restore Damaged Pages

```python
original = pymupdf.open('original.pdf')
modified = pymupdf.open('modified.pdf')

for i in range(3):
    orig_idx = len(original) - 3 + i
    mod_idx = len(modified) - 3 + i
    modified.delete_page(mod_idx)
    modified.insert_pdf(original, from_page=orig_idx, to_page=orig_idx,
                        start_at=mod_idx)
modified.save('fixed.pdf')
```

## Blank Page Detection

Chinese academic thesis templates often insert intentional blank pages (e.g., after the declaration page). These can be detected by text length:

```python
text = page.get_text().strip()
is_blank = len(text) < 50  # threshold for "blank"
```

Delete from back to front to preserve indices during deletion.
