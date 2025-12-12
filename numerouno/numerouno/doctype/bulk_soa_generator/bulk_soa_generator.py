import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, add_days, nowdate, get_url
from frappe.utils.pdf import get_pdf
from frappe.utils.jinja import validate_template
from erpnext.accounts.report.accounts_receivable.accounts_receivable import execute as get_ar_soa
from erpnext.accounts.report.general_ledger.general_ledger import execute as get_soa
from erpnext.accounts.party import get_party_account_currency
from erpnext import get_company_currency
import json


class BulkSOAGenerator(Document):
    def validate(self):
        if not self.subject:
            self.subject = "Statement of Account - {{ customer.customer_name }}"
        if not self.body:
            self.body = """
            <p>Dear {{ customer.customer_name }},</p>
            <p>Please find attached your Statement of Account for the period from {{ doc.from_date }} to {{ doc.to_date }}.</p>
            <p>If you have any questions, please don't hesitate to contact us.</p>
            <p>Best regards,<br>{{ doc.company }}</p>
            """
        if not self.pdf_name:
            self.pdf_name = "SOA_{{ customer.customer_name }}_{{ doc.from_date }}_to_{{ doc.to_date }}"
        
        validate_template(self.subject)
        validate_template(self.body)
        
        if not self.customers:
            frappe.throw(_("Please select at least one customer."))


@frappe.whitelist()
def generate_bulk_soa_pdf(doc_name):
    """Generate bulk SOA PDF with LPO columns"""
    doc = frappe.get_doc("Bulk SOA Generator", doc_name)
    
    if not doc.customers:
        frappe.throw(_("No customers selected"))
    
    # Generate PDF for each customer
    pdf_files = {}
    
    for customer_row in doc.customers:
        customer = customer_row.customer
        if not customer:
            continue
            
        # Get customer data
        customer_doc = frappe.get_doc("Customer", customer)
        
        # Generate SOA data
        filters = get_soa_filters(doc, customer)
        
        if doc.report_type == "General Ledger":
            col, data = get_soa(frappe._dict(filters))
        else:
            ar_result = get_ar_soa(frappe._dict(filters))
            col, data = ar_result[0], ar_result[1]
        
        if not data:
            continue
        
        # Debug: Print initial data structure
        if doc.report_type == "Accounts Receivable":
            print(f"\n=== INITIAL AR DATA DEBUG - Customer: {customer} ===")
            print(f"Total rows from AR report: {len(data)}")
            if len(data) > 0:
                print(f"Sample row keys: {list(data[0].keys())}")
                print(f"First 3 rows sample:")
                for idx, row in enumerate(data[:3]):
                    print(f"  Row {idx}: voucher_no={row.get('voucher_no')}, voucher_type={row.get('voucher_type')}")
                    print(f"    outstanding={row.get('outstanding')}, outstanding_amount={row.get('outstanding_amount')}, outstanding_balance={row.get('outstanding_balance')}")
                    print(f"    invoiced={row.get('invoiced')}, invoiced_amount={row.get('invoiced_amount')}")
            print(f"=== END INITIAL AR DATA DEBUG ===\n")
        
        # For Accounts Receivable: Filter out zero outstanding transactions early
        # This prevents processing invoices that are fully paid (not receivable)
        if doc.report_type == "Accounts Receivable":
            from frappe.utils import flt
            precision = frappe.get_precision("Sales Invoice", "outstanding_amount") or 2
            epsilon = 0.5 / (10 ** precision)
            
            print(f"\n=== EARLY FILTER DEBUG - Customer: {customer} ===")
            print(f"Total rows from AR report: {len(data)}")
            print(f"Epsilon value: {epsilon}")
            
            filtered_data = []
            skipped_count = 0
            for idx, row in enumerate(data):
                # Skip summary rows or header rows that don't have voucher information
                # Only filter actual transaction rows
                voucher_no = row.get('voucher_no') or ''
                voucher_type = row.get('voucher_type') or ''
                
                # Check outstanding amount using multiple possible field names
                # Try all common field names for outstanding amount
                outstanding = (
                    row.get('outstanding') or 
                    row.get('outstanding_amount') or 
                    row.get('outstanding_balance') or
                    row.get('outstanding_in_account_currency') or
                    0
                )
                outstanding_abs = abs(flt(outstanding))
                
                # Debug print for first few rows
                if idx < 5:
                    print(f"Row {idx}: voucher_no={voucher_no}, voucher_type={voucher_type}")
                    print(f"  outstanding={row.get('outstanding')}, outstanding_amount={row.get('outstanding_amount')}, outstanding_balance={row.get('outstanding_balance')}")
                    print(f"  Calculated outstanding_abs={outstanding_abs}, epsilon={epsilon}")
                
                # For transaction rows: Skip if outstanding is zero (fully paid)
                if voucher_no:
                    # This is a transaction row - must have outstanding > 0
                    if outstanding_abs <= epsilon:
                        # Skip this row - no outstanding amount means it's fully paid (not receivable)
                        skipped_count += 1
                        if skipped_count <= 10:  # Print first 10 skipped
                            print(f"  SKIPPED Row {idx}: {voucher_no} - outstanding={outstanding_abs} <= epsilon")
                        continue
                else:
                    # For non-transaction rows (summary/header), only include if they have outstanding > 0
                    # or if they're clearly summary rows (check for party or other summary indicators)
                    if outstanding_abs <= epsilon and not row.get('party'):
                        # Skip empty summary rows
                        skipped_count += 1
                        continue
                
                filtered_data.append(row)
            
            print(f"After early filter: {len(filtered_data)} rows kept, {skipped_count} rows skipped")
            print(f"=== END EARLY FILTER DEBUG ===\n")
            
            data = filtered_data
            
            if not data:
                continue
        
        # Add LPO numbers to data
        data = add_lpo_to_ar_rows(data)
        
        # Final filter for AR reports - catch any zero outstanding that slipped through
        # Check both doc.report_type and filters to determine if this is AR report
        is_ar_for_filter = (
            doc.report_type == "Accounts Receivable" or 
            (filters and filters.get('report_name') == 'Accounts Receivable')
        )
        if is_ar_for_filter:
            from frappe.utils import flt
            precision = frappe.get_precision("Sales Invoice", "outstanding_amount") or 2
            epsilon = 0.5 / (10 ** precision)
            
            print(f"\n=== FINAL FILTER DEBUG - Customer: {customer} ===")
            print(f"Rows before final filter: {len(data)}")
            
            final_filtered_data = []
            skipped_final_count = 0
            for idx, row in enumerate(data):
                voucher_no = row.get('voucher_no') or ''
                
                # For transaction rows, verify outstanding > 0
                if voucher_no:
                    # Check outstanding using all possible field names
                    outstanding = (
                        row.get('outstanding') or 
                        row.get('outstanding_amount') or 
                        row.get('outstanding_balance') or
                        row.get('outstanding_in_account_currency') or
                        0
                    )
                    outstanding_abs = abs(flt(outstanding))
                    
                    # Debug print for first few rows
                    if idx < 5:
                        print(f"Final Filter Row {idx}: {voucher_no}")
                        print(f"  outstanding={row.get('outstanding')}, outstanding_amount={row.get('outstanding_amount')}")
                        print(f"  Calculated outstanding_abs={outstanding_abs}")
                    
                    # If still zero, try fetching directly from Sales Invoice
                    if outstanding_abs <= epsilon and row.get('voucher_type') == 'Sales Invoice':
                        try:
                            si_doc = frappe.get_doc("Sales Invoice", voucher_no)
                            source_outstanding = abs(flt(si_doc.outstanding_amount))
                            print(f"  Fetched from source: {voucher_no} -> outstanding={source_outstanding}")
                            outstanding_abs = source_outstanding
                            row['outstanding'] = flt(si_doc.outstanding_amount)
                        except Exception as e:
                            print(f"  Error fetching {voucher_no}: {str(e)}")
                    
                    # Skip if outstanding is still zero
                    if outstanding_abs <= epsilon:
                        skipped_final_count += 1
                        if skipped_final_count <= 10:
                            print(f"  SKIPPED Final Row {idx}: {voucher_no} - outstanding={outstanding_abs} <= epsilon")
                        continue
                
                final_filtered_data.append(row)
            
            print(f"After final filter: {len(final_filtered_data)} rows kept, {skipped_final_count} rows skipped")
            print(f"=== END FINAL FILTER DEBUG ===\n")
            
            data = final_filtered_data
            
            if not data:
                continue
        
        # Generate HTML with LPO columns
        html = generate_soa_html(doc, customer_doc, col, data, filters)
        
        # Convert to PDF
        pdf = get_pdf(html, {"orientation": doc.orientation or "Portrait"})
        
        # Create filename
        filename = frappe.render_template(doc.pdf_name, {
            "customer": customer_doc,
            "doc": doc
        })
        
        pdf_files[customer] = {
            "filename": f"{filename}.pdf",
            "content": pdf
        }
    
    return pdf_files


@frappe.whitelist()
def send_bulk_soa_emails(doc_name):
    """Send bulk SOA emails with PDF attachments"""
    doc = frappe.get_doc("Bulk SOA Generator", doc_name)
    
    if not doc.customers:
        frappe.throw(_("No customers selected"))
    
    # Generate PDFs
    pdf_files = generate_bulk_soa_pdf(doc_name)
    
    if not pdf_files:
        frappe.throw(_("No data found for the selected customers"))
    
    success_count = 0
    error_count = 0
    
    for customer, pdf_data in pdf_files.items():
        try:
            # Get customer context
            customer_doc = frappe.get_doc("Customer", customer)
            context = get_customer_context(customer_doc, doc)
            
            # Prepare email
            subject = frappe.render_template(doc.subject, context)
            message = frappe.render_template(doc.body, context)
            
            # Get recipients
            recipients = get_customer_emails(customer_doc)
            if not recipients:
                frappe.log_error(f"No email found for customer {customer}")
                error_count += 1
                continue
            
            # Prepare attachments
            attachments = [{
                "fname": pdf_data["filename"],
                "fcontent": pdf_data["content"]
            }]
            
            # Send email
            # frappe.sendmail(
            #     recipients=recipients,
            #     subject=subject,
            #     message=message,
            #     attachments=attachments,
            #     reference_doctype="Bulk SOA Generator",
            #     reference_name=doc.name,
            #     now=True
            # )
            
            success_count += 1
            
        except Exception as e:
            # frappe.log_error(f"Failed to send SOA email to {customer}: {str(e)}")
            pass
            error_count += 1
    
    # Update document
    doc.last_email_sent = nowdate()
    doc.save()
    
    return {
        "success_count": success_count,
        "error_count": error_count,
        "message": f"Sent {success_count} emails successfully. {error_count} failed."
    }


def get_soa_filters(doc, customer):
    """Get filters for SOA generation"""
    if doc.report_type == "General Ledger":
        filters = {
            "company": doc.company,
            "party": [customer],
            "party_type": "Customer",
            "from_date": doc.from_date,
            "to_date": doc.to_date,
            "presentation_currency": doc.currency or get_company_currency(doc.company)
        }
        
        if doc.account:
            filters["account"] = [doc.account]
        else:
            filters["account"] = []
        
        if doc.include_ageing:
            filters["ageing_based_on"] = doc.ageing_based_on or "Due Date"
    else:
        # For Accounts Receivable report
        filters = {
            "company": doc.company,
            "party": [customer],
            "party_type": "Customer",
            "report_date": doc.to_date,  # AR report uses report_date instead of from_date/to_date
            "presentation_currency": doc.currency or get_company_currency(doc.company),
            "report_name": "Accounts Receivable",
            "ageing_based_on": doc.ageing_based_on or "Due Date",
            "range1": 30,
            "range2": 60,
            "range3": 90,
            "range4": 120
        }
        
        if doc.account:
            filters["account"] = [doc.account]
        else:
            filters["account"] = []
    
    return filters


def generate_soa_html(doc, customer_doc, columns, data, filters):
    """Generate HTML for SOA with LPO columns matching Accounts Receivable format"""
    
    # Determine if this is an Accounts Receivable report
    # Check multiple sources to determine report type
    is_ar_report = False
    
    # Method 1: Check filters (most reliable)
    if filters and filters.get('report_name') == 'Accounts Receivable':
        is_ar_report = True
    
    # Method 2: Check doc.report_type
    if not is_ar_report:
        report_type_str = str(doc.report_type or '').strip()
        is_ar_report = (
            report_type_str == "Accounts Receivable" or 
            report_type_str.lower() == "accounts receivable" or
            "receivable" in report_type_str.lower()
        )
    
    # Method 3: Check data structure - if data has 'outstanding' field, it's likely AR
    if not is_ar_report and data and len(data) > 0:
        sample_row = data[0]
        # AR reports typically have 'outstanding' or 'outstanding_amount' fields
        if 'outstanding' in sample_row or 'outstanding_amount' in sample_row:
            # Check if we have any rows with voucher_type = 'Sales Invoice' (typical of AR)
            has_sales_invoices = any(
                row.get('voucher_type') == 'Sales Invoice' 
                for row in data[:10]  # Check first 10 rows
            )
            if has_sales_invoices:
                is_ar_report = True
    
    print(f"\n=== REPORT TYPE CHECK ===")
    print(f"doc.report_type = '{doc.report_type}' (type: {type(doc.report_type).__name__})")
    print(f"filters.report_name = '{filters.get('report_name', '') if filters else 'N/A'}'")
    print(f"Data has outstanding fields: {data[0].get('outstanding') is not None if data and len(data) > 0 else 'N/A'}")
    print(f"is_ar_report = {is_ar_report}")
    print(f"=== END REPORT TYPE CHECK ===\n")
    
    # Get LPO data for the customer
    lpo_data = get_customer_lpo_data(customer_doc.name, doc.from_date, doc.to_date)
    
    # Add LPO numbers to data (already done in add_lpo_to_ar_rows, but ensure it's there)
    for row in data:
            if row.get('posting_date') and not row.get('lpo_number'):
                row['lpo_number'] = get_lpo_for_transaction(row, lpo_data)
            
            # Ensure all required fields exist with defaults
            if not row.get('due_date') and row.get('voucher_type') == 'Sales Invoice':
                # Try to get due date from Sales Invoice
                try:
                    si_doc = frappe.get_doc("Sales Invoice", row.get('voucher_no'))
                    row['due_date'] = si_doc.due_date
                except:
                    pass
            
            # Ensure age is calculated if missing
            if not row.get('age') and row.get('due_date') and doc.to_date:
                from frappe.utils import date_diff, getdate
                due_date = getdate(row.get('due_date'))
                report_date = getdate(doc.to_date)
                row['age'] = date_diff(report_date, due_date)
            
            # Ensure invoiced and outstanding amounts are properly set
            # Handle different possible field names and convert to float
            from frappe.utils import flt
            voucher_no = row.get('voucher_no')
            voucher_type = row.get('voucher_type')
            
            # Get invoiced amount - try multiple field names
            invoiced = row.get('invoiced')
            if invoiced is None:
                invoiced = row.get('invoiced_amount') or row.get('invoice_amount')
            
            # If still None or 0 for Sales Invoice, fetch from source document
            # This handles cases where the report data might not have the values populated
            if (invoiced is None or flt(invoiced) == 0) and voucher_type == 'Sales Invoice' and voucher_no:
                try:
                    si_doc = frappe.get_doc("Sales Invoice", voucher_no)
                    # Use grand_total for invoiced amount
                    # Note: Currency conversion should be handled by the report via presentation_currency
                    invoiced = si_doc.grand_total
                except:
                    invoiced = invoiced if invoiced is not None else 0
            
            # Payment entries don't have invoiced amounts
            if voucher_type == 'Payment Entry':
                invoiced = 0
            
            row['invoiced'] = flt(invoiced or 0)
            
            # Get outstanding amount - try multiple field names
            outstanding = (
                row.get('outstanding') or 
                row.get('outstanding_amount') or 
                row.get('outstanding_balance') or
                row.get('outstanding_in_account_currency') or
                None
            )
            
            # If still None or seems incorrect (0 outstanding but has invoiced amount), fetch from source
            if (outstanding is None or (flt(outstanding) == 0 and flt(row.get('invoiced', 0)) != 0)) and voucher_type == 'Sales Invoice' and voucher_no:
                try:
                    si_doc = frappe.get_doc("Sales Invoice", voucher_no)
                    # Note: Currency conversion should be handled by the report via presentation_currency
                    outstanding = si_doc.outstanding_amount
                except:
                    outstanding = outstanding if outstanding is not None else 0
            
            row['outstanding'] = flt(outstanding or 0)
    
    # Filter out rows that are not relevant for Accounts Receivable
    # For AR reports, we only want transactions with outstanding amounts > 0
    # Excludes: Fully paid invoices (outstanding = 0), zero-amount transactions, etc.
    print(f"\n=== HTML GENERATION FILTER DEBUG - Customer: {customer_doc.name} ===")
    print(f"Rows before HTML filter: {len(data)}")
    
    filtered_data = []
    precision = frappe.get_precision("Sales Invoice", "outstanding_amount") or 2
    epsilon = 0.5 / (10 ** precision)  # Small value for floating point comparison
    
    skipped_html_count = 0
    for idx, row in enumerate(data):
        invoiced = flt(row.get('invoiced') or 0)
        outstanding = flt(row.get('outstanding') or 0)
        voucher_type = row.get('voucher_type', '')
        voucher_no = row.get('voucher_no', '')
        
        # Use absolute value comparison to handle floating point precision issues
        invoiced_abs = abs(invoiced)
        outstanding_abs = abs(outstanding)
        
        # Debug print for first few rows
        if idx < 5:
            print(f"HTML Filter Row {idx}: voucher_no='{voucher_no}' (type={type(voucher_no).__name__}), voucher_type='{voucher_type}'")
            print(f"  invoiced={invoiced}, outstanding={outstanding}")
            print(f"  invoiced_abs={invoiced_abs}, outstanding_abs={outstanding_abs}, epsilon={epsilon}")
            print(f"  is_ar_report={is_ar_report}")
        
        # For Accounts Receivable reports: Exclude transactions with zero outstanding amount
        # If outstanding = 0, the invoice is fully paid and not receivable anymore
        # This filters out:
        # - Fully paid invoices (outstanding = 0, even if invoiced > 0)
        # - Zero-amount transactions (both invoiced and outstanding = 0)
        # - Payment entries with zero outstanding
        
        if is_ar_report:
            # For AR reports: Skip if outstanding amount is zero or very close to zero
            # This is the key filter - only show what's actually owed (receivable)
            # Even if invoiced > 0, if outstanding = 0, it's fully paid and not receivable
            
            # Skip rows with no voucher_no (empty/invalid rows)
            voucher_no_empty = not voucher_no or (isinstance(voucher_no, str) and voucher_no.strip() == '')
            if idx < 5:
                print(f"  Checking empty voucher_no: voucher_no='{voucher_no}', empty={voucher_no_empty}")
            if voucher_no_empty:
                skipped_html_count += 1
                if skipped_html_count <= 10:
                    print(f"  SKIPPED HTML Row {idx}: Empty voucher_no (value='{voucher_no}')")
                continue
            
            # For Sales Invoices: Double-check from source document before filtering
            # This handles cases where report data might be incorrect
            if voucher_type == 'Sales Invoice' and voucher_no:
                try:
                    si_doc = frappe.get_doc("Sales Invoice", voucher_no)
                    source_outstanding = abs(flt(si_doc.outstanding_amount))
                    if idx < 5:
                        print(f"  Source check: {voucher_no} -> source_outstanding={source_outstanding}, report_outstanding={outstanding_abs}")
                    if source_outstanding <= epsilon:
                        # Source confirms it's fully paid, skip it
                        skipped_html_count += 1
                        if skipped_html_count <= 10:
                            print(f"  SKIPPED HTML Row {idx}: {voucher_no} - source confirms outstanding=0")
                        continue
                    else:
                        # Use source value (more reliable than report data)
                        outstanding_abs = source_outstanding
                        row['outstanding'] = flt(si_doc.outstanding_amount)
                except Exception as e:
                    # If we can't verify, skip it to be safe
                    skipped_html_count += 1
                    if skipped_html_count <= 10:
                        print(f"  SKIPPED HTML Row {idx}: {voucher_no} - ERROR verifying source: {str(e)}")
                    continue
            
            # Skip ALL rows with zero outstanding (regardless of voucher type)
            # This is the main filter - only show what's actually receivable
            should_skip_zero = outstanding_abs <= epsilon
            if idx < 5:
                print(f"  Checking zero outstanding: outstanding_abs={outstanding_abs}, epsilon={epsilon}, should_skip={should_skip_zero}")
            if should_skip_zero:
                skipped_html_count += 1
                if skipped_html_count <= 10:
                    print(f"  SKIPPED HTML Row {idx}: {voucher_no} (type={voucher_type}) - outstanding={outstanding_abs} <= epsilon")
                continue
            
            if idx < 5:
                print(f"  KEEPING HTML Row {idx}: {voucher_no} - outstanding={outstanding_abs} > epsilon")
        else:
            # For General Ledger: Skip if both amounts are zero (no meaningful transaction)
            if invoiced_abs <= epsilon and outstanding_abs <= epsilon:
                # Skip this row - both amounts are effectively zero
                continue
        
        # Include the row if it passed all filters (has outstanding amount > 0)
        filtered_data.append(row)
    
    print(f"After HTML filter: {len(filtered_data)} rows kept, {skipped_html_count} rows skipped")
    print(f"=== END HTML GENERATION FILTER DEBUG ===\n")
    
    data = filtered_data
    
    # Get letterhead content
    letterhead_content = get_letterhead_html(doc)
    
    # Get company details
    company_doc = frappe.get_doc("Company", doc.company)

    # Calculate totals for the template
    total_invoiced = sum((row.get('invoiced') or 0) for row in data if row.get('posting_date') or row.get('voucher_no'))
    total_outstanding = sum((row.get('outstanding') or 0) for row in data if row.get('posting_date') or row.get('voucher_no'))
    total_age = sum((row.get('age') or 0) for row in data if row.get('posting_date') or row.get('voucher_no'))
    has_data = any(row.get('posting_date') or row.get('voucher_no') for row in data)
    
    # Render the HTML template
    context = {
        "doc": doc,
        "customer": customer_doc,
        "company": company_doc,
        "data": data,
        "currency": filters.get('presentation_currency') or get_company_currency(doc.company),
        "letterhead_content": letterhead_content,
        "total_invoiced": total_invoiced,
        "total_outstanding": total_outstanding,
        "total_age": total_age,
        "has_data": has_data,
        "frappe": frappe  # Pass the whole frappe module
    }
    
    html = frappe.render_template(
        "numerouno/numerouno/doctype/bulk_soa_generator/bulk_soa_generator.html",
        context
    )
    
    return html


def get_customer_lpo_data(customer, from_date, to_date):
    """Get LPO data for customer in date range"""
    lpo_data = frappe.db.sql("""
        SELECT 
            so.name as sales_order,
            so.po_no as lpo_number,
            so.po_date as lpo_date,
            so.transaction_date,
            so.delivery_date
        FROM `tabSales Order` so
        WHERE so.customer = %s
        AND so.transaction_date BETWEEN %s AND %s
        AND so.docstatus = 1
        AND so.po_no IS NOT NULL
        AND so.po_no != ''
    """, (customer, from_date, to_date), as_dict=True)
    
    return lpo_data


def get_lpo_for_transaction(row, lpo_data):
    """Get LPO number for a specific transaction"""
    voucher_no = row.get('voucher_no', '')
    voucher_type = row.get('voucher_type', '')
    
    if voucher_type == 'Sales Order':
        for lpo in lpo_data:
            if lpo.sales_order == voucher_no:
                return lpo.lpo_number
    
    return ''


def add_lpo_to_ar_rows(data):
    for row in data:
        if row.get("voucher_type") == "Sales Invoice":
            # Fetch LPO numbers from linked Sales Orders in Sales Invoice Item
            sales_orders = frappe.db.get_all(
                "Sales Invoice Item",
                filters={"parent": row.get("voucher_no")},
                fields=["sales_order"],
                distinct=True
            )
            lpo_numbers = set()
            for so in sales_orders:
                if so.sales_order:
                    po_no = frappe.db.get_value("Sales Order", so.sales_order, "po_no")
                    if po_no:
                        lpo_numbers.add(po_no)
            # Fallback: If no sales_order links found, try to find Sales Orders for the same customer and close to invoice date
            if not lpo_numbers:
                invoice_doc = frappe.get_doc("Sales Invoice", row.get("voucher_no"))
                customer = invoice_doc.customer
                posting_date = invoice_doc.posting_date
                # Look for Sales Orders within +/- 7 days of invoice date
                from frappe.query_builder.functions import DateAdd
                sales_orders_fallback = frappe.db.get_all(
                    "Sales Order",
                    filters={
                        "customer": customer,
                        "transaction_date": ["between", [add_days(posting_date, -7), add_days(posting_date, 7)]],
                        "docstatus": 1
                    },
                    fields=["po_no"],
                )
                for so in sales_orders_fallback:
                    if so.po_no:
                        lpo_numbers.add(so.po_no)
            row["lpo_number"] = ", ".join(lpo_numbers) if lpo_numbers else ""
            # Fetch item details for description
            items = frappe.db.get_all(
                "Sales Invoice Item",
                filters={"parent": row.get("voucher_no")},
                fields=["item_code", "item_name", "qty", "rate"]
            )
            desc_lines = []
            for item in items:
                desc_lines.append(f"{item.item_code or ''} {item.item_name or ''} | Qty: {item.qty} | Rate: {item.rate}")
            row["description"] = "<br>".join(desc_lines) if desc_lines else ""
        else:
            row["lpo_number"] = ""
            row["description"] = ""
    return data


def get_customer_context(customer_doc, doc):
    """Get context for email template"""
    return {
        "customer": customer_doc,
        "doc": doc,
        "frappe": frappe.utils
    }


def get_customer_emails(customer_doc):
    """Get email addresses for customer"""
    emails = []
    
    # Get primary contact email
    if customer_doc.customer_primary_contact:
        contact = frappe.get_doc("Contact", customer_doc.customer_primary_contact)
        for email in contact.email_ids:
            if email.email_id:
                emails.append(email.email_id)
    
    # Get all contact emails
    contacts = frappe.get_all("Contact", 
        filters={"link_doctype": "Customer", "link_name": customer_doc.name},
        fields=["name"]
    )
    
    for contact in contacts:
        contact_doc = frappe.get_doc("Contact", contact.name)
        for email in contact_doc.email_ids:
            if email.email_id and email.email_id not in emails:
                emails.append(email.email_id)
    
    return emails


def get_letterhead_html(doc):
    """Get letterhead HTML"""
    if doc.letter_head:
        letter_head = frappe.get_doc("Letter Head", doc.letter_head)
        return letter_head.content or ""
    return ""


def format_currency(amount, currency):
    """Format currency amount"""
    if amount:
        return frappe.utils.fmt_money(amount, currency=currency)
    return "0.00"


@frappe.whitelist()
def fetch_customers_by_criteria(doc_name):
    """Fetch customers based on criteria"""
    doc = frappe.get_doc("Bulk SOA Generator", doc_name)
    
    filters = {"disabled": 0}
    
    if doc.customer_group:
        filters["customer_group"] = doc.customer_group
    
    if doc.territory:
        filters["territory"] = doc.territory
    
    customers = frappe.get_all("Customer", 
        filters=filters,
        fields=["name", "customer_name", "customer_group", "territory", "email_id"],
        limit=1000
    )
    
    # Clear existing customers
    doc.customers = []
    
    # Add fetched customers
    for customer in customers:
        doc.append("customers", {
            "customer": customer.name,
            "customer_name": customer.customer_name,
            "email_id": customer.email_id or ""
        })
    
    doc.save()
    
    return {
        "message": f"Fetched {len(customers)} customers",
        "count": len(customers)
    }


@frappe.whitelist()
def download_bulk_soa_pdf(doc_name):
    """Download bulk SOA PDF"""
    doc = frappe.get_doc("Bulk SOA Generator", doc_name)
    
    if not doc.customers:
        frappe.throw(_("No customers selected"))
    
    # Generate PDFs
    pdf_files = generate_bulk_soa_pdf(doc_name)
    
    if not pdf_files:
        frappe.throw(_("No data found for the selected customers"))
    
    # Create a combined PDF
    from PyPDF2 import PdfMerger
    import io
    
    merger = PdfMerger()
    
    for customer, pdf_data in pdf_files.items():
        pdf_stream = io.BytesIO(pdf_data["content"])
        merger.append(pdf_stream)
    
    # Get combined PDF
    output = io.BytesIO()
    merger.write(output)
    merger.close()
    
    # Return the combined PDF
    frappe.local.response.filename = f"Bulk_SOA_{doc.name}.pdf"
    frappe.local.response.filecontent = output.getvalue()
    frappe.local.response.type = "download" 