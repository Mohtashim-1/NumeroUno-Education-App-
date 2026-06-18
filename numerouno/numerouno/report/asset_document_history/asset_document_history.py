# Copyright (c) 2026, mohtashim and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate

from numerouno.numerouno.asset_document_archive import (
	EXPIRY_FIELD_BY_ATTACH_FIELD,
	TRACKED_ASSET_DOCUMENT_FIELDS,
)


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"fieldname": "asset",
			"label": _("Asset"),
			"fieldtype": "Link",
			"options": "Asset",
			"width": 160,
		},
		{
			"fieldname": "asset_name",
			"label": _("Asset Name"),
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"fieldname": "asset_tag",
			"label": _("Asset Tag"),
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"fieldname": "asset_category",
			"label": _("Asset Category"),
			"fieldtype": "Link",
			"options": "Asset Category",
			"width": 140,
		},
		{
			"fieldname": "location",
			"label": _("Location"),
			"fieldtype": "Link",
			"options": "Location",
			"width": 120,
		},
		{
			"fieldname": "department",
			"label": _("Department"),
			"fieldtype": "Link",
			"options": "Department",
			"width": 120,
		},
		{
			"fieldname": "document_type",
			"label": _("Document Type"),
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"fieldname": "document",
			"label": _("Document"),
			"fieldtype": "Data",
			"width": 220,
		},
		{
			"fieldname": "effective_from",
			"label": _("Effective From"),
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"fieldname": "expiry_date",
			"label": _("Expiry Date"),
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"fieldname": "archived_on",
			"label": _("Archived On"),
			"fieldtype": "Datetime",
			"width": 160,
		},
		{
			"fieldname": "archived_by",
			"label": _("Archived By"),
			"fieldtype": "Link",
			"options": "User",
			"width": 140,
		},
		{
			"fieldname": "notes",
			"label": _("Notes"),
			"fieldtype": "Data",
			"width": 180,
		},
	]


def get_data(filters):
	rows = []
	status_filter = (filters.get("status") or "").strip()

	if status_filter in ("", "Archived"):
		rows.extend(_get_archived_rows(filters))

	if status_filter in ("", "Current"):
		rows.extend(_get_current_rows(filters))

	rows.sort(
		key=lambda row: (
			row.get("asset") or "",
			0 if row.get("status") == "Current" else 1,
			row.get("archived_on") or "",
		),
		reverse=False,
	)
	return rows


def _asset_filters(filters, alias="a"):
	conditions = ["1=1"]
	values = {}

	if filters.get("asset"):
		conditions.append(f"{alias}.name = %(asset)s")
		values["asset"] = filters["asset"]
	if filters.get("asset_category"):
		conditions.append(f"{alias}.asset_category = %(asset_category)s")
		values["asset_category"] = filters["asset_category"]
	if filters.get("location"):
		conditions.append(f"{alias}.location = %(location)s")
		values["location"] = filters["location"]
	if filters.get("department"):
		conditions.append(f"{alias}.department = %(department)s")
		values["department"] = filters["department"]

	return conditions, values


def _get_archived_rows(filters):
	conditions, values = _asset_filters(filters, "a")
	conditions.append("adh.parenttype = 'Asset'")

	if filters.get("document_type"):
		conditions.append("adh.document_type = %(document_type)s")
		values["document_type"] = filters["document_type"]

	if filters.get("from_date"):
		conditions.append("DATE(adh.archived_on) >= %(from_date)s")
		values["from_date"] = getdate(filters["from_date"])

	if filters.get("to_date"):
		conditions.append("DATE(adh.archived_on) <= %(to_date)s")
		values["to_date"] = getdate(filters["to_date"])

	return frappe.db.sql(
		f"""
		SELECT
			a.name AS asset,
			a.asset_name,
			a.custom_asset_tag_number AS asset_tag,
			a.asset_category,
			a.location,
			a.department,
			adh.document_type,
			'Archived' AS status,
			adh.document,
			adh.effective_from,
			COALESCE(adh.expiry_date, adh.effective_to) AS expiry_date,
			adh.archived_on,
			adh.archived_by,
			adh.notes
		FROM `tabAsset Document History` adh
		INNER JOIN `tabAsset` a ON a.name = adh.parent
		WHERE {" AND ".join(conditions)}
		ORDER BY adh.archived_on DESC
		""",
		values,
		as_dict=True,
	)


def _get_current_rows(filters):
	conditions, values = _asset_filters(filters, "a")
	document_type_filter = (filters.get("document_type") or "").strip()

	if filters.get("from_date") or filters.get("to_date"):
		return []

	assets = frappe.db.sql(
		f"""
		SELECT
			a.name,
			a.asset_name,
			a.custom_asset_tag_number,
			a.asset_category,
			a.location,
			a.department,
			a.custom_agreement_document,
			a.custom_insurance_document,
			a.custom_registration_document,
			a.custom_compliance_certificate,
			a.custom_inspection_report,
			a.custom_vendor_contract,
			a.custom_agreement_expiry_date,
			a.custom_registration_expiry_date,
			a.custom_compliance_certificate_expiry,
			a.insurance_start_date,
			a.insurance_end_date
		FROM `tabAsset` a
		WHERE {" AND ".join(conditions)}
		""",
		values,
		as_dict=True,
	)

	rows = []
	for asset in assets:
		for fieldname, document_type in TRACKED_ASSET_DOCUMENT_FIELDS.items():
			if document_type_filter and document_type != document_type_filter:
				continue

			file_url = asset.get(fieldname)
			if not file_url:
				continue

			meta = EXPIRY_FIELD_BY_ATTACH_FIELD.get(fieldname, {})
			expiry_field = meta.get("expiry_field")
			start_field = meta.get("start_field")

			rows.append(
				{
					"asset": asset.name,
					"asset_name": asset.asset_name,
					"asset_tag": asset.custom_asset_tag_number,
					"asset_category": asset.asset_category,
					"location": asset.location,
					"department": asset.department,
					"document_type": document_type,
					"status": "Current",
					"document": file_url,
					"effective_from": asset.get(start_field) if start_field else None,
					"expiry_date": asset.get(expiry_field) if expiry_field else None,
					"archived_on": None,
					"archived_by": None,
					"notes": None,
				}
			)

	return rows
