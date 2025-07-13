#!/usr/bin/env python3
"""
Test script for Bulk SOA Generator functionality
"""

import frappe
from frappe.utils import nowdate, add_months


def test_bulk_soa_generator():
    """Test the bulk SOA generator functionality"""
    
    print("🧪 Testing Bulk SOA Generator...")
    
    # Create a test document
    doc = frappe.new_doc("Bulk SOA Generator")
    doc.company = frappe.defaults.get_global_default("company")
    doc.report_type = "General Ledger"
    doc.from_date = add_months(nowdate(), -1)
    doc.to_date = nowdate()
    doc.subject = "Statement of Account - {{ customer.customer_name }}"
    doc.body = """
    <p>Dear {{ customer.customer_name }},</p>
    <p>Please find attached your Statement of Account for the period from {{ doc.from_date }} to {{ doc.to_date }}.</p>
    <p>Best regards,<br>{{ doc.company }}</p>
    """
    doc.pdf_name = "SOA_{{ customer.customer_name }}_{{ doc.from_date }}_to_{{ doc.to_date }}"
    
    # Add some test customers
    customers = frappe.get_all("Customer", 
        filters={"disabled": 0}, 
        fields=["name", "customer_name"], 
        limit=3
    )
    
    for customer in customers:
        doc.append("customers", {
            "customer": customer.name,
            "customer_name": customer.customer_name
        })
    
    doc.insert()
    print(f"✅ Created Bulk SOA Generator: {doc.name}")
    
    # Test PDF generation
    try:
        from numerouno.numerouno.doctype.bulk_soa_generator.bulk_soa_generator import generate_bulk_soa_pdf
        pdf_files = generate_bulk_soa_pdf(doc.name)
        print(f"✅ PDF generation successful: {len(pdf_files)} files generated")
    except Exception as e:
        print(f"❌ PDF generation failed: {str(e)}")
    
    # Test email sending (commented out to avoid sending actual emails)
    # try:
    #     from numerouno.numerouno.doctype.bulk_soa_generator.bulk_soa_generator import send_bulk_soa_emails
    #     result = send_bulk_soa_emails(doc.name)
    #     print(f"✅ Email sending successful: {result}")
    # except Exception as e:
    #     print(f"❌ Email sending failed: {str(e)}")
    
    print("✅ Test completed successfully!")
    return doc.name


def test_lpo_functionality():
    """Test LPO data retrieval"""
    
    print("🧪 Testing LPO functionality...")
    
    # Get a customer with LPO data
    customers_with_lpo = frappe.db.sql("""
        SELECT DISTINCT so.customer, c.customer_name
        FROM `tabSales Order` so
        JOIN `tabCustomer` c ON c.name = so.customer
        WHERE so.po_no IS NOT NULL 
        AND so.po_no != ''
        AND so.docstatus = 1
        LIMIT 1
    """, as_dict=True)
    
    if customers_with_lpo:
        customer = customers_with_lpo[0]
        print(f"✅ Found customer with LPO: {customer.customer_name}")
        
        # Test LPO data retrieval
        from numerouno.numerouno.doctype.bulk_soa_generator.bulk_soa_generator import get_customer_lpo_data
        
        lpo_data = get_customer_lpo_data(
            customer.customer, 
            add_months(nowdate(), -6), 
            nowdate()
        )
        
        print(f"✅ Retrieved {len(lpo_data)} LPO records for {customer.customer_name}")
        
        for lpo in lpo_data:
            print(f"   - LPO: {lpo.lpo_number}, Date: {lpo.lpo_date}")
    else:
        print("⚠️ No customers with LPO data found")
    
    print("✅ LPO test completed!")


if __name__ == "__main__":
    # Run tests
    test_lpo_functionality()
    test_bulk_soa_generator() 