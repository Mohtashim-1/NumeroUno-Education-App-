# Copyright (c) 2026, NumeroUNO and contributors
# License: MIT

"""Restore Stripe callback + create Sales Invoice after paying a Sales Order."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt
from erpnext.accounts.doctype.payment_request.payment_request import PaymentRequest as ERPNextPaymentRequest


class PaymentRequest(ERPNextPaymentRequest):
	def on_payment_authorized(self, status=None):
		"""Called by payment gateways after a successful charge."""
		if status not in ("Authorized", "Completed"):
			return None

		# Gateway webhooks / checkout run as Guest — elevate to create Payment Entry / Invoice
		previous_user = frappe.session.user
		try:
			frappe.set_user("Administrator")
			if self.status != "Paid":
				self.set_as_paid()
		finally:
			frappe.set_user(previous_user)

		return "/customer-portal"

	def make_invoice(self):
		"""
		After Stripe payment against a Sales Order:
		create & submit Sales Invoice and allocate the advance automatically.

		(ERPNext core only auto-invoices Shopping Cart orders.)
		"""
		if self.reference_doctype == "Sales Order":
			so = frappe.get_doc("Sales Order", self.reference_name)
			if flt(so.per_billed) >= 99.99:
				return None

			from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

			si = make_sales_invoice(self.reference_name, ignore_permissions=True)
			si.allocate_advances_automatically = True
			si.flags.ignore_permissions = True
			si.insert(ignore_permissions=True)
			si.submit()
			frappe.msgprint(_("Sales Invoice {0} created after online payment").format(si.name))
			return si

		# Keep shopping-cart behaviour from core
		return super().make_invoice()
