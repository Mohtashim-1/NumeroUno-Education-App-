import frappe
from frappe.utils import cint, today

from numerouno.numerouno.doctype.safety_briefing.safety_briefing import (
	apply_template,
	get_students_for_group,
	get_template_for_briefing_type,
)


BRIEFING_TYPES = [
	"Basic H2S",
	"TBOSIET",
	"TSbB",
	"TFOET",
	"THUET",
	"BOSIET EBS",
	"FOET EBS",
	"HUET EBS",
]


def _serialize_child_rows(rows, fields):
	return [{field: row.get(field) for field in fields} for row in (rows or [])]


def _serialize_doc(doc):
	_ensure_attendee_rows(doc)
	return {
		"name": doc.name,
		"docstatus": doc.docstatus,
		"naming_series": doc.naming_series or "SB-.YYYY.-",
		"briefing_type": doc.briefing_type,
		"form_code": doc.form_code,
		"title": doc.title,
		"briefing_date": doc.briefing_date,
		"student_group": doc.student_group,
		"course": doc.course,
		"date_ff": doc.date_ff,
		"date_fa": doc.date_fa,
		"date_ss": doc.date_ss,
		"date_lb": doc.date_lb,
		"date_huet": doc.date_huet,
		"date_huet_ebs": doc.date_huet_ebs,
		"attendee_signature_mode": doc.attendee_signature_mode,
		"signature_labels": doc.signature_labels,
		"instructor_mode": doc.instructor_mode,
		"instructor_name": doc.instructor_name,
		"instructor_signature": doc.instructor_signature,
		"instructor_date": doc.instructor_date,
		"discussion_points": _serialize_child_rows(
			doc.discussion_points, ("sr_no", "discussion_point", "confirmed")
		),
		"practical_items": _serialize_child_rows(
			doc.practical_items,
			("sr_no", "exercise_group", "activity_detail", "risk_points", "confirmed"),
		),
		"attendees": _serialize_child_rows(
			doc.attendees,
			(
				"learner_name",
				"student",
				"company",
				"signed",
				"sign_col_1",
				"sign_col_2",
				"sign_col_3",
				"sign_col_4",
				"sign_col_5",
			),
		),
		"instructors": _serialize_child_rows(
			doc.instructors, ("instructor_name", "module", "signature")
		),
	}


def _ensure_attendee_rows(doc):
	while len(doc.attendees or []) < 16:
		doc.append("attendees", {})


def _apply_payload(doc, data):
	for field in (
		"naming_series",
		"briefing_type",
		"form_code",
		"title",
		"briefing_date",
		"student_group",
		"course",
		"date_ff",
		"date_fa",
		"date_ss",
		"date_lb",
		"date_huet",
		"date_huet_ebs",
		"attendee_signature_mode",
		"signature_labels",
		"instructor_mode",
		"instructor_name",
		"instructor_signature",
		"instructor_date",
	):
		if field in data:
			doc.set(field, data.get(field))

	doc.discussion_points = []
	for row in data.get("discussion_points") or []:
		doc.append(
			"discussion_points",
			{
				"sr_no": row.get("sr_no"),
				"discussion_point": row.get("discussion_point"),
				"confirmed": cint(row.get("confirmed")),
			},
		)

	doc.practical_items = []
	for row in data.get("practical_items") or []:
		doc.append(
			"practical_items",
			{
				"sr_no": row.get("sr_no"),
				"exercise_group": row.get("exercise_group"),
				"activity_detail": row.get("activity_detail"),
				"risk_points": row.get("risk_points"),
				"confirmed": cint(row.get("confirmed")),
			},
		)

	doc.attendees = []
	for row in data.get("attendees") or []:
		doc.append(
			"attendees",
			{
				"learner_name": row.get("learner_name"),
				"student": row.get("student"),
				"company": row.get("company"),
				"signed": row.get("signed"),
				"sign_col_1": cint(row.get("sign_col_1")),
				"sign_col_2": cint(row.get("sign_col_2")),
				"sign_col_3": cint(row.get("sign_col_3")),
				"sign_col_4": cint(row.get("sign_col_4")),
				"sign_col_5": cint(row.get("sign_col_5")),
			},
		)
	_ensure_attendee_rows(doc)

	doc.instructors = []
	for row in data.get("instructors") or []:
		doc.append(
			"instructors",
			{
				"instructor_name": row.get("instructor_name"),
				"module": row.get("module"),
				"signature": row.get("signature"),
			},
		)


@frappe.whitelist()
def get_briefing_types():
	return BRIEFING_TYPES


@frappe.whitelist()
def get_form_data(docname=None, briefing_type=None, student_group=None):
	docname = (docname or "").strip()
	student_group = (student_group or "").strip() or None

	if docname:
		doc = frappe.get_doc("Safety Briefing", docname)
	elif briefing_type:
		doc = frappe.new_doc("Safety Briefing")
		doc.briefing_type = briefing_type
		template = get_template_for_briefing_type(briefing_type)
		apply_template(doc, template)
		doc.briefing_date = today()
		if student_group:
			doc.student_group = student_group
			doc.attendees = []
			for row in get_students_for_group(student_group):
				doc.append("attendees", row)
			_ensure_attendee_rows(doc)
	else:
		frappe.throw("Document name or briefing type is required")

	return _serialize_doc(doc)


@frappe.whitelist()
def save_form_data(data):
	data = frappe.parse_json(data)
	docname = (data.get("name") or "").strip()

	if docname:
		doc = frappe.get_doc("Safety Briefing", docname)
		if doc.docstatus == 1:
			frappe.throw("Submitted Safety Briefing cannot be edited")
	else:
		doc = frappe.new_doc("Safety Briefing")

	_apply_payload(doc, data)
	doc.save()
	return _serialize_doc(doc)


@frappe.whitelist()
def submit_form(docname):
	doc = frappe.get_doc("Safety Briefing", docname)
	if doc.docstatus == 0:
		doc.submit()
	return {"name": doc.name, "docstatus": doc.docstatus}


def _doc_for_template(data):
	doc = frappe._dict(data)
	for table in ("discussion_points", "practical_items", "attendees", "instructors"):
		doc[table] = [frappe._dict(row) for row in doc.get(table) or []]
	return doc


def _render_form_html(doc_data):
	doc = _doc_for_template(doc_data)
	return frappe.render_template(
		"numerouno/numerouno/print_format/safety_briefing/safety_briefing.html",
		{"doc": doc},
	)


@frappe.whitelist()
def get_form_html(docname=None, briefing_type=None, student_group=None):
	doc_data = get_form_data(docname=docname, briefing_type=briefing_type, student_group=student_group)
	return {"doc": doc_data, "html": _render_form_html(doc_data)}
