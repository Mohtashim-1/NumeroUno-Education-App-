# Copyright (c) 2026, NumeroUNO and contributors
# License: MIT

"""Customer Invoice Portal — email OTP auth, invoice list, Stripe pay via Payment Request."""

from __future__ import annotations

import random
import string

import frappe
from frappe import _
from frappe.utils import cint, flt, fmt_money, formatdate, get_url, now_datetime


PORTAL_TOKEN_COOKIE = "nutc_customer_portal"
PORTAL_SESSION_HOURS = 12
OTP_EXPIRY_MINUTES = 10
PORTAL_ACCESS_FIELD = "custom_invoice_portal_access"


def _cache_key_otp(email: str) -> str:
	return f"customer_portal_otp:{(email or '').strip().lower()}"


def _cache_key_session(token: str) -> str:
	return f"customer_portal_session:{token}"


def _normalize_email(email: str) -> str:
	return (email or "").strip().lower()


def _new_token(length: int = 40) -> str:
	alphabet = string.ascii_letters + string.digits
	return "".join(random.choice(alphabet) for _ in range(length))


def _portal_access_enabled() -> bool:
	return frappe.db.has_column("Customer", PORTAL_ACCESS_FIELD)


def _has_portal_access(customer_name: str) -> bool:
	if not _portal_access_enabled():
		return True
	return cint(frappe.db.get_value("Customer", customer_name, PORTAL_ACCESS_FIELD)) == 1


def _brand() -> dict:
	company = frappe.db.get_single_value("Global Defaults", "default_company") or "NumeroUNO"
	return {
		"company": company,
		"portal_url": get_url("/customer-portal"),
		"support_email": frappe.db.get_value(
			"Email Account", {"default_outgoing": 1}, "email_id"
		)
		or "erp@numerouno-me.com",
	}


def _email_shell(title: str, preheader: str, body_html: str) -> str:
	"""Branded transactional email wrapper."""
	brand = _brand()
	return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{title}</title>
<!--[if !mso]><!-->
<style>
  body,table,td,a{{ -webkit-text-size-adjust:100%; -ms-text-size-adjust:100%; }}
  table,td{{ mso-table-lspace:0pt; mso-table-rspace:0pt; }}
  img{{ -ms-interpolation-mode:bicubic; border:0; height:auto; line-height:100%; outline:none; text-decoration:none; }}
</style>
<!--<![endif]-->
</head>
<body style="margin:0;padding:0;background:#eef2f4;font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#0b1f2a;">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;">{preheader}</div>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#eef2f4;padding:32px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:560px;background:#ffffff;border-radius:18px;overflow:hidden;box-shadow:0 18px 40px rgba(11,31,42,.10);">
          <tr>
            <td style="background:linear-gradient(135deg,#0b1f2a 0%,#163948 55%,#1f7a72 120%);padding:28px 32px;color:#fff;">
              <div style="font-size:13px;letter-spacing:.12em;text-transform:uppercase;opacity:.75;margin-bottom:8px;">NumeroUNO</div>
              <div style="font-size:26px;font-weight:700;letter-spacing:-.02em;line-height:1.2;">{title}</div>
            </td>
          </tr>
          <tr>
            <td style="padding:32px;">
              {body_html}
            </td>
          </tr>
          <tr>
            <td style="padding:0 32px 28px;color:#5d6f79;font-size:12px;line-height:1.55;border-top:1px solid #e7e0d2;">
              <p style="margin:18px 0 0;">This message was sent by <strong>{frappe.utils.escape_html(brand["company"])}</strong>.</p>
              <p style="margin:6px 0 0;">Need help? Reply to this email or contact <a href="mailto:{brand["support_email"]}" style="color:#1f7a72;text-decoration:none;">{brand["support_email"]}</a>.</p>
            </td>
          </tr>
        </table>
        <p style="margin:18px 0 0;color:#8a97a0;font-size:11px;">© {frappe.utils.now_datetime().year} {frappe.utils.escape_html(brand["company"])}</p>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _otp_email_html(otp: str, minutes: int) -> str:
	brand = _brand()
	body = f"""
<p style="margin:0 0 16px;font-size:16px;line-height:1.55;color:#1a3644;">
  Use this one-time code to sign in to your <strong>Customer Invoice Portal</strong>.
</p>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:24px 0;">
  <tr>
    <td align="center" style="background:#f3efe6;border:1px solid #e7e0d2;border-radius:16px;padding:22px 16px;">
      <div style="font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:#5d6f79;margin-bottom:10px;">Your sign-in code</div>
      <div style="font-size:36px;font-weight:700;letter-spacing:10px;color:#0b1f2a;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;">{otp}</div>
      <div style="margin-top:12px;font-size:13px;color:#5d6f79;">Expires in {minutes} minutes</div>
    </td>
  </tr>
</table>
<p style="margin:0 0 18px;font-size:14px;line-height:1.55;color:#5d6f79;">
  Enter the code on the portal sign-in page. For your security, never share this code with anyone.
</p>
<table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:8px 0 20px;">
  <tr>
    <td style="border-radius:999px;background:#e85d3b;">
      <a href="{brand["portal_url"]}" style="display:inline-block;padding:13px 22px;color:#ffffff;text-decoration:none;font-weight:600;font-size:14px;">
        Open Customer Portal
      </a>
    </td>
  </tr>
</table>
<p style="margin:0;font-size:13px;line-height:1.5;color:#8a97a0;">
  If you didn’t request this code, you can ignore this email — your account remains secure.
</p>
"""
	return _email_shell(
		title="Your sign-in code",
		preheader=f"Your NumeroUNO portal code is {otp}. Expires in {minutes} minutes.",
		body_html=body,
	)


def send_portal_welcome_email(customer_doc, email: str):
	"""Send branded welcome email with portal link."""
	brand = _brand()
	name = frappe.utils.escape_html(customer_doc.customer_name or customer_doc.name)
	body = f"""
<p style="margin:0 0 14px;font-size:16px;line-height:1.55;color:#1a3644;">
  Hello {name},
</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.55;color:#1a3644;">
  Your <strong>NumeroUNO Customer Invoice Portal</strong> is ready. You can view open invoices,
  download details, and pay securely online with Stripe — anytime.
</p>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:20px 0;background:#faf8f3;border:1px solid #e7e0d2;border-radius:14px;">
  <tr>
    <td style="padding:16px 18px;font-size:14px;line-height:1.6;color:#1a3644;">
      <strong>How to sign in</strong><br/>
      1. Open the portal link below<br/>
      2. Enter this email: <strong>{frappe.utils.escape_html(email)}</strong><br/>
      3. We’ll send a one-time code to verify it’s you
    </td>
  </tr>
</table>
<table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:8px 0 22px;">
  <tr>
    <td style="border-radius:999px;background:#1f7a72;">
      <a href="{brand["portal_url"]}" style="display:inline-block;padding:14px 24px;color:#ffffff;text-decoration:none;font-weight:600;font-size:15px;">
        Go to Invoice Portal
      </a>
    </td>
  </tr>
</table>
<p style="margin:0;font-size:13px;line-height:1.55;color:#5d6f79;">
  Bookmark this link for later:<br/>
  <a href="{brand["portal_url"]}" style="color:#1f7a72;word-break:break-all;">{brand["portal_url"]}</a>
</p>
"""
	html = _email_shell(
		title="Welcome to your Invoice Portal",
		preheader="Your NumeroUNO invoice portal is ready — view and pay invoices online.",
		body_html=body,
	)
	frappe.sendmail(
		recipients=[email],
		subject=_("Welcome to your NumeroUNO Invoice Portal"),
		message=html,
		now=True,
		reference_doctype="Customer",
		reference_name=customer_doc.name,
	)


def _find_customers_for_email(email: str) -> list[dict]:
	"""Resolve Customer(s) linked to an email via Contact or Customer.email_id."""
	email = _normalize_email(email)
	if not email:
		return []

	customers = []

	# Contact → Dynamic Link → Customer
	contact_names = frappe.get_all(
		"Contact Email",
		filters={"email_id": email},
		pluck="parent",
	)
	if contact_names:
		links = frappe.get_all(
			"Dynamic Link",
			filters={
				"parenttype": "Contact",
				"parent": ("in", contact_names),
				"link_doctype": "Customer",
			},
			fields=["link_name"],
		)
		for link in links:
			if link.link_name and link.link_name not in [c["name"] for c in customers]:
				row = frappe.db.get_value(
					"Customer",
					link.link_name,
					["name", "customer_name", "customer_group", "territory"],
					as_dict=True,
				)
				if row:
					customers.append(row)

	# Direct Customer.email_id
	direct = frappe.get_all(
		"Customer",
		filters={"email_id": email},
		fields=["name", "customer_name", "customer_group", "territory"],
	)
	for row in direct:
		if row.name not in [c["name"] for c in customers]:
			customers.append(row)

	# Only customers explicitly granted portal access
	if _portal_access_enabled():
		customers = [c for c in customers if _has_portal_access(c["name"])]

	return customers


def _get_session() -> dict | None:
	token = frappe.request.cookies.get(PORTAL_TOKEN_COOKIE) if frappe.request else None
	if not token:
		token = frappe.form_dict.get("portal_token")
	if not token:
		return None
	data = frappe.cache().get_value(_cache_key_session(token))
	if not data:
		return None
	return frappe._dict(data)


def _require_session() -> frappe._dict:
	session = _get_session()
	if not session or not session.get("customer"):
		frappe.throw(_("Please sign in to continue."), frappe.AuthenticationError)
	return session


def _set_portal_cookie(token: str):
	# Max-Age in seconds
	max_age = PORTAL_SESSION_HOURS * 3600
	frappe.local.cookie_manager.set_cookie(
		PORTAL_TOKEN_COOKIE,
		token,
		max_age=max_age,
		httponly=True,
		samesite="Lax",
	)


def _clear_portal_cookie():
	frappe.local.cookie_manager.delete_cookie(PORTAL_TOKEN_COOKIE)


def _serialize_invoice(inv) -> dict:
	outstanding = flt(inv.outstanding_amount)
	grand = flt(inv.grand_total)
	paid = max(grand - outstanding, 0)
	if cint(inv.docstatus) == 2:
		status = "Cancelled"
	elif outstanding <= 0:
		status = "Paid"
	elif paid > 0:
		status = "Partly Paid"
	elif inv.status in ("Overdue",):
		status = "Overdue"
	else:
		status = inv.status or "Unpaid"

	return {
		"name": inv.name,
		"customer": inv.customer,
		"customer_name": inv.customer_name,
		"posting_date": inv.posting_date,
		"posting_date_fmt": formatdate(inv.posting_date) if inv.posting_date else "",
		"due_date": inv.due_date,
		"due_date_fmt": formatdate(inv.due_date) if inv.due_date else "",
		"currency": inv.currency,
		"grand_total": grand,
		"grand_total_fmt": fmt_money(grand, currency=inv.currency),
		"outstanding_amount": outstanding,
		"outstanding_fmt": fmt_money(outstanding, currency=inv.currency),
		"paid_amount": paid,
		"paid_fmt": fmt_money(paid, currency=inv.currency),
		"status": status,
		"can_pay": outstanding > 0 and cint(inv.docstatus) == 1,
		"doc_type": "Sales Invoice",
	}


def _serialize_sales_order(so) -> dict:
	grand = flt(so.grand_total)
	advance = flt(so.advance_paid)
	due = max(grand - advance, 0)
	billed = flt(getattr(so, "per_billed", 0) or 0)
	can_pay = (
		cint(so.docstatus) == 1
		and due > 0
		and so.status not in ("Closed", "Cancelled", "Completed")
		and billed < 99.99
	)
	return {
		"name": so.name,
		"customer": so.customer,
		"customer_name": so.customer_name,
		"transaction_date": so.transaction_date,
		"transaction_date_fmt": formatdate(so.transaction_date) if so.transaction_date else "",
		"currency": so.currency,
		"grand_total": grand,
		"grand_total_fmt": fmt_money(grand, currency=so.currency),
		"advance_paid": advance,
		"amount_due": due,
		"amount_due_fmt": fmt_money(due, currency=so.currency),
		"status": so.status,
		"per_billed": billed,
		"can_pay": can_pay,
		"doc_type": "Sales Order",
		"creates_invoice_after_pay": 1,
	}


@frappe.whitelist(allow_guest=True)
def request_login_otp(email: str | None = None):
	"""Send a one-time code to the customer's email."""
	email = _normalize_email(email or frappe.form_dict.get("email"))
	if not email or "@" not in email:
		frappe.throw(_("Enter a valid email address."))

	customers = _find_customers_for_email(email)
	if not customers:
		return {
			"ok": 0,
			"sent": 0,
			"message": _(
				"No portal access for this email. Ask accounts to enable "
				"“Allow Invoice Portal Access” on your Customer record and ensure your email is linked."
			),
		}

	otp = f"{random.randint(100000, 999999)}"
	# Keep a short history so older emails still work if the user resends by mistake
	prev = frappe.cache().get_value(_cache_key_otp(email)) or {}
	otps = [otp] + [
		x
		for x in (prev.get("otps") or ([prev["otp"]] if prev.get("otp") else []))
		if str(x) != str(otp)
	]
	otps = [str(x) for x in otps][:5]
	frappe.cache().set_value(
		_cache_key_otp(email),
		{
			"otp": otp,
			"otps": otps,
			"email": email,
			"customers": [c["name"] for c in customers],
		},
		expires_in_sec=OTP_EXPIRY_MINUTES * 60,
	)

	try:
		frappe.sendmail(
			recipients=[email],
			subject=_("Your NumeroUNO portal sign-in code"),
			message=_otp_email_html(otp, OTP_EXPIRY_MINUTES),
			now=True,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Customer Portal OTP Email")
		# In developer mode, surface OTP so QA can continue without mail
		if frappe.conf.developer_mode:
			return {
				"ok": 1,
				"sent": 1,
				"message": _("Code generated (dev mode — email failed)."),
				"dev_otp": otp,
			}
		frappe.throw(_("Could not send email. Please contact support."))

	result = {
		"ok": 1,
		"sent": 1,
		"message": _("A 6-digit code was sent to your email."),
	}
	# Helpful when mail is slow / misconfigured during rollout
	if frappe.conf.developer_mode:
		result["dev_otp"] = otp
	return result


@frappe.whitelist(allow_guest=True)
def verify_login_otp(email: str | None = None, otp: str | None = None, customer: str | None = None):
	"""Verify OTP and start a portal session."""
	email = _normalize_email(email or frappe.form_dict.get("email"))
	otp = (otp or frappe.form_dict.get("otp") or "").strip()
	customer = (customer or frappe.form_dict.get("customer") or "").strip()

	cached = frappe.cache().get_value(_cache_key_otp(email)) or {}
	valid_otps = [str(x) for x in (cached.get("otps") or [])]
	if cached.get("otp"):
		valid_otps = list(dict.fromkeys([str(cached.get("otp"))] + valid_otps))
	if not valid_otps:
		frappe.throw(_("Code expired or not found. Tap Continue again to get a new code."))
	if str(otp) not in valid_otps:
		frappe.throw(
			_("That code is incorrect. Open the newest email, or use the Dev code shown on screen.")
		)

	allowed = cached.get("customers") or []
	if not allowed:
		frappe.throw(_("No customer account found for this email."))

	if customer and customer not in allowed:
		frappe.throw(_("Invalid customer selection."))

	if not customer:
		if len(allowed) == 1:
			customer = allowed[0]
		else:
			# Multi-customer email — return searchable choices (prefer accounts with invoices)
			choices = _customer_choices_for_portal(allowed)
			return {
				"ok": 1,
				"needs_customer": 1,
				"customers": choices,
				"truncated": len(allowed) > len(choices),
				"total_matches": len(allowed),
			}

	if not _has_portal_access(customer):
		frappe.throw(_("Invoice portal access is not enabled for this customer."))

	cust = frappe.db.get_value(
		"Customer", customer, ["name", "customer_name", "customer_group"], as_dict=True
	)
	if not cust:
		frappe.throw(_("Customer not found."))

	token = _new_token()
	session = {
		"token": token,
		"email": email,
		"customer": cust.name,
		"customer_name": cust.customer_name,
		"customer_group": cust.customer_group,
		"logged_in_at": str(now_datetime()),
	}
	frappe.cache().set_value(
		_cache_key_session(token),
		session,
		expires_in_sec=PORTAL_SESSION_HOURS * 3600,
	)
	frappe.cache().delete_value(_cache_key_otp(email))
	_set_portal_cookie(token)

	return {"ok": 1, "session": {k: session[k] for k in ("email", "customer", "customer_name")}}


@frappe.whitelist(allow_guest=True)
def logout_portal():
	token = frappe.request.cookies.get(PORTAL_TOKEN_COOKIE) if frappe.request else None
	if token:
		frappe.cache().delete_value(_cache_key_session(token))
	_clear_portal_cookie()
	return {"ok": 1}


@frappe.whitelist(allow_guest=True)
def get_portal_session():
	session = _get_session()
	if not session:
		return {"authenticated": 0}
	return {
		"authenticated": 1,
		"email": session.email,
		"customer": session.customer,
		"customer_name": session.customer_name,
	}


@frappe.whitelist(allow_guest=True)
def get_dashboard():
	session = _require_session()
	customer = session.customer

	invoices = frappe.get_all(
		"Sales Invoice",
		filters={"customer": customer, "docstatus": 1},
		fields=[
			"name",
			"customer",
			"customer_name",
			"posting_date",
			"due_date",
			"currency",
			"grand_total",
			"outstanding_amount",
			"status",
			"docstatus",
		],
		order_by="posting_date desc",
		limit=200,
	)

	rows = [_serialize_invoice(inv) for inv in invoices]

	orders = frappe.get_all(
		"Sales Order",
		filters={
			"customer": customer,
			"docstatus": 1,
			"status": ("not in", ("Closed", "Cancelled")),
		},
		fields=[
			"name",
			"customer",
			"customer_name",
			"transaction_date",
			"currency",
			"grand_total",
			"advance_paid",
			"per_billed",
			"status",
			"docstatus",
		],
		order_by="transaction_date desc",
		limit=100,
	)
	order_rows = [_serialize_sales_order(so) for so in orders]
	payable_orders = [o for o in order_rows if o["can_pay"]]

	portal_requests = []
	if frappe.db.exists("DocType", "Portal Payment Request"):
		pprs = frappe.get_all(
			"Portal Payment Request",
			filters={"customer": customer, "docstatus": 1, "status": ("in", ("Open", "Paid", "Allocated"))},
			fields=[
				"name",
				"customer",
				"customer_name",
				"posting_date",
				"currency",
				"amount",
				"description",
				"status",
				"payment_entry",
				"sales_invoice",
				"paid_on",
			],
			order_by="modified desc",
			limit=100,
		)
		portal_requests = [_serialize_portal_payment_request(r) for r in pprs]

	payable_pprs = [p for p in portal_requests if p["can_pay"]]
	paid_pprs = [p for p in portal_requests if p["status"] in ("Paid", "Allocated")]
	ppr_due = sum(p["amount"] for p in payable_pprs)
	ppr_paid_total = sum(p["amount"] for p in paid_pprs)

	outstanding = sum(r["outstanding_amount"] for r in rows if r["can_pay"])
	order_due = sum(o["amount_due"] for o in payable_orders)
	paid_total = sum(r["paid_amount"] for r in rows) + ppr_paid_total
	currency = (
		rows[0]["currency"]
		if rows
		else (
			order_rows[0]["currency"]
			if order_rows
			else (portal_requests[0]["currency"] if portal_requests else "AED")
		)
	)

	return {
		"customer": session.customer,
		"customer_name": session.customer_name,
		"email": session.email,
		"metrics": {
			"invoice_count": len(rows),
			"unpaid_count": len([r for r in rows if r["can_pay"]]),
			"order_payable_count": len(payable_orders),
			"portal_request_count": len(payable_pprs),
			"portal_paid_count": len(paid_pprs),
			"outstanding": outstanding,
			"outstanding_fmt": fmt_money(outstanding, currency=currency),
			"order_due": order_due,
			"order_due_fmt": fmt_money(order_due, currency=currency),
			"portal_due": ppr_due,
			"portal_due_fmt": fmt_money(ppr_due, currency=currency),
			"paid_total": paid_total,
			"paid_fmt": fmt_money(paid_total, currency=currency),
			"currency": currency,
		},
		"invoices": rows,
		"orders": order_rows,
		"portal_requests": portal_requests,
		"stripe_ready": _stripe_ready(),
	}


def _serialize_portal_payment_request(row) -> dict:
	amount = flt(row.amount)
	can_pay = row.status == "Open"
	return {
		"name": row.name,
		"customer": row.customer,
		"customer_name": row.customer_name,
		"posting_date": row.posting_date,
		"posting_date_fmt": formatdate(row.posting_date) if row.posting_date else "",
		"currency": row.currency,
		"amount": amount,
		"amount_fmt": fmt_money(amount, currency=row.currency),
		"description": row.description or "",
		"status": row.status,
		"payment_entry": row.payment_entry,
		"sales_invoice": row.sales_invoice,
		"paid_on": row.get("paid_on"),
		"paid_on_fmt": formatdate(row.paid_on) if row.get("paid_on") else "",
		"can_pay": can_pay,
		"doc_type": "Portal Payment Request",
	}


def _customer_choices_for_portal(customer_names: list[str], limit: int = 80) -> list[dict]:
	"""Build account picker rows; prefer customers that have submitted invoices."""
	if not customer_names:
		return []

	# Cap work for shared/placeholder emails (e.g. test@…)
	names = list(dict.fromkeys(customer_names))
	meta_rows = frappe.db.sql(
		"""
		select
			si.customer as name,
			c.customer_name,
			count(*) as invoice_count,
			coalesce(sum(si.outstanding_amount), 0) as outstanding
		from `tabSales Invoice` si
		inner join `tabCustomer` c on c.name = si.customer
		where si.customer in %(customers)s and si.docstatus = 1
		group by si.customer, c.customer_name
		order by outstanding desc, invoice_count desc, c.customer_name asc
		limit %(limit)s
		""",
		{"customers": names, "limit": limit},
		as_dict=True,
	)

	if meta_rows:
		return [
			{
				"name": r.name,
				"customer_name": r.customer_name,
				"invoice_count": cint(r.invoice_count),
				"outstanding": flt(r.outstanding),
			}
			for r in meta_rows
		]

	# No invoices for any match — return a small alphabetical sample
	rows = frappe.get_all(
		"Customer",
		filters={"name": ("in", names[:limit])},
		fields=["name", "customer_name"],
		order_by="customer_name asc",
		limit=limit,
	)
	for row in rows:
		row["invoice_count"] = 0
		row["outstanding"] = 0
	return rows


def _stripe_ready() -> bool:
	if not frappe.db.exists("DocType", "Payment Gateway Account"):
		return False
	# Prefer Stripe gateway accounts
	stripe = frappe.db.exists(
		"Payment Gateway Account",
		{"payment_gateway": ("like", "%Stripe%")},
	)
	if stripe:
		return True
	return bool(frappe.db.exists("Payment Gateway Account", {"is_default": 1}))


# Stripe currency minimums (major units). Source: Stripe docs.
STRIPE_MIN_AMOUNT = {
	"AED": 2.00,
	"USD": 0.50,
	"EUR": 0.50,
	"GBP": 0.30,
	"SAR": 2.00,
}


def _validate_stripe_minimum(amount, currency: str):
	"""Block checkout below Stripe's per-currency minimum charge."""
	currency = (currency or "").upper()
	minimum = STRIPE_MIN_AMOUNT.get(currency)
	if minimum is None:
		return
	if flt(amount) + 1e-9 < flt(minimum):
		frappe.throw(
			_(
				"Stripe cannot charge less than {0}. This invoice outstanding is {1}. "
				"Please pay offline or ask accounts to adjust the invoice."
			).format(
				fmt_money(minimum, currency=currency),
				fmt_money(amount, currency=currency),
			)
		)


@frappe.whitelist(allow_guest=True)
def get_invoice(name: str | None = None):
	session = _require_session()
	name = (name or frappe.form_dict.get("name") or "").strip()
	if not name:
		frappe.throw(_("Invoice is required."))

	inv = frappe.get_doc("Sales Invoice", name)
	if inv.customer != session.customer or cint(inv.docstatus) != 1:
		frappe.throw(_("Invoice not found."), frappe.PermissionError)

	items = []
	for row in inv.items:
		items.append(
			{
				"item_code": row.item_code,
				"item_name": row.item_name,
				"qty": row.qty,
				"rate": row.rate,
				"amount": row.amount,
				"amount_fmt": fmt_money(row.amount, currency=inv.currency),
			}
		)

	data = _serialize_invoice(inv)
	data["items"] = items
	data["company"] = inv.company
	data["stripe_ready"] = _stripe_ready()
	return data


@frappe.whitelist(allow_guest=True)
def create_stripe_payment(
	invoice: str | None = None,
	sales_order: str | None = None,
	portal_payment_request: str | None = None,
):
	"""
	Return in-portal Stripe checkout payload.

	Flows:
	1) Sales Invoice → ERPNext Payment Request → pay
	2) Sales Order → ERPNext Payment Request → pay → auto invoice
	3) Portal Payment Request (ad-hoc amount + description) → pay → customer advance
	"""
	session = _require_session()
	invoice = (invoice or frappe.form_dict.get("invoice") or "").strip()
	sales_order = (sales_order or frappe.form_dict.get("sales_order") or "").strip()
	portal_payment_request = (
		portal_payment_request or frappe.form_dict.get("portal_payment_request") or ""
	).strip()

	if not invoice and not sales_order and not portal_payment_request:
		frappe.throw(_("Invoice, Sales Order, or Portal Payment Request is required."))

	if not _stripe_ready():
		frappe.throw(
			_(
				"Online payments are not configured yet. Please contact accounts or try again later."
			)
		)

	# ── Ad-hoc Portal Payment Request (no SI/SO yet) ──
	if portal_payment_request:
		ppr = frappe.get_doc("Portal Payment Request", portal_payment_request)
		if ppr.customer != session.customer or cint(ppr.docstatus) != 1:
			frappe.throw(_("Payment request not found."), frappe.PermissionError)
		if ppr.status != "Open":
			frappe.throw(_("This payment request is not open for payment."))
		_validate_stripe_minimum(ppr.amount, ppr.currency)
		if not ppr.payment_gateway:
			ppr._set_gateway_defaults()
			ppr.db_set(
				{
					"payment_gateway": ppr.payment_gateway,
					"payment_account": ppr.payment_account,
				},
				update_modified=False,
			)

		publishable_key = _get_stripe_publishable_key(ppr.payment_gateway)
		if not publishable_key:
			frappe.throw(_("Stripe publishable key is missing. Check Stripe Settings."))

		amount = flt(ppr.amount)
		checkout = {
			"publishable_key": publishable_key,
			"amount": amount,
			"amount_fmt": fmt_money(amount, currency=ppr.currency),
			"currency": ppr.currency,
			"title": ppr.company,
			"description": ppr.description or ppr.name,
			"reference_doctype": "Portal Payment Request",
			"reference_docname": ppr.name,
			"payer_name": session.customer_name,
			"payer_email": session.email,
			"payment_gateway": ppr.payment_gateway,
			"redirect_to": "/customer-portal",
		}
		return {
			"ok": 1,
			"embed": 1,
			"payment_request": ppr.name,
			"checkout": checkout,
			"creates_invoice_after_pay": 0,
		}

	from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request

	frappe.set_user("Administrator")
	try:
		if sales_order:
			so = frappe.get_doc("Sales Order", sales_order)
			if so.customer != session.customer or cint(so.docstatus) != 1:
				frappe.throw(_("Order not found."), frappe.PermissionError)
			if so.status in ("Closed", "Cancelled"):
				frappe.throw(_("This order cannot be paid online."))

			amount = flt(so.grand_total) - flt(so.advance_paid)
			if amount <= 0:
				frappe.throw(_("This order is already fully paid."))
			_validate_stripe_minimum(amount, so.currency)

			pr = make_payment_request(
				dt="Sales Order",
				dn=so.name,
				party_type="Customer",
				party=so.customer,
				party_name=so.customer_name,
				recipient_id=session.email,
				mute_email=1,
				submit_doc=1,
				return_doc=1,
			)
			description = _("Payment for Sales Order {0}").format(so.name)
			company = so.company
		else:
			inv = frappe.get_doc("Sales Invoice", invoice)
			if inv.customer != session.customer or cint(inv.docstatus) != 1:
				frappe.throw(_("Invoice not found."), frappe.PermissionError)
			if flt(inv.outstanding_amount) <= 0:
				frappe.throw(_("This invoice is already paid."))
			_validate_stripe_minimum(inv.outstanding_amount, inv.currency)

			pr = make_payment_request(
				dt="Sales Invoice",
				dn=inv.name,
				party_type="Customer",
				party=inv.customer,
				party_name=inv.customer_name,
				recipient_id=session.email,
				mute_email=1,
				submit_doc=1,
				return_doc=1,
			)
			description = _("Payment for Invoice {0}").format(inv.name)
			company = inv.company

		if not pr.payment_url:
			try:
				url = pr.get_payment_url()
				if url:
					pr.db_set("payment_url", url, update_modified=False)
			except Exception:
				frappe.log_error(frappe.get_traceback(), "Customer Portal PR URL")
	finally:
		frappe.set_user("Guest")

	publishable_key = _get_stripe_publishable_key(pr.payment_gateway)
	if not publishable_key:
		frappe.throw(_("Stripe publishable key is missing. Check Stripe Settings."))

	amount = flt(pr.grand_total)
	checkout = {
		"publishable_key": publishable_key,
		"amount": amount,
		"amount_fmt": fmt_money(amount, currency=pr.currency),
		"currency": pr.currency,
		"title": company,
		"description": description,
		"reference_doctype": "Payment Request",
		"reference_docname": pr.name,
		"payer_name": session.customer_name,
		"payer_email": session.email,
		"payment_gateway": pr.payment_gateway,
		"redirect_to": "/customer-portal",
	}

	return {
		"ok": 1,
		"embed": 1,
		"payment_request": pr.name,
		"checkout": checkout,
		"creates_invoice_after_pay": 1 if sales_order else 0,
	}


def _get_stripe_publishable_key(payment_gateway: str | None) -> str | None:
	if not payment_gateway:
		return None
	controller = frappe.db.get_value("Payment Gateway", payment_gateway, "gateway_controller")
	if not controller:
		return None
	return frappe.db.get_value("Stripe Settings", controller, "publishable_key")


@frappe.whitelist(allow_guest=True)
def complete_stripe_payment(
	stripe_token_id: str | None = None,
	payment_request: str | None = None,
	reference_doctype: str | None = None,
	reference_docname: str | None = None,
):
	"""Charge card via Stripe from the branded portal (same backend as stripe_checkout)."""
	session = _require_session()
	stripe_token_id = (stripe_token_id or frappe.form_dict.get("stripe_token_id") or "").strip()
	payment_request = (payment_request or frappe.form_dict.get("payment_request") or "").strip()
	reference_doctype = (
		reference_doctype or frappe.form_dict.get("reference_doctype") or ""
	).strip()
	reference_docname = (
		reference_docname or frappe.form_dict.get("reference_docname") or payment_request or ""
	).strip()

	if not stripe_token_id or not reference_docname:
		frappe.throw(_("Payment details are incomplete."))

	# Resolve reference: Portal Payment Request OR classic Payment Request
	if not reference_doctype:
		if frappe.db.exists("Portal Payment Request", reference_docname):
			reference_doctype = "Portal Payment Request"
		else:
			reference_doctype = "Payment Request"

	doc = frappe.get_doc(reference_doctype, reference_docname)

	if reference_doctype == "Portal Payment Request":
		if doc.customer != session.customer:
			frappe.throw(_("Payment request not found."), frappe.PermissionError)
		if doc.status == "Paid":
			return {"ok": 1, "status": "Completed", "redirect_to": "/customer-portal"}
		amount = flt(doc.amount)
		currency = doc.currency
		company = doc.company
		description = doc.description or doc.name
		payment_gateway = doc.payment_gateway
	else:
		ref_customer = frappe.db.get_value(doc.reference_doctype, doc.reference_name, "customer")
		if ref_customer != session.customer:
			frappe.throw(_("Payment Request not found."), frappe.PermissionError)
		if doc.status == "Paid":
			return {"ok": 1, "status": "Completed", "redirect_to": "/customer-portal"}
		amount = flt(doc.grand_total)
		currency = doc.currency
		company = doc.company
		description = doc.subject or doc.name
		payment_gateway = doc.payment_gateway

	from payments.payment_gateways.doctype.stripe_settings.stripe_settings import (
		get_gateway_controller,
	)

	gateway_controller = get_gateway_controller(
		reference_doctype, reference_docname, payment_gateway
	)
	data = {
		"amount": amount,
		"title": company,
		"description": description,
		"reference_doctype": reference_doctype,
		"reference_docname": reference_docname,
		"payer_name": session.customer_name,
		"payer_email": session.email,
		"currency": currency,
		"payment_gateway": payment_gateway,
		"stripe_token_id": stripe_token_id,
		"redirect_to": "/customer-portal",
	}

	previous = frappe.session.user
	try:
		frappe.set_user("Administrator")
		result = frappe.get_doc("Stripe Settings", gateway_controller).create_request(data)
	finally:
		frappe.set_user(previous)

	status = (result or {}).get("status")
	redirect_to = (result or {}).get("redirect_to") or "/customer-portal"
	if status == "Completed" or (isinstance(redirect_to, str) and "payment-success" in redirect_to):
		redirect_to = "/customer-portal"

	return {
		"ok": 1 if status == "Completed" else 0,
		"status": status,
		"redirect_to": redirect_to,
		"message": (
			_("Payment successful. Your receipt will appear shortly.")
			if status == "Completed"
			else _("Payment could not be completed. Please try another card or contact accounts.")
		),
	}
