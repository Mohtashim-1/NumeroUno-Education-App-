for row in doc.students:
    if not row.custom_sales_order:  # Only process students without sales orders
        customer = row.customer_name or doc.custom_customer
        payment_mode = row.custom_mode_of_payment or "Cash Payment"  # Default to Cash Payment 