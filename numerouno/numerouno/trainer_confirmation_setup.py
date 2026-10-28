"""Trainer confirmation fields on Assessment Result (required before certificate print)."""

from __future__ import annotations

import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CONFIRMED_FIELD = "custom_trainer_confirmed"
CONFIRMED_BY_FIELD = "custom_trainer_confirmed_by"
CONFIRMED_ON_FIELD = "custom_trainer_confirmed_on"
CONFIRMED_SECTION = "custom_trainer_confirmation_section"


def get_custom_fields():
	return {
		"Assessment Result": [
			{
				"fieldname": CONFIRMED_SECTION,
				"label": "Trainer Confirmation",
				"fieldtype": "Section Break",
				"insert_after": "custom_certificate",
				"collapsible": 1,
			},
			{
				"fieldname": CONFIRMED_FIELD,
				"label": "Trainer Confirmed for Certificate",
				"fieldtype": "Check",
				"insert_after": CONFIRMED_SECTION,
				"allow_on_submit": 1,
				"in_list_view": 1,
				"in_standard_filter": 1,
				"read_only": 1,
				"translatable": 0,
			},
			{
				"fieldname": CONFIRMED_BY_FIELD,
				"label": "Confirmed By",
				"fieldtype": "Link",
				"options": "User",
				"insert_after": CONFIRMED_FIELD,
				"allow_on_submit": 1,
				"read_only": 1,
				"translatable": 0,
			},
			{
				"fieldname": CONFIRMED_ON_FIELD,
				"label": "Confirmed On",
				"fieldtype": "Datetime",
				"insert_after": CONFIRMED_BY_FIELD,
				"allow_on_submit": 1,
				"read_only": 1,
				"translatable": 0,
			},
		],
	}


def setup():
	create_custom_fields(get_custom_fields(), update=True)
	_insert_in_field_order(
		"Assessment Result",
		[CONFIRMED_SECTION, CONFIRMED_FIELD, CONFIRMED_BY_FIELD, CONFIRMED_ON_FIELD],
		after="custom_certificate",
	)
	frappe.clear_cache(doctype="Assessment Result")
	frappe.db.commit()
	return {"ok": 1}


def after_migrate():
	setup()


def _insert_in_field_order(doctype, fieldnames, after):
	name = frappe.db.get_value(
		"Property Setter",
		{"doc_type": doctype, "property": "field_order", "doctype_or_field": "DocType"},
		"name",
	)
	if not name:
		return

	doc = frappe.get_doc("Property Setter", name)
	try:
		order = json.loads(doc.value or "[]")
	except Exception:
		return

	insert_at = order.index(after) + 1 if after in order else len(order)
	for fieldname in fieldnames:
		if fieldname in order:
			continue
		order.insert(insert_at, fieldname)
		insert_at += 1

	doc.value = json.dumps(order)
	doc.save(ignore_permissions=True)
