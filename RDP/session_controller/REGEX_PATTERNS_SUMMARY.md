# RDP Controller Regex Patterns Summary

This document summarizes all regex patterns and validation patterns used in the `rdp-controller` container modules.

## Regex Patterns Implemented

### 1. URL Validation - Localhost Detection

**Pattern:** Used to detect `localhost` or `127.0.0.1` in URLs

**Implementation:**
```python
import re

# Pattern for localhost (word boundary ensures exact match)
localhost_pattern = re.compile(r'\blocalhost\b', re.IGNORECASE)

# Pattern for 127.0.0.1 (word boundary ensures exact match)
ip_pattern = re.compile(r'\b127\.0\.0\.1\b')
```

**Usage Locations:**
- `config.py` - `validate_mongodb_url()` and `validate_redis_url()`
- `integration/service_base.py` - URL validation in `__init__()`

**Why Regex Instead of Simple String Check:**
- `\blocalhost\b` ensures "localhost" is matched as a whole word
- Prevents false positives like "mylocalhost.com" matching
- `\b127\.0\.0\.1\b` ensures exact IP match
- Prevents false positives like "127.0.0.10" matching

**Example:**
```python
# ✅ Correctly matches
localhost_pattern.search("http://localhost:8080")  # True
ip_pattern.search("http://127.0.0.1:8080")  # True

# ✅ Correctly rejects
localhost_pattern.search("http://mylocalhost.com:8080")  # False
ip_pattern.search("http://127.0.0.10:8080")  # False
```

## Error Handling Patterns

### 2. HTTP Status Code Handling

**Pattern:** Standardized exception types for HTTP errors

**Implementation:**
```python
class ServiceError(Exception):
    """Base exception with status code"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code

class ServiceNotFoundError(ServiceError):
    """Exception for 404 errors"""
    def __init__(self, message: str):
        super().__init__(message, status_code=404)
```

**Usage:**
- `integration/service_base.py` - Raises `ServiceNotFoundError` for 404
- `integration/rdp_server_manager_client.py` - Catches `ServiceNotFoundError`
- `integration/rdp_monitor_client.py` - Catches `ServiceNotFoundError`

**Before (Fragile):**
```python
except ServiceError as e:
    if "404" in str(e):  # ❌ Fragile string check
        return {"status": "not_found"}
```

**After (Robust):**
```python
except ServiceNotFoundError:  # ✅ Type-based check
    return {"status": "not_found"}
```

## String Matching Patterns (Non-Regex)

### 3. File Extension Validation

**Pattern:** Case-insensitive file extension checking

**Implementation:**
```python
if path.suffix.lower() == '.yaml' or path.suffix.lower() == '.yml':
    # Handle YAML file
elif path.suffix.lower() == '.json':
    # Handle JSON file
```

**Location:** `config.py` - `_load_config_file()`

**Note:** This is appropriate for file extensions - no regex needed.

### 4. Log Level Validation

**Pattern:** Case-insensitive log level validation

**Implementation:**
```python
valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
if v.upper() not in valid_levels:
    raise ValueError(f'LOG_LEVEL must be one of {valid_levels}')
return v.upper()
```

**Location:** `config.py` - `validate_log_level()`

**Note:** This is appropriate for enum-like values - no regex needed.

## Pattern Consistency

All modules now use consistent patterns:

1. **URL Validation:** Regex with word boundaries (`\b`) for localhost/IP detection
2. **Error Handling:** Type-based exceptions (`ServiceNotFoundError`) instead of string checks
3. **File Extensions:** Case-insensitive `.lower()` comparison (appropriate for extensions)
4. **Enum Values:** Case-insensitive `.upper()` comparison (appropriate for enums)

## Files Updated

1. `config.py` - Added regex patterns for URL validation
2. `integration/service_base.py` - Added regex patterns and improved exception types
3. `integration/rdp_server_manager_client.py` - Updated to use `ServiceNotFoundError`
4. `integration/rdp_monitor_client.py` - Updated to use `ServiceNotFoundError`
5. `integration/__init__.py` - Added exception exports

## Testing

Regex patterns have been verified:
- ✅ `localhost` matches correctly
- ✅ `mylocalhost.com` does NOT match (word boundary prevents false positive)
- ✅ `127.0.0.1` matches correctly
- ✅ `127.0.0.10` does NOT match (word boundary prevents false positive)

## Benefits

1. **More Robust:** Word boundaries prevent false positives
2. **Type Safety:** Exception types instead of string checks
3. **Consistency:** All modules use the same patterns
4. **Maintainability:** Clear, documented patterns

