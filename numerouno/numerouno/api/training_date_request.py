# Copyright (c) 2026, NumeroUNO and contributors
# License: MIT

"""Training Date Negotiation — Certificate Portal (training requesters) + coordinator desk."""

from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import cint, formatdate, getdate, today

from numerouno.numerouno.doctype.training_date_request.training_date_request import (
	notify_customer_status,
)


def _normalize_customer_text(value):
	if not value:
		return None
	return " ".join(str(value).split())


def _customer_names_for_user(user: str | None = None) -> list[str]:
	"""Resolve Customer docnames linked to the logged-in desk user (same logic as certificate portal)."""
	user = user or frappe.session.user
	if not user or user == "Guest":
		return []

	names: list[str] = []

	def add(name):
		if name and name not in names:
			names.append(name)

	for row in frappe.get_all("Customer", filters={"owner": user}, fields=["name"]):
		add(row.name)

	user_email = frappe.db.get_value("User", user, "email")
	if user_email:
		for row in frappe.get_all("Customer", filters={"email_id": user_email}, fields=["name"]):
			add(row.name)

		contact_names = [
			ce.parent
			for ce in frappe.get_all(
				"Contact Email", filters={"email_id": user_email}, fields=["parent"]
			)
		]
		old = frappe.db.get_value("Contact", {"email_id": user_email}, "name")
		if old and old not in contact_names:
			contact_names.append(old)

		if contact_names:
			links = frappe.get_all(
				"Dynamic Link",
				filters={
					"link_doctype": "Customer",
					"parenttype": "Contact",
					"parent": ("in", contact_names),
				},
				fields=["link_name"],
			)
			for link in links:
				add(link.link_name)

	return names


def _require_requester_customer() -> dict:
	"""Training requester on Certificate Portal (desk login)."""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Please sign in to the Certificate Portal."), frappe.PermissionError)

	roles = set(frappe.get_roles(user))
	is_staff = bool(
		roles.intersection(
			{
				"System Manager",
				"Administrator",
				"Training Coordinator",
				"Academics User",
				"Education Manager",
				"Sales User",
				"Sales Manager",
			}
		)
		or user == "Administrator"
	)

	customers = _customer_names_for_user(user)
	# Staff can still submit on behalf of a customer when explicitly passed;
	# for listing, staff sees all unless filtered.
	email = frappe.db.get_value("User", user, "email") or user
	full_name = frappe.db.get_value("User", user, "full_name") or email

	primary = customers[0] if customers else None
	customer_name = (
		frappe.db.get_value("Customer", primary, "customer_name") if primary else None
	)

	return frappe._dict(
		{
			"user": user,
			"email": email,
			"full_name": full_name,
			"customers": customers,
			"customer": primary,
			"customer_name": customer_name,
			"is_staff": is_staff,
		}
	)


def _require_coordinator():
	user = frappe.session.user
	roles = set(frappe.get_roles(user))
	allowed = {
		"System Manager",
		"Administrator",
		"Training Coordinator",
		"Academics User",
		"Education Manager",
		"Sales User",
		"Sales Manager",
	}
	if user == "Administrator" or roles.intersection(allowed):
		return
	frappe.throw(_("Only coordinators can perform this action."), frappe.PermissionError)


def _serialize(doc) -> dict:
	candidates = []
	for row in doc.get("candidates") or []:
		candidates.append(
			{
				"full_name": row.full_name,
				"date_of_birth": row.date_of_birth,
				"date_of_birth_fmt": formatdate(row.date_of_birth) if row.date_of_birth else "",
				"id_number": row.id_number or "",
				"contact_number": row.contact_number or "",
				"email": row.email or "",
				"id_attachment": row.id_attachment or "",
			}
		)
	return {
		"name": doc.name,
		"status": doc.status,
		"customer": doc.customer,
		"customer_name": doc.customer_name,
		"course": doc.course,
		"course_name": doc.course_name or doc.course,
		"preferred_date": doc.preferred_date,
		"preferred_date_fmt": formatdate(doc.preferred_date) if doc.preferred_date else "",
		"preferred_batch": getattr(doc, "preferred_batch", None) or "",
		"po_number": getattr(doc, "po_number", None) or "",
		"po_attachment": getattr(doc, "po_attachment", None) or "",
		"proposed_date": doc.proposed_date,
		"proposed_date_fmt": formatdate(doc.proposed_date) if doc.proposed_date else "",
		"confirmed_date": doc.confirmed_date,
		"confirmed_date_fmt": formatdate(doc.confirmed_date) if doc.confirmed_date else "",
		"participants": cint(doc.participants) or len(candidates) or 1,
		"candidates": candidates,
		"customer_notes": doc.customer_notes or "",
		"coordinator_notes": doc.coordinator_notes or "",
		"contact_email": doc.contact_email or "",
		"contact_name": doc.contact_name or "",
		"contact_phone": doc.contact_phone or "",
		"posting_date_fmt": formatdate(doc.posting_date) if doc.posting_date else "",
		"student_group": doc.student_group or "",
		"course_schedule": doc.course_schedule or "",
		"can_confirm_proposal": doc.status == "Proposed" and bool(doc.proposed_date),
		"can_request_review": doc.status == "Proposed",
		"is_open": doc.status == "Open",
		"is_confirmed": doc.status == "Confirmed",
	}


def _academic_year_for_date(schedule_date):
	"""Pick Academic Year covering the confirmed date (fallback to Education Settings)."""
	d = getdate(schedule_date)
	rows = frappe.db.sql(
		"""
		select name from `tabAcademic Year`
		where year_start_date <= %(d)s and year_end_date >= %(d)s
		order by year_start_date desc
		limit 1
		""",
		{"d": d},
		as_dict=True,
	)
	if rows:
		return rows[0].name
	current = frappe.db.get_single_value("Education Settings", "current_academic_year")
	if current and frappe.db.exists("Academic Year", current):
		return current
	latest = frappe.get_all("Academic Year", order_by="name desc", limit=1, pluck="name")
	return latest[0] if latest else None


def _unique_student_group_name(base: str) -> str:
	name = (base or "Training Group").strip()[:120]
	if not frappe.db.exists("Student Group", name):
		return name
	for i in range(2, 50):
		candidate = f"{name} ({i})"[:140]
		if not frappe.db.exists("Student Group", candidate):
			return candidate
	return f"{name}-{frappe.generate_hash(length=6)}"


BATCH_OPTIONS = (
	"Morning Batch (8:00 AM)",
	"Afternoon Batch (1:00 PM)",
	"Evening Batch (5:00 PM)",
)

BATCH_PERIODS = {
	"Morning Batch (8:00 AM)": {
		"key": "morning",
		"label": "Morning Batch (8:00 AM)",
		"from_time": "08:00:00",
		"to_time": "12:00:00",
	},
	"Afternoon Batch (1:00 PM)": {
		"key": "afternoon",
		"label": "Afternoon Batch (1:00 PM)",
		"from_time": "13:00:00",
		"to_time": "17:00:00",
	},
	"Evening Batch (5:00 PM)": {
		"key": "evening",
		"label": "Evening Batch (5:00 PM)",
		"from_time": "17:00:00",
		"to_time": "21:00:00",
	},
}


def _batch_period(batch: str | None) -> dict:
	batch = (batch or "").strip()
	if batch in BATCH_PERIODS:
		return BATCH_PERIODS[batch]
	# Fallback morning if older requests have no batch
	return BATCH_PERIODS[BATCH_OPTIONS[0]]


def _require_valid_batch(batch: str | None) -> str:
	batch = (batch or "").strip()
	if batch not in BATCH_PERIODS:
		frappe.throw(
			_("Please select a batch: Morning (8:00 AM), Afternoon (1:00 PM), or Evening (5:00 PM).")
		)
	return batch


def _relink_portal_file(file_url: str | None, doctype: str, docname: str):
	"""Attach a previously uploaded File (by URL) to the Training Date Request."""
	file_url = (file_url or "").strip()
	if not file_url or not docname:
		return
	file_name = frappe.db.get_value("File", {"file_url": file_url}, "name")
	if not file_name:
		return
	frappe.db.set_value(
		"File",
		file_name,
		{
			"attached_to_doctype": doctype,
			"attached_to_name": docname,
		},
		update_modified=False,
	)


def _validate_calendar_session(cs_doc):
	"""Light validation for calendar slots created from date requests (no instructor yet)."""
	label = cs_doc.course or "Training Session"
	cs_doc.title = f"{label} (instructor TBD)"
	if cs_doc.from_time and cs_doc.to_time and cs_doc.from_time > cs_doc.to_time:
		frappe.throw(_("From Time cannot be greater than To Time."))


def _sync_confirmed_to_training_calendar(doc) -> dict:
	"""Create Student Group + Course Schedule when a request is Confirmed.

	Instructor and room are left blank — coordinator assigns them later on the
	Training Calendar. Idempotent: skips if course_schedule already linked.
	"""
	if doc.course_schedule and frappe.db.exists("Course Schedule", doc.course_schedule):
		return {
			"student_group": doc.student_group,
			"course_schedule": doc.course_schedule,
			"created": False,
		}

	confirmed = doc.confirmed_date
	if not confirmed:
		frappe.throw(_("Confirmed date is required before adding to the training calendar."))
	if not doc.course:
		frappe.throw(_("Course is required before adding to the training calendar."))

	academic_year = _academic_year_for_date(confirmed)
	if not academic_year:
		frappe.throw(_("No Academic Year found. Please create one before confirming dates."))

	sg_name = doc.student_group
	if not sg_name or not frappe.db.exists("Student Group", sg_name):
		course_label = (doc.course_name or doc.course or "Course").strip()
		cust_label = (doc.customer_name or doc.customer or "").strip()
		base = f"{course_label} — {formatdate(confirmed)}"
		if cust_label:
			base = f"{base} — {cust_label}"
		base = f"{base} [{doc.name}]"

		sg = frappe.new_doc("Student Group")
		sg.student_group_name = _unique_student_group_name(base)
		sg.academic_year = academic_year
		sg.group_based_on = "Course"
		sg.course = doc.course
		sg.max_strength = cint(doc.participants) or len(doc.get("candidates") or []) or 0
		if sg.meta.has_field("custom_customer"):
			sg.custom_customer = doc.customer
		if sg.meta.has_field("from_date"):
			sg.from_date = confirmed
		if sg.meta.has_field("to_date"):
			sg.to_date = confirmed
		if sg.meta.has_field("custom_from_date"):
			sg.custom_from_date = confirmed
		if sg.meta.has_field("custom_to_date"):
			sg.custom_to_date = confirmed
		sg.flags.ignore_permissions = True
		sg.flags.ignore_mandatory = True
		sg.insert(ignore_permissions=True)
		sg_name = sg.name

	period = _batch_period(getattr(doc, "preferred_batch", None))
	cs = frappe.new_doc("Course Schedule")
	cs.student_group = sg_name
	cs.course = doc.course
	cs.schedule_date = getdate(confirmed)
	cs.from_time = period["from_time"]
	cs.to_time = period["to_time"]
	# instructor + room assigned later manually
	cs.flags.ignore_permissions = True
	cs.flags.ignore_mandatory = True
	cs.validate = lambda: _validate_calendar_session(cs)
	cs.insert(ignore_permissions=True)

	doc.db_set("student_group", sg_name, update_modified=False)
	doc.db_set("course_schedule", cs.name, update_modified=False)
	doc.student_group = sg_name
	doc.course_schedule = cs.name

	return {
		"student_group": sg_name,
		"course_schedule": cs.name,
		"created": True,
		"batch": period["label"],
	}


def _get_owned(name: str, session) -> "frappe.model.document.Document":
	if not frappe.db.exists("Training Date Request", name):
		frappe.throw(_("Request not found."), frappe.DoesNotExistError)
	doc = frappe.get_doc("Training Date Request", name)
	if session.is_staff:
		return doc
	if doc.customer not in (session.customers or []):
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	return doc


def _parse_candidates(candidates, require_attachment: bool = False) -> list[dict]:
	if isinstance(candidates, str):
		candidates = json.loads(candidates or "[]")
	if not isinstance(candidates, list):
		frappe.throw(_("Candidates must be a list."))
	rows = []
	for i, raw in enumerate(candidates, start=1):
		if not isinstance(raw, dict):
			frappe.throw(_("Invalid candidate row #{0}.").format(i))
		full_name = (raw.get("full_name") or "").strip()
		id_number = (raw.get("id_number") or "").strip()
		date_of_birth = raw.get("date_of_birth") or None
		contact_number = (raw.get("contact_number") or "").strip()
		email = (raw.get("email") or "").strip()
		id_attachment = (raw.get("id_attachment") or "").strip()
		if not full_name:
			frappe.throw(_("Candidate #{0}: Full Name is required.").format(i))
		if not id_number:
			frappe.throw(_("Candidate #{0}: Emirates ID / Passport No. is required.").format(i))
		if not date_of_birth:
			frappe.throw(_("Candidate #{0}: Date of Birth is required.").format(i))
		if not contact_number:
			frappe.throw(_("Candidate #{0}: Contact Number is required.").format(i))
		if not email:
			frappe.throw(_("Candidate #{0}: Email is required.").format(i))
		if require_attachment and not id_attachment:
			frappe.throw(
				_("Candidate #{0}: Please attach the ID document (upload a file, not a link).").format(i)
			)
		if id_attachment.startswith("http://") or id_attachment.startswith("https://"):
			if "/files/" not in id_attachment and "/private/files/" not in id_attachment:
				frappe.throw(
					_("Candidate #{0}: Attach the ID file from your device — do not paste an external link.").format(
						i
					)
				)
		rows.append(
			{
				"full_name": full_name,
				"date_of_birth": date_of_birth,
				"id_number": id_number,
				"contact_number": contact_number,
				"email": email,
				"id_attachment": id_attachment or None,
			}
		)
	if not rows:
		frappe.throw(_("Please add at least one candidate."))
	return rows


@frappe.whitelist()
def get_courses_for_portal(txt=None):
	"""Active courses for the date-request picker (optional search text)."""
	_require_requester_customer()
	filters = {}
	if frappe.get_meta("Course").has_field("disabled"):
		filters["disabled"] = 0
	txt = (txt or "").strip()
	or_filters = None
	if txt:
		or_filters = [
			["name", "like", f"%{txt}%"],
			["course_name", "like", f"%{txt}%"],
		]
	rows = frappe.get_all(
		"Course",
		filters=filters,
		or_filters=or_filters,
		fields=["name", "course_name"],
		order_by="course_name asc",
		limit_page_length=50 if txt else 500,
	)
	return [{"name": r.name, "course_name": r.course_name or r.name} for r in rows if r.name]


def _normalize_id_number(value: str | None) -> str:
	"""Normalize Emirates ID / Passport for matching (strip spaces, dashes, slashes)."""
	if not value:
		return ""
	return "".join(ch for ch in str(value).strip().upper() if ch.isalnum())


@frappe.whitelist()
def list_saved_candidates(txt=None):
	"""Previous candidates/students for this customer — pick from dropdown next booking.

	Identity key is Emirates ID / Passport Number (normalized). One person = one option.
	Sources: prior Training Date Request candidates + Student records linked to customer.
	"""
	session = _require_requester_customer()
	customers = session.customers or []
	if not customers:
		return []

	txt = (txt or "").strip()
	params = {"customers": customers}
	extra = ""
	if txt:
		extra = " and (c.full_name like %(txt)s or ifnull(c.id_number,'') like %(txt)s)"
		params["txt"] = f"%{txt}%"

	# From earlier date requests (portal-created candidates)
	tdr_rows = frappe.db.sql(
		f"""
		select
			c.full_name,
			c.id_number,
			c.date_of_birth,
			c.contact_number,
			c.email,
			c.id_attachment,
			p.modified as last_used
		from `tabTraining Date Request Candidate` c
		inner join `tabTraining Date Request` p on p.name = c.parent
		where p.customer in %(customers)s
		  and ifnull(c.full_name, '') != ''
		  and ifnull(c.id_number, '') != ''
		  {extra}
		order by p.modified desc
		limit 500
		""",
		params,
		as_dict=True,
	)

	# From Student master (once staff/customer created them) — match by customer + EID
	student_rows = []
	if frappe.get_meta("Student").has_field("custom_eid_no") and frappe.get_meta("Student").has_field(
		"customer_name"
	):
		stu_extra = ""
		stu_params = {"customers": customers}
		if txt:
			stu_extra = """
				and (
					ifnull(s.student_name,'') like %(txt)s
					or ifnull(s.first_name,'') like %(txt)s
					or ifnull(s.custom_eid_no,'') like %(txt)s
				)
			"""
			stu_params["txt"] = f"%{txt}%"
		phone_expr = "s.student_mobile_number"
		if frappe.get_meta("Student").has_field("custom_phone"):
			phone_expr = "ifnull(nullif(s.student_mobile_number,''), s.custom_phone)"
		student_rows = frappe.db.sql(
			f"""
			select
				ifnull(nullif(s.student_name,''), trim(concat(ifnull(s.first_name,''),' ',ifnull(s.last_name,'')))) as full_name,
				s.custom_eid_no as id_number,
				s.date_of_birth,
				{phone_expr} as contact_number,
				s.student_email_id as email,
				s.name as student,
				s.modified as last_used
			from `tabStudent` s
			where s.customer_name in %(customers)s
			  and ifnull(s.custom_eid_no, '') != ''
			  and ifnull(s.enabled, 1) = 1
			  {stu_extra}
			order by s.modified desc
			limit 500
			""",
			stu_params,
			as_dict=True,
		)

	# Deduplicate by normalized Emirates ID / Passport — keep newest details
	by_id: dict[str, dict] = {}
	for r in list(tdr_rows) + list(student_rows):
		norm = _normalize_id_number(r.get("id_number"))
		if not norm:
			continue
		existing = by_id.get(norm)
		last_used = r.get("last_used")
		if existing and existing.get("_last_used") and last_used and last_used < existing["_last_used"]:
			continue
		by_id[norm] = {
			"full_name": (r.get("full_name") or "").strip(),
			"id_number": (r.get("id_number") or "").strip(),
			"date_of_birth": str(r.date_of_birth) if r.get("date_of_birth") else "",
			"date_of_birth_fmt": formatdate(r.date_of_birth) if r.get("date_of_birth") else "",
			"contact_number": (r.get("contact_number") or "").strip(),
			"email": (r.get("email") or "").strip(),
			"id_attachment": (r.get("id_attachment") or "").strip(),
			"student": (r.get("student") or "").strip(),
			"_last_used": last_used,
			"id_key": norm,
		}

	out = sorted(
		by_id.values(),
		key=lambda x: x.get("_last_used") or "",
		reverse=True,
	)[:100]

	for row in out:
		row.pop("_last_used", None)
		name = row["full_name"] or "Candidate"
		eid = row["id_number"]
		row["label"] = f"{name} · ID/Passport: {eid}" + (
			f" · {row['date_of_birth_fmt']}" if row.get("date_of_birth_fmt") else ""
		)
	return out


@frappe.whitelist()
def find_candidate_by_id(id_number=None):
	"""Lookup one saved candidate/student by Emirates ID or Passport for auto-fill."""
	session = _require_requester_customer()
	needle = _normalize_id_number(id_number)
	if not needle or not (session.customers or []):
		return None
	for row in list_saved_candidates():
		if row.get("id_key") == needle or _normalize_id_number(row.get("id_number")) == needle:
			return row
	return None


@frappe.whitelist()
def list_my_date_requests():
	session = _require_requester_customer()
	filters: dict = {"status": ("!=", "Cancelled")}
	if not session.is_staff:
		if not session.customers:
			return {"requests": [], "is_staff": False, "pending_open_count": None}
		filters["customer"] = ("in", session.customers)

	rows = frappe.get_all(
		"Training Date Request",
		filters=filters,
		fields=["name"],
		order_by="modified desc",
		limit_page_length=100,
	)
	requests = [_serialize(frappe.get_doc("Training Date Request", r.name)) for r in rows]

	pending_open_count = None
	if session.is_staff:
		# Staff-only: how many Open/Proposed across all customers
		pending_open_count = frappe.db.count(
			"Training Date Request",
			{"status": ("in", ("Open", "Proposed"))},
		)

	return {
		"requests": requests,
		"is_staff": bool(session.is_staff),
		"pending_open_count": pending_open_count,
	}


@frappe.whitelist()
def submit_date_request(
	course=None,
	preferred_date=None,
	preferred_batch=None,
	candidates=None,
	customer_notes=None,
	contact_name=None,
	contact_phone=None,
	customer=None,
	po_number=None,
	po_attachment=None,
):
	session = _require_requester_customer()
	course = (course or "").strip()
	preferred_date = (preferred_date or "").strip()
	preferred_batch = _require_valid_batch(preferred_batch)
	po_number = (po_number or "").strip()
	po_attachment = (po_attachment or "").strip()
	if not course:
		frappe.throw(_("Please select a course."))
	if not preferred_date:
		frappe.throw(_("Please choose a preferred date."))
	if getdate(preferred_date) < getdate(today()):
		frappe.throw(_("Preferred date cannot be in the past."))
	if not frappe.db.exists("Course", course):
		frappe.throw(_("Invalid course."))

	candidate_rows = _parse_candidates(candidates, require_attachment=True)

	# Resolve customer
	customer = (customer or "").strip() or session.customer
	if session.is_staff and customer:
		pass
	elif customer and customer in (session.customers or []):
		pass
	elif session.customer:
		customer = session.customer
	else:
		frappe.throw(_("No customer account is linked to your user. Contact NUTC."))

	if not frappe.db.exists("Customer", customer):
		frappe.throw(_("Invalid customer."))

	doc = frappe.new_doc("Training Date Request")
	doc.customer = customer
	doc.customer_name = frappe.db.get_value("Customer", customer, "customer_name")
	doc.contact_email = session.email
	doc.contact_name = (contact_name or "").strip() or session.full_name
	doc.contact_phone = (contact_phone or "").strip()
	doc.course = course
	doc.preferred_date = preferred_date
	doc.preferred_batch = preferred_batch
	doc.po_number = po_number
	doc.po_attachment = po_attachment
	doc.customer_notes = (customer_notes or "").strip()
	doc.status = "Open"
	for row in candidate_rows:
		doc.append("candidates", row)
	doc.participants = len(candidate_rows)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)

	if po_attachment:
		_relink_portal_file(po_attachment, doc.doctype, doc.name)

	frappe.db.commit()
	return _serialize(doc)


@frappe.whitelist()
def confirm_proposed_date(name=None):
	"""Requester accepts coordinator's proposed date → Training Calendar."""
	session = _require_requester_customer()
	doc = _get_owned((name or "").strip(), session)
	if doc.status != "Proposed" or not doc.proposed_date:
		frappe.throw(_("There is no proposed date to confirm."))

	doc.confirmed_date = doc.proposed_date
	doc.status = "Confirmed"
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)
	calendar = _sync_confirmed_to_training_calendar(doc)
	frappe.db.commit()

	notify_customer_status(
		doc,
		"Training date confirmed",
		f"Your training date for <strong>{frappe.utils.escape_html(doc.course_name or doc.course)}</strong> "
		f"is confirmed for <strong>{formatdate(doc.confirmed_date)}</strong>. "
		f"It has been added to the training calendar.",
	)
	from numerouno.numerouno.doctype.training_date_request.training_date_request import (
		_coordinator_emails,
		_send_mail,
	)
	from numerouno.numerouno.api.customer_portal import _email_shell

	body = f"""
<p>Customer confirmed the proposed date for request <strong>{doc.name}</strong>.</p>
<p>Course: {frappe.utils.escape_html(doc.course_name or doc.course)}<br/>
Confirmed: <strong>{formatdate(doc.confirmed_date)}</strong><br/>
Candidates: {len(doc.candidates or [])}<br/>
Training calendar: {frappe.utils.escape_html(calendar.get("course_schedule") or "")}<br/>
Student group: {frappe.utils.escape_html(calendar.get("student_group") or "")}</p>
<p>Assign an instructor on the Training Calendar when ready.</p>
"""
	_send_mail(
		_coordinator_emails(),
		f"Customer confirmed date — {doc.name}",
		_email_shell("Date confirmed", "Customer accepted the proposed training date.", body),
	)
	return _serialize(doc)


@frappe.whitelist()
def request_date_review(name=None, customer_notes=None):
	"""Requester rejects proposal and asks for another review (back to Open)."""
	session = _require_requester_customer()
	doc = _get_owned((name or "").strip(), session)
	if doc.status != "Proposed":
		frappe.throw(_("Only proposed requests can be sent back for review."))

	note = (customer_notes or "").strip()
	if note:
		prev = (doc.customer_notes or "").strip()
		doc.customer_notes = f"{prev}\n\n[Review request] {note}".strip() if prev else note
	doc.status = "Open"
	doc.proposed_date = None
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)
	frappe.db.commit()

	from numerouno.numerouno.doctype.training_date_request.training_date_request import (
		_notify_coordinators_new_request,
	)

	_notify_coordinators_new_request(doc)
	return _serialize(doc)


@frappe.whitelist()
def accept_preferred_date(name=None):
	"""Coordinator accepts customer's preferred date → Training Calendar."""
	_require_coordinator()
	name = (name or "").strip()
	doc = frappe.get_doc("Training Date Request", name)
	if doc.status not in ("Open", "Proposed"):
		frappe.throw(_("Only open or proposed requests can be accepted."))
	doc.confirmed_date = doc.preferred_date
	doc.status = "Confirmed"
	doc.save()
	calendar = _sync_confirmed_to_training_calendar(doc)
	frappe.db.commit()
	notify_customer_status(
		doc,
		"Training date accepted",
		f"NUTC has accepted your preferred date for "
		f"<strong>{frappe.utils.escape_html(doc.course_name or doc.course)}</strong>: "
		f"<strong>{formatdate(doc.confirmed_date)}</strong>. "
		f"It has been added to the training calendar.",
	)
	doc.student_group = calendar.get("student_group") or doc.student_group
	doc.course_schedule = calendar.get("course_schedule") or doc.course_schedule
	return _serialize(doc)


@frappe.whitelist()
def propose_new_date(name=None, proposed_date=None, coordinator_notes=None):
	_require_coordinator()
	name = (name or "").strip()
	proposed_date = (proposed_date or "").strip()
	if not proposed_date:
		frappe.throw(_("Proposed date is required."))
	if getdate(proposed_date) < getdate(today()):
		frappe.throw(_("Proposed date cannot be in the past."))

	doc = frappe.get_doc("Training Date Request", name)
	if doc.status not in ("Open", "Proposed"):
		frappe.throw(_("Cannot propose a date for this request."))

	doc.proposed_date = proposed_date
	doc.status = "Proposed"
	if coordinator_notes is not None:
		doc.coordinator_notes = (coordinator_notes or "").strip()
	doc.save()
	frappe.db.commit()

	notify_customer_status(
		doc,
		"New training date proposed",
		f"NUTC proposed an alternative date for "
		f"<strong>{frappe.utils.escape_html(doc.course_name or doc.course)}</strong>: "
		f"<strong>{formatdate(doc.proposed_date)}</strong>. "
		f"Please open the Certificate Portal to confirm or request another review.",
	)
	return _serialize(doc)


@frappe.whitelist()
def cancel_request(name=None, coordinator_notes=None):
	_require_coordinator()
	doc = frappe.get_doc("Training Date Request", (name or "").strip())
	if doc.status == "Cancelled":
		return _serialize(doc)
	doc.status = "Cancelled"
	if coordinator_notes:
		doc.coordinator_notes = (coordinator_notes or "").strip()
	doc.save()
	frappe.db.commit()
	notify_customer_status(
		doc,
		"Training date request cancelled",
		"Your training date request was cancelled by NUTC. Please contact us if you need a new booking.",
	)
	return _serialize(doc)


CANDIDATE_CSV_HEADERS = (
	"full_name",
	"id_number",
	"date_of_birth",
	"contact_number",
	"email",
)


@frappe.whitelist()
def get_candidate_csv_template():
	"""Sample CSV for Certificate Portal bulk candidate upload."""
	_require_requester_customer()
	import csv
	from io import StringIO

	buf = StringIO()
	writer = csv.DictWriter(buf, fieldnames=CANDIDATE_CSV_HEADERS)
	writer.writeheader()
	writer.writerow(
		{
			"full_name": "Ahmed Ali",
			"id_number": "784-1990-1234567-1",
			"date_of_birth": "1990-05-15",
			"contact_number": "+971500000000",
			"email": "ahmed@example.com",
		}
	)
	return {
		"filename": "training_candidates_template.csv",
		"content": buf.getvalue(),
		"headers": list(CANDIDATE_CSV_HEADERS),
		"instructions": [
			"Columns: Full Name, Emirates ID / Passport No., Date of Birth (YYYY-MM-DD), Contact Number, Email.",
			"Select course and preferred date on the portal, then upload this CSV.",
            "Optional: after loading CSV into the form, upload each candidate ID one by one, then submit.",
		],
	}


def _parse_candidate_csv(content: bytes | str) -> list[dict]:
	import csv
	from io import StringIO

	if isinstance(content, bytes):
		text = content.decode("utf-8-sig")
	else:
		text = content
	reader = csv.DictReader(StringIO(text))
	if not reader.fieldnames:
		frappe.throw(_("CSV has no header row."))

	norm_map = {}
	for h in reader.fieldnames:
		key = (h or "").strip().lower().replace(" ", "_")
		key = key.replace("/", "_").replace("__", "_")
		aliases = {
			"emirates_id": "id_number",
			"emirates_id_passport_no": "id_number",
			"emirates_id_/_passport_no": "id_number",
			"passport_no": "id_number",
			"passport_number": "id_number",
			"dob": "date_of_birth",
			"phone": "contact_number",
			"mobile": "contact_number",
			"name": "full_name",
			"candidate_name": "full_name",
		}
		key = aliases.get(key, key)
		norm_map[key] = h

	required = ("full_name", "id_number", "date_of_birth", "contact_number", "email")
	missing = [h for h in required if h not in norm_map]
	if missing:
		frappe.throw(_("CSV is missing required columns: {0}").format(", ".join(missing)))

	rows = []
	for i, raw in enumerate(reader, start=2):
		def g(key, _raw=raw):
			src = norm_map.get(key)
			return ((_raw.get(src) if src else "") or "").strip()

		full_name = g("full_name")
		if not full_name:
			continue
		rows.append(
			{
				"row": i,
				"full_name": full_name,
				"id_number": g("id_number"),
				"date_of_birth": g("date_of_birth"),
				"contact_number": g("contact_number"),
				"email": g("email"),
			}
		)
	if not rows:
		frappe.throw(_("CSV has no candidate rows."))
	if len(rows) > 200:
		frappe.throw(_("Please upload at most 200 candidates per CSV."))
	return rows


@frappe.whitelist(methods=["POST"])
def submit_date_request_csv():
	"""Create one Training Date Request from course/date + candidate CSV (Certificate Portal)."""
	from frappe.utils.file_manager import save_file
	from frappe.utils import now_datetime

	session = _require_requester_customer()

	course = (frappe.form_dict.get("course") or "").strip()
	preferred_date = (frappe.form_dict.get("preferred_date") or "").strip()
	preferred_batch = _require_valid_batch(frappe.form_dict.get("preferred_batch"))
	po_number = (frappe.form_dict.get("po_number") or "").strip()
	po_attachment = (frappe.form_dict.get("po_attachment") or "").strip()
	customer_notes = (frappe.form_dict.get("customer_notes") or "").strip()
	contact_name = (frappe.form_dict.get("contact_name") or "").strip()
	contact_phone = (frappe.form_dict.get("contact_phone") or "").strip()
	customer = (frappe.form_dict.get("customer") or "").strip()

	if not course:
		frappe.throw(_("Please select a course."))
	if not preferred_date:
		frappe.throw(_("Please choose a preferred date."))
	if getdate(preferred_date) < getdate(today()):
		frappe.throw(_("Preferred date cannot be in the past."))
	if not frappe.db.exists("Course", course):
		frappe.throw(_("Invalid course."))

	files = getattr(frappe.request, "files", None) or {}
	csv_upload = files.get("csv_file") or files.get("file")
	if not csv_upload or not getattr(csv_upload, "filename", None):
		frappe.throw(_("Please upload a candidates CSV file."))
	if not csv_upload.filename.lower().endswith(".csv"):
		frappe.throw(_("File must be a .csv"))

	csv_rows = _parse_candidate_csv(csv_upload.read())

	extra = []
	if hasattr(files, "getlist"):
		extra.extend([u for u in (files.getlist("id_files") or []) if u])
		extra.extend([u for u in (files.getlist("attachments") or []) if u])
	for key, upload in list(files.items()):
		if key in ("csv_file", "file", "id_files", "attachments"):
			continue
		if upload and getattr(upload, "filename", None):
			extra.append(upload)

	def find_id_file(id_number: str):
		needle = (id_number or "").lower().replace(" ", "").replace("/", "")
		for up in extra:
			base = (up.filename or "").rsplit(".", 1)[0].lower().replace(" ", "").replace("/", "")
			if base == needle or base.startswith(needle) or needle in base:
				return up
		return None

	if session.is_staff and customer:
		pass
	elif customer and customer in (session.customers or []):
		pass
	elif session.customer:
		customer = session.customer
	else:
		frappe.throw(_("No customer account is linked to your user. Contact NUTC."))
	if not frappe.db.exists("Customer", customer):
		frappe.throw(_("Invalid customer."))

	candidates = []
	for row in csv_rows:
		cand = {
			"full_name": row["full_name"],
			"id_number": row["id_number"],
			"date_of_birth": row["date_of_birth"],
			"contact_number": row["contact_number"],
			"email": row["email"],
		}
		if not cand["id_number"] or not cand["date_of_birth"] or not cand["contact_number"] or not cand["email"]:
			frappe.throw(
				_("CSV row {0}: Full Name, Emirates ID/Passport No., Date of Birth, Contact Number and Email are required.").format(
					row["row"]
				)
			)
		try:
			getdate(cand["date_of_birth"])
		except Exception:
			frappe.throw(_("CSV row {0}: invalid date_of_birth (use YYYY-MM-DD).").format(row["row"]))

		up = find_id_file(cand["id_number"])
		if up:
			content = up.read()
			if hasattr(up, "seek"):
				try:
					up.seek(0)
				except Exception:
					pass
			if content:
				stamp = now_datetime().strftime("%Y%m%d%H%M%S")
				safe = f"candidate_id_{stamp}_{up.filename}"
				fdoc = save_file(safe, content, None, None, is_private=1)
				cand["id_attachment"] = fdoc.file_url
				cand["_file_name"] = fdoc.name
		candidates.append(cand)

	doc = frappe.new_doc("Training Date Request")
	doc.customer = customer
	doc.customer_name = frappe.db.get_value("Customer", customer, "customer_name")
	doc.contact_email = session.email
	doc.contact_name = contact_name or session.full_name
	doc.contact_phone = contact_phone
	doc.course = course
	doc.preferred_date = preferred_date
	doc.preferred_batch = preferred_batch
	doc.po_number = po_number
	doc.po_attachment = po_attachment
	doc.customer_notes = customer_notes or _("Submitted via Certificate Portal CSV bulk upload")
	doc.status = "Open"
	for cand in candidates:
		row = {k: v for k, v in cand.items() if not k.startswith("_")}
		doc.append("candidates", row)
	doc.participants = len(candidates)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)

	if po_attachment:
		_relink_portal_file(po_attachment, doc.doctype, doc.name)

	for cand in candidates:
		fname = cand.get("_file_name")
		if fname and frappe.db.exists("File", fname):
			frappe.db.set_value(
				"File",
				fname,
				{
					"attached_to_doctype": "Training Date Request",
					"attached_to_name": doc.name,
				},
				update_modified=False,
			)

	frappe.db.commit()
	return {
		"status": "success",
		"request": _serialize(doc),
		"candidate_count": len(candidates),
		"message": _("Training date request {0} created with {1} candidate(s).").format(
			doc.name, len(candidates)
		),
	}
