# Copyright (c) 2026, Numerouno and contributors
# For license information, please see license.txt

from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.model.document import Document


class OvertimeRequest(Document):
    def validate(self):
        self._set_employee_from_user()
        self._set_manager_chain()
        self._calculate_overtime_hours()
        self._set_default_status()

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
