import frappe
from frappe.utils import cint, today

PORTAL_ROLES = (
	"System Manager",
	"Vehicle User",
	"Delivery User",
	"Sales User",
	"Sales Manager",
	"Accounts User",
	"Accounts Manager",
)

OVERSEER_ROLES = (
	"System Manager",
	"Sales Manager",
	"Accounts Manager",
	"Accounts User",
)


def _ensure_portal_access():
	frappe.only_for(PORTAL_ROLES)


def _has_delivery_driver_field():
	return frappe.get_meta("Sales Invoice").has_field("custom_delivery_driver")


def _is_driver_only_user():
	roles = set(frappe.get_roles())
	if roles.intersection(OVERSEER_ROLES):
		return False
	return bool(roles.intersection({"Vehicle User", "Delivery User"}))


def _driver_filter_sql(alias="si"):
	if not _has_delivery_driver_field():
		return "", {}
	if _is_driver_only_user():
		return f" AND {alias}.custom_delivery_driver = %(driver)s", {"driver": frappe.session.user}
	return "", {}


def _unack_sql(alias="si"):
	if frappe.get_meta("Sales Invoice").has_field("custom_delivery_acknowledged"):
		return f" AND IFNULL({alias}.custom_delivery_acknowledged, 0) = 0"
	return f" AND {alias}.docstatus = 1"


def _ensure_assign_access():
	frappe.only_for(OVERSEER_ROLES)


def _validate_delivery_driver(driver):
	driver = (driver or "").strip()
	if not driver:
		frappe.throw("Delivery Driver is required")
	if not frappe.db.exists("User", driver):
		frappe.throw("Invalid driver user")
	roles = frappe.get_roles(driver)
	if not set(roles).intersection({"Vehicle User", "Delivery User"}):
		frappe.throw("Selected user is not a delivery driver")
	return driver


def _parse_invoice_names(sales_invoices):
	invoices = frappe.parse_json(sales_invoices) if isinstance(sales_invoices, str) else sales_invoices
	if not invoices:
		frappe.throw("Select at least one Sales Invoice")
	if not isinstance(invoices, (list, tuple)):
		frappe.throw("Invalid invoice list")
	return list(dict.fromkeys(invoices))


@frappe.whitelist()
def bulk_assign_delivery_driver(sales_invoices, driver):
	_ensure_assign_access()
	if not _has_delivery_driver_field():
		frappe.throw("Delivery Driver field is not configured on Sales Invoice.")

	driver = _validate_delivery_driver(driver)
	invoices = _parse_invoice_names(sales_invoices)

	updated = []
	skipped = []
	for invoice in invoices:
		si = frappe.db.get_value(
			"Sales Invoice",
			invoice,
			["name", "docstatus", "custom_delivery_acknowledged"],
			as_dict=True,
		)
		if not si or si.docstatus != 1:
			skipped.append({"invoice": invoice, "reason": "Not a submitted invoice"})
			continue
		if si.get("custom_delivery_acknowledged"):
			skipped.append({"invoice": invoice, "reason": "Already acknowledged"})
			continue
		frappe.db.set_value("Sales Invoice", invoice, "custom_delivery_driver", driver, update_modified=True)
		updated.append(invoice)

	return {
		"updated": len(updated),
		"updated_invoices": updated,
		"skipped": skipped,
		"driver": driver,
		"driver_name": frappe.utils.get_fullname(driver),
	}


@frappe.whitelist()
def bulk_clear_delivery_driver(sales_invoices):
	_ensure_assign_access()
	if not _has_delivery_driver_field():
		frappe.throw("Delivery Driver field is not configured on Sales Invoice.")

	invoices = _parse_invoice_names(sales_invoices)
	updated = []
	skipped = []
	for invoice in invoices:
		si = frappe.db.get_value(
			"Sales Invoice",
			invoice,
			["name", "docstatus", "custom_delivery_acknowledged"],
			as_dict=True,
		)
		if not si or si.docstatus != 1:
			skipped.append({"invoice": invoice, "reason": "Not a submitted invoice"})
			continue
		if si.get("custom_delivery_acknowledged"):
			skipped.append({"invoice": invoice, "reason": "Already acknowledged"})
			continue
		frappe.db.set_value("Sales Invoice", invoice, "custom_delivery_driver", "", update_modified=True)
		updated.append(invoice)

	return {"updated": len(updated), "updated_invoices": updated, "skipped": skipped}


@frappe.whitelist()
def get_delivery_driver_users(doctype, txt, searchfield, start, page_len, filters):
	delivered_roles = ("Vehicle User", "Delivery User")
	users = frappe.db.sql(
		"""
		SELECT DISTINCT u.name, u.full_name
		FROM `tabUser` u
		INNER JOIN `tabHas Role` hr ON hr.parent = u.name
		WHERE hr.role IN %(roles)s
		  AND u.enabled = 1
		  AND (u.name LIKE %(txt)s OR u.full_name LIKE %(txt)s)
		ORDER BY u.full_name
		LIMIT %(start)s, %(page_len)s
		""",
		{
			"roles": delivered_roles,
			"txt": f"%{txt or ''}%",
			"start": start,
			"page_len": page_len,
		},
	)
	return users


@frappe.whitelist()
def get_portal_kpis():
	_ensure_portal_access()
	driver_only = _is_driver_only_user()
	driver_sql, driver_params = _driver_filter_sql("si")
	unack = _unack_sql("si")

	pending = frappe.db.sql(
		f"""
		SELECT COUNT(*) FROM `tabSales Invoice` si
		WHERE si.docstatus = 1
		{unack}
		{driver_sql}
		""",
		driver_params,
	)[0][0]

	assigned_pending = 0
	unassigned_pending = 0
	if _has_delivery_driver_field() and not driver_only:
		assigned_pending = frappe.db.sql(
			f"""
			SELECT COUNT(*) FROM `tabSales Invoice` si
			WHERE si.docstatus = 1
			{unack}
			AND IFNULL(si.custom_delivery_driver, '') != ''
			""",
		)[0][0]
		unassigned_pending = max(pending - assigned_pending, 0)

	ack_filters = {"docstatus": 1}
	if driver_only:
		ack_filters["driver"] = frappe.session.user

	completed = frappe.db.count("Invoice Delivery Acknowledgement", ack_filters)
	completed_today = frappe.db.count(
		"Invoice Delivery Acknowledgement",
		{**ack_filters, "receiving_date": today()},
	)

	return {
		"pending": pending,
		"completed": completed,
		"completed_today": completed_today,
		"assigned_pending": assigned_pending,
		"unassigned_pending": unassigned_pending,
		"driver_only": driver_only,
		"can_assign_driver": not driver_only and _has_delivery_driver_field(),
		"driver_name": frappe.utils.get_fullname(frappe.session.user),
		"user": frappe.session.user,
	}


@frappe.whitelist()
def get_pending_invoices(search=None, limit=50, offset=0):
	_ensure_portal_access()

	limit = min(cint(limit) or 50, 100)
	offset = cint(offset) or 0
	search = (search or "").strip()

	driver_sql, driver_params = _driver_filter_sql("si")
	unack = _unack_sql("si")
	params = {**driver_params, "limit": limit, "offset": offset}

	search_sql = ""
	if search:
		params["search"] = f"%{search}%"
		search_sql = """
			AND (
				si.name LIKE %(search)s
				OR si.customer_name LIKE %(search)s
				OR si.customer LIKE %(search)s
			)
		"""

	order_sql = "si.posting_date DESC, si.modified DESC"
	if _has_delivery_driver_field() and not _is_driver_only_user():
		order_sql = """
			CASE WHEN IFNULL(si.custom_delivery_driver, '') != '' THEN 0 ELSE 1 END,
			si.posting_date DESC,
			si.modified DESC
		"""

	rows = frappe.db.sql(
		f"""
		SELECT
			si.name,
			si.customer,
			si.customer_name,
			si.posting_date,
			si.grand_total,
			si.currency,
			si.custom_delivery_driver
		FROM `tabSales Invoice` si
		WHERE si.docstatus = 1
		{unack}
		{driver_sql}
		{search_sql}
		ORDER BY {order_sql}
		LIMIT %(limit)s OFFSET %(offset)s
		""",
		params,
		as_dict=True,
	)

	total = frappe.db.sql(
		f"""
		SELECT COUNT(*) FROM `tabSales Invoice` si
		WHERE si.docstatus = 1
		{unack}
		{driver_sql}
		{search_sql}
		""",
		params,
	)[0][0]

	_attach_ack_status(rows)
	_attach_driver_labels(rows)
	return {"rows": rows, "total": total, "offset": offset, "limit": limit}


@frappe.whitelist()
def get_completed_invoices(limit=30, offset=0):
	_ensure_portal_access()
	limit = min(cint(limit) or 30, 100)
	offset = cint(offset) or 0

	filters = {"docstatus": 1}
	if _is_driver_only_user():
		filters["driver"] = frappe.session.user

	rows = frappe.get_all(
		"Invoice Delivery Acknowledgement",
		filters=filters,
		fields=[
			"name",
			"sales_invoice",
			"customer_name",
			"receiver_name",
			"receiving_date",
			"has_certificates",
			"has_cards",
			"driver",
			"modified",
		],
		order_by="modified desc",
		limit_start=offset,
		limit_page_length=limit,
	)
	return {"rows": rows, "total": frappe.db.count("Invoice Delivery Acknowledgement", filters)}


def _attach_ack_status(rows):
	if not rows:
		return
	existing = frappe.get_all(
		"Invoice Delivery Acknowledgement",
		filters={"sales_invoice": ["in", [r.name for r in rows]], "docstatus": ["<", 2]},
		fields=["name", "sales_invoice", "docstatus"],
	)
	ack_map = {row.sales_invoice: row for row in existing}
	for row in rows:
		ack = ack_map.get(row.name)
		row["acknowledgement"] = ack.name if ack else None
		row["acknowledgement_status"] = (
			"Submitted" if ack and ack.docstatus == 1 else "Draft" if ack else "Pending"
		)


def _attach_driver_labels(rows):
	if not _has_delivery_driver_field():
		return
	driver_ids = {row.custom_delivery_driver for row in rows if row.get("custom_delivery_driver")}
	if not driver_ids:
		return
	users = {
		row.name: row.full_name
		for row in frappe.get_all("User", filters={"name": ["in", list(driver_ids)]}, fields=["name", "full_name"])
	}
	for row in rows:
		driver_id = row.get("custom_delivery_driver")
		row["delivery_driver_name"] = users.get(driver_id) or driver_id


@frappe.whitelist()
def save_acknowledgement(data):
	data = frappe.parse_json(data)
	sales_invoice = (data.get("sales_invoice") or "").strip()
	if not sales_invoice:
		frappe.throw("Sales Invoice is required")

	from numerouno.numerouno.doctype.invoice_delivery_acknowledgement.invoice_delivery_acknowledgement import (
		get_invoice_context,
	)

	context = get_invoice_context(sales_invoice)
	if context.get("already_acknowledged"):
		frappe.throw("This invoice is already acknowledged.")

	assigned_driver = context.get("delivery_driver")
	if assigned_driver and assigned_driver != frappe.session.user and not set(frappe.get_roles(frappe.session.user)).intersection(
		OVERSEER_ROLES
	):
		frappe.throw("This invoice is assigned to another driver.")

	existing = frappe.db.exists(
		"Invoice Delivery Acknowledgement",
		{"sales_invoice": sales_invoice, "docstatus": ["<", 2]},
	)
	if existing:
		doc = frappe.get_doc("Invoice Delivery Acknowledgement", existing)
		if doc.docstatus == 1:
			frappe.throw("This invoice is already acknowledged.")
	else:
		doc = frappe.new_doc("Invoice Delivery Acknowledgement")

	doc.sales_invoice = sales_invoice
	doc.customer = context.get("customer")
	doc.customer_name = context.get("customer_name")
	doc.invoice_date = context.get("posting_date")
	doc.grand_total = context.get("grand_total")
	doc.currency = context.get("currency")
	doc.invoice_description = context.get("items_text")
	doc.students_summary = context.get("students_text")
	doc.driver = assigned_driver or frappe.session.user
	doc.receiver_name = (data.get("receiver_name") or "").strip()
	doc.receiving_date = data.get("receiving_date") or today()
	doc.contact_no = (data.get("contact_no") or "").strip()
	doc.has_certificates = cint(data.get("has_certificates"))
	doc.has_cards = cint(data.get("has_cards"))
	doc.receiver_signature = data.get("receiver_signature") or ""
	doc.remarks = (data.get("remarks") or "").strip()
	if data.get("submission_latitude") is not None:
		doc.submission_latitude = data.get("submission_latitude")
	if data.get("submission_longitude") is not None:
		doc.submission_longitude = data.get("submission_longitude")
	if data.get("submission_location_accuracy") is not None:
		doc.submission_location_accuracy = data.get("submission_location_accuracy")
	if data.get("client_device_info"):
		doc.client_device_info = data.get("client_device_info")

	if not doc.receiver_name:
		frappe.throw("Receiver name is required")
	if not doc.receiver_signature:
		frappe.throw("Receiver signature is required")

	doc.save()

	if cint(data.get("submit")):
		doc.submit()

	return {
		"name": doc.name,
		"docstatus": doc.docstatus,
		"sales_invoice": doc.sales_invoice,
	}
