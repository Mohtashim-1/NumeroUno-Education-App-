"""Add Course checkboxes that control which forms show on the instructor portal."""

from __future__ import annotations

import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from numerouno.numerouno.utils.course_form_flags import (
	FLAG_ASSESSOR_CHECKLIST,
	FLAG_ROSPA,
	FLAG_SAFETY_BRIEFING,
)

AFTER_FIELD = "custom_will_card_issue"
FIELD_ORDER_AFTER = ("will_card_issue", "custom_will_card_issue", "custom_enable_make_and_model")


def get_custom_fields():
	return {
		"Course": [
			{
				"fieldname": FLAG_SAFETY_BRIEFING,
				"label": "Safety Briefing Required",
				"fieldtype": "Check",
				"insert_after": AFTER_FIELD,
				"default": "0",
				"description": "Show Safety Briefing on the Instructor Portal for this course.",
				"translatable": 0,
			},
			{
				"fieldname": FLAG_ASSESSOR_CHECKLIST,
				"label": "Course Assessor Checklist Required",
				"fieldtype": "Check",
				"insert_after": FLAG_SAFETY_BRIEFING,
				"default": "0",
				"description": "Show Course Assessor Checklist on the Instructor Portal for this course.",
				"translatable": 0,
			},
			{
				"fieldname": FLAG_ROSPA,
				"label": "ROSPA Required",
				"fieldtype": "Check",
				"insert_after": FLAG_ASSESSOR_CHECKLIST,
				"default": "0",
				"description": "Show ROSPA Practical Assessment and ROSPA Learning Outcome on the Instructor Portal for this course.",
				"translatable": 0,
			},
		]
	}


def setup():
	create_custom_fields(get_custom_fields(), update=True)
	_insert_in_field_order(
		"Course",
		[FLAG_SAFETY_BRIEFING, FLAG_ASSESSOR_CHECKLIST, FLAG_ROSPA],
	)
	frappe.clear_cache(doctype="Course")
	frappe.db.commit()
	return {"ok": 1}


def after_migrate():
	setup()


def _insert_in_field_order(doctype, fieldnames):
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

	after = next((field for field in FIELD_ORDER_AFTER if field in order), None)
	insert_at = order.index(after) + 1 if after else len(order)
	for fieldname in fieldnames:
		if fieldname in order:
			continue
		order.insert(insert_at, fieldname)
		insert_at += 1

	doc.value = json.dumps(order)
	doc.save(ignore_permissions=True)
