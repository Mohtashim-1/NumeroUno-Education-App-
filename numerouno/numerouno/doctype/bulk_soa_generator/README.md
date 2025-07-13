# Bulk SOA Generator

## Overview

The Bulk SOA (Statement of Account) Generator is a comprehensive tool for generating and sending Statement of Account PDFs to multiple customers with LPO (Letter of Purchase Order) columns included.

## Features

### ✅ Bulk PDF Generation
- Generate SOA PDFs for multiple customers at once
- Support for both General Ledger and Accounts Receivable reports
- Customizable date ranges and filters
- Professional PDF formatting with letterhead support

### ✅ LPO Integration
- Automatically includes LPO (Letter of Purchase Order) numbers in SOA reports
- Links Sales Orders with their corresponding LPO numbers
- Displays LPO information in a dedicated column

### ✅ Single-Click Email Dispatch
- Send SOA emails to multiple customers with one click
- Automatic PDF attachment generation
- Customizable email templates with Jinja2 support
- Email tracking and status updates

### ✅ Customer Management
- Bulk customer selection by Customer Group or Territory
- Individual customer selection
- Email address validation and management

## How to Use

### 1. Create a New Bulk SOA Generator

1. Navigate to **Accounts > Bulk SOA Generator**
2. Click **New**
3. Fill in the required fields:
   - **Company**: Select your company
   - **Report Type**: Choose between General Ledger or Accounts Receivable
   - **From Date** and **To Date**: Set the period for the SOA
   - **Account**: (Optional) Filter by specific account
   - **Currency**: (Optional) Set presentation currency

### 2. Select Customers

#### Option A: Fetch by Criteria
1. Select **Customer Group** or **Territory**
2. Click **Fetch Customers** button
3. Review and modify the customer list as needed

#### Option B: Manual Selection
1. Add customers manually in the **Customers** table
2. Each customer will be validated for email addresses

### 3. Configure Email Settings

1. **Subject**: Customize email subject (supports Jinja2 templates)
2. **Body**: Write email body (supports Jinja2 templates)
3. **PDF Filename**: Set template for PDF filename
4. **Sender**: Select email account for sending

### 4. Generate and Send

#### Generate PDF Only
- Click **Generate PDF** button
- PDFs will be generated for all selected customers
- LPO numbers will be included in the reports

#### Send Emails
- Click **Send Emails** button
- Confirm the action
- Emails will be sent to all customers with valid email addresses
- PDFs will be automatically attached

#### Download Combined PDF
- Click **Download PDF** button
- All customer SOAs will be combined into a single PDF file

## Template Variables

### Available in Email Templates

- `{{ customer.customer_name }}` - Customer name
- `{{ customer.name }}` - Customer ID
- `{{ doc.from_date }}` - Start date
- `{{ doc.to_date }}` - End date
- `{{ doc.company }}` - Company name

### Example Email Template

```html
<p>Dear {{ customer.customer_name }},</p>
<p>Please find attached your Statement of Account for the period from {{ doc.from_date }} to {{ doc.to_date }}.</p>
<p>If you have any questions, please don't hesitate to contact us.</p>
<p>Best regards,<br>{{ doc.company }}</p>
```

## LPO Integration

### How LPO Data is Retrieved

The system automatically retrieves LPO data by:
1. Querying Sales Orders for the customer in the specified date range
2. Extracting PO numbers (LPO) from Sales Orders
3. Matching transactions with their corresponding LPO numbers
4. Displaying LPO numbers in a dedicated column in the SOA

### LPO Column Display

The LPO column shows:
- LPO number for Sales Order transactions
- Empty for other transaction types
- Helps track purchase order references

## Technical Details

### Files Created

1. **`bulk_soa_generator.py`** - Main Python controller
2. **`bulk_soa_generator.json`** - DocType configuration
3. **`bulk_soa_generator_customer.json`** - Child table configuration
4. **`bulk_soa_generator.js`** - Frontend JavaScript
5. **`bulk_soa_generator.html`** - PDF template
6. **`test_bulk_soa.py`** - Test script

### Key Functions

- `generate_bulk_soa_pdf()` - Generate PDFs for all customers
- `send_bulk_soa_emails()` - Send emails with PDF attachments
- `get_customer_lpo_data()` - Retrieve LPO data for customers
- `fetch_customers_by_criteria()` - Bulk customer selection

### Dependencies

- ERPNext Accounts module
- Frappe PDF generation
- Frappe email system
- PyPDF2 for PDF merging

## Testing

Run the test script to verify functionality:

```python
# In Frappe console
exec(open('apps/numerouno/numerouno/numerouno/doctype/bulk_soa_generator/test_bulk_soa.py').read())
```

## Troubleshooting

### Common Issues

1. **No PDF Generated**
   - Check if customers have transaction data in the date range
   - Verify account filters are correct

2. **Emails Not Sent**
   - Ensure customers have valid email addresses
   - Check email configuration in System Settings
   - Verify sender email account is configured

3. **LPO Numbers Missing**
   - Ensure Sales Orders have PO numbers filled
   - Check if Sales Orders are submitted
   - Verify date range includes LPO transactions

### Error Logs

Check the following for error details:
- **Error Logs**: `bench --site your-site.com logs`
- **Email Queue**: Check Email Queue doctype for failed emails
- **System Console**: Use Frappe console for debugging

## Security Considerations

- Only users with appropriate permissions can access the tool
- Email addresses are validated before sending
- PDF generation is limited to authorized users
- All operations are logged for audit purposes

## Support

For issues or questions about the Bulk SOA Generator:
1. Check the error logs
2. Verify customer and transaction data
3. Test with a small customer group first
4. Contact system administrator for technical support 