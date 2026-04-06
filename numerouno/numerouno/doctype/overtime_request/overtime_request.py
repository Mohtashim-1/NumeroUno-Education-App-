# Copyright (c) 2026, Numerouno and contributors
# For license information, please see license.txt

from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import escape_html, format_date, format_time, get_fullname, get_url


class OvertimeRequest(Document):
    def validate(self):
        self._set_employee_from_user()
        self._set_manager_chain()
        self._calculate_overtime_hours()
        self._set_default_status()

    def on_update(self):
        self._notify_hr_final_approval()

    def _set_employee_from_user(self):
        if self.employee:
            return

        employee = frappe.db.get_value(
            "Employee",
            {"user_id": frappe.session.user, "status": "Active"},
            "name",
        )

        if employee:
            self.employee = employee
            return

        if "System Manager" not in frappe.get_roles(frappe.session.user):
            frappe.throw(_("No active Employee record is linked to your user."))

    def _set_manager_chain(self):
        if not self.employee:
            return

        direct_manager_employee = frappe.db.get_value("Employee", self.employee, "reports_to")
        direct_manager_user = (
            frappe.db.get_value("Employee", direct_manager_employee, "user_id")
            if direct_manager_employee
            else None
        )

        next_manager_employee = (
            frappe.db.get_value("Employee", direct_manager_employee, "reports_to")
            if direct_manager_employee
            else None
        )
        next_manager_user = (
            frappe.db.get_value("Employee", next_manager_employee, "user_id")
            if next_manager_employee
            else None
        )

        self.direct_manager = direct_manager_user
        self.next_manager = next_manager_user

        if not self.hr_approver:
            self.hr_approver = _get_default_hr_approver()

        if not self.direct_manager:
            frappe.throw(_("Direct manager is not configured for employee {0}.").format(self.employee))

    def _calculate_overtime_hours(self):
        self.overtime_hours = compute_overtime_hours(self.date, self.time_from, self.time_to)

    def _set_default_status(self):
        if not self.status:
            self.status = "Draft"

    def _notify_hr_final_approval(self):
        if self.status != "Approved":
            return

        prev = self.get_doc_before_save()
        if not prev or prev.get("status") == "Approved":
            return

        try:
            from numerouno.numerouno.notifications.notification_config import NotificationConfig

            if not NotificationConfig.should_send_emails():
                return
        except Exception:
            pass

        if not _overtime_approval_recipient_emails(self):
            frappe.msgprint(
                _(
                    "This request is approved, but no email addresses were found for the employee or approvers. "
                    "Check Employee and User records have valid emails."
                ),
                title=_("Overtime request approved"),
                indicator="orange",
            )
            return

        approver_name = get_fullname(frappe.session.user)
        frappe.enqueue(
            "numerouno.numerouno.doctype.overtime_request.overtime_request.send_overtime_hr_approval_emails",
            queue="short",
            docname=self.name,
            approved_by=approver_name,
            enqueue_after_commit=True,
        )

        frappe.msgprint(
            _(
                "Everyone in the approval chain and the employee have been emailed a summary of this approved request."
            ),
            title=_("Overtime request approved"),
            indicator="green",
        )


def _get_default_hr_approver():
    hr_users = frappe.get_all(
        "Has Role",
        filters={"role": "HR Manager", "parenttype": "User"},
        pluck="parent",
        limit=1,
    )
    return hr_users[0] if hr_users else None


def get_permission_query_conditions(user=None):
    user = user or frappe.session.user

    if not user or user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return ""

    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    conditions = [
        "`tabOvertime Request`.`owner` = {0}".format(frappe.db.escape(user)),
        "`tabOvertime Request`.`direct_manager` = {0}".format(frappe.db.escape(user)),
        "`tabOvertime Request`.`next_manager` = {0}".format(frappe.db.escape(user)),
        "`tabOvertime Request`.`hr_approver` = {0}".format(frappe.db.escape(user)),
    ]

    if employee:
        conditions.append("`tabOvertime Request`.`employee` = {0}".format(frappe.db.escape(employee)))

    if "HR Manager" in frappe.get_roles(user):
        conditions.append("`tabOvertime Request`.`name` is not null")

    return "({0})".format(" or ".join(conditions))


def has_permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user

    if not user:
        return False

    if user == "Administrator":
        return True

    roles = set(frappe.get_roles(user))
    if "System Manager" in roles:
        return True

    if permission_type == "create":
        return "Employee" in roles or "Employee Self Service" in roles or "HR Manager" in roles

    if user in {doc.owner, doc.direct_manager, doc.next_manager, doc.hr_approver}:
        return True

    if doc.employee and frappe.db.get_value("Employee", doc.employee, "user_id") == user:
        return True

    if "HR Manager" in roles:
        return True

    return False


def send_overtime_hr_approval_emails(docname, approved_by=None):
    doc = frappe.get_doc("Overtime Request", docname)
    if doc.status != "Approved":
        return

    recipients = _overtime_approval_recipient_emails(doc)
    if not recipients:
        return

    subject = "Overtime approved: {0} — {1}".format(doc.name, doc.employee_name or doc.employee)
    doc_url = get_url(f"/app/overtime-request/{doc.name}")
    hours_display = doc.overtime_hours if doc.overtime_hours is not None else 0
    body = _build_hr_approval_email_html(
        doc=doc,
        doc_url=doc_url,
        approved_by=approved_by or _("HR"),
        hours_display=hours_display,
    )

    for email in recipients:
        try:
            frappe.sendmail(
                recipients=[email],
                subject=subject,
                message=body,
                reference_doctype=doc.doctype,
                reference_name=doc.name,
            )
        except frappe.OutgoingEmailError:
            frappe.log_error(frappe.get_traceback(), "Overtime HR approval email failed")
            return


def _user_email(user):
    if not user:
        return None
    return frappe.db.get_value("User", user, "email")


def _employee_contact_email(employee):
    if not employee:
        return None
    user_id = frappe.db.get_value("Employee", employee, "user_id")
    email = _user_email(user_id)
    if email:
        return email
    row = frappe.db.get_value(
        "Employee",
        employee,
        ["prefered_email", "company_email", "personal_email"],
        as_dict=True,
    )
    if not row:
        return None
    for key in ("prefered_email", "company_email", "personal_email"):
        if row.get(key):
            return row[key]
    return None


def _overtime_approval_recipient_emails(doc):
    emails = []
    for user in (
        doc.owner,
        doc.direct_manager,
        doc.next_manager,
        doc.hr_approver,
    ):
        e = _user_email(user)
        if e:
            emails.append(e)

    emp_email = _employee_contact_email(doc.employee)
    if emp_email:
        emails.append(emp_email)

    seen = set()
    out = []
    for e in emails:
        el = (e or "").strip().lower()
        if not el or el in seen or el == "guest@example.com":
            continue
        seen.add(el)
        out.append(e.strip())
    return out


def _build_hr_approval_email_html(doc, doc_url, approved_by, hours_display):
    date_s = format_date(doc.date) if doc.date else "—"
    time_from_s = format_time(doc.time_from) if doc.time_from else "—"
    time_to_s = format_time(doc.time_to) if doc.time_to else "—"
    reason = escape_html((doc.reason_for_work or "").strip()) or "—"
    dept = escape_html(doc.department or "—")
    emp_name = escape_html(doc.employee_name or doc.employee or "—")
    approver = escape_html(str(approved_by))
    req_id = escape_html(doc.name)

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;background:#f0f2f5;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f0f2f5;padding:24px 12px;">
    <tr><td align="center">
      <table role="presentation" width="100%" style="max-width:560px;background:#ffffff;border-radius:12px;overflow:hidden;
        box-shadow:0 4px 24px rgba(15,23,42,0.08);font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;">
        <tr>
          <td style="background:linear-gradient(135deg,#0d9488 0%,#0f766e 100%);padding:22px 24px;color:#fff;">
            <p style="margin:0;font-size:11px;letter-spacing:0.12em;text-transform:uppercase;opacity:0.9;">Overtime request</p>
            <h1 style="margin:6px 0 0;font-size:22px;font-weight:600;line-height:1.25;">Approved by HR</h1>
            <p style="margin:8px 0 0;font-size:14px;opacity:0.95;">{emp_name} · {req_id}</p>
          </td>
        </tr>
        <tr><td style="padding:22px 24px 8px;">
          <p style="margin:0 0 16px;font-size:15px;line-height:1.55;color:#334155;">
            This overtime request has been <strong style="color:#0f766e;">fully approved</strong> (final sign-off by {approver}).
            A copy is sent to the employee and everyone who took part in the approval chain.
          </p>
          <table role="presentation" width="100%" style="border-collapse:collapse;font-size:14px;color:#1e293b;">
            <tr><td style="padding:10px 0;border-bottom:1px solid #e2e8f0;color:#64748b;width:38%;">Date</td>
                <td style="padding:10px 0;border-bottom:1px solid #e2e8f0;font-weight:500;">{date_s}</td></tr>
            <tr><td style="padding:10px 0;border-bottom:1px solid #e2e8f0;color:#64748b;">Time</td>
                <td style="padding:10px 0;border-bottom:1px solid #e2e8f0;font-weight:500;">{time_from_s} – {time_to_s}</td></tr>
            <tr><td style="padding:10px 0;border-bottom:1px solid #e2e8f0;color:#64748b;">Overtime hours</td>
                <td style="padding:10px 0;border-bottom:1px solid #e2e8f0;font-weight:500;">{hours_display}</td></tr>
            <tr><td style="padding:10px 0;border-bottom:1px solid #e2e8f0;color:#64748b;vertical-align:top;">Reason</td>
                <td style="padding:10px 0;border-bottom:1px solid #e2e8f0;line-height:1.5;">{reason}</td></tr>
            <tr><td style="padding:10px 0;color:#64748b;">Department</td>
                <td style="padding:10px 0;font-weight:500;">{dept}</td></tr>
          </table>
        </td></tr>
        <tr><td style="padding:0 24px 28px;">
          <a href="{escape_html(doc_url)}" style="display:inline-block;background:#0d9488;color:#fff !important;
            text-decoration:none;padding:12px 22px;border-radius:8px;font-size:14px;font-weight:600;">
            Open in NumeroUNO
          </a>
          <p style="margin:16px 0 0;font-size:12px;color:#94a3b8;line-height:1.45;">
            If the button does not work, copy this link:<br/>
            <span style="color:#64748b;word-break:break-all;">{escape_html(doc_url)}</span>
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def compute_overtime_hours(request_date, time_from, time_to):
    if not time_from or not time_to:
        return 0

    parsed_time_from = datetime.strptime(str(time_from), "%H:%M:%S")
    parsed_time_to = datetime.strptime(str(time_to), "%H:%M:%S")

    if parsed_time_to <= parsed_time_from:
        parsed_time_to += timedelta(days=1)

    duration = parsed_time_to - parsed_time_from
    duration_hours = round(duration.total_seconds() / 3600, 2)

    if duration_hours > 0 and is_sunday(request_date):
        return 8

    return duration_hours


def is_sunday(request_date):
    if not request_date:
        return False

    return datetime.strptime(str(request_date), "%Y-%m-%d").weekday() == 6
