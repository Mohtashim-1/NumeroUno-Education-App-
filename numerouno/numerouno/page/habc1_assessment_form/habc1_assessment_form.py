import frappe
from frappe.utils import cint, getdate, today

from numerouno.numerouno.doctype.habc1_assessment_pack.habc1_assessment_pack import (
	DEFAULT_CENTRE_NO,
	group_defaults,
	pad_referrals,
	paginate_learners,
)

DOCTYPE = "HABC1 Assessment Pack"
TEMPLATE = "numerouno/numerouno/print_format/habc1_assessment_pack/habc1_assessment_pack.html"

PARENT_FIELDS = (
	"naming_series",
	"student_group",
	"course",
	"form_title",
	"centre_name",
	"venue_address",
	"telephone_no",
	"centre_number",
	"tutor",
	"tutor_name",
	"assessor",
	"assessor_name",
	"iqa_name",
	"course_identification_no",
	"course_start_date",
	"course_finish_date",
	"blended_learning",
	"tutor_signature",
	"tutor_date",
	"assessor_signature",
	"assessor_date",
)


def _as_date(value):
	if not value:
		return ""
	try:
		return str(getdate(value))
	except Exception:
		return str(value)


def _serialize_row(row):
	return {
		"sr_no": row.get("sr_no"),
		"student": row.get("student") or "",
		"learner_name": row.get("learner_name") or "",
		"date_of_birth": _as_date(row.get("date_of_birth")),
		"telephone": row.get("telephone") or "",
		"gender": row.get("gender") or "",
		"refer": cint(row.get("refer")),
	}


def _serialize_ref(row):
	return {
		"learner_name": row.get("learner_name") or "",
		"criteria": row.get("criteria") or "",
		"rationale": row.get("rationale") or "",
	}


def _serialize_doc(doc):
	from numerouno.numerouno.utils.signatures import resolve_signature_url

	_ensure_instructor_signatures(doc)
	learners = [_serialize_row(row) for row in (doc.learners or [])]
	referrals = [_serialize_ref(row) for row in (doc.referrals or [])]
	data = {field: doc.get(field) for field in PARENT_FIELDS}
	data.update(
		{
			"name": doc.name,
			"docstatus": doc.docstatus,
			"tutor_signature_url": resolve_signature_url(doc.tutor_signature),
			"assessor_signature_url": resolve_signature_url(doc.assessor_signature),
			"blended_learning": cint(doc.blended_learning),
			"course_start_date": _as_date(doc.course_start_date),
			"course_finish_date": _as_date(doc.course_finish_date),
			"tutor_date": _as_date(doc.tutor_date),
			"assessor_date": _as_date(doc.assessor_date),
			"learners": learners,
			"learner_pages": paginate_learners(learners),
			"referrals": referrals,
			"referral_rows": pad_referrals(referrals),
		}
	)
	return data


def _apply_payload(doc, data):
	for field in PARENT_FIELDS:
		if field in data:
			value = data.get(field)
			if field == "blended_learning":
				value = cint(value)
			doc.set(field, value)
	doc.learners = []
	for row in data.get("learners") or []:
		if not (row.get("student") or row.get("learner_name") or row.get("telephone")):
			continue
		doc.append(
			"learners",
			{
				"sr_no": row.get("sr_no"),
				"student": row.get("student") or None,
				"learner_name": (row.get("learner_name") or "").upper(),
				"date_of_birth": row.get("date_of_birth") or None,
				"telephone": row.get("telephone") or "",
				"gender": row.get("gender") or "",
				"refer": cint(row.get("refer")),
			},
		)
	doc.referrals = []
	for row in data.get("referrals") or []:
		if not (row.get("learner_name") or row.get("criteria") or row.get("rationale")):
			continue
		doc.append("referrals", row)


def _get_or_create(student_group):
	student_group = (student_group or "").strip()
	if not student_group:
		frappe.throw("Student Group is required")
	existing = frappe.db.get_value(DOCTYPE, {"student_group": student_group, "docstatus": ["<", 2]}, "name")
	if existing:
		return _fill_empty_draft(frappe.get_doc(DOCTYPE, existing), student_group)
	defaults = group_defaults(student_group)
	doc = frappe.new_doc(DOCTYPE)
	for field, value in defaults.items():
		if field in ("learners", "referrals"):
			continue
		doc.set(field, value)
	for row in defaults.get("learners") or []:
		doc.append("learners", row)
	doc.insert(ignore_permissions=True)
	return doc


def _fill_empty_draft(doc, student_group):
	if cint(doc.docstatus) != 0:
		return doc
	has_learners = any((row.student or row.learner_name) for row in (doc.learners or []))
	if has_learners:
		return doc
	defaults = group_defaults(student_group)
	for field, value in defaults.items():
		if field in ("learners", "referrals"):
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
		frappe.throw("Select a student group to open the HABC1 form.")
	_ensure_instructor_signatures(doc, persist=True)
	if not doc.centre_number:
		doc.centre_number = DEFAULT_CENTRE_NO
		if doc.name and cint(doc.docstatus) == 0:
			doc.db_set("centre_number", DEFAULT_CENTRE_NO, update_modified=False)
	return _serialize_doc(doc)


def _ensure_instructor_signatures(doc, persist=False):
	from numerouno.numerouno.utils.signatures import get_instructor_signature, resolve_signature_url

	changed = {}
	if doc.tutor:
		if not doc.tutor_name:
			doc.tutor_name = frappe.db.get_value("Instructor", doc.tutor, "instructor_name") or doc.tutor_name
		sig = get_instructor_signature(doc.tutor)
		if sig and doc.tutor_signature != sig:
			doc.tutor_signature = sig
			changed["tutor_signature"] = sig

	if doc.assessor:
		if not doc.assessor_name:
			doc.assessor_name = frappe.db.get_value("Instructor", doc.assessor, "instructor_name") or doc.assessor_name
		sig = get_instructor_signature(doc.assessor)
		if sig and doc.assessor_signature != sig:
			doc.assessor_signature = sig
			changed["assessor_signature"] = sig
	elif doc.tutor_signature and doc.assessor_signature != doc.tutor_signature:
		doc.assessor_signature = doc.tutor_signature
		changed["assessor_signature"] = doc.tutor_signature

	if changed and persist and doc.name and cint(doc.docstatus) == 0:
		for field, value in changed.items():
			doc.db_set(field, value, update_modified=False)

	doc.tutor_signature_url = resolve_signature_url(doc.tutor_signature)
	doc.assessor_signature_url = resolve_signature_url(doc.assessor_signature)
	return doc


def _doc_for_template(data):
	from numerouno.numerouno.utils.signatures import resolve_signature_url

	doc = frappe._dict(data)
	doc.tutor_signature_url = doc.get("tutor_signature_url") or resolve_signature_url(doc.get("tutor_signature"))
	doc.assessor_signature_url = doc.get("assessor_signature_url") or resolve_signature_url(doc.get("assessor_signature"))
	doc.learner_pages = [[frappe._dict(row) for row in page] for page in data.get("learner_pages") or []]
	doc.learners = [frappe._dict(row) for row in data.get("learners") or []]
	doc.referral_rows = [frappe._dict(row) for row in data.get("referral_rows") or []]
	doc.referrals = [frappe._dict(row) for row in data.get("referrals") or []]
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
	_ensure_instructor_signatures(doc)
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
		frappe.throw("Only a submitted HABC1 Assessment Pack can be cancelled")
	doc.cancel()
	return {"name": doc.name, "docstatus": doc.docstatus}


@frappe.whitelist()
def amend_form(docname):
	doc = frappe.get_doc(DOCTYPE, docname)
	if doc.docstatus != 2:
		frappe.throw("Only cancelled HABC1 Assessment Packs can be amended")
	amended = frappe.copy_doc(doc)
	amended.amended_from = doc.name
	amended.insert()
	return _serialize_doc(amended)
