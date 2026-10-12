# Copyright (c) 2026, NumeroUNO and contributors
# License: MIT

"""Guest Training Portal — approved accounts, booking requests, candidate ID upload."""

from __future__ import annotations

import json
import random
import string

import frappe
from frappe import _
from frappe.utils import add_days, cint, formatdate, get_url, getdate, now_datetime, today

from numerouno.numerouno.api.training_schedule import (
	PERIODS,
	_apply_candidate_invite_counts,
	_attach_capacity,
	_attach_student_counts,
	_candidate_table_exists,
	_fmt_time,
	_insert_candidate,
	_period_by_key,
	_period_from_time,
	_room_label,
	create_confirmed_booking,
)


PORTAL_TOKEN_COOKIE = "nutc_guest_training"
PORTAL_SESSION_HOURS = 12
OTP_EXPIRY_MINUTES = 10
DEFAULT_DAYS = 21
MAX_DAYS = 42
MAX_CANDIDATES = 20

SLOT_LABELS = {
	"morning": "Morning · 08:00",
	"afternoon": "Afternoon · 13:00",
	"evening": "Evening · 18:00",
}


def _cache_key_otp(email: str) -> str:
	return f"guest_training_otp:{(email or '').strip().lower()}"


def _cache_key_session(token: str) -> str:
	return f"guest_training_session:{token}"


def _normalize_email(email: str) -> str:
	return (email or "").strip().lower()


def _new_token(length: int = 40) -> str:
	alphabet = string.ascii_letters + string.digits
	return "".join(random.choice(alphabet) for _ in range(length))


def _brand() -> dict:
	company = frappe.db.get_single_value("Global Defaults", "default_company") or "NumeroUNO"
	return {
		"company": company,
		"portal_url": get_url("/book-training"),
		"support_email": frappe.db.get_value(
			"Email Account", {"default_outgoing": 1}, "email_id"
		)
		or "erp@numerouno-me.com",
	}


def _slots() -> list[dict]:
	return [
		{
			"key": p["key"],
			"label": SLOT_LABELS.get(p["key"], p["label"]),
			"from_time": p["from_time"][:5],
			"to_time": p["to_time"][:5],
		}
		for p in PERIODS
	]


def _otp_email_html(otp: str, minutes: int) -> str:
	brand = _brand()
	return f"""<!DOCTYPE html>
<html lang="en"><body style="margin:0;padding:0;background:#eef2f4;font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#0b1f2a;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#eef2f4;padding:32px 12px;">
<tr><td align="center">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#fff;border-radius:18px;overflow:hidden;">
<tr><td style="background:linear-gradient(135deg,#0b1f2a 0%,#163948 55%,#1f7a72 120%);padding:28px 32px;color:#fff;">
<div style="font-size:13px;letter-spacing:.12em;text-transform:uppercase;opacity:.75;margin-bottom:8px;">NumeroUNO</div>
<div style="font-size:24px;font-weight:700;">Training portal code</div>
</td></tr>
<tr><td style="padding:32px;">
<p style="margin:0 0 16px;font-size:16px;line-height:1.55;">Use this code to sign in to the <strong>Guest Training Portal</strong>.</p>
<div style="background:#f3efe6;border:1px solid #e7e0d2;border-radius:16px;padding:22px;text-align:center;">
<div style="font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:#5d6f79;margin-bottom:10px;">Your code</div>
<div style="font-size:36px;font-weight:700;letter-spacing:10px;">{otp}</div>
<div style="margin-top:10px;color:#5d6f79;font-size:13px;">Expires in {minutes} minutes</div>
</div>
<p style="margin:20px 0 0;color:#5d6f79;font-size:13px;">Need help? Contact <a href="mailto:{brand["support_email"]}">{brand["support_email"]}</a>.</p>
</td></tr>
</table>
</td></tr>
</table>
</body></html>"""


def _set_session_cookie(token: str):
	frappe.local.cookie_manager.set_cookie(
		PORTAL_TOKEN_COOKIE,
		token,
		max_age=PORTAL_SESSION_HOURS * 3600,
		httponly=True,
		samesite="Lax",
	)


def _clear_session_cookie():
	frappe.local.cookie_manager.delete_cookie(PORTAL_TOKEN_COOKIE)


def _account_by_email(email: str):
	email = _normalize_email(email)
	if not email:
		return None
	name = frappe.db.get_value("Guest Training Account", {"email": email}, "name")
	return frappe.get_doc("Guest Training Account", name) if name else None


def _current_session() -> dict | None:
	token = frappe.request.cookies.get(PORTAL_TOKEN_COOKIE) if frappe.request else None
	if not token:
		return None
	data = frappe.cache().get_value(_cache_key_session(token))
	if not data or not data.get("account"):
		return None
	status = frappe.db.get_value("Guest Training Account", data["account"], "status")
	if status != "Approved":
		return None
	return data


def _require_session() -> dict:
	session = _current_session()
	if not session:
		frappe.throw(_("Please sign in with an approved account."), frappe.PermissionError)
	return session


def _require_staff():
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Not allowed."), frappe.PermissionError)
	roles = set(frappe.get_roles(user))
	allowed = {
		"System Manager",
		"Administrator",
		"Training Coordinator",
		"Training Portal",
		"Training Schedule",
		"Education Manager",
	}
	if user != "Administrator" and not roles.intersection(allowed):
		frappe.throw(_("Not allowed."), frappe.PermissionError)


def _notify(recipients, subject, body):
	if not recipients:
		return
	try:
		frappe.sendmail(recipients=list({r for r in recipients if r}), subject=subject, message=body, now=True)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Guest Training Notify")


def _public_session(row: dict, preferred_slot: str | None = None) -> dict:
	period = _period_from_time(row.get("from_time") or "")
	slot_key = period["key"]
	remaining = row.get("remaining")
	return {
		"name": row["name"],
		"date": str(row["schedule_date"]),
		"date_label": formatdate(row["schedule_date"], "dd MMM yyyy"),
		"weekday": getdate(row["schedule_date"]).strftime("%a"),
		"from_time": _fmt_time(row.get("from_time")),
		"to_time": _fmt_time(row.get("to_time")),
		"slot": slot_key,
		"slot_label": SLOT_LABELS.get(slot_key, period["label"]),
		"period": SLOT_LABELS.get(slot_key, period["label"]),
		"course": row.get("course") or "",
		"course_name": row.get("course_name") or row.get("course") or "",
		"room_label": _room_label(row.get("room"), row.get("room_name"), row.get("room_number")),
		"student_group": row.get("student_group") or "",
		"max_strength": cint(row.get("max_strength")),
		"remaining": remaining,
		"seats_label": (
			f"{cint(remaining)} seat{'s' if cint(remaining) != 1 else ''} left"
			if remaining is not None
			else "Open"
		),
		"matches_preferred": bool(preferred_slot and preferred_slot == slot_key),
	}


def _serialize_booking(doc) -> dict:
	slot = (doc.slot or "morning").lower()
	return {
		"name": doc.name,
		"status": doc.status,
		"course": doc.course,
		"course_name": doc.course_name or doc.course,
		"schedule_date": str(doc.schedule_date) if doc.schedule_date else "",
		"date_label": formatdate(doc.schedule_date, "dd MMM yyyy") if doc.schedule_date else "",
		"slot": slot,
		"slot_label": SLOT_LABELS.get(slot, slot),
		"company_name": doc.company_name,
		"participants": cint(doc.participants),
		"course_schedule": doc.course_schedule,
		"candidate_count": len(doc.candidates or []),
		"can_upload_candidates": doc.status == "Confirmed",
	}


# ── Account request + login ───────────────────────────────────────────


@frappe.whitelist(allow_guest=True)
def request_account(
	email: str | None = None,
	company_name: str | None = None,
	contact_name: str | None = None,
	phone: str | None = None,
	preferred_slot: str | None = None,
	notes: str | None = None,
):
	"""Public: request a guest portal account (staff must approve)."""
	email = _normalize_email(email or frappe.form_dict.get("email"))
	company_name = (company_name or frappe.form_dict.get("company_name") or "").strip()
	contact_name = (contact_name or frappe.form_dict.get("contact_name") or "").strip()
	phone = (phone or frappe.form_dict.get("phone") or "").strip()
	# Slot is chosen only when booking — not at account registration.
	preferred_slot = "morning"
	notes = (notes or frappe.form_dict.get("notes") or "").strip()

	if not email or "@" not in email:
		frappe.throw(_("Enter a valid work email."))
	if not company_name:
		frappe.throw(_("Company / organisation is required."))
	if not contact_name:
		frappe.throw(_("Contact name is required."))

	existing = _account_by_email(email)
	if existing:
		if existing.status == "Approved":
			return {
				"ok": 1,
				"already": 1,
				"message": _("This email already has an approved account. Sign in with a code."),
			}
		if existing.status == "Pending":
			return {
				"ok": 1,
				"pending": 1,
				"message": _("Your account request is already waiting for approval."),
			}
		# Rejected — allow re-request
		existing.status = "Pending"
		existing.company_name = company_name
		existing.contact_name = contact_name
		existing.phone = phone
		existing.preferred_slot = preferred_slot
		existing.notes = notes
		existing.reviewed_by = None
		existing.reviewed_on = None
		existing.flags.ignore_permissions = True
		existing.save()
		doc = existing
	else:
		doc = frappe.get_doc(
			{
				"doctype": "Guest Training Account",
				"email": email,
				"company_name": company_name,
				"contact_name": contact_name,
				"phone": phone,
				"preferred_slot": preferred_slot,
				"notes": notes,
				"status": "Pending",
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert()

	brand = _brand()
	_notify(
		[brand["support_email"]],
		_("Guest training account request: {0}").format(company_name),
		f"""<p>New guest portal account request.</p>
		<ul>
		<li>Company: {frappe.utils.escape_html(company_name)}</li>
		<li>Contact: {frappe.utils.escape_html(contact_name)}</li>
		<li>Email: {frappe.utils.escape_html(email)}</li>
		<li>Phone: {frappe.utils.escape_html(phone or '—')}</li>
		</ul>
		<p><a href="{get_url(doc.get_url())}">Open in ERPNext</a></p>""",
	)
	return {
		"ok": 1,
		"message": _("Request submitted. We’ll email you once your account is approved."),
		"name": doc.name,
	}


@frappe.whitelist(allow_guest=True)
def request_access_otp(email: str | None = None):
	email = _normalize_email(email or frappe.form_dict.get("email"))
	if not email or "@" not in email:
		frappe.throw(_("Enter a valid email address."))

	account = _account_by_email(email)
	if not account:
		return {
			"ok": 0,
			"sent": 0,
			"needs_account": 1,
			"message": _("No account for this email. Request access first — we approve company accounts before booking."),
		}
	if account.status == "Pending":
		return {
			"ok": 0,
			"sent": 0,
			"pending": 1,
			"message": _("Your account is waiting for approval. We’ll email you when it’s ready."),
		}
	if account.status != "Approved":
		return {
			"ok": 0,
			"sent": 0,
			"message": _("This account was not approved. Contact us for help."),
		}

	rate_key = f"guest_training_otp_rate:{email}"
	sent_count = cint(frappe.cache().get_value(rate_key) or 0)
	if sent_count >= 5:
		frappe.throw(_("Too many codes requested. Wait a few minutes and try again."))

	otp = f"{random.randint(100000, 999999)}"
	prev = frappe.cache().get_value(_cache_key_otp(email)) or {}
	otps = [otp] + [
		x
		for x in (prev.get("otps") or ([prev["otp"]] if prev.get("otp") else []))
		if str(x) != str(otp)
	][:5]
	frappe.cache().set_value(
		_cache_key_otp(email),
		{"otp": otp, "otps": [str(x) for x in otps], "email": email, "account": account.name},
		expires_in_sec=OTP_EXPIRY_MINUTES * 60,
	)
	frappe.cache().set_value(rate_key, sent_count + 1, expires_in_sec=15 * 60)

	try:
		frappe.sendmail(
			recipients=[email],
			subject=_("Your NumeroUNO training portal code"),
			message=_otp_email_html(otp, OTP_EXPIRY_MINUTES),
			now=True,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Guest Training OTP Email")
		frappe.throw(_("Could not send email. Please contact support."))

	return {"ok": 1, "sent": 1, "message": _("A 6-digit code was sent to your email.")}


@frappe.whitelist(allow_guest=True)
def verify_access_otp(email: str | None = None, otp: str | None = None):
	email = _normalize_email(email or frappe.form_dict.get("email"))
	otp = (otp or frappe.form_dict.get("otp") or "").strip()
	cached = frappe.cache().get_value(_cache_key_otp(email)) or {}
	valid_otps = [str(x) for x in (cached.get("otps") or [])]
	if cached.get("otp"):
		valid_otps = list(dict.fromkeys([str(cached.get("otp"))] + valid_otps))
	if not valid_otps:
		frappe.throw(_("Code expired or not found. Tap Continue again to get a new code."))
	if str(otp) not in valid_otps:
		frappe.throw(_("That code is incorrect. Open the newest email and try again."))

	account_name = cached.get("account") or frappe.db.get_value(
		"Guest Training Account", {"email": email, "status": "Approved"}, "name"
	)
	if not account_name:
		frappe.throw(_("No approved account found."))
	account = frappe.get_doc("Guest Training Account", account_name)
	if account.status != "Approved":
		frappe.throw(_("This account is not approved yet."))

	token = _new_token()
	session = {
		"token": token,
		"account": account.name,
		"email": account.email,
		"company": account.company_name,
		"contact_name": account.contact_name,
		"phone": account.phone or "",
		"preferred_slot": account.preferred_slot or "morning",
	}
	frappe.cache().set_value(_cache_key_session(token), session, expires_in_sec=PORTAL_SESSION_HOURS * 3600)
	_set_session_cookie(token)
	frappe.cache().delete_value(_cache_key_otp(email))
	return {
		"ok": 1,
		"email": account.email,
		"company": account.company_name,
		"contact_name": account.contact_name,
		"phone": account.phone or "",
		"preferred_slot": account.preferred_slot or "morning",
	}


@frappe.whitelist(allow_guest=True)
def get_session():
	session = _current_session()
	brand = _brand()
	if not session:
		return {"ok": 0, "authenticated": 0, "brand": brand, "slots": _slots()}
	return {
		"ok": 1,
		"authenticated": 1,
		"email": session.get("email"),
		"company": session.get("company") or "",
		"contact_name": session.get("contact_name") or "",
		"phone": session.get("phone") or "",
		"preferred_slot": session.get("preferred_slot") or "morning",
		"account": session.get("account"),
		"brand": brand,
		"slots": _slots(),
	}


@frappe.whitelist(allow_guest=True)
def logout():
	token = frappe.request.cookies.get(PORTAL_TOKEN_COOKIE) if frappe.request else None
	if token:
		frappe.cache().delete_value(_cache_key_session(token))
	_clear_session_cookie()
	return {"ok": 1}


# ── Schedule browse + booking request ─────────────────────────────────


@frappe.whitelist(allow_guest=True)
def get_available_sessions(from_date=None, days=None, course=None, slot=None):
	session = _require_session()
	preferred = session.get("preferred_slot") or "morning"
	start = getdate(from_date or today())
	day_count = min(max(cint(days) or DEFAULT_DAYS, 1), MAX_DAYS)
	end = add_days(start, day_count - 1)
	course = (course or "").strip() or None
	slot = (slot or "").strip().lower() or None

	filters_sql = """
		cs.docstatus < 2
		and cs.schedule_date between %(start)s and %(end)s
		and cs.schedule_date >= %(today)s
	"""
	params = {"start": start, "end": end, "today": today()}
	if course:
		filters_sql += " and cs.course = %(course)s"
		params["course"] = course

	rows = frappe.db.sql(
		f"""
		select
			cs.name, cs.schedule_date, cs.from_time, cs.to_time,
			cs.room, cs.course, cs.student_group,
			r.room_name, r.room_number,
			co.course_name
		from `tabCourse Schedule` cs
		left join `tabRoom` r on r.name = cs.room
		left join `tabCourse` co on co.name = cs.course
		where {filters_sql}
		order by cs.schedule_date asc, cs.from_time asc
		""",
		params,
		as_dict=True,
	)

	sessions = []
	for row in rows:
		sessions.append(
			{
				"name": row.name,
				"schedule_date": row.schedule_date,
				"from_time": _fmt_time(row.from_time),
				"to_time": _fmt_time(row.to_time),
				"room": row.room,
				"room_name": row.room_name,
				"room_number": row.room_number,
				"course": row.course,
				"course_name": row.course_name or row.course,
				"student_group": row.student_group,
				"student_count": 0,
			}
		)
	_attach_student_counts(sessions)
	_attach_capacity(sessions)
	_apply_candidate_invite_counts(sessions)

	public = []
	for row in sessions:
		remaining = row.get("remaining")
		if remaining is not None and cint(remaining) <= 0:
			continue
		item = _public_session(row, preferred)
		if slot and item["slot"] != slot:
			continue
		public.append(item)

	# Preferred slot first
	public.sort(key=lambda s: (0 if s.get("matches_preferred") else 1, s["date"], s["from_time"]))

	courses = sorted(
		{(s["course"], s["course_name"]) for s in public if s.get("course")},
		key=lambda x: (x[1] or x[0]).lower(),
	)
	return {
		"ok": 1,
		"from_date": str(start),
		"to_date": str(end),
		"days": day_count,
		"sessions": public,
		"courses": [{"name": c[0], "label": c[1]} for c in courses],
		"slots": _slots(),
		"preferred_slot": preferred,
		"company": session.get("company"),
	}


@frappe.whitelist(allow_guest=True)
def submit_booking_request(
	course_schedule: str | None = None,
	slot: str | None = None,
	phone: str | None = None,
	po_number: str | None = None,
	participants: int | None = None,
	guest_notes: str | None = None,
):
	"""Create a booking request only — does NOT create Course Schedule or candidates yet."""
	session = _require_session()
	course_schedule = (course_schedule or frappe.form_dict.get("course_schedule") or "").strip()
	if not course_schedule:
		frappe.throw(_("Select a training session."))

	slot = (slot or frappe.form_dict.get("slot") or session.get("preferred_slot") or "morning").strip().lower()
	if slot not in SLOT_LABELS:
		slot = "morning"
	phone = (phone or frappe.form_dict.get("phone") or session.get("phone") or "").strip()
	po_number = (po_number or frappe.form_dict.get("po_number") or "").strip()
	guest_notes = (guest_notes or frappe.form_dict.get("guest_notes") or "").strip()
	participants = max(cint(participants or frappe.form_dict.get("participants") or 1), 1)

	row = frappe.db.sql(
		"""
		select cs.name, cs.schedule_date, cs.from_time, cs.to_time, cs.course, cs.student_group,
			co.course_name
		from `tabCourse Schedule` cs
		left join `tabCourse` co on co.name = cs.course
		where cs.name = %(name)s and cs.docstatus < 2
		limit 1
		""",
		{"name": course_schedule},
		as_dict=True,
	)
	if not row:
		frappe.throw(_("That training session was not found."))
	row = row[0]
	if getdate(row.schedule_date) < getdate(today()):
		frappe.throw(_("That session has already started or passed."))

	# Infer slot from session time; guest can only book that session's slot
	session_slot = _period_from_time(_fmt_time(row.from_time))["key"]
	slot = session_slot

	# Prevent duplicate pending requests for same account+session
	dup = frappe.db.exists(
		"Guest Training Booking",
		{
			"account": session["account"],
			"course_schedule": course_schedule,
			"status": ("in", ["Pending", "Confirmed"]),
		},
	)
	if dup:
		frappe.throw(_("You already have an open booking for this session."))

	doc = frappe.get_doc(
		{
			"doctype": "Guest Training Booking",
			"account": session["account"],
			"company_name": session.get("company"),
			"contact_email": session.get("email"),
			"contact_phone": phone,
			"course": row.course,
			"course_name": row.course_name or row.course,
			"schedule_date": row.schedule_date,
			"slot": slot,
			"course_schedule": row.name,
			"student_group": row.student_group,
			"po_number": po_number,
			"participants": participants,
			"guest_notes": guest_notes,
			"status": "Pending",
			"requested_on": today(),
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()

	brand = _brand()
	_notify(
		[brand["support_email"]],
		_("Guest booking request: {0} — {1}").format(
			doc.course_name or doc.course, formatdate(doc.schedule_date, "dd MMM yyyy")
		),
		f"""<p><strong>New booking request (awaiting confirmation)</strong></p>
		<ul>
		<li>Company: {frappe.utils.escape_html(doc.company_name or '')}</li>
		<li>Email: {frappe.utils.escape_html(doc.contact_email or '')}</li>
		<li>Course: {frappe.utils.escape_html(doc.course_name or '')}</li>
		<li>Date: {frappe.utils.escape_html(formatdate(doc.schedule_date, 'dd MMM yyyy'))}</li>
		<li>Slot: {frappe.utils.escape_html(SLOT_LABELS.get(slot, slot))}</li>
		<li>Participants: {participants}</li>
		</ul>
		<p>No schedule was created yet. Confirm in ERPNext when ready.</p>
		<p><a href="{get_url(doc.get_url())}">Open booking</a></p>""",
	)

	return {
		"ok": 1,
		"message": _("Booking request submitted. Our training coordinator will confirm it shortly."),
		"booking": _serialize_booking(doc),
	}


@frappe.whitelist(allow_guest=True)
def get_my_bookings():
	session = _require_session()
	rows = frappe.get_all(
		"Guest Training Booking",
		filters={"account": session["account"]},
		fields=[
			"name",
			"status",
			"course",
			"course_name",
			"schedule_date",
			"slot",
			"company_name",
			"participants",
			"course_schedule",
		],
		order_by="schedule_date desc, creation desc",
		limit_page_length=50,
	)
	out = []
	for r in rows:
		doc = frappe.get_doc("Guest Training Booking", r.name)
		out.append(_serialize_booking(doc))
	return {"ok": 1, "bookings": out}


@frappe.whitelist(allow_guest=True)
def submit_candidates(booking: str | None = None, candidates: str | list | None = None):
	"""After coordinator confirms — guest uploads candidate name + ID (like certificate portal)."""
	session = _require_session()
	booking = (booking or frappe.form_dict.get("booking") or "").strip()
	if not booking:
		frappe.throw(_("Booking is required."))
	doc = frappe.get_doc("Guest Training Booking", booking)
	if doc.account != session["account"]:
		frappe.throw(_("Not allowed."), frappe.PermissionError)
	if doc.status != "Confirmed":
		frappe.throw(_("Candidates can only be uploaded after the coordinator confirms the booking."))

	raw = candidates
	if raw is None:
		raw = frappe.form_dict.get("candidates")
	if isinstance(raw, str):
		raw = json.loads(raw)
	if not isinstance(raw, list) or not raw:
		frappe.throw(_("Add at least one candidate with name and ID."))

	rows = []
	for i, item in enumerate(raw, start=1):
		if not isinstance(item, dict):
			continue
		full_name = (item.get("full_name") or item.get("candidate_name") or "").strip()
		id_number = (item.get("id_number") or "").strip()
		id_attachment = (item.get("id_attachment") or "").strip()
		if not full_name:
			frappe.throw(_("Candidate #{0}: name is required.").format(i))
		if not id_number:
			frappe.throw(_("Candidate #{0}: Emirates ID / Passport No. is required.").format(i))
		if not id_attachment:
			frappe.throw(_("Candidate #{0}: please upload the ID document.").format(i))
		if id_attachment.startswith("http://") or id_attachment.startswith("https://"):
			frappe.throw(_("Candidate #{0}: attach the ID file from your device — do not paste a link.").format(i))
		rows.append(
			{
				"full_name": full_name,
				"id_number": id_number,
				"id_attachment": id_attachment,
			}
		)
	if not rows:
		frappe.throw(_("Add at least one candidate."))
	if len(rows) > MAX_CANDIDATES:
		frappe.throw(_("You can upload at most {0} candidates.").format(MAX_CANDIDATES))

	doc.set("candidates", [])
	for row in rows:
		doc.append("candidates", row)
	doc.status = "Candidates Submitted"
	doc.flags.ignore_permissions = True
	doc.save()

	# Create Training Candidates on the confirmed schedule (if available)
	if doc.course_schedule and _candidate_table_exists():
		for row in rows:
			_insert_candidate(
				{
					"student_group": doc.student_group,
					"course_schedule": doc.course_schedule,
					"course": doc.course,
					"date": doc.schedule_date,
					"customer_name": doc.company_name,
					"po_number": doc.po_number,
				},
				row["full_name"],
			)

	brand = _brand()
	_notify(
		[brand["support_email"]],
		_("Candidates uploaded: {0}").format(doc.name),
		f"""<p>Guest uploaded {len(rows)} candidate(s) for <strong>{frappe.utils.escape_html(doc.course_name or '')}</strong>.</p>
		<p><a href="{get_url(doc.get_url())}">Open booking</a></p>""",
	)
	return {
		"ok": 1,
		"message": _("Candidates submitted. Thank you."),
		"booking": _serialize_booking(doc),
	}


@frappe.whitelist(allow_guest=True)
def upload_id_file():
	"""Guest file upload for candidate ID documents."""
	from frappe.utils.file_manager import save_file

	session = _require_session()
	uploaded = None
	if frappe.request and getattr(frappe.request, "files", None):
		uploaded = frappe.request.files.get("file") or frappe.request.files.get("id_file")
	if not uploaded and frappe.form_dict.get("filedata"):
		# fallback: ignore
		pass
	if not uploaded:
		frappe.throw(_("No file received."))
	content = uploaded.stream.read()
	fname = frappe.utils.cstr(uploaded.filename)
	if not content:
		frappe.throw(_("Empty file."))
	file_doc = save_file(fname, content, "Guest Training Account", session["account"], is_private=1)
	return {"ok": 1, "file_url": file_doc.file_url, "account": session.get("account")}


# ── Staff actions ─────────────────────────────────────────────────────


@frappe.whitelist()
def staff_approve_account(name: str | None = None):
	_require_staff()
	name = (name or frappe.form_dict.get("name") or "").strip()
	doc = frappe.get_doc("Guest Training Account", name)
	doc.status = "Approved"
	doc.reviewed_by = frappe.session.user
	doc.reviewed_on = now_datetime()
	doc.save()
	_notify(
		[doc.email],
		_("Your NumeroUNO training portal account is approved"),
		f"""<p>Hi {frappe.utils.escape_html(doc.contact_name or '')},</p>
		<p>Your guest training account for <strong>{frappe.utils.escape_html(doc.company_name or '')}</strong> is approved.</p>
		<p><a href="{get_url('/book-training')}">Sign in to book training</a></p>""",
	)
	return {"ok": 1, "status": doc.status}


@frappe.whitelist()
def staff_confirm_booking(name: str | None = None):
	"""Confirm guest request. Creates Course Schedule only if none is linked yet."""
	_require_staff()
	name = (name or frappe.form_dict.get("name") or "").strip()
	doc = frappe.get_doc("Guest Training Booking", name)
	if doc.status != "Pending":
		frappe.throw(_("Only pending bookings can be confirmed."))

	created_schedule = None
	if not doc.course_schedule:
		# Create schedule now (not at guest submit time)
		result = create_confirmed_booking(
			course_name=doc.course_name or doc.course,
			schedule_date=str(doc.schedule_date),
			participants=cint(doc.participants) or 1,
			customer_email=doc.contact_email,
			customer_name=doc.company_name,
			period=doc.slot or "morning",
		)
		if result.get("name"):
			created_schedule = result["name"]
			doc.course_schedule = created_schedule
			sg = frappe.db.get_value("Course Schedule", created_schedule, "student_group")
			if sg:
				doc.student_group = sg
		elif result.get("reason") not in ("already_exists",):
			frappe.throw(_("Could not create schedule: {0}").format(result.get("reason") or "unknown"))
		elif result.get("name"):
			doc.course_schedule = result["name"]

	doc.status = "Confirmed"
	doc.confirmed_by = frappe.session.user
	doc.confirmed_on = now_datetime()
	doc.save()

	_notify(
		[doc.contact_email],
		_("Booking confirmed — upload candidate names & IDs"),
		f"""<p>Hi,</p>
		<p>Your training booking for <strong>{frappe.utils.escape_html(doc.course_name or '')}</strong>
		on {frappe.utils.escape_html(formatdate(doc.schedule_date, 'dd MMM yyyy'))}
		({frappe.utils.escape_html(SLOT_LABELS.get(doc.slot, doc.slot))})</p>
		<p>is <strong>confirmed</strong>.</p>
		<p>Please sign in and upload each candidate’s <strong>name and Emirates ID / Passport</strong>.</p>
		<p><a href="{get_url('/book-training')}">Open Guest Training Portal</a></p>""",
	)
	return {"ok": 1, "status": doc.status, "course_schedule": doc.course_schedule, "created": created_schedule}


@frappe.whitelist()
def staff_reject_booking(name: str | None = None, reason: str | None = None):
	_require_staff()
	name = (name or frappe.form_dict.get("name") or "").strip()
	reason = (reason or frappe.form_dict.get("reason") or "").strip()
	doc = frappe.get_doc("Guest Training Booking", name)
	doc.status = "Rejected"
	if reason:
		doc.coordinator_notes = ((doc.coordinator_notes or "") + "\n" + reason).strip()
	doc.save()
	_notify(
		[doc.contact_email],
		_("Training booking update"),
		f"""<p>Your booking request for {frappe.utils.escape_html(doc.course_name or '')}
		on {frappe.utils.escape_html(formatdate(doc.schedule_date, 'dd MMM yyyy') if doc.schedule_date else '')}
		was not confirmed.</p>
		<p>{frappe.utils.escape_html(reason) if reason else 'Please contact us for details.'}</p>""",
	)
	return {"ok": 1, "status": doc.status}
