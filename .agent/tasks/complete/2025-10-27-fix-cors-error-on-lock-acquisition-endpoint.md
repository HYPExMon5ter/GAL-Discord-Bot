# Plan: Fix CORS Error on Lock Acquisition Endpoint

## Problem Analysis
The error shows:
1. **CORS Error**: `No 'Access-Control-Allow-Origin' header is present`
2. **500 Internal Server Error**: The endpoint is crashing before CORS headers can be added
3. **Endpoint**: `POST /api/v1/lock/5`

The issue is that middleware order matters in FastAPI. When an endpoint throws an exception (500 error), if CORS middleware isn't first, the error response won't have CORS headers.

## Root Cause
In `api/main.py`, the middleware is added in this order:
```python
# Line 43: CORS middleware
app.add_middleware(CORSMiddleware, ...)

# Lines 194-195: Custom middleware (added AFTER routers are included)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
```

The custom middleware is added **after** the routers, which reverses the execution order. When an exception occurs in an endpoint, the response goes through middleware in reverse order, and CORS headers might not be added.

## Solution

**Fix middleware order in `api/main.py`:**
1. Move CORS middleware addition to be the LAST middleware added (so it executes FIRST)
2. Ensure CORS middleware wraps all other middleware
3. This ensures CORS headers are added even for error responses

### Changes Required

**File: `api/main.py`**

Move the middleware configuration block:
```python
# BEFORE: (lines 43-48)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ... routers included ...

# Lines 194-195
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
```

**TO:**
```python
# Import middleware early (after app creation)
from .middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware

# Add custom middleware FIRST
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Add CORS middleware LAST (so it executes first in chain)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ... then include routers ...
```

## Expected Outcome
- CORS headers will be present on all responses, including errors
- The lock acquisition endpoint will still fail with 500, but the frontend will receive the error details
- This allows us to see the actual error and fix the underlying issue

## Files to Modify
1. `api/main.py` - Reorder middleware declarations