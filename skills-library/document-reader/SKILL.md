---
name: document-reader
description: Read uploaded PDF, DOCX, PPTX, and XLSX files inside the Sandbox. Use this skill whenever a user asks to inspect or extract content from one of these files.
---

# Document

Use the exact input path supplied by the user:

```bash
sandbox-cli document read <input-path>
```

The command returns JSON containing `text`, `text_truncated`, and `image_paths`.
Read the text, then inspect the page images with the available image-viewing tool when layout or visual content matters. If `text_truncated` is true, read the complete content from `text_path`.

## Example

Input:

```bash
sandbox-cli document read "/home/user/uploads/report.pdf"
```

Output:

```json
{"schema_version":1,"text":"Quarterly report...","text_truncated":false,"image_paths":["/tmp/document-reader-123456789/page-1.png"]}
```
