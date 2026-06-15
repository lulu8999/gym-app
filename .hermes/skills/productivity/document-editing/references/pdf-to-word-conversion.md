# PDF to Word Conversion Workflow

Complete guide for converting PDF documents to Word (.docx) format while preserving structure, formatting, and content integrity.

## User Workflow Requirement

**CRITICAL**: The user explicitly stated: "以后让你做你要把事情做完了再报告" (finish things completely before reporting).

This means:
1. Extract ALL content from source PDF first
2. Verify completeness before any reporting
3. Structure the Word document properly
4. Only report when the full document is ready

## Complete Workflow

### Step 1: Extract PDF Content (No Reporting Yet)

```python
import fitz  # PyMuPDF

def extract_pdf_content(pdf_path):
    """Extract all content from PDF without modifications"""
    doc = fitz.open(pdf_path)
    
    pages_content = []
    for i in range(len(doc)):
        page = doc[i]
        text = page.get_text()
        pages_content.append({
            'page_num': i + 1,
            'text': text
        })
    
    doc.close()
    return pages_content

# EXTRACT FIRST, VERIFY, THEN REPORT
pages = extract_pdf_content('input.pdf')
print(f"Extracted {len(pages)} pages")  # Only for verification, not user report
```

### Step 2: Analyze and Identify Chapters

```python
import re

def identify_chapters(all_text):
    """Identify chapter boundaries in the text"""
    # Common Chinese chapter patterns
    chapter_patterns = [
        r'第[一二三四五六七八九十百千]+章[^\n]{0,50}',
        r'第\d+章[^\n]{0,50}',
    ]
    
    chapters = []
    for pattern in chapter_patterns:
        matches = list(re.finditer(pattern, all_text))
        for m in matches:
            chapters.append({
                'title': m.group(),
                'start': m.start(),
                'end': 0  # Will be set later
            })
    
    # Sort by position and remove duplicates
    chapters = sorted(chapters, key=lambda x: x['start'])
    
    # Set end positions
    for i in range(len(chapters) - 1):
        chapters[i]['end'] = chapters[i + 1]['start']
    if chapters:
        chapters[-1]['end'] = len(all_text)
    
    return chapters
```

### Step 3: Create Structured Word Document

```python
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

def create_structured_docx(chapters, all_text, output_path):
    """Create Word document with proper structure"""
    doc = Document()
    
    # Set default font
    style = doc.styles['Normal']
    style.font.name = 'Microsoft YaHei'
    style._element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')
    style.font.size = Pt(11)
    
    # 1. Cover Page
    title = doc.add_heading('Document Title', level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in title.runs:
        run.font.size = Pt(26)
        run.font.name = 'Microsoft YaHei'
    
    # Source and target info
    doc.add_paragraph().alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph('Target: [School/Organization]')
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    doc.add_page_break()
    
    # 2. Table of Contents (Required!)
    doc.add_heading('目录', level=1)
    
    # Create TOC table
    toc_table = doc.add_table(rows=len(chapters)+1, cols=3)
    toc_table.style = 'Light Grid Accent 1'
    
    # Headers
    headers = ['章节', '页码/分值', '重要程度']
    for i, h in enumerate(headers):
        cell = toc_table.rows[0].cells[i]
        cell.text = h
        # Set header background
        shading = OxmlElement('w:shd')
        shading.set(qn('w:fill'), '4472C4')
        cell._tc.get_or_add_tcPr().append(shading)
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.color.rgb = RGBColor(255, 255, 255)
                r.font.bold = True
    
    # Fill chapter info
    for i, ch in enumerate(chapters):
        row = toc_table.rows[i+1]
        row.cells[0].text = ch['title']
        row.cells[1].text = ch.get('score', '')
        row.cells[2].text = ch.get('importance', '')
    
    doc.add_page_break()
    
    # 3. Main Content - ALL CHAPTERS
    for ch in chapters:
        content = all_text[ch['start']:ch['end']].strip()
        
        # Chapter heading
        doc.add_heading(ch['title'], level=1)
        
        # Process content lines
        lines = content.split('\n')
        for line in lines[1:]:  # Skip chapter title line
            line = line.strip()
            if not line:
                continue
            
            # Detect table rows (| separated)
            if '|' in line:
                # Handle table conversion
                pass  # See table conversion below
            else:
                # Regular paragraph
                p = doc.add_paragraph(line)
                
                # Format special markers
                if line.startswith('[WARN]'):
                    for r in p.runs:
                        r.font.color.rgb = RGBColor(255, 0, 0)
                        r.font.bold = True
                elif '★★★' in line or '必考' in line:
                    for r in p.runs:
                        r.font.color.rgb = RGBColor(255, 0, 0)
                        r.font.bold = True
        
        doc.add_page_break()
    
    # 4. Final Blessing/Dedication (if appropriate)
    doc.add_heading('结语', level=1)
    # ... add closing content
    
    doc.save(output_path)
    return output_path
```

### Step 4: Table Conversion

```python
def convert_table_lines_to_docx_table(doc, table_lines):
    """Convert text table (| separated) to proper Word table"""
    if not table_lines or len(table_lines) < 2:
        return
    
    # Parse table data
    rows_data = []
    for line in table_lines:
        parts = [p.strip() for p in line.split('|') if p.strip()]
        if parts:
            rows_data.append(parts)
    
    if len(rows_data) < 2:
        return
    
    # Create table
    num_cols = max(len(r) for r in rows_data)
    table = doc.add_table(rows=len(rows_data), cols=num_cols)
    table.style = 'Light Grid Accent 1'
    
    # Fill data
    for r_idx, row_data in enumerate(rows_data):
        for c_idx, cell_text in enumerate(row_data):
            if c_idx < num_cols:
                table.rows[r_idx].cells[c_idx].text = cell_text
    
    doc.add_paragraph()  # Space after table
```

## Common Formatting Requirements

### Score/Grade Notation
- **WRONG**: `5-8分` (uses hyphen)
- **CORRECT**: `5~8分` (uses tilde ~)

### Target Institution Changes
When user requests target school changes:
1. Find all occurrences of old name
2. Replace with new name
3. Verify no broken context

```python
all_text = all_text.replace('南通大学医学院', '中山大学医学院')
```

### Chapter Navigation (MUST HAVE)
User expects:
1. Cover page with source/target info
2. Table of Contents page
3. All chapters in order
4. Clear chapter headings

## Verification Checklist

Before reporting completion, verify:

- [ ] All pages from source PDF extracted
- [ ] Chapter count matches source
- [ ] Tables converted to proper Word tables
- [ ] Special formatting preserved ([WARN], ★★★, etc.)
- [ ] Target/school names updated correctly
- [ ] Score notation uses ~ not -
- [ ] Table of Contents included
- [ ] Document structure is logical

## Common Pitfalls

### Pitfall 1: Incomplete Extraction
**Problem**: Only extracting first few pages
**Solution**: ALWAYS use `for i in range(len(doc))` to get ALL pages

### Pitfall 2: Duplicate Chapter Detection
**Problem**: Same chapter title appears multiple times (in TOC and body)
**Solution**: Deduplicate by position or choose the longer content version

### Pitfall 3: Table Line Breaks
**Problem**: Table rows split across pages break the | pattern detection
**Solution**: Collect all lines between table start and end markers

### Pitfall 4: Missing Cover/TOC
**Problem**: User expects navigation but only content pages provided
**Solution**: ALWAYS include: Cover → TOC → Chapters → Closing

## Full Example

```python
import fitz
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
import re

# STEP 1: Extract (no reporting)
doc_pdf = fitz.open('input.pdf')
all_pages = [doc_pdf[i].get_text() for i in range(len(doc_pdf))]
doc_pdf.close()

all_text = '\n\n'.join(all_pages)

# STEP 2: Apply modifications (silently)
all_text = all_text.replace('Old School', 'New School')
all_text = all_text.replace('5-8分', '5~8分')

# STEP 3: Identify structure
chapters = identify_chapters(all_text)

# STEP 4: Create complete document
create_structured_docx(chapters, all_text, 'output.docx')

# STEP 5: Verify completeness
doc_check = Document('output.docx')
assert len([p for p in doc_check.paragraphs if p.style.name.startswith('Heading')]) >= len(chapters)

# NOW report completion
print("✅ Document conversion complete")
print(f"   - {len(chapters)} chapters")
print(f"   - {len(doc_check.tables)} tables")
print(f"   - Target: [New School]")
```

## Related Files

- `chinese-doc-tools.md` - Full doc_tools implementation for PDF/Excel/PPT generation
