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
        
        # Add LPO numbers to data
        data = add_lpo_to_ar_rows(data)
        
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
            frappe.sendmail(
                recipients=recipients,
                subject=subject,
                message=message,
                attachments=attachments,
                reference_doctype="Bulk SOA Generator",
                reference_name=doc.name,
                now=True
            )
            
            success_count += 1
            
        except Exception as e:
            frappe.log_error(f"Failed to send SOA email to {customer}: {str(e)}")
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
    """Generate HTML for SOA with LPO columns"""
    
    # Get LPO data for the customer
    lpo_data = get_customer_lpo_data(customer_doc.name, doc.from_date, doc.to_date)
    
    # Add LPO numbers to data
    for row in data:
        if row.get('posting_date'):
            row['lpo_number'] = get_lpo_for_transaction(row, lpo_data)
    
    # Get letterhead content
    letterhead_content = get_letterhead_html(doc)

    # Render the HTML template
    context = {
        "doc": doc,
        "customer": customer_doc,
        "data": data,
        "currency": filters.get('presentation_currency'),
        "letterhead_content": letterhead_content,
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