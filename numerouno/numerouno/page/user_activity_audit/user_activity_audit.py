# Copyright (c) 2026, mohtashim and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime, format_datetime, cint
from frappe.utils.pdf import get_pdf

from numerouno.numerouno.report.user_route_history.user_route_history import parse_route


@frappe.whitelist()
def get_activity_data(filters=None):
	filters = frappe.parse_json(filters) if filters else {}
	route_rows, access_rows = _fetch_rows(filters)
	summary = _build_summary(route_rows, access_rows, filters)

	return {
		"summary": summary,
		"route_history": route_rows,
		"access_log": access_rows,
	}


def _fetch_rows(filters):
	route_rows = []
	access_rows = []

	if cint(filters.get("include_route_history", 1)):
		route_rows = _get_route_history(filters)

	if cint(filters.get("include_access_log", 1)):
		access_rows = _get_access_log(filters)

	return route_rows, access_rows


def _get_route_history(filters):
	conditions = ["rh.route IS NOT NULL", "rh.route != ''"]
	values = {}

	if filters.get("user"):
		conditions.append("rh.user = %(user)s")
		values["user"] = filters["user"]

	if filters.get("from_date"):
		conditions.append("DATE(COALESCE(rh.creation, rh.modified)) >= %(from_date)s")
		values["from_date"] = getdate(filters["from_date"])

	if filters.get("to_date"):
		conditions.append("DATE(COALESCE(rh.creation, rh.modified)) <= %(to_date)s")
		values["to_date"] = getdate(filters["to_date"])

	if filters.get("route_contains"):
		conditions.append("rh.route LIKE %(route_contains)s")
		values["route_contains"] = f"%{filters['route_contains'].strip()}%"

	if filters.get("access_type"):
		if filters["access_type"] == "Report":
			conditions.append("rh.route LIKE 'query-report/%'")
		else:
			conditions.append("rh.route LIKE %(access_type)s")
			values["access_type"] = f"{filters['access_type']}/%"

	if filters.get("accessed_item"):
		conditions.append("rh.route LIKE %(accessed_item)s")
		values["accessed_item"] = f"%/{filters['accessed_item'].strip()}%"

	rows = frappe.db.sql(
		f"""
		SELECT
			COALESCE(rh.creation, rh.modified) AS accessed_on,
			rh.user,
			u.full_name,
			rh.route
		FROM `tabRoute History` rh
		LEFT JOIN `tabUser` u ON u.name = rh.user
		WHERE {" AND ".join(conditions)}
		ORDER BY COALESCE(rh.creation, rh.modified) DESC
		LIMIT 10000
		""",
		values,
		as_dict=True,
	)

	for row in rows:
		row.update(parse_route(row.route))
		row["accessed_on"] = format_datetime(row["accessed_on"])

	return rows


def _get_access_log(filters):
	conditions = ["1=1"]
	values = {}

	if filters.get("user"):
		conditions.append("al.user = %(user)s")
		values["user"] = filters["user"]

	if filters.get("from_date"):
		conditions.append("DATE(al.creation) >= %(from_date)s")
		values["from_date"] = getdate(filters["from_date"])

	if filters.get("to_date"):
		conditions.append("DATE(al.creation) <= %(to_date)s")
		values["to_date"] = getdate(filters["to_date"])

	if filters.get("export_from"):
		conditions.append("al.export_from = %(export_from)s")
		values["export_from"] = filters["export_from"]

	if filters.get("method"):
		conditions.append("al.method = %(method)s")
		values["method"] = filters["method"]

	rows = frappe.db.sql(
		f"""
		SELECT
			al.creation AS accessed_on,
			al.user,
			u.full_name,
			al.export_from,
			al.reference_document,
			al.file_type,
			al.method,
			al.page,
			al.report_name
		FROM `tabAccess Log` al
		LEFT JOIN `tabUser` u ON u.name = al.user
		WHERE {" AND ".join(conditions)}
		ORDER BY al.creation DESC
		LIMIT 10000
		""",
		values,
		as_dict=True,
	)

	for row in rows:
		row["accessed_on"] = format_datetime(row["accessed_on"])

	return rows


def _build_summary(route_rows, access_rows, filters):
	rh_range = frappe.db.sql(
		"""
		SELECT COUNT(*) AS total, MIN(creation) AS oldest, MAX(creation) AS newest
		FROM `tabRoute History`
		""",
		as_dict=True,
	)[0]

	print_exports = [r for r in access_rows if (r.get("method") or "").lower() in ("print", "export", "download")]
	quotation_prints = [
		r for r in access_rows if r.get("export_from") == "Quotation" and r.get("method") == "Print"
	]

	return {
		"route_visits": len(route_rows),
		"access_log_entries": len(access_rows),
		"print_export_count": len(print_exports),
		"quotation_print_count": len(quotation_prints),
		"unique_routes": len({r.get("route") for r in route_rows if r.get("route")}),
		"unique_documents": len(
			{r.get("reference_document") for r in access_rows if r.get("reference_document")}
		),
		"route_history_db_total": rh_range.total or 0,
		"route_history_db_oldest": format_datetime(rh_range.oldest) if rh_range.oldest else None,
		"route_history_db_newest": format_datetime(rh_range.newest) if rh_range.newest else None,
		"generated_on": format_datetime(now_datetime()),
		"filters_applied": filters,
	}


@frappe.whitelist()
def export_pdf(filters=None):
	filters = frappe.parse_json(filters) if filters else {}
	html = _build_export_html(filters)
	pdf = get_pdf(html)

	user_slug = (filters.get("user") or "all_users").replace("@", "_at_")
	filename = f"User_Activity_Audit_{user_slug}_{filters.get('from_date', '')}_{filters.get('to_date', '')}.pdf"

	frappe.local.response.filename = filename
	frappe.local.response.filecontent = pdf
	frappe.local.response.type = "download"


@frappe.whitelist()
def export_word(filters=None):
	filters = frappe.parse_json(filters) if filters else {}
	html = _build_export_html(filters, for_word=True)

	user_slug = (filters.get("user") or "all_users").replace("@", "_at_")
	filename = f"User_Activity_Audit_{user_slug}_{filters.get('from_date', '')}_{filters.get('to_date', '')}.doc"

	frappe.local.response.filename = filename
	frappe.local.response.filecontent = html.encode("utf-8")
	frappe.local.response.type = "download"
	frappe.local.response["Content-Type"] = "application/msword"


def _build_export_html(filters, for_word=False):
	data = get_activity_data(filters)
	summary = data["summary"]
	route_rows = data["route_history"]
	access_rows = data["access_log"]

	user_label = filters.get("user") or _("All Users")
	title = _("User Activity Audit Report")

	styles = """
		body { font-family: Arial, sans-serif; font-size: 11px; color: #222; }
		h1 { font-size: 18px; margin-bottom: 4px; }
		h2 { font-size: 14px; margin-top: 24px; border-bottom: 1px solid #ccc; padding-bottom: 4px; }
		.meta { color: #555; margin-bottom: 16px; }
		.summary-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
		.summary-table td { padding: 6px 8px; border: 1px solid #ddd; }
		.summary-table td.label { background: #f5f5f5; font-weight: bold; width: 220px; }
		table.data { width: 100%; border-collapse: collapse; margin-top: 8px; }
		table.data th, table.data td { border: 1px solid #ccc; padding: 5px 6px; text-align: left; vertical-align: top; }
		table.data th { background: #eef2f7; }
		.note { background: #fff8e1; border: 1px solid #ffe082; padding: 8px; margin: 12px 0; }
	"""

	word_header = ""
	if for_word:
		word_header = """
		<html xmlns:o="urn:schemas-microsoft-com:office:office"
			xmlns:w="urn:schemas-microsoft-com:office:word"
			xmlns="http://www.w3.org/TR/REC-html40">
		<head><meta charset="utf-8">
		<!--[if gte mso 9]><xml><w:WordDocument><w:View>Print</w:View></w:WordDocument></xml><![endif]-->
		"""
	else:
		word_header = "<html><head><meta charset='utf-8'>"

	html = f"""{word_header}
	<style>{styles}</style></head><body>
	<h1>{title}</h1>
	<div class="meta">
		<div><strong>{_("User")}:</strong> {frappe.utils.escape_html(user_label)}</div>
		<div><strong>{_("From Date")}:</strong> {frappe.utils.escape_html(str(filters.get('from_date') or '-'))}
		&nbsp;|&nbsp; <strong>{_("To Date")}:</strong> {frappe.utils.escape_html(str(filters.get('to_date') or '-'))}</div>
		<div><strong>{_("Generated On")}:</strong> {frappe.utils.escape_html(summary.get('generated_on') or '')}</div>
	</div>

	<div class="note">
		<strong>{_("Note")}:</strong> {_("Route History is retained for 90 days and may only contain recent navigation data. Access Log covers print/export/download actions for a longer period.")}
	</div>

	<h2>{_("Summary")}</h2>
	<table class="summary-table">
		<tr><td class="label">{_("Navigation visits (filtered)")}</td><td>{summary.get('route_visits', 0)}</td></tr>
		<tr><td class="label">{_("Access log entries (filtered)")}</td><td>{summary.get('access_log_entries', 0)}</td></tr>
		<tr><td class="label">{_("Print / Export / Download actions")}</td><td>{summary.get('print_export_count', 0)}</td></tr>
		<tr><td class="label">{_("Quotation PDF prints")}</td><td>{summary.get('quotation_print_count', 0)}</td></tr>
		<tr><td class="label">{_("Unique routes visited")}</td><td>{summary.get('unique_routes', 0)}</td></tr>
		<tr><td class="label">{_("Unique documents in access log")}</td><td>{summary.get('unique_documents', 0)}</td></tr>
		<tr><td class="label">{_("Route History DB range")}</td>
			<td>{summary.get('route_history_db_oldest') or '-'} — {summary.get('route_history_db_newest') or '-'}
			({summary.get('route_history_db_total', 0)} {_("total rows")})</td></tr>
	</table>
	"""

	if route_rows:
		html += f"<h2>{_('Navigation Activity (Route History)')}</h2>"
		html += _table_html(
			[_("Date/Time"), _("User"), _("Full Name"), _("Access Type"), _("Item"), _("Document"), _("Route")],
			[
				[
					r.get("accessed_on"),
					r.get("user"),
					r.get("full_name"),
					r.get("access_type"),
					r.get("accessed_item"),
					r.get("document"),
					r.get("route"),
				]
				for r in route_rows
			],
		)
	else:
		html += f"<h2>{_('Navigation Activity (Route History)')}</h2><p>{_('No route history records for selected filters.')}</p>"

	if access_rows:
		html += f"<h2>{_('Print / Export Activity (Access Log)')}</h2>"
		html += _table_html(
			[
				_("Date/Time"),
				_("User"),
				_("Full Name"),
				_("Export From"),
				_("Document"),
				_("File Type"),
				_("Method"),
				_("Page / Format"),
			],
			[
				[
					r.get("accessed_on"),
					r.get("user"),
					r.get("full_name"),
					r.get("export_from"),
					r.get("reference_document"),
					r.get("file_type"),
					r.get("method"),
					r.get("page") or r.get("report_name"),
				]
				for r in access_rows
			],
		)
	else:
		html += f"<h2>{_('Print / Export Activity (Access Log)')}</h2><p>{_('No access log records for selected filters.')}</p>"

	html += "</body></html>"
	return html


def _table_html(headers, rows):
	head = "".join(f"<th>{frappe.utils.escape_html(str(h))}</th>" for h in headers)
	body_rows = []
	for row in rows:
		cells = "".join(
			f"<td>{frappe.utils.escape_html(str(c or ''))}</td>" for c in row
		)
		body_rows.append(f"<tr>{cells}</tr>")
	return f"<table class='data'><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"
