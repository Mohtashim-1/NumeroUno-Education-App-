"""Add Food item lines on Sales Orders / Sales Invoices for students who need food."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt

FOOD_ITEM_CODE = "Food Charges"
FOOD_REQUIRED_YES = "Yes"
FOOD_OPTIONS = "Yes\nNo\nNot Applicable"


def is_food_required(value) -> bool:
	return (value or "").strip() == FOOD_REQUIRED_YES


def _row_value(row, fieldname, default=None):
	if isinstance(row, dict):
		return row.get(fieldname, default)
	return row.get(fieldname, default)


def get_food_item_rate():
	price = frappe.db.get_value(
		"Item Price",
		{"item_code": FOOD_ITEM_CODE, "selling": 1, "price_list": "Standard Selling"},
		"price_list_rate",
	)
	if price is None:
		price = frappe.db.get_value(
			"Item Price",
			{"item_code": FOOD_ITEM_CODE, "selling": 1},
			"price_list_rate",
		)
	return flt(price or 0)


def get_food_rate(student_group=None):
	if student_group:
		rate = frappe.db.get_value("Student Group", student_group, "custom_food_rate")
		if flt(rate):
			return flt(rate)
	return get_food_item_rate()


@frappe.whitelist()
def get_default_food_rate():
	return get_food_rate()


def count_food_students(rows) -> int:
	return sum(1 for row in (rows or []) if is_food_required(_row_value(row, "custom_food_required")))


def append_food_for_student_rows(doc, rows, default_student_group=None):
	"""Add FOOD item qty for students with Food Required = Yes."""
	qty_by_rate = {}
	missing_rate = 0

	for row in rows or []:
		if not is_food_required(_row_value(row, "custom_food_required")):
			continue
		group = _row_value(row, "student_group") or _row_value(row, "custom_student_group") or default_student_group
		rate = flt(get_food_rate(group))
		if not rate:
			missing_rate += 1
			continue
		qty_by_rate[rate] = qty_by_rate.get(rate, 0) + 1

	if missing_rate:
		frappe.throw(
			_(
				"Food is required for {0} student(s), but Food Rate is not set. "
				"Set Food Rate on the Student Group or Item Price for {1}."
			).format(missing_rate, FOOD_ITEM_CODE)
		)

	for rate, qty in qty_by_rate.items():
		_append_or_increase_food_item(doc, qty, rate)


def _append_or_increase_food_item(doc, qty, rate):
	if not qty:
		return

	ensure_food_item()
	rate = flt(rate)

	for item in doc.get("items") or []:
		if item.item_code == FOOD_ITEM_CODE and flt(item.rate) == rate:
			item.qty = flt(item.qty) + qty
			if hasattr(item, "description"):
				item.description = _("Food for {0} student(s)").format(int(item.qty))
			return

	doc.append(
		"items",
		{
			"item_code": FOOD_ITEM_CODE,
			"qty": qty,
			"rate": rate,
			"description": _("Food for {0} student(s)").format(int(qty)),
		},
	)


def ensure_food_item():
	if frappe.db.exists("Item", FOOD_ITEM_CODE):
		return FOOD_ITEM_CODE

	item_group = frappe.db.get_value("Item Group", {"name": "Services", "is_group": 0}, "name")
	if not item_group:
		item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name")
	if not item_group:
		item_group = "All Item Groups"
	uom = "Nos" if frappe.db.exists("UOM", "Nos") else frappe.db.get_value("UOM", {}, "name")

	item = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": FOOD_ITEM_CODE,
			"item_name": "Food",
			"item_group": item_group,
			"stock_uom": uom or "Nos",
			"is_stock_item": 0,
			"is_sales_item": 1,
			"is_purchase_item": 0,
			"include_item_in_manufacturing": 0,
			"description": "Food",
		}
	)
	item.flags.ignore_permissions = True
	item.insert()
	return FOOD_ITEM_CODE
