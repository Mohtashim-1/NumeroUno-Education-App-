# Copyright (c) 2024, Numerouno and contributors
# For license information, please see license.txt

import frappe
import os
import io
from PIL import Image
import numpy as np
from frappe.utils import get_files_path

# Try to import pytesseract with fallback handling
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError as e:
    TESSERACT_AVAILABLE = False
    frappe.log_error(f"pytesseract not available: {e}", "OCR Utils")

# Try to import OpenCV with fallback handling
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError as e:
    OPENCV_AVAILABLE = False
    frappe.log_error(f"OpenCV not available: {e}", "OCR Utils")

# Configure Tesseract path if needed
def configure_tesseract():
    """Configure Tesseract path for different environments"""
    if not TESSERACT_AVAILABLE:
        return False
    
    try:
        # Try to find tesseract in common locations
        possible_paths = [
            '/usr/bin/tesseract',
            '/usr/local/bin/tesseract',
            '/opt/homebrew/bin/tesseract',  # macOS with Homebrew
            '/usr/bin/tesseract-ocr',
            '/usr/local/bin/tesseract-ocr'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                frappe.logger().info(f"Tesseract configured at: {path}")
                return True
        
        # Try to use system PATH
        pytesseract.get_tesseract_version()
        frappe.logger().info("Tesseract found in system PATH")
        return True
        
    except Exception as e:
        frappe.logger().error(f"Tesseract configuration failed: {e}")
        return False

# Configure tesseract on import
TESSERACT_CONFIGURED = configure_tesseract()

@frappe.whitelist()
def check_ocr_availability():
    """
    Check if OCR functionality is available
    
    Returns:
        dict: Status of OCR availability
    """
    status = {
        'pytesseract_available': TESSERACT_AVAILABLE,
        'opencv_available': OPENCV_AVAILABLE,
        'tesseract_configured': TESSERACT_CONFIGURED,
        'ocr_available': TESSERACT_AVAILABLE and TESSERACT_CONFIGURED
    }
    
    if not TESSERACT_AVAILABLE:
        status['error'] = "pytesseract module is not installed. Please add it to requirements.txt and restart the server."
    elif not OPENCV_AVAILABLE:
        status['error'] = "OpenCV is not available. This might be due to missing system dependencies (libGL.so.1)."
    elif not TESSERACT_CONFIGURED:
        status['error'] = "Tesseract OCR binary is not found. Please install Tesseract OCR on your system."
    else:
        status['message'] = "OCR functionality is available and ready to use."
    
    return status

def extract_text_from_image(file_path):
	"""
	Extract text from image using OCR
	
	Args:
		file_path (str): Path to the image file
		
	Returns:
		dict: Dictionary containing extracted text and confidence scores
	"""
	print(f"DEBUG: extract_text_from_image called with file_path: {file_path}")
	
	# Check if Tesseract is available
	if not TESSERACT_AVAILABLE:
		error_msg = "pytesseract module is not available. Please install it using: pip install pytesseract"
		print(f"DEBUG: {error_msg}")
		frappe.log_error(error_msg, "OCR Utils")
		return {
			'text': '',
			'confidence': 0,
			'text_blocks': [],
			'confidences': [],
			'success': False,
			'error': error_msg
		}
	
	if not TESSERACT_CONFIGURED:
		error_msg = "Tesseract OCR binary is not configured or not found. Please install Tesseract OCR on your system."
		print(f"DEBUG: {error_msg}")
		frappe.log_error(error_msg, "OCR Utils")
		return {
			'text': '',
			'confidence': 0,
			'text_blocks': [],
			'confidences': [],
			'success': False,
			'error': error_msg
		}
	
	try:
		# Check if file exists
		if not os.path.exists(file_path):
			print(f"DEBUG: File not found: {file_path}")
			frappe.throw(f"Image file not found: {file_path}")
		
		print("DEBUG: File exists, reading image with PIL")
		# Read image using PIL
		image = Image.open(file_path)
		print(f"DEBUG: Image loaded, mode: {image.mode}, size: {image.size}")
		
		# Convert to RGB if necessary
		if image.mode != 'RGB':
			print("DEBUG: Converting image to RGB")
			image = image.convert('RGB')
		
		# Handle OpenCV availability
		if OPENCV_AVAILABLE:
			print("DEBUG: Converting PIL image to OpenCV format")
			# Convert PIL image to OpenCV format
			opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
			print(f"DEBUG: OpenCV image shape: {opencv_image.shape}")
			
			print("DEBUG: Preprocessing image for better OCR")
			# Preprocess image for better OCR
			processed_image = preprocess_image(opencv_image)
			print("DEBUG: Image preprocessing completed")
		else:
			print("DEBUG: OpenCV not available, using PIL image directly")
			# Use PIL image directly if OpenCV is not available
			processed_image = image
		
		print("DEBUG: Running Tesseract OCR with multiple PSM modes")
		# Try multiple PSM modes to capture different text layouts
		psm_modes = [3, 6, 8, 13, 1, 4, 7]  # Different page segmentation modes
		best_text = ""
		best_confidence = 0
		all_texts = []
		
		for psm in psm_modes:
			try:
				print(f"DEBUG: Trying PSM mode {psm}")
				# Get structured data
				extracted_data = pytesseract.image_to_data(
					processed_image, 
					output_type=pytesseract.Output.DICT,
					config=f'--psm {psm}'
				)
				
				# Get raw text
				raw_text = pytesseract.image_to_string(processed_image, config=f'--psm {psm}')
				all_texts.append(raw_text)
				
				# Filter out empty text and low confidence
				text_blocks = []
				confidences = []
				
				for i in range(len(extracted_data['text'])):
					text = extracted_data['text'][i].strip()
					conf = int(extracted_data['conf'][i])
					
					if text and conf > 30:  # Only include text with confidence > 30%
						text_blocks.append(text)
						confidences.append(conf)
				
				combined_text = ' '.join(text_blocks)
				avg_confidence = sum(confidences) / len(confidences) if confidences else 0
				
				print(f"DEBUG: PSM {psm} - Text length: {len(combined_text)}, Confidence: {avg_confidence:.2f}")
				print(f"DEBUG: PSM {psm} - Sample: {combined_text[:100]}...")
				
				if len(combined_text) > len(best_text):
					best_text = combined_text
					best_confidence = avg_confidence
					
			except Exception as e:
				print(f"DEBUG: PSM {psm} failed: {e}")
				continue
		
		# Also try with different image preprocessing (only if OpenCV is available)
		if OPENCV_AVAILABLE:
			print("DEBUG: Trying alternative image preprocessing")
			try:
				# Try with different preprocessing
				alt_processed = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
				alt_processed = cv2.threshold(alt_processed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
				
				alt_text = pytesseract.image_to_string(alt_processed, config='--psm 3')
				all_texts.append(alt_text)
				print(f"DEBUG: Alternative preprocessing text: {alt_text[:200]}...")
				
			except Exception as e:
				print(f"DEBUG: Alternative preprocessing failed: {e}")
		else:
			print("DEBUG: Skipping alternative preprocessing (OpenCV not available)")
		
		# Combine all texts and find the most complete one
		combined_all_text = '\n'.join(all_texts)
		print(f"DEBUG: Combined all texts length: {len(combined_all_text)}")
		
		# Use the best structured text or the most complete raw text
		if len(combined_all_text) > len(best_text):
			final_text = combined_all_text
			print("DEBUG: Using combined all texts as it's more complete")
		else:
			final_text = best_text
			print("DEBUG: Using best structured text")
		
		print(f"DEBUG: Final OCR text: {final_text[:500]}...")
		print(f"DEBUG: Tesseract completed with best confidence: {best_confidence:.2f}")
		
		# Use the final text as the result
		full_text = final_text.strip()
		
		# Calculate average confidence from the best result
		avg_confidence = best_confidence
		print(f"DEBUG: Final text length: {len(full_text)}")
		print(f"DEBUG: Final text preview: {full_text[:200]}...")
		
		result = {
			'text': full_text,
			'confidence': avg_confidence,
			'text_blocks': full_text.split(),  # Split into words for compatibility
			'confidences': [avg_confidence] * len(full_text.split()),  # Use average confidence for all words
			'success': True
		}
		print(f"DEBUG: Returning OCR result: {result}")
		return result
		
	except Exception as e:
		print(f"DEBUG: Exception in extract_text_from_image: {str(e)}")
		print(f"DEBUG: Exception type: {type(e)}")
		import traceback
		print(f"DEBUG: Traceback: {traceback.format_exc()}")
		frappe.log_error(f"OCR Error: {str(e)}", "OCR Utils")
		return {
			'text': '',
			'confidence': 0,
			'text_blocks': [],
			'confidences': [],
			'success': False,
			'error': str(e)
		}

def preprocess_image(image):
	"""
	Preprocess image for better OCR results
	
	Args:
		image: OpenCV image or PIL image
		
	Returns:
		Preprocessed image
	"""
	if not OPENCV_AVAILABLE:
		# If OpenCV is not available, return the image as is
		frappe.logger().info("OpenCV not available, skipping image preprocessing")
		return image
	
	try:
		# Convert to grayscale
		gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
		
		# Apply Gaussian blur to reduce noise
		blurred = cv2.GaussianBlur(gray, (5, 5), 0)
		
		# Apply adaptive thresholding
		thresh = cv2.adaptiveThreshold(
			blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
		)
		
		# Morphological operations to clean up the image
		kernel = np.ones((1, 1), np.uint8)
		processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
		
		return processed
		
	except Exception as e:
		frappe.log_error(f"Image preprocessing error: {str(e)}", "OCR Utils")
		return image

def extract_text_from_attachment(attachment_name):
	"""
	Extract text from Frappe attachment
	
	Args:
		attachment_name (str): Name of the attachment
		
	Returns:
		dict: OCR result
	"""
	print(f"DEBUG: extract_text_from_attachment called with attachment_name: {attachment_name}")
	
	try:
		# Get file path from Frappe
		print("DEBUG: Getting file document from Frappe")
		print(f"DEBUG: Looking for file with name: {attachment_name}")
		
		# Try different ways to find the file
		file_doc = None
		
		# Method 1: Direct lookup by name
		try:
			file_doc = frappe.get_doc("File", {"name": attachment_name})
			print(f"DEBUG: File found by name: {file_doc.name}")
		except:
			pass
		
		# Method 2: Lookup by file_url
		if not file_doc:
			try:
				file_doc = frappe.get_doc("File", {"file_url": attachment_name})
				print(f"DEBUG: File found by file_url: {file_doc.name}")
			except:
				pass
		
		# Method 3: Lookup by attachment name pattern
		if not file_doc:
			try:
				# Extract filename from path
				filename = attachment_name.split('/')[-1]
				file_doc = frappe.get_doc("File", {"file_name": filename})
				print(f"DEBUG: File found by filename: {file_doc.name}")
			except:
				pass
		
		# Method 4: Search in database for similar files
		if not file_doc:
			try:
				# Extract filename from path
				filename = attachment_name.split('/')[-1]
				# Search for files with similar names
				files = frappe.db.sql("""
					SELECT name, file_name, file_url 
					FROM `tabFile` 
					WHERE file_name LIKE %s OR file_url LIKE %s
					ORDER BY creation DESC
					LIMIT 5
				""", (f"%{filename}%", f"%{filename}%"), as_dict=True)
				
				if files:
					print(f"DEBUG: Found similar files: {files}")
					# Use the first match
					file_doc = frappe.get_doc("File", files[0]['name'])
					print(f"DEBUG: Using similar file: {file_doc.name}")
			except Exception as e:
				print(f"DEBUG: Similar file search failed: {e}")
				pass
		
		if not file_doc:
			print(f"DEBUG: File not found with any method for: {attachment_name}")
			# List recent files to help debug
			debug_files()
			return {
				'text': '',
				'confidence': 0,
				'text_blocks': [],
				'confidences': [],
				'success': False,
				'error': f'File not found: {attachment_name}'
			}
		
		file_path = file_doc.get_full_path()
		print(f"DEBUG: File path: {file_path}")
		
		# Check if file exists
		import os
		if not os.path.exists(file_path):
			print(f"DEBUG: File does not exist at path: {file_path}")
			return {
				'text': '',
				'confidence': 0,
				'text_blocks': [],
				'confidences': [],
				'success': False,
				'error': f'File not found: {file_path}'
			}
		
		print("DEBUG: File exists, calling extract_text_from_image")
		# Extract text
		result = extract_text_from_image(file_path)
		print(f"DEBUG: extract_text_from_image result: {result}")
		return result
		
	except Exception as e:
		print(f"DEBUG: Exception in extract_text_from_attachment: {str(e)}")
		frappe.log_error(f"Attachment OCR Error: {str(e)}", "OCR Utils")
		return {
			'text': '',
			'confidence': 0,
			'text_blocks': [],
			'confidences': [],
			'success': False,
			'error': str(e)
		}

def format_ocr_result_for_display(ocr_result):
	"""
	Format OCR result for display in comments and print
	
	Args:
		ocr_result (dict): Result from extract_text_from_image
		
	Returns:
		str: Formatted text for display
	"""
	if not ocr_result.get('success', False):
		return f"OCR Error: {ocr_result.get('error', 'Unknown error')}"
	
	text = ocr_result.get('text', '')
	confidence = ocr_result.get('confidence', 0)
	
	if not text.strip():
		return "No text detected in the image"
	
	# Format the result
	formatted_text = f"""
📄 **OCR Extracted Text** (Confidence: {confidence:.1f}%)

{text}

---
*This text was automatically extracted from the uploaded certificate image using OCR technology.*
"""
	
	return formatted_text.strip()

def extract_specific_data_from_ocr(ocr_text):
	"""
	Extract specific information from OCR text
	
	Args:
		ocr_text (str): OCR extracted text
		
	Returns:
		dict: Extracted specific data
	"""
	import re
	from datetime import datetime
	
	extracted_data = {}
	
	try:
		print(f"DEBUG: Extracting data from OCR text: {ocr_text[:500]}...")
		print(f"DEBUG: Full OCR text for analysis:")
		print(f"DEBUG: {ocr_text}")
		print(f"DEBUG: " + "="*50)
		
		# Debug: Search for any text containing L followed by numbers
		import re
		l_patterns = re.findall(r'L\d+', ocr_text, re.IGNORECASE)
		print(f"DEBUG: Found L patterns: {l_patterns}")
		
		# Debug: Search for any text containing OPITO
		opito_patterns = re.findall(r'OPITO[A-Za-z0-9]*', ocr_text, re.IGNORECASE)
		print(f"DEBUG: Found OPITO patterns: {opito_patterns}")
		
		# Debug: Search for any long alphanumeric strings
		long_patterns = re.findall(r'[A-Za-z0-9]{10,}', ocr_text)
		print(f"DEBUG: Found long alphanumeric patterns: {long_patterns}")
		
		# Extract OPITO Learner No (multiple patterns)
		opito_patterns = [
			r'OPITO\s+Learner\s+No\s+([A-Z]\d+)',
			r'Learner\s+No\s+([A-Z]\d+)',
			r'OPITO\s+([A-Z]\d+)',
			r'OPITO\s+Learner\s+No\s+(\d+)',  # OPITO Learner No followed by just numbers
			r'Learner\s+No\s+(\d+)',  # Learner No followed by just numbers
			r'L(\d+)',  # Just L followed by numbers
			r'L0(\d+)',  # L0 followed by numbers
			r'L(\d{8})',  # L followed by 8 digits
			r'([A-Z]\d{8})',  # Letter followed by 8 digits
			r'L0(\d{7})',  # L0 followed by 7 digits
			r'L(\d{7})',  # L followed by 7 digits
			r'([A-Z]\d{7})',  # Letter followed by 7 digits
			r'L0(\d{6})',  # L0 followed by 6 digits
			r'L(\d{6})',  # L followed by 6 digits
			r'([A-Z]\d{6})',  # Letter followed by 6 digits
			r'L0(\d{5})',  # L0 followed by 5 digits
			r'L(\d{5})',  # L followed by 5 digits
			r'([A-Z]\d{5})',  # Letter followed by 5 digits
		]
		
		for pattern in opito_patterns:
			opito_match = re.search(pattern, ocr_text, re.IGNORECASE)
			if opito_match:
				learner_no = opito_match.group(1)
				print(f"DEBUG: Pattern matched: {pattern}, Group 1: {learner_no}")
				
				# Handle different patterns
				if pattern.startswith(r'OPITO\s+Learner\s+No\s+(\d+)') or pattern.startswith(r'Learner\s+No\s+(\d+)'):
					# For patterns that match just numbers, add L prefix (not L0)
					if not learner_no.startswith('L'):
						learner_no = 'L' + learner_no
				elif not learner_no.startswith('L'):
					learner_no = 'L' + learner_no
				
				extracted_data['opito_learner_no'] = learner_no
				print(f"DEBUG: Found OPITO Learner No: {learner_no}")
				break
		
		# Extract Unique Certificate No (multiple patterns)
		cert_patterns = [
			r'Unique\s+Certificate\s+No\s+OPITOKRK([A-Za-z0-9]+)',  # Specific for OPITOKRK pattern
			r'Unique\s+Certificate\s+No\s+([A-Za-z0-9]+)',  # General pattern
			r'Certificate\s+No\s+OPITOKRK([A-Za-z0-9]+)',  # Specific for OPITOKRK pattern
			r'Certificate\s+No\s+([A-Za-z0-9]+)',  # General pattern
			r'OPITOKRK([A-Za-z0-9]+)',  # Direct OPITOKRK pattern
			r'OPITO([A-Za-z0-9]+)',
			r'Cert\s+No\s+([A-Za-z0-9]+)',
			r'OPITO([A-Za-z0-9]{10,})',  # OPITO followed by 10+ alphanumeric
			r'([A-Z]{5}[A-Za-z0-9]{10,})',  # 5 letters followed by 10+ alphanumeric
			r'([A-Za-z0-9]{15,})',  # Any 15+ alphanumeric characters
			r'OPITO([A-Za-z0-9]{8,})',  # OPITO followed by 8+ alphanumeric chars
			r'([A-Za-z0-9]{12,})',  # Any 12+ alphanumeric characters
		]
		
		for pattern in cert_patterns:
			cert_match = re.search(pattern, ocr_text, re.IGNORECASE)
			if cert_match:
				cert_no = cert_match.group(1)
				print(f"DEBUG: Certificate pattern matched: {pattern}, Group 1: {cert_no}")
				
				# Clean the certificate number (remove spaces)
				cert_no = cert_no.replace(' ', '')
				
				# Handle different patterns
				if 'OPITOKRK' in pattern:
					# For OPITOKRK patterns, add OPITOKRK prefix
					cert_no = 'OPITOKRK' + cert_no
				elif pattern.startswith(r'Unique\s+Certificate\s+No\s+([A-Za-z0-9]+)') or pattern.startswith(r'Certificate\s+No\s+([A-Za-z0-9]+)'):
					# For patterns that already include the full certificate number, use as is
					pass  # cert_no is already the full number
				elif not cert_no.startswith('OPITO'):
					cert_no = 'OPITO' + cert_no
				
				extracted_data['unique_certificate_no'] = cert_no
				print(f"DEBUG: Found Unique Certificate No: {cert_no}")
				break
		
		# Extract Expiry Date (multiple patterns)
		expiry_patterns = [
			r'Expiry\s+Date\s+(\d{1,2})(?:st|nd|rd|th)?\s+(\w+)\s+(\d{4})',
			r'Expires?\s+(\d{1,2})(?:st|nd|rd|th)?\s+(\w+)\s+(\d{4})',
			r'Valid\s+until\s+(\d{1,2})(?:st|nd|rd|th)?\s+(\w+)\s+(\d{4})',
			r'(\d{1,2})(?:st|nd|rd|th)?\s+(\w+)\s+(\d{4})',  # Just date pattern
		]
		
		for pattern in expiry_patterns:
			expiry_match = re.search(pattern, ocr_text, re.IGNORECASE)
			if expiry_match:
				day = expiry_match.group(1)
				month_name = expiry_match.group(2)
				year = expiry_match.group(3)
				
				# Convert month name to number
				month_map = {
					'january': '01', 'february': '02', 'march': '03', 'april': '04',
					'may': '05', 'june': '06', 'july': '07', 'august': '08',
					'september': '09', 'october': '10', 'november': '11', 'december': '12'
				}
				
				month_num = month_map.get(month_name.lower(), '01')
				
				# Format as yyyy-mm-dd for MySQL compatibility
				formatted_date = f"{year}-{month_num}-{day.zfill(2)}"
				extracted_data['expiry_date'] = formatted_date
				print(f"DEBUG: Found Expiry Date: {formatted_date}")
				break
		
		print(f"DEBUG: Final extracted data: {extracted_data}")
		return extracted_data
		
	except Exception as e:
		print(f"DEBUG: Error extracting specific data: {e}")
		import traceback
		print(f"DEBUG: Traceback: {traceback.format_exc()}")
		return {}

@frappe.whitelist()
def debug_files():
	"""Debug function to list all files in the database"""
	try:
		files = frappe.db.sql("SELECT name, file_name, file_url FROM `tabFile` ORDER BY creation DESC LIMIT 10", as_dict=True)
		print("DEBUG: Recent files in database:")
		for file in files:
			print(f"  - Name: {file.name}, File Name: {file.file_name}, URL: {file.file_url}")
		return files
	except Exception as e:
		print(f"DEBUG: Error listing files: {e}")
		return []

@frappe.whitelist()
def process_certificate_ocr(doctype, docname, field_name):
	"""
	Process OCR for certificate field and add comment
	
	Args:
		doctype (str): Document type
		docname (str): Document name
		field_name (str): Field name containing the image
		
	Returns:
		dict: Processing result
	"""
	print(f"DEBUG: process_certificate_ocr called with doctype={doctype}, docname={docname}, field_name={field_name}")
	
	# Debug: List recent files
	debug_files()
	
	try:
		# Get the document
		doc = frappe.get_doc(doctype, docname)
		print(f"DEBUG: Document retrieved: {doc.name}")
		
		# Get the attachment name from the field
		attachment_name = getattr(doc, field_name, None)
		print(f"DEBUG: Attachment name from field '{field_name}': {attachment_name}")
		
		if not attachment_name:
			print("DEBUG: No attachment name found")
			return {
				'success': False,
				'message': 'No certificate image found'
			}
		
		# Extract text using OCR
		print(f"DEBUG: Calling extract_text_from_attachment with attachment_name: {attachment_name}")
		ocr_result = extract_text_from_attachment(attachment_name)
		print(f"DEBUG: OCR result: {ocr_result}")
		
		if not ocr_result.get('success', False):
			print(f"DEBUG: OCR failed: {ocr_result.get('error', 'Unknown error')}")
			return {
				'success': False,
				'message': f"OCR failed: {ocr_result.get('error', 'Unknown error')}"
			}
		
		# Format the result
		formatted_text = format_ocr_result_for_display(ocr_result)
		print(f"DEBUG: Formatted text length: {len(formatted_text)}")
		
		# Add comment to the document
		print("DEBUG: Adding comment to document")
		comment = frappe.get_doc({
			'doctype': 'Comment',
			'reference_doctype': doctype,
			'reference_name': docname,
			'content': formatted_text,
			'comment_type': 'Info',
			'comment_by': frappe.session.user
		})
		comment.insert(ignore_permissions=True)
		print("DEBUG: Comment added successfully")
		
		# Update document with OCR data (if needed)
		# You can add custom fields to store OCR data
		if hasattr(doc, 'ocr_extracted_text'):
			print("DEBUG: Updating document with OCR data")
			doc.ocr_extracted_text = ocr_result.get('text', '')
			doc.ocr_confidence = ocr_result.get('confidence', 0)
			
			# Extract specific information from OCR text
			extracted_data = extract_specific_data_from_ocr(ocr_result.get('text', ''))
			print(f"DEBUG: Extracted specific data: {extracted_data}")
			
			# Update custom fields with extracted data
			if extracted_data.get('opito_learner_no'):
				doc.custom_opito_learner_no = extracted_data['opito_learner_no']
				print(f"DEBUG: Set custom_opito_learner_no: {extracted_data['opito_learner_no']}")
			
			if extracted_data.get('unique_certificate_no'):
				doc.custom_unique_certificate_no = extracted_data['unique_certificate_no']
				print(f"DEBUG: Set custom_unique_certificate_no: {extracted_data['unique_certificate_no']}")
			
			if extracted_data.get('expiry_date'):
				doc.certificate_validity_date = extracted_data['expiry_date']
				print(f"DEBUG: Set certificate_validity_date: {extracted_data['expiry_date']}")
			
			doc.save(ignore_permissions=True)
			print("DEBUG: Document updated with OCR data and extracted fields")
		else:
			print("DEBUG: Document does not have ocr_extracted_text field")
		
		result = {
			'success': True,
			'message': 'OCR processing completed successfully',
			'extracted_text': ocr_result.get('text', ''),
			'confidence': ocr_result.get('confidence', 0),
			'comment_added': True,
			'extracted_data': extracted_data
		}
		print(f"DEBUG: Returning result: {result}")
		return result
		
	except Exception as e:
		frappe.log_error(f"Certificate OCR processing error: {str(e)}", "OCR Utils")
		return {
			'success': False,
			'message': f"Error processing OCR: {str(e)}"
		}
