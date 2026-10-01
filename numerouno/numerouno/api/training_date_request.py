# Copyright (c) 2026, NumeroUNO and contributors
# License: MIT

"""Training Date Negotiation — customer portal + coordinator desk actions."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, formatdate, getdate, today

from numerouno.numerouno.api.customer_portal import _require_session
from numerouno.numerouno.doctype.training_date_request.training_date_request import (
	notify_customer_status,
)


def _serialize(doc) -> dict:
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
		"participants": cint(doc.participants) or 1,
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


def _get_owned(name: str, customer: str):
	if not frappe.db.exists("Training Date Request", name):
		frappe.throw(_("Request not found."), frappe.DoesNotExistError)
	doc = frappe.get_doc("Training Date Request", name)
	if doc.customer != customer:
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	return doc


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


@frappe.whitelist(allow_guest=True)
def get_courses_for_portal():
	"""Active courses for the date-request dropdown."""
	_require_session()
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


@frappe.whitelist(allow_guest=True)
def list_my_date_requests():
	session = _require_session()
	rows = frappe.get_all(
		"Training Date Request",
		filters={"customer": session.customer, "status": ("!=", "Cancelled")},
		fields=[
			"name",
			"status",
			"customer",
			"customer_name",
			"course",
			"course_name",
			"preferred_date",
			"proposed_date",
			"confirmed_date",
			"participants",
			"customer_notes",
			"coordinator_notes",
			"contact_email",
			"contact_name",
			"contact_phone",
			"posting_date",
		],
		order_by="modified desc",
		limit_page_length=100,
	)
	return [_serialize(frappe._dict(r)) for r in rows]


@frappe.whitelist(allow_guest=True)
def submit_date_request(
	course=None,
	preferred_date=None,
	participants=1,
	customer_notes=None,
	contact_name=None,
	contact_phone=None,
):
	session = _require_session()
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

	doc = frappe.new_doc("Training Date Request")
	doc.customer = session.customer
	doc.customer_name = session.customer_name
	doc.contact_email = session.email
	doc.contact_name = (contact_name or "").strip() or session.customer_name
	doc.contact_phone = (contact_phone or "").strip()
	doc.course = course
	doc.preferred_date = preferred_date
	doc.participants = max(cint(participants) or 1, 1)
	doc.customer_notes = (customer_notes or "").strip()
	doc.status = "Open"
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return _serialize(doc)


@frappe.whitelist(allow_guest=True)
def confirm_proposed_date(name=None):
	"""Customer accepts coordinator's proposed date."""
	session = _require_session()
	doc = _get_owned((name or "").strip(), session.customer)
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
	# also ping coordinators
	from numerouno.numerouno.doctype.training_date_request.training_date_request import (
		_coordinator_emails,
		_send_mail,
	)
	from numerouno.numerouno.api.customer_portal import _email_shell

	body = f"""
<p>Customer confirmed the proposed date for request <strong>{doc.name}</strong>.</p>
<p>Course: {frappe.utils.escape_html(doc.course_name or doc.course)}<br/>
Confirmed: <strong>{formatdate(doc.confirmed_date)}</strong></p>
"""
	_send_mail(
		_coordinator_emails(),
		f"Customer confirmed date — {doc.name}",
		_email_shell("Date confirmed", "Customer accepted the proposed training date.", body),
	)
	return _serialize(doc)


@frappe.whitelist(allow_guest=True)
def request_date_review(name=None, customer_notes=None):
	"""Customer rejects proposal and asks for another review (back to Open)."""
	session = _require_session()
	doc = _get_owned((name or "").strip(), session.customer)
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
		_coordinator_emails,
		_notify_coordinators_new_request,
	)

	# reuse new-request style alert
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
		f"Please sign in to the Customer Portal to confirm or request another review.",
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
