# Using QR Code in Print Formats

This guide explains how to use the bulk QR code functionality in print formats.

## Setup

The QR code filter has been added to the Jinja environment. After restarting your Frappe bench, the filter will be available in all print format templates.

## Usage in Print Formats

### Basic Usage

Use the `qr_code` filter to generate QR codes directly in your print format templates:

```jinja
<!-- Simple QR code with default size (120px) -->
{% set verify_url = frappe.utils.get_url() ~ "/certificate-verification?cert=" ~ doc.name %}
<img src="{{ verify_url | qr_code }}" alt="QR Code">
```

### With Custom Size

```jinja
<!-- QR code with custom size (150px) -->
<img src="{{ verify_url | qr_code(150) }}" alt="QR Code">
```

### With All Parameters

```jinja
<!-- QR code with custom size, box_size, and border -->
<img src="{{ verify_url | qr_code(150, 12, 2) }}" alt="QR Code">
```

**Parameters:**
- `size`: Output image size in pixels (default: 120)
- `box_size`: Size of each box in pixels (default: 10)
- `border`: Border thickness in boxes (default: 4)

## Examples

### Example 1: Student ATM Card Print Format

Replace the external QR code service with your own:

**Before:**
```jinja
<img src="https://barcode.tec-it.com/barcode.ashx?data={{ verify_url|urlencode }}&code=QRCode&dpi=150">
```

**After:**
```jinja
{% set verify_url = frappe.utils.get_url() ~ "/certificate-verification?cert=" ~ doc.name %}
<img src="{{ verify_url | qr_code(120) }}" style="width: 16mm; height: 16mm;" alt="QR Code">
```

### Example 2: Assessment Certificate Print Format

```jinja
<td>
  {% set verify_url = frappe.utils.get_url() ~ "/certificate-verification?cert=" ~ doc.name %}
  <img src="{{ verify_url | qr_code(120) }}" width="120" height="120" alt="QR Code">
  ACTVET License No.<br/>0716/2013
</td>
```

### Example 3: Bulk Print Format (Multiple QR Codes)

For bulk printing scenarios where you need QR codes for multiple documents:

```jinja
{% for item in doc.items %}
  <div class="item-row">
    <h3>{{ item.name }}</h3>
    {% set item_url = frappe.utils.get_url() ~ "/item-details?item=" ~ item.name %}
    <img src="{{ item_url | qr_code(100) }}" alt="QR Code for {{ item.name }}">
  </div>
{% endfor %}
```

### Example 4: Custom Data in QR Code

You can encode any data in the QR code:

```jinja
<!-- Encode document name -->
<img src="{{ doc.name | qr_code }}" alt="QR Code">

<!-- Encode custom URL -->
{% set custom_data = "https://example.com/verify/" ~ doc.name %}
<img src="{{ custom_data | qr_code(150) }}" alt="QR Code">

<!-- Encode JSON data -->
{% set json_data = '{"doc": "' ~ doc.name ~ '", "type": "' ~ doc.doctype ~ '"}' %}
<img src="{{ json_data | qr_code }}" alt="QR Code">
```

## Complete Print Format Example

Here's a complete example showing how to integrate QR codes into a print format:

```jinja
<style>
  .qr-code {
    width: 120px;
    height: 120px;
    display: block;
    margin: 10px auto;
  }
</style>

<div class="certificate">
  <h1>Certificate</h1>
  <p>Student: {{ doc.student_name }}</p>
  <p>Course: {{ doc.course }}</p>
  
  <!-- QR Code Section -->
  <div class="qr-section">
    <p>Scan to verify:</p>
    {% set verify_url = frappe.utils.get_url() ~ "/certificate-verification?cert=" ~ doc.name %}
    <img src="{{ verify_url | qr_code(150) }}" class="qr-code" alt="Verification QR Code">
  </div>
</div>
```

## Troubleshooting

### Filter Not Working

1. **Restart Frappe Bench**: After adding the filter, restart your bench:
   ```bash
   bench restart
   ```

2. **Check Hook Registration**: Verify that `hooks.py` has:
   ```python
   jinja = {
       "filters": "numerouno.numerouno.utils.jinja_filters"
   }
   ```

3. **Check Function Name**: The filter function must be named `qr_code` in `jinja_filters.py`

### QR Code Not Displaying

1. **Check Data**: Ensure the data being encoded is not empty
2. **Check Image Tag**: Verify the `<img>` tag syntax is correct
3. **Check Size**: Very large QR codes may take time to generate

### Performance

- For bulk printing with many QR codes, consider:
  - Using smaller sizes (e.g., 100px instead of 150px)
  - Generating QR codes in batches
  - Caching QR codes if the same data is used multiple times

## API Reference

The filter uses the `generate_qr_code` function from `numerouno.api`:

```python
generate_qr_code(data, size=120, box_size=10, border=4)
```

This function returns a base64-encoded data URI that can be used directly in `<img src="">` tags.

