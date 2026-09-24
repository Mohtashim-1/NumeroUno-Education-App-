# Copyright (c) 2026, NumeroUNO and contributors
# License: MIT

"""Supplier compliance custom fields (Trade License + ICV validity gate)."""

from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_migrate():
	ensure_supplier_compliance_fields()


def ensure_supplier_compliance_fields():
	create_custom_fields(get_supplier_compliance_fields(), update=True)


def get_supplier_compliance_fields():
	return {
		"Supplier": [
			{
				"fieldname": "custom_portal_compliance_section",
				"fieldtype": "Section Break",
				"label": "Portal Compliance",
				"insert_after": "disabled",
				"collapsible": 1,
			},
			{
				"fieldname": "custom_trade_license_file",
				"fieldtype": "Attach",
				"label": "Trade License",
				"insert_after": "custom_portal_compliance_section",
			},
			{
				"fieldname": "custom_trade_license_valid_until",
				"fieldtype": "Date",
				"label": "Trade License Validity",
				"insert_after": "custom_trade_license_file",
				"in_standard_filter": 1,
			},
			{
				"fieldname": "custom_icv_certificate_file",
				"fieldtype": "Attach",
				"label": "ICV Certificate",
				"insert_after": "custom_trade_license_valid_until",
			},
			{
				"fieldname": "custom_icv_valid_until",
				"fieldtype": "Date",
				"label": "ICV Certificate Validity",
				"insert_after": "custom_icv_certificate_file",
				"in_standard_filter": 1,
			},
			{
				"fieldname": "custom_tax_registration_certificate",
				"fieldtype": "Attach",
				"label": "Tax Registration Certificate",
				"insert_after": "custom_icv_valid_until",
			},
			{
				"fieldname": "custom_iban_letter",
				"fieldtype": "Attach",
				"label": "IBAN Letter",
				"insert_after": "custom_tax_registration_certificate",
			},
			{
				"fieldname": "custom_additional_documents",
				"fieldtype": "Attach",
				"label": "Additional Documents",
				"insert_after": "custom_iban_letter",
			},
		]
	}


def apply_registration_compliance_to_supplier(supplier: str, registration) -> None:
	"""Copy registration compliance attachments + validity onto Supplier."""
	ensure_supplier_compliance_fields()
	if not supplier or not frappe.db.exists("Supplier", supplier):
		return

	updates = {}
	if getattr(registration, "trade_license_attachment", None):
		updates["custom_trade_license_file"] = registration.trade_license_attachment
	if getattr(registration, "trade_license_valid_until", None):
		updates["custom_trade_license_valid_until"] = registration.trade_license_valid_until
	if getattr(registration, "icv_certificate", None):
		updates["custom_icv_certificate_file"] = registration.icv_certificate
	if getattr(registration, "icv_valid_until", None):
		updates["custom_icv_valid_until"] = registration.icv_valid_until
	if getattr(registration, "tax_registration_certificate", None):
		updates["custom_tax_registration_certificate"] = registration.tax_registration_certificate
	if getattr(registration, "iban_letter", None):
		updates["custom_iban_letter"] = registration.iban_letter
	if getattr(registration, "additional_documents", None):
		updates["custom_additional_documents"] = registration.additional_documents

	if updates:
		frappe.db.set_value("Supplier", supplier, updates, update_modified=True)
