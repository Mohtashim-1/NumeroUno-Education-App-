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
		"can_confirm_proposal": doc.status == "Proposed" and bool(doc.proposed_date),
		"can_request_review": doc.status == "Proposed",
		"is_open": doc.status == "Open",
		"is_confirmed": doc.status == "Confirmed",
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
def get_courses_for_portal():
	"""Active courses for the date-request dropdown."""
	_require_requester_customer()
	filters = {}
	if frappe.get_meta("Course").has_field("disabled"):
		filters["disabled"] = 0
	rows = frappe.get_all(
		"Course",
		filters=filters,
		fields=["name", "course_name"],
		order_by="course_name asc",
		limit_page_length=500,
	)
	return [{"name": r.name, "course_name": r.course_name or r.name} for r in rows if r.name]


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
	candidates=None,
	customer_notes=None,
	contact_name=None,
	contact_phone=None,
	customer=None,
):
	session = _require_requester_customer()
	course = (course or "").strip()
	preferred_date = (preferred_date or "").strip()
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
	doc.customer_notes = (customer_notes or "").strip()
	doc.status = "Open"
	for row in candidate_rows:
		doc.append("candidates", row)
	doc.participants = len(candidate_rows)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return _serialize(doc)


@frappe.whitelist()
def confirm_proposed_date(name=None):
	"""Requester accepts coordinator's proposed date."""
	session = _require_requester_customer()
	doc = _get_owned((name or "").strip(), session)
	if doc.status != "Proposed" or not doc.proposed_date:
		frappe.throw(_("There is no proposed date to confirm."))

	doc.confirmed_date = doc.proposed_date
	doc.status = "Confirmed"
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)
	frappe.db.commit()

	notify_customer_status(
		doc,
		"Training date confirmed",
		f"Your training date for <strong>{frappe.utils.escape_html(doc.course_name or doc.course)}</strong> "
		f"is confirmed for <strong>{formatdate(doc.confirmed_date)}</strong>.",
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
Candidates: {len(doc.candidates or [])}</p>
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
	_require_coordinator()
	name = (name or "").strip()
	doc = frappe.get_doc("Training Date Request", name)
	if doc.status not in ("Open", "Proposed"):
		frappe.throw(_("Only open or proposed requests can be accepted."))
	doc.confirmed_date = doc.preferred_date
	doc.status = "Confirmed"
	doc.save()
	frappe.db.commit()
	notify_customer_status(
		doc,
		"Training date accepted",
		f"NUTC has accepted your preferred date for "
		f"<strong>{frappe.utils.escape_html(doc.course_name or doc.course)}</strong>: "
		f"<strong>{formatdate(doc.confirmed_date)}</strong>. The training calendar will be updated shortly.",
	)
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
	doc.customer_notes = customer_notes or _("Submitted via Certificate Portal CSV bulk upload")
	doc.status = "Open"
	for cand in candidates:
		row = {k: v for k, v in cand.items() if not k.startswith("_")}
		doc.append("candidates", row)
	doc.participants = len(candidates)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)

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
