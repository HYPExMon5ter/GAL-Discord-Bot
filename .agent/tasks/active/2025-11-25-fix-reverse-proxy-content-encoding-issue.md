# Fix Reverse Proxy Content Encoding Issue

## Issue
The `net::ERR_CONTENT_DECODING_FAILED` error occurs because:
1. Next.js sends gzip-compressed responses with `content-encoding: gzip` header
2. httpx automatically decompresses the content when we access `response.content`
3. We then pass the decompressed content with the original `content-encoding: gzip` header
4. Browser tries to decompress already-decompressed content → fails

## Solution
Filter out problematic headers from the proxied response, specifically:
- `content-encoding` - httpx handles decompression
- `content-length` - length changes after decompression
- `transfer-encoding` - may conflict with our response

### Code Change in `api/main.py`:

```python
# Return the response from Next.js
# Filter out headers that cause encoding issues
excluded_headers = {'content-encoding', 'content-length', 'transfer-encoding'}
filtered_headers = {
    k: v for k, v in response.headers.items() 
    if k.lower() not in excluded_headers
}

return Response(
    content=response.content,
    status_code=response.status_code,
    headers=filtered_headers
)
```

This ensures the browser receives properly decoded content without conflicting encoding headers.
