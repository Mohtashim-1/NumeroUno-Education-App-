import frappe
from frappe.utils import getdate, nowdate


ITEM_FIELDS = ("coverall", "towel", "gloves")
ITEM_LABELS = {
	"coverall": "Coverall",
	"towel": "Towel",
	"gloves": "Gloves",
}


@frappe.whitelist()
def get_daily_report(report_date=None):
	report_date = getdate(report_date or nowdate())
	records = frappe.get_all(
		"Laundry",
		filters={"transaction_date": report_date},
		fields=[
			"name",
			"employee_name",
			"type",
			"transaction_time",
			*ITEM_FIELDS,
		],
		order_by="transaction_time asc, creation asc",
	)

	out_rows = []
	in_rows = []
	out_totals = {}
	in_totals = {}

	for row in records:
		for fieldname in ITEM_FIELDS:
			qty = cint(row.get(fieldname))
			if qty <= 0:
				continue

			entry = {
				"laundry_id": row.name,
				"employee": row.employee_name,
				"item": ITEM_LABELS[fieldname],
				"qty": qty,
				"time": row.transaction_time,
			}
			if row.type == "OUT":
				out_rows.append(entry)
				out_totals[fieldname] = out_totals.get(fieldname, 0) + qty
			else:
				in_rows.append(entry)
				in_totals[fieldname] = in_totals.get(fieldname, 0) + qty

	missing_rows = []
	for fieldname in ITEM_FIELDS:
		missing_qty = out_totals.get(fieldname, 0) - in_totals.get(fieldname, 0)
		if missing_qty > 0:
			missing_rows.append(
				{
					"laundry_id": report_date.isoformat(),
					"item": ITEM_LABELS[fieldname],
					"missing_qty": missing_qty,
				}
			)

	return {
		"report_date": report_date.isoformat(),
		"out_rows": out_rows,
		"in_rows": in_rows,
		"missing_rows": missing_rows,
	}


def cint(value):
	try:
		return int(value or 0)
	except (TypeError, ValueError):
		return 0
