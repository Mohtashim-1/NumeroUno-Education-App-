# Copyright (c) 2026, NumeroUNO and contributors
# License: MIT

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, get_link_to_form, now_datetime, nowdate


class PortalPaymentRequest(Document):
	def validate(self):
		if flt(self.amount) <= 0:
			frappe.throw(_("Amount must be greater than zero."))
		if not self.company:
			self.company = frappe.db.get_single_value("Global Defaults", "default_company")
		if not self.currency and self.company:
			self.currency = frappe.get_cached_value("Company", self.company, "default_currency")
		if self.customer and not self.customer_name:
			self.customer_name = frappe.db.get_value("Customer", self.customer, "customer_name")

	def before_submit(self):
		self._set_gateway_defaults()
		self.status = "Open"

	def on_cancel(self):
		# Block only while the linked Payment Entry is still submitted.
		# When PE is cancelled first (or already cancelled), allow this cancel.
		if self.status == "Paid" and self.payment_entry:
			pe_docstatus = frappe.db.get_value("Payment Entry", self.payment_entry, "docstatus")
			if cint(pe_docstatus) == 1:
				frappe.throw(
					_("Cannot cancel a paid Portal Payment Request. Cancel/reallocate the Payment Entry first.")
				)
		self.db_set("status", "Cancelled")

	def _set_gateway_defaults(self):
		"""Pick default Stripe gateway + bank account for this currency."""
		row = frappe.db.get_value(
			"Payment Gateway Account",
			{"payment_gateway": ("like", "%Stripe%"), "currency": self.currency},
			["payment_gateway", "payment_account"],
			as_dict=True,
		)
		if not row:
			row = frappe.db.get_value(
				"Payment Gateway Account",
				{"payment_gateway": ("like", "%Stripe%")},
				["payment_gateway", "payment_account"],
				as_dict=True,
			)
		if not row:
			row = frappe.db.get_value(
				"Payment Gateway Account",
				{"is_default": 1},
				["payment_gateway", "payment_account"],
				as_dict=True,
			)
		if not row:
			frappe.throw(_("No Payment Gateway Account found. Configure Stripe first."))

		self.payment_gateway = row.payment_gateway
		self.payment_account = row.payment_account

	def on_payment_authorized(self, status=None):
		"""Called by Stripe checkout after a successful charge."""
		if status not in ("Authorized", "Completed"):
			return None
		if self.status == "Paid" and self.payment_entry:
			return "/customer-portal"

		pe = self.create_advance_payment_entry()
		self.db_set(
			{
				"status": "Paid",
				"payment_entry": pe.name,
				"paid_on": now_datetime(),
			},
			update_modified=True,
		)
		return "/customer-portal"

	def create_advance_payment_entry(self):
		"""Create unallocated Customer Receive PE (advance) against Stripe bank account."""
		from erpnext.accounts.party import get_party_account

		if self.payment_entry and frappe.db.exists("Payment Entry", self.payment_entry):
			return frappe.get_doc("Payment Entry", self.payment_entry)

		party_account = get_party_account("Customer", self.customer, self.company)
		if not party_account:
			frappe.throw(_("Could not find Receivable account for customer {0}").format(self.customer))
		if not self.payment_account:
			self._set_gateway_defaults()

		pe = frappe.new_doc("Payment Entry")
		pe.payment_type = "Receive"
		pe.company = self.company
		pe.posting_date = nowdate()
		pe.party_type = "Customer"
		pe.party = self.customer
		pe.party_name = self.customer_name
		pe.paid_from = party_account
		pe.paid_to = self.payment_account
		pe.mode_of_payment = get_or_create_stripe_mode_of_payment(self.company, self.payment_account)
		pe.paid_amount = flt(self.amount)
		pe.received_amount = flt(self.amount)
		pe.target_exchange_rate = 1
		pe.source_exchange_rate = 1
		pe.reference_no = self.name
		pe.reference_date = nowdate()
		pe.remarks = _("Stripe portal payment for {0}: {1}").format(self.name, self.description or "")
		pe.setup_party_account_field()
		pe.set_missing_values()
		pe.set_exchange_rate()
		pe.set_amounts()
		pe.insert(ignore_permissions=True)
		pe.submit()
		return pe

	@frappe.whitelist()
	def allocate_payment_to_invoice(self, sales_invoice: str | None = None):
		"""Link Payment Entry advance against a Sales Invoice (marks invoice paid if full)."""
		sales_invoice = sales_invoice or self.sales_invoice
		if not sales_invoice:
			frappe.throw(_("Select a Sales Invoice first."))
		if self.status not in ("Paid", "Allocated"):
			frappe.throw(_("Portal Payment Request must be Paid before allocating."))
		if not self.payment_entry:
			frappe.throw(_("No Payment Entry found on this request."))

		si = frappe.get_doc("Sales Invoice", sales_invoice)
		if si.customer != self.customer:
			frappe.throw(_("Sales Invoice customer must match this request."))
		if cint(si.docstatus) != 1:
			frappe.throw(_("Sales Invoice must be submitted."))

		pe = frappe.get_doc("Payment Entry", self.payment_entry)
		if pe.docstatus != 1:
			frappe.throw(_("Payment Entry must be submitted."))

		# Already fully allocated?
		unallocated = flt(pe.unallocated_amount)
		if unallocated <= 0 and pe.references:
			self.db_set({"sales_invoice": si.name, "status": "Allocated"})
			return {"ok": 1, "message": _("Already allocated."), "payment_entry": pe.name}

		outstanding = flt(si.outstanding_amount)
		if outstanding <= 0:
			self.db_set({"sales_invoice": si.name, "status": "Allocated"})
			return {"ok": 1, "message": _("Invoice is already paid."), "payment_entry": pe.name}

		allocate_amount = min(unallocated or flt(self.amount), outstanding)

		from erpnext.accounts.utils import reconcile_against_document

		lst = [
			frappe._dict(
				{
					"voucher_type": "Payment Entry",
					"voucher_no": pe.name,
					"against_voucher_type": "Sales Invoice",
					"against_voucher": si.name,
					"account": pe.paid_from,
					"party_type": "Customer",
					"party": self.customer,
					"dr_or_cr": "credit_in_account_currency",
					"unadjusted_amount": unallocated or flt(pe.paid_amount),
					"unreconciled_amount": unallocated or flt(pe.paid_amount),
					"allocated_amount": allocate_amount,
					"is_advance": "Yes",
				}
			)
		]
		reconcile_against_document(lst)

		self.db_set({"sales_invoice": si.name, "status": "Allocated"}, update_modified=True)
		if frappe.db.has_column("Sales Invoice", "custom_portal_payment_request"):
			frappe.db.set_value(
				"Sales Invoice",
				si.name,
				"custom_portal_payment_request",
				self.name,
				update_modified=False,
			)

		frappe.msgprint(
			_("Allocated {0} from {1} to {2}").format(
				allocate_amount,
				get_link_to_form("Payment Entry", pe.name),
				get_link_to_form("Sales Invoice", si.name),
			)
		)
		return {"ok": 1, "allocated": allocate_amount, "payment_entry": pe.name, "sales_invoice": si.name}


def sync_portal_payment_request_on_payment_entry_cancel(doc, method=None):
	"""Allow PE cancel despite Portal Payment Request links; cancel linked PPRs after PE."""
	if not frappe.db.exists("DocType", "Portal Payment Request"):
		return

	ignored = list(doc.get("ignore_linked_doctypes") or [])
	if "Portal Payment Request" not in ignored:
		ignored.append("Portal Payment Request")
	doc.ignore_linked_doctypes = tuple(ignored)

	ppr_names = frappe.get_all(
		"Portal Payment Request",
		filters={"payment_entry": doc.name, "docstatus": 1},
		pluck="name",
	)
	for name in ppr_names:
		ppr = frappe.get_doc("Portal Payment Request", name)
		ppr.flags.ignore_permissions = True
		ppr.cancel()


def get_or_create_stripe_mode_of_payment(company: str | None, payment_account: str | None) -> str | None:
	"""Resolve Mode of Payment for Stripe receives; create Stripe MoP if missing."""
	if not company or not payment_account:
		return None

	existing = frappe.db.get_value(
		"Mode of Payment Account",
		{"company": company, "default_account": payment_account},
		"parent",
	)
	if existing:
		return existing

	mop_name = "Stripe"
	if not frappe.db.exists("Mode of Payment", mop_name):
		mop = frappe.get_doc(
			{
				"doctype": "Mode of Payment",
				"mode_of_payment": mop_name,
				"enabled": 1,
				"type": "Bank",
				"accounts": [
					{
						"company": company,
						"default_account": payment_account,
					}
				],
			}
		)
		mop.insert(ignore_permissions=True)
		return mop.name

	# Stripe MoP exists but missing this company/account mapping
	mop = frappe.get_doc("Mode of Payment", mop_name)
	if not any(
		row.company == company and row.default_account == payment_account for row in mop.accounts
	):
		mop.append(
			"accounts",
			{
				"company": company,
				"default_account": payment_account,
			},
		)
		mop.save(ignore_permissions=True)
	return mop.name


def set_stripe_mode_of_payment_on_payment_entry(doc, method=None):
	"""Fill Mode of Payment on Stripe receives created via Payment Request / portal."""
	if doc.mode_of_payment or doc.payment_type != "Receive" or not doc.paid_to:
		return
	if not doc.company:
		return

	is_stripe_account = frappe.db.exists(
		"Payment Gateway Account",
		{"payment_account": doc.paid_to, "payment_gateway": ("like", "%Stripe%")},
	)
	looks_like_stripe = (doc.paid_to or "").startswith("Stripe") or "Stripe" in (doc.remarks or "")
	if not is_stripe_account and not looks_like_stripe:
		return

	doc.mode_of_payment = get_or_create_stripe_mode_of_payment(doc.company, doc.paid_to)


@frappe.whitelist()
def allocate_to_invoice(name: str, sales_invoice: str | None = None):
	doc = frappe.get_doc("Portal Payment Request", name)
	doc.check_permission("write")
	return doc.allocate_payment_to_invoice(sales_invoice)
