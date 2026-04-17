<p>Dear Sales Manager,</p>

<p>A new Quotation has been submitted for your approval.</p>

<p>Details:
- Quotation: {{ doc.name }}
- Customer: {{ doc.customer }}
- Transaction Date: {{ doc.transaction_date }}
- Grand Total: {{ doc.grand_total }}</p>

<p>Please review and take the necessary action.</p>

<p>You can view the document here:
{{ frappe.utils.get_url() }}/app/quotation/{{ doc.name }}</p>

<p>Regards,<br/>
ERP System</p>
