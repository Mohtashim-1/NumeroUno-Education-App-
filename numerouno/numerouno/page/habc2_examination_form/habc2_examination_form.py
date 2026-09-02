import frappe
from frappe.utils import cint, getdate, today

from numerouno.numerouno.doctype.habc2_examination_declaration.habc2_examination_declaration import (
	DEFAULT_CENTRE_NO,
	_split_name,
	group_defaults,
	paginate_learners,
)
from numerouno.numerouno.utils.signatures import is_empty_signature, resolve_learner_signature

DOCTYPE = "HABC2 Examination Declaration"
TEMPLATE = "numerouno/numerouno/print_format/habc2_examination_declaration/habc2_examination_declaration.html"

PARENT_FIELDS = (
	"naming_series",
	"student_group",
	"course",
	"centre_name",
	"centre_number",
	"nominated_tutor",
	"nominated_tutor_name",
	"tutor_number",
	"examination_venue",
	"course_exam_id",
	"number_of_learners",
	"qualification_unit_title",
	"examination_date",
	"exam_start_time",
	"exam_end_time",
	"course_from",
	"course_to",
	"invigilator_name",
	"invigilator_position",
	"invigilator_signature",
	"invigilator_date",
	"comments",
)


def _as_date(value):
	if not value:
		return ""
	try:
		return str(getdate(value))
	except Exception:
		return str(value)


def _as_time(value):
	if value in (None, ""):
		return ""
	text = str(value)
	if ":" in text:
		parts = text.split(":")
		return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"
	return text


def _serialize_row(row, student_group=None):
	signature = resolve_learner_signature(row.get("student"), student_group, row.get("signature"))
	names = row.get("learner_names") or ""
	surname = row.get("learner_surname") or ""
	if row.get("student"):
		names, surname = _split_name(row.get("student"))
	return {
		"sr_no": row.get("sr_no"),
		"student": row.get("student") or "",
		"learner_names": names,
		"learner_surname": surname,
		"signature": signature or "",
		"date_of_birth": _as_date(row.get("date_of_birth")),
		"id_type": row.get("id_type") or "",
		"telephone": row.get("telephone") or "",
		"retake": cint(row.get("retake")),
		"gender": row.get("gender") or "",
	}


def _serialize_doc(doc):
	_ensure_learner_signatures(doc)
	_ensure_learner_names(doc)
	learners = [_serialize_row(row, doc.student_group) for row in (doc.learners or [])]
	pages = paginate_learners(learners)
	data = {field: doc.get(field) for field in PARENT_FIELDS}
	data.update(
		{
			"name": doc.name,
			"docstatus": doc.docstatus,
			"examination_date": _as_date(doc.examination_date),
			"invigilator_date": _as_date(doc.invigilator_date),
			"course_from": _as_date(doc.course_from),
			"course_to": _as_date(doc.course_to),
			"exam_start_time": _as_time(doc.exam_start_time),
			"exam_end_time": _as_time(doc.exam_end_time),
			"learners": learners,
			"learner_pages": pages,
		}
	)
	return data


def _ensure_learner_names(doc):
	if cint(doc.docstatus) != 0:
		return
	for row in doc.learners or []:
		if not row.get("student"):
			continue
		names, surname = _split_name(row.get("student"))
		if (row.get("learner_names") or "") == names and (row.get("learner_surname") or "") == surname:
			continue
		row.learner_names = names
		row.learner_surname = surname
		if row.get("name"):
			frappe.db.set_value(
				"HABC2 Learner",
				row.name,
				{"learner_names": names, "learner_surname": surname},
				update_modified=False,
			)


def _ensure_learner_signatures(doc):
	changed = False
	for row in doc.learners or []:
		if not row.get("student"):
			continue
		sig = resolve_learner_signature(row.get("student"), doc.student_group, row.get("signature"))
		if sig and is_empty_signature(row.get("signature")):
			row.signature = sig
			changed = True
			if row.get("name") and cint(doc.docstatus) == 0:
				frappe.db.set_value("HABC2 Learner", row.name, "signature", sig, update_modified=False)
	return changed


def _apply_payload(doc, data):
	for field in PARENT_FIELDS:
		if field in data:
			doc.set(field, data.get(field))
	doc.learners = []
	for row in data.get("learners") or []:
		if not (
			row.get("student")
			or row.get("learner_names")
			or row.get("learner_surname")
			or row.get("signature")
			or row.get("telephone")
			or row.get("id_type")
		):
			continue
		doc.append(
			"learners",
			{
				"sr_no": row.get("sr_no"),
				"student": row.get("student") or None,
				"learner_names": row.get("learner_names") or "",
				"learner_surname": row.get("learner_surname") or "",
				"signature": row.get("signature") or "",
				"date_of_birth": row.get("date_of_birth") or None,
				"id_type": row.get("id_type") or "",
				"telephone": row.get("telephone") or "",
				"retake": cint(row.get("retake")),
				"gender": row.get("gender") or "",
			},
		)


def _get_or_create(student_group):
	student_group = (student_group or "").strip()
	if not student_group:
		frappe.throw("Student Group is required")

	existing = frappe.db.get_value(
		DOCTYPE,
		{"student_group": student_group, "docstatus": ["<", 2]},
		"name",
	)
	if existing:
		return _fill_empty_draft(frappe.get_doc(DOCTYPE, existing), student_group)

	defaults = group_defaults(student_group)
	doc = frappe.new_doc(DOCTYPE)
	for field, value in defaults.items():
		if field == "learners":
			continue
		doc.set(field, value)
	if not doc.examination_date:
		doc.examination_date = today()
	if not doc.invigilator_date:
		doc.invigilator_date = today()
	for row in defaults.get("learners") or []:
		doc.append("learners", row)
	doc.insert(ignore_permissions=True)
	return doc


def _fill_empty_draft(doc, student_group):
	if cint(doc.docstatus) != 0:
		return doc
	has_learners = any(
		(row.student or row.learner_names or row.learner_surname) for row in (doc.learners or [])
	)
	if has_learners:
		return doc
	defaults = group_defaults(student_group)
	for field, value in defaults.items():
		if field == "learners":
			continue
		if value and not doc.get(field):
			doc.set(field, value)
	doc.learners = []
	for row in defaults.get("learners") or []:
		doc.append("learners", row)
	doc.save(ignore_permissions=True)
	return doc


@frappe.whitelist()
def get_form_data(docname=None, student_group=None):
	docname = (docname or "").strip()
	student_group = (student_group or "").strip() or None
	if docname:
		doc = frappe.get_doc(DOCTYPE, docname)
	elif student_group:
		doc = _get_or_create(student_group)
	else:
		frappe.throw("Select a student group to open the HABC2 form.")
	if not doc.centre_number:
		doc.centre_number = DEFAULT_CENTRE_NO
		if doc.name and cint(doc.docstatus) == 0:
			doc.db_set("centre_number", DEFAULT_CENTRE_NO, update_modified=False)
	return _serialize_doc(doc)


def _doc_for_template(data):
	doc = frappe._dict(data)
	pages = []
	for page in data.get("learner_pages") or []:
		pages.append([frappe._dict(row) for row in page])
	doc.learner_pages = pages
	doc.learners = [frappe._dict(row) for row in data.get("learners") or []]
	doc.get_formatted = lambda field: doc.get(field) or ""
	return doc


@frappe.whitelist()
def get_form_html(docname=None, student_group=None):
	doc_data = get_form_data(docname=docname, student_group=student_group)
	html = frappe.render_template(TEMPLATE, {"doc": _doc_for_template(doc_data), "editable": 1})
	return {"doc": doc_data, "html": html}


@frappe.whitelist()
def save_form_data(data):
	data = frappe.parse_json(data)
	docname = (data.get("name") or "").strip()
	if docname:
		doc = frappe.get_doc(DOCTYPE, docname)
		if doc.docstatus == 1:
			frappe.throw("Submitted form cannot be edited")
	else:
		doc = frappe.new_doc(DOCTYPE)
	_apply_payload(doc, data)
	doc.save()
	return _serialize_doc(doc)


@frappe.whitelist()
def submit_form(docname):
	doc = frappe.get_doc(DOCTYPE, docname)
	if doc.docstatus == 0:
		doc.submit()
	return {"name": doc.name, "docstatus": doc.docstatus}


@frappe.whitelist()
def cancel_form(docname):
	doc = frappe.get_doc(DOCTYPE, docname)
	if doc.docstatus == 2:
		return {"name": doc.name, "docstatus": doc.docstatus}
	if doc.docstatus != 1:
		frappe.throw("Only a submitted HABC2 Examination Declaration can be cancelled")
	doc.cancel()
	return {"name": doc.name, "docstatus": doc.docstatus}


@frappe.whitelist()
def amend_form(docname):
	doc = frappe.get_doc(DOCTYPE, docname)
	if doc.docstatus != 2:
		frappe.throw("Only cancelled HABC2 Examination Declarations can be amended")
	amended = frappe.copy_doc(doc)
	amended.amended_from = doc.name
	amended.insert()
	return _serialize_doc(amended)
