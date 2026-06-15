# Cron Output Viewing Page — Implementation Reference

## What it does

Adds a read-only page to the Flask admin panel showing all scheduled cron jobs, their execution history, and the full output of each run.

## Data Sources

| Data | Source | Format |
|------|--------|--------|
| Job config | `~/.hermes/cron/jobs.json` | JSON (`{jobs: [{id, name, schedule, last_run_at, last_status, ...}]}`) |
| Run output files | `~/.hermes/cron/output/<job_id>/` | `.md` files named `<YYYY-MM-DD_HH-MM-SS>.md` |

## Key Implementation Details

### Path traversal protection

When reading user-facing file content by filename from URL, always validate:

```python
def get_cron_job_run(job_id, filename):
    fpath = os.path.join(CRON_OUTPUT_DIR, job_id, filename)
    real = os.path.realpath(fpath)
    expected = os.path.realpath(CRON_OUTPUT_DIR)
    if not real.startswith(expected):  # blocks ../../etc/passwd attacks
        return None
    if not os.path.isfile(real):
        return None
    with open(real, encoding='utf-8') as f:
        return f.read()
```

### Jobs without runs

- Cron jobs in `no_agent` mode (script-only) store output as files in the output directory
- Cron jobs in agent mode (LLM-driven) store output as sessions in `state.db`
- Jobs that have never run have no output directory — return empty gracefully
- Use `last_run_at` and `last_status` from jobs.json for quick status display

### Stats on homepage

```python
cron_jobs = get_cron_jobs()
stats['cron_total'] = len(cron_jobs)
stats['cron_ok'] = sum(1 for j in cron_jobs if j.get('last_status') == 'ok')
```

### Template flow

```
index.html → /cron (job list) → /cron/<job_id> (run history) → /cron/<job_id>/<filename> (full output)
```

## Files Modified/Added

| File | Lines | Description |
|------|-------|-------------|
| `app.py` | ~100 | 3 helper functions + 3 routes |
| `templates/cron.html` | ~95 | Job list overview |
| `templates/cron_job.html` | ~100 | Single job run history |
| `templates/cron_run.html` | ~55 | Full output display |
| `templates/index.html` | ~10 | Entry card on homepage |

## Zero Token Cost

This feature reads local files and JSON only — no API calls, no LLM invocations.

## Cleanup Strategy

Output files accumulate over time (especially high-frequency jobs like a 20-minute watchdog). Implement auto-cleanup to prevent disk bloat:

```python
def cleanup_cron_outputs():
    \"\"\"Keep runs from the last 7 days, max 100 per job.\"\"\"
    if not os.path.isdir(CRON_OUTPUT_DIR):
        return 0
    cleaned = 0
    now = time.time()
    for job_id in os.listdir(CRON_OUTPUT_DIR):
        job_dir = os.path.join(CRON_OUTPUT_DIR, job_id)
        if not os.path.isdir(job_dir):
            continue
        files = [(f, os.path.getmtime(os.path.join(job_dir, f)))
                 for f in os.listdir(job_dir) if f.endswith('.md')]
        files.sort(key=lambda x: x[1])  # oldest first
        keep = [f for f in files if (now - f[1]) / 86400 <= 7]
        if len(keep) > 100:
            keep = keep[-100:]
        keep_set = {f[0] for f in keep}
        for fname, _ in files:
            if fname not in keep_set:
                os.remove(os.path.join(job_dir, fname))
                cleaned += 1
    return cleaned
```

**When to trigger:** Call `cleanup_cron_outputs()` at the top of the cron detail route so cleanup happens naturally when someone visits the page. For heavier deployments, add a separate scheduled maintenance script.

## Pagination

When a job has many runs (e.g., watchdog executing every 20 minutes → 72+ runs/day), paginate the history list:

```python
# In the route
page = request.args.get('page', 1, type=int)
per_page = 30
all_runs = get_cron_job_runs(job_id)
total = len(all_runs)
total_pages = max(1, math.ceil(total / per_page))
start = (page - 1) * per_page
runs = all_runs[start:start + per_page]

# Pass to template
render_template('cron_job.html', job=job, runs=runs,
               page=page, total_pages=total_pages, total=total)
```

Template pagination controls (GitHub Dark theme):
```html
{% if total_pages > 1 %}
<div class="pagination">
    {% if page > 1 %}
    <a href="?page={{ page - 1 }}" class="page-btn">‹ 上一页</a>
    {% endif %}
    <span class="page-info">{{ page }} / {{ total_pages }}</span>
    {% if page < total_pages %}
    <a href="?page={{ page + 1 }}" class="page-btn">下一页 ›</a>
    {% endif %}
</div>
{% endif %}
```

```css
.pagination {
    display: flex; align-items: center; justify-content: center;
    gap: 12px; margin-top: 16px;
}
.page-btn {
    color: #58a6ff; text-decoration: none; padding: 6px 14px;
    border: 1px solid #30363d; border-radius: 6px;
}
.page-btn:hover { background: #1f6feb33; border-color: #58a6ff; }
.page-info { color: #8b949e; font-size: 13px; }
```
