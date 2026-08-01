"""Sequential Customer Code (e.g. 1001) for existing and new customers."""

from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import cint

FIELDNAME = "custom_customer_code"
SERIES_KEY = "customer_code"
START_CODE = 1001


def setup(start_code: int = START_CODE):
	"""Create field, searchable settings, series, and backfill all customers."""
	create_field()
	update_search_settings()
	assigned = backfill_customers(start_code=start_code)
	frappe.clear_cache(doctype="Customer")
	frappe.db.commit()
	current = frappe.db.sql(
		"select `current` from `tabSeries` where name=%s",
		(SERIES_KEY,),
	)
	return {
		"field": FIELDNAME,
		"assigned": assigned,
		"next_code": cint(current[0][0]) + 1 if current else START_CODE,
	}


def create_field():
	create_custom_fields(
		{
			"Customer": [
				{
					"fieldname": FIELDNAME,
					"label": "Customer Code",
					"fieldtype": "Data",
					"insert_after": "naming_series",
					"unique": 1,
					"read_only": 1,
					"no_copy": 1,
					"in_list_view": 1,
					"in_standard_filter": 1,
					"in_global_search": 1,
					"in_preview": 1,
					"translatable": 0,
					"bold": 1,
					"description": "Auto-assigned sequential code used to find this customer system-wide.",
				}
			]
		},
		update=True,
	)


def update_search_settings():
	"""Make Customer Code searchable in Link fields and Awesome Bar."""
	meta = frappe.get_meta("Customer")
	search_fields = [
		part.strip()
		for part in (meta.search_fields or "").split(",")
		if part and part.strip()
	]
	if FIELDNAME not in search_fields:
		search_fields.insert(0, FIELDNAME)
		_set_property("search_fields", ",".join(search_fields))

	_set_property("show_title_field_in_link", "1")


def _set_property(prop: str, value: str):
	name = frappe.db.get_value(
		"Property Setter",
		{"doc_type": "Customer", "property": prop, "field_name": ""},
		"name",
	)
	if name:
		doc = frappe.get_doc("Property Setter", name)
		doc.value = value
		doc.save(ignore_permissions=True)
		return

	frappe.get_doc(
		{
			"doctype": "Property Setter",
			"doctype_or_field": "DocType",
			"doc_type": "Customer",
			"property": prop,
			"property_type": "Data" if prop == "search_fields" else "Check",
			"value": value,
		}
	).insert(ignore_permissions=True)


def ensure_series(current: int | None = None):
	exists = frappe.db.exists("Series", SERIES_KEY)
	if not exists:
		frappe.db.sql(
			"insert into tabSeries (name, current) values (%s, %s)",
			(SERIES_KEY, cint(current if current is not None else START_CODE - 1)),
		)
	elif current is not None:
		frappe.db.sql(
			"update tabSeries set current=%s where name=%s",
			(cint(current), SERIES_KEY),
		)


def get_next_customer_code() -> str:
	"""Reserve and return the next sequential customer code (thread-safe via Series)."""
	ensure_series()
	row = frappe.db.sql(
		"select `current` from `tabSeries` where name=%s for update",
		(SERIES_KEY,),
	)
	next_val = cint(row[0][0]) + 1
	frappe.db.sql(
		"update `tabSeries` set current=%s where name=%s",
		(next_val, SERIES_KEY),
	)
	return str(next_val)


def assign_customer_code(doc, method=None):
	"""Doc event: assign code on insert/validate if missing."""
	if (doc.get(FIELDNAME) or "").strip():
		return
	doc.set(FIELDNAME, get_next_customer_code())


def backfill_customers(start_code: int = START_CODE) -> int:
	"""Assign codes to all customers missing one, ordered by creation."""
	customers = frappe.get_all(
		"Customer",
		fields=["name", FIELDNAME],
		order_by="creation asc, name asc",
	)

	max_existing = start_code - 1
	for row in customers:
		code = (row.get(FIELDNAME) or "").strip()
		if code.isdigit():
			max_existing = max(max_existing, cint(code))

	next_code = max_existing + 1
	assigned = 0
	for row in customers:
		if (row.get(FIELDNAME) or "").strip():
			continue
		frappe.db.set_value(
			"Customer",
			row.name,
			FIELDNAME,
			str(next_code),
			update_modified=False,
		)
		next_code += 1
		assigned += 1

	ensure_series(current=next_code - 1)
	return assigned
