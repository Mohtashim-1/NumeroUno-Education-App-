import io
import json
import zipfile

import frappe
from frappe import _
from frappe.utils import cint, cstr


# scope: student = one doc per student; group = one doc per student group
PDF_CATALOG = [
	{
		"category": "Assessments",
		"key": "rospa_practical",
		"label": "ROSPA Practical Assessment",
		"doctype": "ROSPA Practical Assessment",
		"print_format": "ROSPA Practical Assessment Form",
		"scope": "student",
	},
	{
		"category": "Assessments",
		"key": "off_road_practical",
		"label": "Off Road Practical Assessment",
		"doctype": "Off Road Practical Assessment",
		"print_format": "Off Road Practical Assessment Form",
		"scope": "student",
	},
	{
		"category": "Assessments",
		"key": "rospa_learning_outcome",
		"label": "ROSPA Learning Outcome Assessment",
		"doctype": "ROSPA Learning Outcome Assessment",
		"print_format": "ROSPA Learning Outcome Assessment Form",
		"scope": "student",
	},
	{
		"category": "Assessments",
		"key": "lv_practical",
		"label": "LV Practical Assessment",
		"doctype": "LV Practical Assessment",
		"print_format": "LV Practical Assessment Form",
		"scope": "student",
	},
	{
		"category": "Assessments",
		"key": "english_proficiency",
		"label": "English Proficiency Test",
		"doctype": "English Proficiency Test",
		"print_format": "English Proficiency Test",
		"scope": "student",
	},
	{
		"category": "Assessments",
		"key": "pre_test_adsd",
		"label": "Pre Test ADSD",
		"doctype": "Pre Test ADSD",
		"print_format": "Pre Test ADSD",
		"scope": "student",
	},
	{
		"category": "Assessments",
		"key": "nyc_reassessment",
		"label": "NYC Reassessment Checklist",
		"doctype": "NYC Reassessment Checklist",
		"print_format": "NYC Reassessment Checklist",
		"scope": "student",
	},
	{
		"category": "Results & Certificates",
		"key": "theory_assessment",
		"label": "Theory Assessment",
		"doctype": "Assessment Result",
		"print_format": "Theory Assesment",
		"scope": "student",
	},
	{
		"category": "Results & Certificates",
		"key": "assessment_certificate",
		"label": "Assessment Certificate",
		"doctype": "Assessment Result",
		"print_format": "Assesment Result 1",
		"scope": "student",
	},
	{
		"category": "Results & Certificates",
		"key": "student_card",
		"label": "Student Card",
		"doctype": "Assessment Result",
		"print_format": "Student ATM Card",
		"scope": "student",
	},
	{
		"category": "Results & Certificates",
		"key": "driving_card_adnoc",
		"label": "ADNOC Driving ID",
		"doctype": "Driving Card",
		"print_format": "ADNOC Defensive Safe Driving ID",
		"scope": "student_only",
	},
	{
		"category": "Results & Certificates",
		"key": "driving_card_rospa",
		"label": "ROSPA Driving ID",
		"doctype": "Driving Card",
		"print_format": "ROSPA Defensive Safe Driving ID",
		"scope": "student_only",
	},
	{
		"category": "Group Documents",
		"key": "attendance_sheet",
		"label": "Attendance Sheet",
		"doctype": "Student Group",
		"print_format": "NumeroUno Attendance Sheet",
		"scope": "group",
	},
	{
		"category": "Group Documents",
		"key": "safety_briefing",
		"label": "Safety Briefing",
		"doctype": "Safety Briefing",
		"print_format": "Safety Briefing",
		"scope": "group",
	},
	{
		"category": "Group Documents",
		"key": "assessor_checklist",
		"label": "Assessor Checklist",
		"doctype": "Assessor Checklist",
		"print_format": "Assessor Checklist",
		"scope": "group",
	},
	{
		"category": "Group Documents",
		"key": "course_assessor_checklist",
		"label": "Course Assessor Checklist",
		"doctype": "Course Assessor Checklist",
		"print_format": "Course Assessor Checklist",
		"scope": "group",
	},
]


def _students_in_group(student_group):
	return frappe.get_all(
		"Student Group Student",
		filters={"parent": student_group},
		fields=["student", "student_name"],
		order_by="idx asc",
	)


def _resolve_print_format(doctype, print_format):
	if print_format and frappe.db.exists("Print Format", print_format):
		return print_format
	default = frappe.get_meta(doctype).default_print_format
	if default:
		return default
	row = frappe.get_all(
		"Print Format",
		filters={"doc_type": doctype, "disabled": 0},
		pluck="name",
		limit=1,
	)
	return row[0] if row else None


def _student_filters(student_group=None, student=None):
	filters = {"docstatus": ["<", 2]}
	if student_group:
		filters["student_group"] = student_group
	if student:
		filters["student"] = student
	return filters


def _find_student_docs(source, student_group=None, student=None):
	if not frappe.db.exists("DocType", source["doctype"]):
		return []

	meta = frappe.get_meta(source["doctype"])
	fields = ["name"]
	for fieldname in ("student", "student_group", "student_name", "candidate_name", "docstatus"):
		if meta.has_field(fieldname):
			fields.append(fieldname)

	if source["scope"] == "student_only":
		filters = {"docstatus": ["<", 2]}
		if student:
			filters["student"] = student
		elif student_group:
			students = [row.student for row in _students_in_group(student_group)]
			if not students:
				return []
			filters["student"] = ["in", students]
		else:
			return []
	else:
		filters = _student_filters(student_group, student)

	rows = frappe.get_all(source["doctype"], filters=filters, fields=fields, order_by="modified desc")
	print_format = _resolve_print_format(source["doctype"], source.get("print_format"))
	if not print_format:
		return []

	items = []
	for row in rows:
		student_name = row.get("student_name") or row.get("candidate_name") or row.get("student") or ""
		items.append(
			{
				"id": f"{source['key']}:{row.name}",
				"category": source["category"],
				"key": source["key"],
				"label": source["label"],
				"doctype": source["doctype"],
				"name": row.name,
				"print_format": print_format,
				"student": row.get("student") or "",
				"student_name": student_name,
				"student_group": row.get("student_group") or student_group or "",
				"docstatus": row.docstatus,
				"title": f"{source['label']} — {student_name or row.name}",
			}
		)
	return items


def _find_group_docs(source, student_group):
	if not student_group or not frappe.db.exists("DocType", source["doctype"]):
		return []

	print_format = _resolve_print_format(source["doctype"], source.get("print_format"))
	if not print_format:
		return []

	if source["doctype"] == "Student Group":
		if not frappe.db.exists("Student Group", student_group):
			return []
		return [
			{
				"id": f"{source['key']}:{student_group}",
				"category": source["category"],
				"key": source["key"],
				"label": source["label"],
				"doctype": source["doctype"],
				"name": student_group,
				"print_format": print_format,
				"student": "",
				"student_name": "",
				"student_group": student_group,
				"docstatus": frappe.db.get_value("Student Group", student_group, "docstatus") or 0,
				"title": f"{source['label']} — {student_group}",
			}
		]

	rows = frappe.get_all(
		source["doctype"],
		filters={"student_group": student_group, "docstatus": ["<", 2]},
		fields=["name", "docstatus"],
		order_by="modified desc",
	)
	return [
		{
			"id": f"{source['key']}:{row.name}",
			"category": source["category"],
			"key": source["key"],
			"label": source["label"],
			"doctype": source["doctype"],
			"name": row.name,
			"print_format": print_format,
			"student": "",
			"student_name": "",
			"student_group": student_group,
			"docstatus": row.docstatus,
			"title": f"{source['label']} — {row.name}",
		}
		for row in rows
	]


def get_pdf_catalog():
	return PDF_CATALOG


def _print_format_enabled(print_format):
	if not print_format or not frappe.db.exists("Print Format", print_format):
		return False
	return not cint(frappe.db.get_value("Print Format", print_format, "disabled"))


@frappe.whitelist()
def find_pdfs(student_group=None, student=None):
	student_group = (student_group or "").strip() or None
	student = (student or "").strip() or None
	if not student_group and not student:
		frappe.throw(_("Select a Student Group and/or Student."))

	items = []
	seen = set()
	for source in PDF_CATALOG:
		if not frappe.db.exists("DocType", source["doctype"]):
			continue
		if not _print_format_enabled(source.get("print_format")):
			continue
		if source["scope"] == "group":
			if not student_group:
				continue
			found = _find_group_docs(source, student_group)
		else:
			found = _find_student_docs(source, student_group=student_group, student=student)
		for row in found:
			if row["id"] in seen:
				continue
			seen.add(row["id"])
			items.append(row)

	items.sort(key=lambda row: (row["category"], row["student_name"] or "", row["label"], row["name"]))
	return {
		"count": len(items),
		"items": items,
		"student_group": student_group,
		"student": student,
	}


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def student_query(doctype, txt, searchfield, start, page_len, filters):
	student_group = ((filters or {}).get("student_group") or "").strip()
	if not student_group:
		return frappe.get_all(
			"Student",
			filters={"name": ["like", f"%{txt}%"]},
			fields=["name", "student_name"],
			limit_start=start,
			limit_page_length=page_len,
		)

	return frappe.db.sql(
		"""
		select s.name, s.student_name
		from `tabStudent Group Student` sgs
		inner join `tabStudent` s on s.name = sgs.student
		where sgs.parent = %(student_group)s
		  and (
			s.name like %(txt)s
			or s.student_name like %(txt)s
		  )
		order by sgs.idx asc
		limit %(start)s, %(page_len)s
		""",
		{
			"student_group": student_group,
			"txt": f"%{txt}%",
			"start": start,
			"page_len": page_len,
		},
	)


def _safe_filename(value):
	value = cstr(value or "document").strip()
	for ch in ('/', '\\', ':', '*', '?', '"', '<', '>', '|'):
		value = value.replace(ch, "-")
	return value[:180] or "document"


def _render_pdf(item):
	if not frappe.has_permission(item["doctype"], "print", item["name"]):
		frappe.throw(_("Not permitted to print {0} {1}").format(item["doctype"], item["name"]))
	if not _print_format_enabled(item.get("print_format")):
		frappe.throw(_("Print Format {0} is disabled").format(item.get("print_format")))
	doc = frappe.get_doc(item["doctype"], item["name"])
	return frappe.get_print(
		item["doctype"],
		item["name"],
		print_format=item["print_format"],
		doc=doc,
		as_pdf=True,
		no_letterhead=1,
	)


@frappe.whitelist()
def prepare_download(items, merge=1):
	"""Store selected PDFs in cache and return a short download key."""
	if isinstance(items, str):
		items = json.loads(items)
	if not items:
		frappe.throw(_("Select at least one PDF."))

	key = frappe.generate_hash(length=16)
	frappe.cache().set_value(
		f"student_pdf_bundle:{key}",
		{"items": items, "merge": cint(merge)},
		expires_in_sec=600,
	)
	return key


@frappe.whitelist()
def download_pdfs(key=None, items=None, merge=1):
	if key:
		payload = frappe.cache().get_value(f"student_pdf_bundle:{key}")
		if not payload:
			frappe.throw(_("Download link expired. Please try again."))
		items = payload.get("items") or []
		merge = payload.get("merge", 1)
	elif isinstance(items, str):
		items = json.loads(items)
	if not items:
		frappe.throw(_("Select at least one PDF."))

	rendered = []
	errors = []
	for item in items:
		item = frappe._dict(item)
		try:
			content = _render_pdf(item)
		except Exception as e:
			errors.append(f"{item.get('title') or item.get('name')}: {cstr(e)}")
			continue
		filename = _safe_filename(item.get("title") or f"{item.doctype}-{item.name}") + ".pdf"
		rendered.append((filename, content))

	if not rendered:
		frappe.throw(_("Could not generate any PDFs.<br>{0}").format("<br>".join(errors)))

	if cint(merge):
		from PyPDF2 import PdfMerger

		merger = PdfMerger()
		for filename, content in rendered:
			merger.append(io.BytesIO(content))
		output = io.BytesIO()
		merger.write(output)
		merger.close()
		frappe.local.response.filename = "Student-PDF-Bundle.pdf"
		frappe.local.response.filecontent = output.getvalue()
		frappe.local.response.type = "download"
		return

	buffer = io.BytesIO()
	with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
		used = set()
		for filename, content in rendered:
			name = filename
			counter = 1
			while name in used:
				base = filename.rsplit(".", 1)[0]
				name = f"{base}-{counter}.pdf"
				counter += 1
			used.add(name)
			zf.writestr(name, content)
	buffer.seek(0)
	frappe.local.response.filename = "Student-PDF-Bundle.zip"
	frappe.local.response.filecontent = buffer.getvalue()
	frappe.local.response.type = "download"
