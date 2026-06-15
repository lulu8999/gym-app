# Debugging Silent Failures in Scripts

## Problem

Scripts can fail silently due to missing dependencies, network issues, or other errors, then fall back to reading stale data. This causes "same as yesterday" problems in reports and monitoring.

## Detection Pattern

```python
import os, time, glob

def check_data_freshness(data_dir, pattern, max_age_hours=24):
    """Check if data files are fresh"""
    files = sorted(glob.glob(os.path.join(data_dir, pattern)), reverse=True)
    if not files:
        return False, "No data files found"
    
    newest = files[0]
    mtime = os.path.getmtime(newest)
    age_hours = (time.time() - mtime) / 3600
    
    if age_hours > max_age_hours:
        return False, f"Data is {age_hours:.1f}h old (max {max_age_hours}h)"
    
    return True, f"Data is {age_hours:.1f}h old"

# Usage
fresh, msg = check_data_freshness('/root/stock_analyzer/reports', 'report_*.md')
if not fresh:
    print(f"⚠️ Warning: {msg}")
```

## Common Silent Failure Patterns

### 1. Missing Dependencies

```python
# PROBLEM: Script fails, no error shown
try:
    import akshare as ak
    # ... use akshare
except ImportError:
    pass  # Silently fails

# SOLUTION: Check dependency explicitly
def check_dependencies():
    required = ['akshare', 'pandas', 'requests']
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print(f"❌ Missing dependencies: {', '.join(missing)}")
        print(f"   Install with: pip install {' '.join(missing)}")
        return False
    return True
```

### 2. Network Timeouts

```python
# PROBLEM: Network fails silently
try:
    response = requests.get(url, timeout=10)
    data = response.json()
except:
    pass  # Silently uses stale data

# SOLUTION: Track success/failure
def fetch_data_with_tracking(url, cache_file):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Save success timestamp
        with open(cache_file, 'w') as f:
            json.dump({'last_success': time.time()}, f)
        
        return data
    except Exception as e:
        # Check when we last succeeded
        if os.path.exists(cache_file):
            with open(cache_file) as f:
                cache = json.load(f)
            last_success = cache.get('last_success', 0)
            hours_ago = (time.time() - last_success) / 3600
            print(f"⚠️ Network error: {e}")
            print(f"   Last successful fetch: {hours_ago:.1f}h ago")
        else:
            print(f"❌ Network error and no cache: {e}")
        
        return None
```

### 3. API Rate Limits

```python
# PROBLEM: 429 errors cause silent fallback
try:
    data = api_call()
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 429:
        pass  # Silently uses old data

# SOLUTION: Handle rate limits explicitly
def api_call_with_rate_limit():
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"⚠️ Rate limited, retry after {retry_after}s")
            time.sleep(retry_after)
            return api_call_with_rate_limit()  # Retry once
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ API error: {e}")
        return None
```

## Debugging Checklist

1. **Check file timestamps:**
   ```bash
   ls -lt /path/to/data/ | head -5
   ```

2. **Check for error logs:**
   ```bash
   grep -i "error\|warning\|failed" /path/to/script.log | tail -20
   ```

3. **Test dependencies:**
   ```bash
   python3 -c "import akshare; print('akshare OK')"
   ```

4. **Run script manually:**
   ```bash
   python3 /path/to/script.py 2>&1 | tail -20
   ```

5. **Check network connectivity:**
   ```bash
   curl -I https://api.example.com/endpoint
   ```

## Prevention Patterns

### 1. Always Log Errors

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    # ... risky operation
except Exception as e:
    logger.error(f"Operation failed: {e}")
    raise  # Re-raise if critical
```

### 2. Track Success/Failure State

```python
def track_operation(name, success):
    state_file = f'/tmp/{name}_state.json'
    state = {'last_run': time.time(), 'success': success}
    with open(state_file, 'w') as f:
        json.dump(state, f)

def check_operation_freshness(name, max_age_hours=24):
    state_file = f'/tmp/{name}_state.json'
    if not os.path.exists(state_file):
        return False, "No state file"
    
    with open(state_file) as f:
        state = json.load(f)
    
    age_hours = (time.time() - state['last_run']) / 3600
    if age_hours > max_age_hours:
        return False, f"Last success was {age_hours:.1f}h ago"
    
    return True, f"Last success was {age_hours:.1f}h ago"
```

### 3. Validate Output Before Using

```python
def load_report(report_dir):
    files = sorted(glob.glob(os.path.join(report_dir, 'report_*.md')), reverse=True)
    if not files:
        return "No report found"
    
    with open(files[0]) as f:
        content = f.read()
    
    # Validate content is not empty or error message
    if len(content) < 100:
        return "Report too short - possible error"
    if 'Error' in content or 'Failed' in content:
        return "Report contains errors"
    
    return content
```

## Real-World Example: Stock Report

**Problem:** Stock report showed same data as yesterday because akshare was missing.

**Root cause:**
1. `main.py` failed to import akshare
2. Script caught exception and continued
3. Script read yesterday's report file (most recent)
4. User saw "same as yesterday"

**Solution:**
```bash
pip install akshare  # Install missing dependency
```

**Verification:**
```bash
# Check if new report was generated
ls -lt /root/stock_analyzer/reports/ | head -3

# Verify content differs from yesterday
diff report_20260604.md report_20260605.md
```