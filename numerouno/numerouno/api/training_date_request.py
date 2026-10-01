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
				"nationality": row.nationality or "",
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


def _parse_candidates(candidates) -> list[dict]:
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
		id_attachment = (raw.get("id_attachment") or "").strip()
		if not full_name:
			frappe.throw(_("Candidate #{0}: Full Name is required.").format(i))
		if not id_number:
			frappe.throw(_("Candidate #{0}: Passport / Emirates ID No. is required.").format(i))
		if not id_attachment:
			frappe.throw(
				_("Candidate #{0}: Please attach the ID document (upload a file, not a link).").format(i)
			)
		# Reject bare http(s) "photo links" — must be an uploaded File path
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
				"nationality": (raw.get("nationality") or "").strip(),
				"date_of_birth": raw.get("date_of_birth") or None,
				"id_number": id_number,
				"contact_number": (raw.get("contact_number") or "").strip(),
				"email": (raw.get("email") or "").strip(),
				"id_attachment": id_attachment,
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
			return []
		filters["customer"] = ("in", session.customers)

	rows = frappe.get_all(
		"Training Date Request",
		filters=filters,
		fields=["name"],
		order_by="modified desc",
		limit_page_length=100,
	)
	return [_serialize(frappe.get_doc("Training Date Request", r.name)) for r in rows]


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

	candidate_rows = _parse_candidates(candidates)

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
