# OCR Feature Setup Guide

## Overview

This feature adds OCR (Optical Character Recognition) functionality to the Assessment Result doctype. When users upload a certificate image in the `custom_certificate` field, the system will automatically extract text from the image and display it in comments and print formats.

## Features

- **Automatic OCR Processing**: Text is automatically extracted when a certificate image is uploaded
- **Comments Integration**: OCR results are added as comments to the document
- **Print Format Integration**: OCR data is displayed in the certificate print format
- **Confidence Scoring**: Shows the confidence level of text extraction
- **Manual Processing**: Users can manually trigger OCR processing with a button

## Installation

### 1. Install System Dependencies

First, install Tesseract OCR on your system:

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-eng  # English language pack
```

**CentOS/RHEL:**
```bash
sudo yum install tesseract
sudo yum install tesseract-langpack-eng  # English language pack
```

**macOS:**
```bash
brew install tesseract
```

### 2. Install Python Dependencies

The required Python packages are already added to `requirements.txt`:

```bash
pip install pytesseract>=0.3.10
pip install Pillow>=9.0.0
pip install opencv-python>=4.5.0
```

### 3. Restart Frappe Services

After installing dependencies, restart your Frappe services:

```bash
bench restart
```

## Testing

Run the test script to verify OCR functionality:

```bash
cd /home/frappe/numero
python test_ocr_functionality.py
```

## Usage

### For Users

1. **Upload Certificate**: Go to an Assessment Result document and upload an image in the "Certificate" field
2. **Automatic Processing**: OCR will automatically process the image and extract text
3. **View Results**: 
   - Check the "OCR Extracted Text" field for the extracted text
   - Check the "OCR Confidence" field for the confidence score
   - View comments for detailed OCR results
4. **Manual Processing**: Click the "Extract Text (OCR)" button to manually process OCR
5. **Print Certificate**: The OCR data will be included in the certificate print format

### For Developers

#### OCR Utility Functions

```python
from numerouno.numerouno.utils.ocr_utils import extract_text_from_image, process_certificate_ocr

# Extract text from an image file
result = extract_text_from_image('/path/to/image.jpg')
print(result['text'])
print(result['confidence'])

# Process OCR for a document
result = process_certificate_ocr('Assessment Result', 'DOC-001', 'custom_certificate')
```

#### Custom Fields Added

- `ocr_extracted_text`: Stores the extracted text (read-only)
- `ocr_confidence`: Stores the confidence score (read-only)

## Configuration

### Tesseract Configuration

You can modify OCR settings in `/home/frappe/numero/apps/numerouno/numerouno/numerouno/utils/ocr_utils.py`:

- **Confidence Threshold**: Change the minimum confidence level (default: 30%)
- **Image Preprocessing**: Modify image preprocessing settings for better results
- **Tesseract Options**: Adjust Tesseract configuration parameters

### Print Format Customization

The OCR data display in print format can be customized in:
`/home/frappe/numero/apps/numerouno/numerouno/numerouno/print_format/assessment_certificate/assessment_certificate.json`

## Troubleshooting

### Common Issues

1. **Tesseract not found**
   - Ensure Tesseract is installed and in PATH
   - On some systems, you may need to set the Tesseract path in the code

2. **Low OCR accuracy**
   - Ensure images are clear and high resolution
   - Try different image preprocessing settings
   - Consider using different Tesseract language packs

3. **Import errors**
   - Ensure all Python dependencies are installed
   - Check that the virtual environment is activated

4. **Permission errors**
   - Ensure Frappe has read access to uploaded files
   - Check file permissions in the files directory

### Debug Mode

Enable debug logging by adding this to your site's `site_config.json`:

```json
{
  "logging": {
    "level": "DEBUG"
  }
}
```

## File Structure

```
apps/numerouno/numerouno/numerouno/
├── utils/
│   └── ocr_utils.py                    # OCR utility functions
├── doctype/assessment_result/
│   ├── assessment_result.py            # Server-side logic
│   └── assessment_result.js            # Client-side logic
├── custom/
│   └── assessment_result.json          # Custom fields definition
└── print_format/assessment_certificate/
    └── assessment_certificate.json     # Print format with OCR data
```

## Support

For issues or questions regarding the OCR feature:

1. Check the test script output for common issues
2. Review the Frappe logs for error messages
3. Ensure all dependencies are properly installed
4. Verify Tesseract is working with command line: `tesseract --version`

## License

This feature is part of the Numerouno app and follows the same license terms.
