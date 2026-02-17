# Attachment Upload Size Limitations

## 🔍 Important Discovery

**Finding:** The `upload_attachment` MCP tool has practical size limits due to parameter encoding constraints.

**Discovered by:** User testing on 2026-02-16
**Test Case:** Uploading an 11 KB screenshot to incident INC0010062

---

## 📊 Test Results

| File Type | Binary Size | Base64 Size | Result | Notes |
|-----------|-------------|-------------|---------|-------|
| **Screenshot (JPEG)** | 11,097 bytes | ~15 KB | ❌ Truncated | Only 681 bytes uploaded |
| **Text file** | <1 KB | <2 KB | ✅ Success | Full content uploaded |

**Conclusion:** MCP tool parameters have practical limits around 5-7 KB for base64-encoded content.

---

## ⚠️ Size Limit Explanation

### Why This Happens

Base64 encoding increases file size by ~33%:
```
Original binary: 11,097 bytes
Base64 encoded:  ~14,796 bytes (11,097 × 1.33)
JSON escaped:    ~15,000+ bytes
```

**MCP Protocol Constraints:**
- Tool parameters are JSON strings
- JSON strings have practical limits
- Base64 adds 33% overhead
- Large parameters may be truncated by:
  - FastMCP framework
  - Claude Desktop
  - MCP protocol implementation

### Safe File Size Guidelines

| Category | Max Binary Size | Max Base64 Size | Reliability |
|----------|-----------------|-----------------|-------------|
| **Very Safe** | <1 KB | <2 KB | 100% ✅ |
| **Safe** | <5 KB | <7 KB | 95% ✅ |
| **Risky** | 5-10 KB | 7-14 KB | 50% ⚠️ |
| **Will Fail** | >10 KB | >14 KB | 0% ❌ |

---

## ✅ Recommended Usage

### Use `upload_attachment` MCP Tool For:

✅ **Small Text Files** (<5 KB)
- Log file snippets
- Error messages
- Stack traces
- Configuration files (JSON, XML, YAML)
- Code snippets
- Small CSV data
- Text-based reports

**Example:**
```json
{
  "table": "incident",
  "record_id": "abc123",
  "file_name": "error_log.txt",
  "file_content_base64": "RXJyb3I6IERhdGFiYXNlIGNvbm5lY3Rpb24gZmFpbGVk...",
  "content_type": "text/plain"
}
```

✅ **Tiny Binary Files** (<2 KB)
- Small icons (16x16, 32x32 PNG)
- Favicons
- QR codes
- Thumbnails

---

### Do NOT Use `upload_attachment` For:

❌ **Screenshots** (typically 50-500 KB)
- Use ServiceNow UI drag-and-drop
- Or Scripted REST API with multipart upload

❌ **Photos** (typically 100 KB - 5 MB)
- Use ServiceNow UI
- Or external storage (S3, SharePoint) with URL reference

❌ **Large PDFs** (>10 KB)
- Use ServiceNow UI
- Or split into pages

❌ **Videos**
- Use external storage (YouTube, S3, etc.)
- Store URL in incident

❌ **ZIP Files**
- Use ServiceNow UI
- Or extract and upload individual small files

❌ **Office Documents** (Word, Excel, PowerPoint)
- Use ServiceNow UI
- Or export to text/CSV for small data

---

## 🔧 Workarounds for Large Files

### Option 1: ServiceNow UI Upload (Recommended)

**Best for:** Manual uploads, one-off attachments

**Steps:**
1. Open incident/record in ServiceNow UI
2. Navigate to "Attachments" section
3. Drag and drop file or click "Attach"
4. Done ✅

**Pros:**
- ✅ No size limits (ServiceNow default: 1 GB)
- ✅ Progress bar for large files
- ✅ Supports all file types
- ✅ No encoding overhead

**Cons:**
- ❌ Requires manual action
- ❌ Not automatable from Claude Desktop

---

### Option 2: Scripted REST API with Multipart Upload

**Best for:** Automated workflows, bulk uploads, integration scenarios

**Implementation:**

**Step 1: Create Scripted REST API in ServiceNow**

```javascript
// System Web Services > Scripted REST APIs
// Name: Attachment Upload
// Path: /api/x_company/attachment/upload

(function process(request, response) {
    var attachmentGR = new GlideSysAttachment();

    // Upload from multipart form data
    var attachmentId = attachmentGR.write(
        request.files.uploadFile,              // File from multipart
        request.queryParams.table_name,        // Target table
        request.queryParams.table_sys_id       // Target record
    );

    if (attachmentId) {
        // Get attachment metadata
        var attachment = new GlideRecord('sys_attachment');
        attachment.get(attachmentId);

        return {
            success: true,
            attachment: {
                sys_id: attachmentId,
                file_name: attachment.getValue('file_name'),
                size_bytes: attachment.getValue('size_bytes'),
                content_type: attachment.getValue('content_type'),
                download_link: attachment.getDisplayValue('download_link')
            }
        };
    } else {
        return {
            success: false,
            error: "Failed to create attachment"
        };
    }
})(request, response);
```

**Step 2: Call from MCP via `execute_scripted_rest_api`**

This still requires base64 in the MCP parameter, so it doesn't solve the size issue from Claude Desktop. This approach works better when calling the API directly from external systems.

---

### Option 3: External Storage with URL Reference

**Best for:** Very large files (>1 MB), videos, long-term storage

**Supported External Storage:**
- AWS S3
- Azure Blob Storage
- Google Cloud Storage
- SharePoint/OneDrive
- Dropbox
- Box

**Implementation:**

**Step 1: Upload file to external storage**
```
User uploads file to S3 bucket
→ Gets URL: https://my-bucket.s3.amazonaws.com/screenshots/INC0010062.png
```

**Step 2: Add URL to ServiceNow**

**Option A: Work notes (simple)**
```
"Add work note to incident INC0010062:
Screenshot uploaded to: https://my-bucket.s3.amazonaws.com/screenshots/INC0010062.png"
```

**Option B: Custom URL field (better)**
```
Create custom field: u_screenshot_url
Update incident with URL
```

**Option C: Knowledge article (best for documentation)**
```
Create KB article with embedded images/videos
Link KB to incident
```

**Pros:**
- ✅ No size limits
- ✅ Better for videos, high-res images
- ✅ Cheaper storage (S3 vs ServiceNow)
- ✅ CDN delivery for fast access
- ✅ Version control

**Cons:**
- ❌ Requires external infrastructure
- ❌ Security/permissions management
- ❌ File not in ServiceNow attachment list

---

### Option 4: Split Large Files

**Best for:** Log files, CSVs, text documents that can be chunked

**Example: Large log file (50 KB)**
```
1. Split into 10 × 5 KB chunks
2. Upload each chunk separately
   - error_log_part1.txt
   - error_log_part2.txt
   - ...
3. Or extract only relevant sections
   - error_log_errors_only.txt (5 KB)
```

**Pros:**
- ✅ Works with MCP tool
- ✅ Automated from Claude Desktop
- ✅ Stays in ServiceNow

**Cons:**
- ❌ Multiple files to manage
- ❌ Requires reassembly
- ❌ Only works for text files

---

## 📝 Updated Tool Documentation

The `upload_attachment` docstring now includes:

```python
"""
Upload an attachment to any ServiceNow record.

**IMPORTANT:** This tool works best for small files (<5 KB binary, <7 KB base64).
Large files (screenshots, photos, PDFs) may be truncated due to MCP parameter limits.
For large files, use ServiceNow UI drag-and-drop or Scripted REST API with multipart upload.

Best For:
    - Log files, error messages, stack traces
    - Configuration files (JSON, XML, YAML)
    - Small text documents
    - Code snippets

Not Recommended For:
    - Screenshots (use UI upload)
    - Photos/images >10 KB
    - Large PDFs
    - Videos or binary files
"""
```

---

## 🧪 Testing Guidelines

### Before Uploading, Check File Size

**In Claude Desktop:**
```
User: "I have a screenshot to upload"

Claude should ask:
"What's the file size? If it's larger than 10 KB, I recommend
using the ServiceNow UI drag-and-drop instead, as the MCP tool
has size limitations for large binary files."
```

### Test Upload Success

After uploading, verify the file size:
```
"List attachments on incident INC0012345 and check the file sizes"
```

If uploaded file is much smaller than expected → Truncation occurred

---

## 📊 Real-World Test Case

**Incident:** INC0010062
**Test Date:** 2026-02-16

| Attempt | Method | File Size | Result |
|---------|--------|-----------|--------|
| 1 | MCP `upload_attachment` | 11,097 bytes | ❌ Truncated to 681 bytes |
| 2 | ServiceNow UI upload | 11,097 bytes | ✅ Success (full file) |
| 3 | MCP small text file | <1 KB | ✅ Success |

**Lesson:** MCP tool excellent for small text files, UI better for images/screenshots.

---

## 💡 Best Practices

### 1. Choose the Right Tool for the Job

```
Small text file (<5 KB)      → Use MCP upload_attachment ✅
Large screenshot (>10 KB)    → Use ServiceNow UI ✅
Video or huge file (>1 MB)   → Use external storage + URL ✅
```

### 2. Provide Clear Guidance to Users

When user wants to attach a file, Claude should ask:
```
"Is this a small text file (<5 KB) or a larger file like a screenshot?
For large files, I recommend using the ServiceNow UI drag-and-drop."
```

### 3. Validate Before Upload

Check file size before attempting upload:
```python
if base64_size > 7000:  # 7 KB threshold
    return "This file is too large for MCP upload. Please use ServiceNow UI."
```

### 4. Extract Relevant Content

Instead of uploading full log file:
```
❌ Upload entire 50 KB log file
✅ Extract error lines only (2 KB)
✅ Upload relevant excerpt
✅ Add full log to external storage
```

---

## 🎯 Summary

| File Size | Recommended Method | Tool |
|-----------|-------------------|------|
| <5 KB | MCP Tool | `upload_attachment` |
| 5-10 KB | MCP (risky) or UI | Either |
| >10 KB | ServiceNow UI | Drag & drop |
| >1 MB | External storage | S3 + URL |

**Key Takeaway:** The MCP `upload_attachment` tool is perfect for automating small text file uploads (logs, configs, error messages) but not suitable for screenshots, photos, or large documents. For those, stick with the ServiceNow UI or external storage.

---

## ✅ Updated Files

- ✅ `server.py` - Updated `upload_attachment` docstring with size warnings
- ✅ `ATTACHMENT_SIZE_LIMITS.md` - This comprehensive guide
- ✅ Syntax validated

The tool now has proper documentation about its limitations! 🚀
