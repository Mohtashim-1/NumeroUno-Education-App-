# Copyright (c) 2026, NumeroUNO and contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, validate_email_address


class SupplierRegistration(Document):
	def validate(self):
		self.supplier_name = (self.supplier_name or "").strip()
		self.contact_person = (self.contact_person or "").strip()
		self.email = (self.email or "").strip().lower()
		self.mobile_no = (self.mobile_no or "").strip()

		if self.email:
			validate_email_address(self.email, throw=True)

		# Soft duplicate guard on pending/approved name
		if self.is_new() and self.supplier_name:
			dup = frappe.db.exists(
				"Supplier Registration",
				{
					"supplier_name": self.supplier_name,
					"status": "Pending Approval",
					"name": ["!=", self.name or ""],
				},
			)
			if dup:
				frappe.throw(_("A pending registration already exists for {0} ({1}).").format(self.supplier_name, dup))

		if self.status == "Approved" and not self.supplier:
			frappe.throw(_("Approve the registration to create a Supplier before marking Approved."))

	@frappe.whitelist()
	def approve_registration(self):
		"""Create ERPNext Supplier (+ contact/address) and mark Approved."""
		self.reload()
		if self.status == "Approved" and self.supplier:
			frappe.throw(_("This registration is already approved ({0}).").format(self.supplier))
		if self.status == "Rejected":
			frappe.throw(_("Rejected registrations cannot be approved. Ask the supplier to re-register."))

		_ensure_can_approve()

		supplier_name = self._create_supplier()
		self.db_set(
			{
				"status": "Approved",
				"supplier": supplier_name,
				"approved_by": frappe.session.user,
				"approved_on": now_datetime(),
				"rejection_reason": "",
			},
			update_modified=True,
		)
		self.add_comment(
			"Info",
			_("Approved — Supplier {0} created.").format(frappe.utils.get_link_to_form("Supplier", supplier_name)),
		)
		frappe.msgprint(_("Supplier {0} created and registration approved.").format(supplier_name), indicator="green")
		return {"supplier": supplier_name, "status": "Approved"}

	@frappe.whitelist()
	def reject_registration(self, reason=None):
		self.reload()
		if self.status == "Approved":
			frappe.throw(_("Approved registrations cannot be rejected."))
		_ensure_can_approve()

		reason = (reason or "").strip()
		if not reason:
			frappe.throw(_("Please enter a rejection reason."))

		self.db_set(
			{
				"status": "Rejected",
				"approved_by": frappe.session.user,
				"approved_on": now_datetime(),
				"rejection_reason": reason,
			},
			update_modified=True,
		)
		self.add_comment("Info", _("Rejected: {0}").format(reason))
		frappe.msgprint(_("Registration rejected."), indicator="orange")
		return {"status": "Rejected"}

	def _create_supplier(self):
		existing = frappe.db.get_value("Supplier", {"supplier_name": self.supplier_name}, "name")
		if existing:
			frappe.throw(
				_("A Supplier named {0} already exists ({1}). Link or rename before approving.").format(
					self.supplier_name, existing
				)
			)

		meta = frappe.get_meta("Supplier")
		if self.email and meta.has_field("email_id") and frappe.db.exists("Supplier", {"email_id": self.email}):
			dup = frappe.db.get_value("Supplier", {"email_id": self.email}, "name")
			frappe.throw(_("A Supplier with email {0} already exists ({1}).").format(self.email, dup))

		supplier_group = self.supplier_group or _default_supplier_group()

		doc = frappe.new_doc("Supplier")
		doc.supplier_name = self.supplier_name
		doc.supplier_type = self.supplier_type or "Company"
		doc.supplier_group = supplier_group
		doc.country = self.country or "United Arab Emirates"
		if self.tax_id and meta.has_field("tax_id"):
			doc.tax_id = self.tax_id
		if meta.has_field("email_id") and self.email:
			doc.email_id = self.email
		if meta.has_field("mobile_no") and self.mobile_no:
			doc.mobile_no = self.mobile_no
		if meta.has_field("default_currency"):
			doc.default_currency = "AED"
		if self.payment_terms and frappe.db.exists("Payment Terms Template", self.payment_terms):
			doc.payment_terms = self.payment_terms

		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)

		self._create_address(doc.name)
		self._create_contact(doc.name)

		bank_note = []
		if self.bank_name:
			bank_note.append(f"Bank: {self.bank_name}")
		if self.iban:
			bank_note.append(f"IBAN: {self.iban}")
		if self.account_name:
			bank_note.append(f"Account: {self.account_name}")
		if self.trade_license:
			bank_note.append(f"Trade License: {self.trade_license}")
		if self.goods_services:
			bank_note.append(f"Goods/Services: {self.goods_services}")
		if bank_note:
			doc.add_comment("Info", "From Supplier Registration {0}:\n{1}".format(self.name, "\n".join(bank_note)))

		return doc.name

	def _create_address(self, supplier):
		if not self.address_line1:
			return
		addr = frappe.new_doc("Address")
		addr.address_title = self.supplier_name
		addr.address_type = "Billing"
		addr.address_line1 = self.address_line1
		addr.address_line2 = self.address_line2 or ""
		addr.city = self.city or self.emirate or "Abu Dhabi"
		addr.country = self.country or "United Arab Emirates"
		addr.state = self.emirate or ""
		addr.append("links", {"link_doctype": "Supplier", "link_name": supplier})
		addr.flags.ignore_permissions = True
		addr.insert(ignore_permissions=True)

	def _create_contact(self, supplier):
		if not self.contact_person:
			return
		contact = frappe.new_doc("Contact")
		parts = self.contact_person.split(None, 1)
		contact.first_name = parts[0]
		if len(parts) > 1:
			contact.last_name = parts[1]
		if self.email:
			contact.append("email_ids", {"email_id": self.email, "is_primary": 1})
		if self.mobile_no:
			contact.append("phone_nos", {"phone": self.mobile_no, "is_primary_mobile_no": 1})
		if self.phone:
			contact.append("phone_nos", {"phone": self.phone, "is_primary_phone": 1})
		contact.append("links", {"link_doctype": "Supplier", "link_name": supplier})
		contact.flags.ignore_permissions = True
		contact.insert(ignore_permissions=True)


def _ensure_can_approve():
	roles = set(frappe.get_roles())
	allowed = {"System Manager", "Accounts Manager", "Purchase Manager", "Administrator"}
	if not roles.intersection(allowed) and frappe.session.user != "Administrator":
		frappe.throw(_("Only Accounts / Purchase Managers can approve supplier registrations."))


def _default_supplier_group():
	if frappe.db.exists("Supplier Group", "All Supplier Groups"):
		return "All Supplier Groups"
	group = frappe.db.get_value("Supplier Group", {}, "name", order_by="lft asc")
	if not group:
		frappe.throw(_("Please create a Supplier Group before approving registrations."))
	return group
