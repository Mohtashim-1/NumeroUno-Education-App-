# Copyright (c) 2026, NumeroUNO and contributors
# License: MIT

"""Daily pro-rata accrual for NUTC Annual Leave.

Opening balances were imported once; HRMS earned leave was disabled (is_earned_leave=0)
and there are no Leave Policy Assignments — so balances never increased after import.

This job runs daily and adds each employee's monthly entitlement spread across calendar days
(2.0 or 2.5 days/month per get_annual_accrual_rate), idempotent per employee per day.
"""

from __future__ import annotations

import calendar

import frappe
from frappe.utils import flt, getdate, today

from numerouno.numerouno.hr.leave_policy_setup import (
	ALLOCATE_TO,
	ANNUAL_LEAVE,
	COMPANY,
	get_annual_accrual_rate,
)

ACCRUAL_NOTE_PREFIX = "NUTC daily accrual"


def _active_annual_allocation(employee: str, as_on):
	return frappe.db.get_value(
		"Leave Allocation",
		{
			"employee": employee,
			"leave_type": ANNUAL_LEAVE,
			"docstatus": 1,
			"from_date": ("<=", as_on),
			"to_date": (">=", as_on),
		},
		["name", "from_date", "to_date", "total_leaves_allocated"],
		as_dict=True,
	)


def _accrual_already_posted(allocation_name: str, accrual_date) -> bool:
	"""One accrual ledger row per allocation per day."""
	return bool(
		frappe.db.exists(
			"Leave Ledger Entry",
			{
				"transaction_type": "Leave Allocation",
				"transaction_name": allocation_name,
				"leave_type": ANNUAL_LEAVE,
				"from_date": accrual_date,
				"to_date": accrual_date,
				"docstatus": 1,
				"leaves": (">", 0),
			},
		)
	)


def _daily_accrual_amount(date_of_joining, as_on) -> float:
	as_on = getdate(as_on)
	monthly = get_annual_accrual_rate(date_of_joining, as_on)
	if monthly <= 0:
		return 0.0
	days_in_month = calendar.monthrange(as_on.year, as_on.month)[1]
	raw = monthly / days_in_month
	# Keep at least 0.01 day; avoid round(x*4)/4 zeroing small daily amounts (e.g. 2/30)
	return max(flt(raw, 4), 0.01)


def accrue_nutc_annual_leave_daily(force_date=None):
	"""Accrue today's share of annual leave for all active employees."""
	from hrms.hr.doctype.leave_ledger_entry.leave_ledger_entry import create_leave_ledger_entry

	as_on = getdate(force_date or today())
	if as_on > getdate(ALLOCATE_TO):
		return {"skipped": "after_allocate_to", "date": str(as_on)}

	employees = frappe.get_all(
		"Employee",
		filters={"status": "Active", "company": COMPANY},
		fields=["name", "date_of_joining"],
	)
	if not employees:
		employees = frappe.get_all(
			"Employee",
			filters={"status": "Active"},
			fields=["name", "date_of_joining"],
		)

	accrued = []
	skipped = []
	errors = []

	for emp in employees:
		if not emp.date_of_joining:
			skipped.append({"employee": emp.name, "reason": "no_doj"})
			continue

		daily = _daily_accrual_amount(emp.date_of_joining, as_on)
		if daily <= 0:
			skipped.append({"employee": emp.name, "reason": "zero_rate"})
			continue

		alloc = _active_annual_allocation(emp.name, as_on)
		if not alloc:
			skipped.append({"employee": emp.name, "reason": "no_allocation"})
			continue

		if _accrual_already_posted(alloc.name, as_on):
			skipped.append({"employee": emp.name, "reason": "already_posted"})
			continue

		try:
			doc = frappe.get_doc("Leave Allocation", alloc.name)
			new_total = flt(doc.total_leaves_allocated) + daily
			doc.db_set("total_leaves_allocated", new_total, update_modified=False)
			create_leave_ledger_entry(
				doc,
				{"leaves": daily, "from_date": as_on, "to_date": as_on, "is_carry_forward": 0},
				submit=True,
			)
			accrued.append({"employee": emp.name, "allocation": alloc.name, "days": daily})
		except Exception as exc:
			frappe.log_error(frappe.get_traceback(), "NUTC Daily Leave Accrual")
			skipped.append({"employee": emp.name, "reason": "error"})
			if len(errors) < 3:
				errors.append({"employee": emp.name, "error": str(exc)})

	if accrued:
		frappe.db.commit()
	from collections import Counter

	reason_counts = Counter(row.get("reason") for row in skipped)
	return {
		"date": str(as_on),
		"accrued_count": len(accrued),
		"accrued": accrued[:20],
		"skipped_count": len(skipped),
		"skip_reasons": dict(reason_counts),
		"skipped_sample": skipped[:8],
		"sample_errors": errors,
	}


@frappe.whitelist()
def run_nutc_leave_accrual(force_date=None):
	frappe.only_for(("System Manager", "HR Manager"))
	return accrue_nutc_annual_leave_daily(force_date=force_date)
