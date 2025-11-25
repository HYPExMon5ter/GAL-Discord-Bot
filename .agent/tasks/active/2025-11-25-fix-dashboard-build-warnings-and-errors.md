# Fix Dashboard Build Warnings and Errors

## Issue Summary
The dashboard frontend is working but showing several warnings that should be fixed to prevent future issues:
1. Non-standard NODE_ENV value warning
2. Invalid next.config.js options (isrMemoryCacheSize)
3. Output standalone configuration warning with next start

## Root Causes
1. dotenv in next.config.js loads env vars that conflict with Next.js expectations
2. isrMemoryCacheSize is not a valid experimental option in Next.js 14.2
3. Using output: 'standalone' with npm start (should use node server.js instead)

## Solution
Update next.config.js to:
- Remove dotenv imports (Next.js handles .env files natively)
- Remove output: 'standalone' 
- Remove invalid isrMemoryCacheSize option

## Expected Outcome
- Clean startup without warnings
- Properly configured Next.js build
- Maintained functionality while following best practices
