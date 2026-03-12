import frappe
from frappe.model.document import Document


class BulkSOAGeneratorCustomer(Document):
    """Child table for Bulk SOA Generator customers"""
    
    def validate(self):
        """Validate customer data"""
        if self.customer:
            # Fetch customer name if not set
            if not self.customer_name:
                customer_name = frappe.db.get_value("Customer", self.customer, "customer_name")
                if customer_name:
                    self.customer_name = customer_name 