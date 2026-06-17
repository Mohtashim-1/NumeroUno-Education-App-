import frappe
from frappe.utils import getdate, now, nowdate, cstr

TRACKED_ASSET_DOCUMENT_FIELDS = {
	"custom_agreement_document": "Agreement",
	"custom_insurance_document": "Insurance",
	"custom_registration_document": "Registration",
	"custom_compliance_certificate": "Compliance Certificate",
	"custom_inspection_report": "Inspection Report",
	"custom_vendor_contract": "Vendor Contract",
}

EXPIRY_FIELD_BY_ATTACH_FIELD = {
	"custom_insurance_document": {
		"expiry_field": "insurance_end_date",
		"start_field": "insurance_start_date",
	},
	"custom_registration_document": {
		"expiry_field": "custom_registration_expiry_date",
	},
	"custom_agreement_document": {
		"expiry_field": "custom_agreement_expiry_date",
	},
	"custom_compliance_certificate": {
		"expiry_field": "custom_compliance_certificate_expiry",
	},
}

DOCUMENT_TYPE_TO_FIELD = {label: fieldname for fieldname, label in TRACKED_ASSET_DOCUMENT_FIELDS.items()}


def archive_changed_asset_documents(doc, method=None):
	"""Move replaced attach files into Asset Document History."""
	if doc.is_new():
		return

	before = doc.get_doc_before_save()
	if not before:
		return

	for fieldname, document_type in TRACKED_ASSET_DOCUMENT_FIELDS.items():
		archived_fields = getattr(frappe.flags, "asset_document_archived_fields", None) or set()
		if fieldname in archived_fields:
			continue

		old_file = before.get(fieldname)
		new_file = doc.get(fieldname)
		if not old_file or old_file == new_file:
			continue

		meta = EXPIRY_FIELD_BY_ATTACH_FIELD.get(fieldname, {})
		expiry_field = meta.get("expiry_field")
		start_field = meta.get("start_field")

		_append_document_history(
			doc,
			document_type=document_type,
			file_url=old_file,
			expiry_date=before.get(expiry_field) if expiry_field else None,
			effective_from=before.get(start_field) if start_field else None,
			effective_to=before.get(expiry_field) if expiry_field else nowdate(),
			source_field=fieldname,
			notes=getattr(frappe.flags, "asset_document_renewal_notes", None),
		)


def _append_document_history(
	doc,
	document_type,
	file_url,
	expiry_date=None,
	source_field=None,
	effective_from=None,
	effective_to=None,
	notes=None,
):
	doc.append(
		"custom_document_history",
		{
			"document_type": document_type,
			"document": file_url,
			"expiry_date": expiry_date,
			"source_field": source_field,
			"effective_from": effective_from,
			"effective_to": effective_to or nowdate(),
			"archived_on": now(),
			"archived_by": frappe.session.user,
			"notes": notes,
		},
	)


def _get_current_documents(asset):
	current = []
	for fieldname, document_type in TRACKED_ASSET_DOCUMENT_FIELDS.items():
		file_url = asset.get(fieldname)
		if not file_url:
			continue

		meta = EXPIRY_FIELD_BY_ATTACH_FIELD.get(fieldname, {})
		expiry_field = meta.get("expiry_field")
		start_field = meta.get("start_field")

		current.append(
			{
				"document_type": document_type,
				"fieldname": fieldname,
				"document": file_url,
				"expiry_date": asset.get(expiry_field) if expiry_field else None,
				"effective_from": asset.get(start_field) if start_field else None,
				"status": "Current",
			}
		)

	return current


@frappe.whitelist()
def get_asset_documents(asset_name):
	asset_name = cstr(asset_name).strip()
	if not asset_name:
		frappe.throw("Asset is required.")

	asset = frappe.get_doc("Asset", asset_name)
	archived = sorted(
		[
			{
				"document_type": row.document_type,
				"document": row.document,
				"expiry_date": row.expiry_date,
				"effective_from": row.effective_from,
				"effective_to": row.effective_to,
				"archived_on": row.archived_on,
				"archived_by": row.archived_by,
				"notes": row.notes,
				"status": "Archived",
			}
			for row in asset.get("custom_document_history") or []
		],
		key=lambda row: row.get("archived_on") or "",
		reverse=True,
	)

	return {
		"asset_name": asset.name,
		"asset_title": asset.asset_name,
		"current_documents": _get_current_documents(asset),
		"archived_documents": archived,
		"document_types": list(TRACKED_ASSET_DOCUMENT_FIELDS.values()),
		"compliance_certificate": {
			"fieldname": "custom_compliance_certificate",
			"document_type": "Compliance Certificate",
			"document": asset.get("custom_compliance_certificate"),
			"expiry_date": asset.get("custom_compliance_certificate_expiry"),
		},
	}


@frappe.whitelist()
def save_compliance_certificate(asset_name, file_url, expiry_date=None, notes=None):
	"""Add or renew Asset.custom_compliance_certificate from the portal."""
	return renew_asset_document(
		asset_name=asset_name,
		document_type="Compliance Certificate",
		file_url=file_url,
		expiry_date=expiry_date,
		notes=notes,
	)


@frappe.whitelist()
def renew_asset_document(
	asset_name,
	document_type,
	file_url,
	expiry_date=None,
	effective_from=None,
	notes=None,
):
	asset_name = cstr(asset_name).strip()
	document_type = cstr(document_type).strip()
	file_url = cstr(file_url).strip()

	if not asset_name:
		frappe.throw("Asset is required.")
	if not document_type:
		frappe.throw("Document type is required.")
	if not file_url:
		frappe.throw("Document file is required.")

	fieldname = DOCUMENT_TYPE_TO_FIELD.get(document_type)
	if not fieldname:
		frappe.throw(f"Unsupported document type: {document_type}")

	asset = frappe.get_doc("Asset", asset_name)
	meta = EXPIRY_FIELD_BY_ATTACH_FIELD.get(fieldname, {})
	expiry_field = meta.get("expiry_field")
	start_field = meta.get("start_field")

	old_file = asset.get(fieldname)
	if old_file and old_file != file_url:
		_append_document_history(
			asset,
			document_type=document_type,
			file_url=old_file,
			expiry_date=asset.get(expiry_field) if expiry_field else None,
			effective_from=asset.get(start_field) if start_field else None,
			effective_to=asset.get(expiry_field) if expiry_field else nowdate(),
			source_field=fieldname,
			notes=notes,
		)
		frappe.flags.asset_document_archived_fields = set(
			getattr(frappe.flags, "asset_document_archived_fields", set()) or set()
		) | {fieldname}

	asset.set(fieldname, file_url)
	if expiry_field and expiry_date:
		asset.set(expiry_field, expiry_date)
	elif fieldname == "custom_compliance_certificate" and not expiry_date:
		frappe.throw("Certificate expiry date is required for compliance certificates.")
	if start_field and effective_from:
		asset.set(start_field, effective_from)

	frappe.flags.asset_document_renewal_notes = notes
	try:
		asset.save(ignore_permissions=True)
	finally:
		frappe.flags.asset_document_renewal_notes = None
		frappe.flags.asset_document_archived_fields = None

	frappe.db.commit()

	return get_asset_documents(asset_name)
