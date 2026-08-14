"""Create Food Required fields on Student Group / student rows and the FOOD item."""

from __future__ import annotations

import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from numerouno.numerouno.utils.food_invoice import FOOD_OPTIONS, ensure_food_item

FOOD_REQUIRED_FIELD = "custom_food_required"
FOOD_RATE_FIELD = "custom_food_rate"


def get_custom_fields():
	return {
		"Student Group": [
			{
				"fieldname": FOOD_REQUIRED_FIELD,
				"label": "Food Required",
				"fieldtype": "Select",
				"options": FOOD_OPTIONS,
				"insert_after": "custom_customer",
				"translatable": 0,
			},
			{
				"fieldname": FOOD_RATE_FIELD,
				"label": "Food Rate",
				"fieldtype": "Currency",
				"insert_after": FOOD_REQUIRED_FIELD,
				"depends_on": 'eval:doc.custom_food_required=="Yes"',
				"mandatory_depends_on": 'eval:doc.custom_food_required=="Yes"',
				"translatable": 0,
			},
		],
		"Student Group Student": [
			{
				"fieldname": FOOD_REQUIRED_FIELD,
				"label": "Food Required",
				"fieldtype": "Select",
				"options": FOOD_OPTIONS,
				"insert_after": "custom_mode_of_payment",
				"in_list_view": 1,
				"in_standard_filter": 1,
				"columns": 1,
				"translatable": 0,
			},
		],
	}


def setup():
	create_custom_fields(get_custom_fields(), update=True)
	_insert_in_field_order(
		"Student Group",
		[FOOD_REQUIRED_FIELD, FOOD_RATE_FIELD],
		after="custom_customer",
	)
	_insert_in_field_order(
		"Student Group Student",
		[FOOD_REQUIRED_FIELD],
		after="custom_mode_of_payment",
	)
	ensure_food_item()
	frappe.clear_cache(doctype="Student Group")
	frappe.clear_cache(doctype="Student Group Student")
	frappe.db.commit()
	return {"ok": 1, "food_item": "Food Charges"}


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
