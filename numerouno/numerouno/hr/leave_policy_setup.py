# Copyright (c) 2026, NumeroUNO and contributors
# License: MIT

"""Implement NUTC HR Leave Policy and import opening Annual Leave balances.

Policy highlights (see company HR policy document):
- 6-month probation; annual leave accrues but becomes available after probation
- 6–12 months service: 2 days/month (including first 6 months, once confirmed)
- 1+ year service: 30 days/year (2.5 days/month)
- Carry forward max 15 days, expire after first quarter (~90 days)
- Sick leave after probation: 15 full / 30 half / 45 unpaid (90 total)

Opening balances from "Annual Leave Balance Till 14.07.2026" are loaded as
Leave Allocations (with ledger adjustments for negatives).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import frappe
from frappe.utils import add_months, cint, flt, getdate, today

COMPANY = "Numero Uno Training and Consulting LLC"
LEAVE_PERIOD_NAME = "2026"
ANNUAL_LEAVE = "Annual Leave"
SICK_FULL = "Sick Leave"
SICK_HALF = "Sick Leave - Half Pay"
SICK_UNPAID = "Sick Leave - Unpaid"
POLICY_NAME = "NUTC Leave Policy 2026"
BALANCE_AS_ON = "2026-07-14"
ALLOCATE_TO = "2026-12-31"
PROBATION_DAYS = 180


def _norm(name: str) -> str:
	return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()


def _name_tokens(name: str) -> set[str]:
	stop = {"bin", "al", "ul", "the", "of", "and", "mr", "mrs", "ms"}
	return {t for t in _norm(name).split() if len(t) > 1 and t not in stop}


def configure_leave_types():
	"""Align Leave Types with HR policy."""
	# Annual Leave — policy base
	al = frappe.get_doc("Leave Type", ANNUAL_LEAVE)
	al.max_leaves_allowed = 0  # allow opening balances above 30; entitlement enforced by policy/accrual
	al.applicable_after = PROBATION_DAYS
	al.max_continuous_days_allowed = 30
	al.is_carry_forward = 1
	al.maximum_carry_forwarded_leaves = 15
	al.expire_carry_forwarded_leaves_after_days = 90  # first quarter
	al.allow_encashment = 1
	al.max_encashable_leaves = 30
	al.allow_negative = 1
	al.allow_over_allocation = 1
	al.include_holiday = 1
	al.is_earned_leave = 0  # enable after Leave Policy Assignments are rolled out
	al.earned_leave_frequency = "Monthly"
	al.allocate_on_day = "Last Day"
	al.rounding = "0.5"
	al.save(ignore_permissions=True)

	# Sick Leave — first 15 days fully paid (after probation)
	sl = frappe.get_doc("Leave Type", SICK_FULL)
	sl.max_leaves_allowed = 15
	sl.applicable_after = PROBATION_DAYS
	sl.is_carry_forward = 0
	sl.allow_encashment = 0
	sl.allow_negative = 0
	sl.include_holiday = 1
	sl.is_lwp = 0
	sl.is_ppl = 0
	sl.save(ignore_permissions=True)

	# Sick Leave — Half Pay (next 30 days)
	if not frappe.db.exists("Leave Type", SICK_HALF):
		half = frappe.new_doc("Leave Type")
		half.leave_type_name = SICK_HALF
	else:
		half = frappe.get_doc("Leave Type", SICK_HALF)
	half.max_leaves_allowed = 30
	half.applicable_after = PROBATION_DAYS
	half.is_ppl = 1
	half.fraction_of_daily_salary_per_leave = 0.5
	half.include_holiday = 1
	half.is_carry_forward = 0
	half.allow_encashment = 0
	half.save(ignore_permissions=True)

	# Sick Leave — Unpaid (final 45 days)
	if not frappe.db.exists("Leave Type", SICK_UNPAID):
		unpaid = frappe.new_doc("Leave Type")
		unpaid.leave_type_name = SICK_UNPAID
	else:
		unpaid = frappe.get_doc("Leave Type", SICK_UNPAID)
	unpaid.max_leaves_allowed = 45
	unpaid.applicable_after = PROBATION_DAYS
	unpaid.is_lwp = 1
	unpaid.include_holiday = 1
	unpaid.is_carry_forward = 0
	unpaid.allow_encashment = 0
	unpaid.save(ignore_permissions=True)

	# Ensure LWP exists for unpaid leave generally
	if frappe.db.exists("Leave Type", "Leave Without Pay"):
		lwp = frappe.get_doc("Leave Type", "Leave Without Pay")
		lwp.is_lwp = 1
		lwp.include_holiday = 1
		lwp.save(ignore_permissions=True)


def configure_leave_period():
	existing = frappe.db.get_value(
		"Leave Period",
		{"from_date": "2026-01-01", "to_date": "2026-12-31", "company": COMPANY},
		"name",
	)
	if existing:
		doc = frappe.get_doc("Leave Period", existing)
		doc.is_active = 1
		doc.save(ignore_permissions=True)
		return doc.name

	doc = frappe.new_doc("Leave Period")
	doc.from_date = "2026-01-01"
	doc.to_date = "2026-12-31"
	doc.company = COMPANY
	doc.is_active = 1
	# optional name / naming handled by system
	doc.insert(ignore_permissions=True)
	return doc.name


def configure_leave_policy():
	"""Annual 30 + sick tiers. Monthly earned leave uses annual allocation / 12."""
	existing = frappe.db.get_value("Leave Policy", {"title": POLICY_NAME, "docstatus": 1}, "name")
	if existing:
		return existing

	# Reuse draft named by title if present
	draft = frappe.db.get_value("Leave Policy", {"title": POLICY_NAME, "docstatus": 0}, "name")
	if draft:
		doc = frappe.get_doc("Leave Policy", draft)
		doc.set("leave_policy_details", [])
	else:
		doc = frappe.new_doc("Leave Policy")
		doc.title = POLICY_NAME

	for leave_type, annual_allocation in (
		(ANNUAL_LEAVE, 30),
		(SICK_FULL, 15),
		(SICK_HALF, 30),
		(SICK_UNPAID, 45),
	):
		doc.append(
			"leave_policy_details",
			{"leave_type": leave_type, "annual_allocation": annual_allocation},
		)

	if doc.is_new():
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)

	if cint(doc.docstatus) == 0:
		doc.submit()

	return doc.name


def configure_hr_settings():
	hrs = frappe.get_single("HR Settings")
	hrs.leave_approver_mandatory_in_leave_application = 1
	hrs.prevent_self_leave_approval = 1
	hrs.send_leave_notification = 1
	hrs.show_leaves_of_all_department_members_in_calendar = 1
	hrs.save(ignore_permissions=True)


def _load_balance_rows():
	path = Path(__file__).parent / "leave_balances_2026_07_14.json"
	return json.loads(path.read_text())


# Explicit aliases where spreadsheet spelling differs from Employee name
NAME_ALIASES = {
	"vinod ullal": "vinod kumar",
	"monis khan": "mohammed monis",
	"faiz usmani": "fiaz usmani",
	"haroon rasheed": "haroon abdul rashid",
	"mamoun": "mohammad abdulla al mamun",
	"binod shakya": "binod shaky",
	"yasir iqbal": "yasir iqpal",
	"mahmood soortee": "mahmood yousuf",
	"lal said": "lal syed",
	"ali mohammed abozaid": "ali abu zaid",
	"abdul rahman dimnang": "abdul rahman dimang",
	"shaik mohammad javed": "shaikh mohammad javed",
	"essra mohammad": "essra",
	"madhuparna": "madhuparna sengupta",
	"norah alnahdi": "norah",
	"thiab al nahdi": "thiab",
	"mohammad al hinidi": "hinidi",
	"ajay manue": "ajay manue",
	"omar samy": "omar",
	"khalfan salem": "khalfan",
	"shafiya khanum": "shafiya",
	"butti ahmed": "butti",
	"salama": "salama",
	"faiz ahmed": "faiz ahmed",
	"mohammad sarfraz": "sarfraz",
}


def _match_employee(sheet_name: str, joining_date: str, employees: list[dict]) -> dict | None:
	"""Strict fuzzy match spreadsheet row to Employee."""
	alias = NAME_ALIASES.get(_norm(sheet_name), _norm(sheet_name))
	tokens = _name_tokens(alias)
	strong = {t for t in tokens if len(t) >= 4}
	jd = getdate(joining_date) if joining_date else None
	best = None
	best_score = 0

	for emp in employees:
		emp_tokens = _name_tokens(emp.employee_name)
		if not tokens or not emp_tokens:
			continue

		overlap = tokens & emp_tokens
		strong_overlap = strong & emp_tokens if strong else set()
		partial_hits = 0
		for t in strong or tokens:
			for et in emp_tokens:
				if t != et and len(t) >= 4 and (t in et or et in t):
					partial_hits += 1

		if not strong_overlap and not partial_hits and not overlap:
			continue

		score = len(overlap) * 12 + len(strong_overlap) * 10 + partial_hits * 4
		for t in strong or tokens:
			for et in emp_tokens:
				if t == et:
					score += 6

		delta = None
		if jd and emp.date_of_joining:
			delta = abs((getdate(emp.date_of_joining) - jd).days)
			if delta == 0:
				score += 30
			elif delta <= 10:
				score += 20
			elif delta <= 31:
				score += 10
			elif delta <= 90:
				score += 3
			elif delta > 400:
				score -= 8  # light penalty; sheet DOJ can be off by a year

		# Reject weak collisions when sheet has extra unique surname not on employee
		sheet_strong_missing = bool(strong - emp_tokens) if len(strong) >= 2 else False
		if sheet_strong_missing and len(strong_overlap) < 2 and partial_hits < 1:
			continue
		if len(strong_overlap) + partial_hits == 0 and len(overlap) <= 1:
			if delta is None or delta > 45:
				continue

		if score > best_score:
			best_score = score
			best = emp

	if best_score < 28:
		return None
	return best


# Force exact employee IDs for known sheet ↔ ERP mismatches / missing fuzzy targets
FORCED_EMPLOYEE_MAP = {
	"dip bahadur": "HR-EMP-00060",
	"vinod ullal": "HR-EMP-00008",
	"mamoun": "HR-EMP-00054",
	"venkatesan": "HR-EMP-00025",
	"jeselle": "HR-EMP-00009",
	"harish": "HR-EMP-00018",
	"lakmal": "HR-EMP-00050",
	"madhusudan": "HR-EMP-00029",
	"tu tu": "HR-EMP-00043",
	"gihan": "HR-EMP-00046",
	"jayesh": "HR-EMP-00052",
	"nayab": "HR-EMP-00036",
	"malaka": "HR-EMP-00042",
	"ambala": "HR-EMP-00053",
	"aparna": "HR-EMP-00059",
	"madeleine flore": "HR-EMP-00057",
	"kamal": "HR-EMP-00035",
	"afsana": "HR-EMP-00005",
	"nanda": "HR-EMP-00022",
	"sarim": "HR-EMP-00021",
}


def _cancel_existing_annual_allocations(employee: str):
	names = frappe.get_all(
		"Leave Allocation",
		filters={
			"employee": employee,
			"leave_type": ANNUAL_LEAVE,
			"docstatus": 1,
			"from_date": ("<=", ALLOCATE_TO),
			"to_date": (">=", "2026-01-01"),
		},
		pluck="name",
	)
	for name in names:
		doc = frappe.get_doc("Leave Allocation", name)
		doc.cancel()


def _create_opening_allocation(employee: str, balance: float, from_date, probation: bool):
	"""Create Annual Leave allocation reflecting opening balance as of BALANCE_AS_ON."""
	from hrms.hr.doctype.leave_ledger_entry.leave_ledger_entry import create_leave_ledger_entry

	balance = flt(balance, 2)
	alloc = frappe.new_doc("Leave Allocation")
	alloc.employee = employee
	alloc.leave_type = ANNUAL_LEAVE
	alloc.from_date = from_date
	alloc.to_date = ALLOCATE_TO
	alloc.carry_forward = 0
	alloc.description = (
		f"Opening Annual Leave balance as of {BALANCE_AS_ON}"
		+ (" (probation — usable after 6 months)" if probation else "")
	)

	if balance > 0:
		# Positive remaining balance
		alloc.new_leaves_allocated = balance
		alloc.insert(ignore_permissions=True)
		alloc.submit()
	elif balance == 0:
		# Zero balance still needs a positive allocation row then reduce to zero
		alloc.new_leaves_allocated = 0.01
		alloc.insert(ignore_permissions=True)
		alloc.submit()
		create_leave_ledger_entry(
			alloc,
			dict(leaves=-0.01, from_date=from_date, to_date=ALLOCATE_TO, is_carry_forward=0),
			submit=True,
		)
	else:
		# Negative remaining: allocate |balance|, then reverse 2× so net = -|balance|
		abs_bal = abs(balance)
		alloc.new_leaves_allocated = abs_bal
		alloc.insert(ignore_permissions=True)
		alloc.submit()
		create_leave_ledger_entry(
			alloc,
			dict(leaves=-2 * abs_bal, from_date=from_date, to_date=ALLOCATE_TO, is_carry_forward=0),
			submit=True,
		)

	return alloc.name


def import_opening_balances(replace_existing: bool = True):
	rows = _load_balance_rows()
	employees = frappe.get_all(
		"Employee",
		filters={"status": "Active", "company": COMPANY},
		fields=["name", "employee_name", "date_of_joining"],
	)
	# also include Left? stick to Active only but company filter soft
	if not employees:
		employees = frappe.get_all(
			"Employee",
			filters={"status": "Active"},
			fields=["name", "employee_name", "date_of_joining"],
		)

	# Score all pairs then greedily assign unique employee matches
	candidates = []
	for idx, row in enumerate(rows):
		forced = FORCED_EMPLOYEE_MAP.get(_norm(row["name"]))
		if forced:
			emp = next((e for e in employees if e.name == forced), None)
		else:
			emp = _match_employee(row["name"], row.get("joining_date"), employees)
		if not emp:
			continue
		tokens = _name_tokens(NAME_ALIASES.get(_norm(row["name"]), _norm(row["name"])))
		emp_tokens = _name_tokens(emp.employee_name)
		score = len(tokens & emp_tokens) * 20 + (100 if forced else 0)
		if row.get("joining_date") and emp.date_of_joining:
			delta = abs((getdate(emp.date_of_joining) - getdate(row["joining_date"])).days)
			score += max(0, 40 - min(delta, 40))
		candidates.append((score, idx, row, emp))

	candidates.sort(key=lambda x: x[0], reverse=True)
	matched = []
	used_employees = set()
	used_rows = set()
	for score, idx, row, emp in candidates:
		if emp.name in used_employees or idx in used_rows:
			continue
		used_employees.add(emp.name)
		used_rows.add(idx)
		matched.append((row, emp))

	unmatched = [row for idx, row in enumerate(rows) if idx not in used_rows]

	results = {"allocated": [], "skipped": [], "unmatched": unmatched}

	for row, emp in matched:
		try:
			if replace_existing:
				_cancel_existing_annual_allocations(emp.name)
			from_date = max(getdate(emp.date_of_joining or "2026-01-01"), getdate("2026-01-01"))
			# Probation rows still get calculated balance stored; usable only after applicable_after
			name = _create_opening_allocation(
				emp.name, row["balance"], from_date, cint(row.get("probation"))
			)
			results["allocated"].append(
				{
					"employee": emp.name,
					"employee_name": emp.employee_name,
					"sheet_name": row["name"],
					"balance": row["balance"],
					"allocation": name,
					"probation": bool(row.get("probation")),
				}
			)
		except Exception as e:
			frappe.log_error(frappe.get_traceback(), "Leave Balance Import")
			results["skipped"].append(
				{"employee": emp.name, "sheet_name": row["name"], "error": str(e)}
			)

	frappe.db.commit()
	return results


def get_annual_accrual_rate(date_of_joining, as_on=None) -> float:
	"""Return monthly accrual days based on completed service."""
	as_on = getdate(as_on or today())
	doj = getdate(date_of_joining)
	if not doj or doj > as_on:
		return 0.0
	months = (as_on.year - doj.year) * 12 + (as_on.month - doj.month)
	if as_on.day < doj.day:
		months -= 1
	if months < 0:
		return 0.0
	if months < 6:
		# Accrues during probation at 2/month but not usable yet
		return 2.0
	if months < 12:
		return 2.0
	return 2.5


def allocate_sick_leave_entitlements():
	"""Allocate annual sick leave tiers for employees who completed probation."""
	as_on = getdate(BALANCE_AS_ON)
	created = []
	for emp in frappe.get_all(
		"Employee",
		filters={"status": "Active"},
		fields=["name", "date_of_joining"],
	):
		if not emp.date_of_joining:
			continue
		months = (as_on.year - emp.date_of_joining.year) * 12 + (
			as_on.month - emp.date_of_joining.month
		)
		if as_on.day < emp.date_of_joining.day:
			months -= 1
		if months < 6:
			continue  # still on probation — no sick leave yet

		from_date = max(getdate(emp.date_of_joining), getdate("2026-01-01"))
		for leave_type, days in (
			(SICK_FULL, 15),
			(SICK_HALF, 30),
			# Unpaid sick leave is LWP — cannot be pre-allocated in HRMS; applied as needed
		):
			exists = frappe.db.exists(
				"Leave Allocation",
				{
					"employee": emp.name,
					"leave_type": leave_type,
					"docstatus": 1,
					"from_date": ("<=", ALLOCATE_TO),
					"to_date": (">=", from_date),
				},
			)
			if exists:
				continue
			alloc = frappe.new_doc("Leave Allocation")
			alloc.employee = emp.name
			alloc.leave_type = leave_type
			alloc.from_date = from_date
			alloc.to_date = ALLOCATE_TO
			alloc.new_leaves_allocated = days
			alloc.description = f"2026 sick leave entitlement per NUTC HR policy ({leave_type})"
			alloc.insert(ignore_permissions=True)
			alloc.submit()
			created.append(alloc.name)
	return created


@frappe.whitelist()
def setup_nutc_leave_policy(import_balances: int = 1, allocate_sick: int = 1):
	"""Configure leave policy artifacts and optionally import opening balances."""
	frappe.only_for(("System Manager", "HR Manager"))
	configure_leave_types()
	period = configure_leave_period()
	policy = configure_leave_policy()
	configure_hr_settings()

	result = {
		"leave_period": period,
		"leave_policy": policy,
		"leave_types": [ANNUAL_LEAVE, SICK_FULL, SICK_HALF, SICK_UNPAID],
	}
	if cint(import_balances):
		result["balances"] = import_opening_balances(replace_existing=True)
		result["balances_summary"] = {
			"allocated": len(result["balances"]["allocated"]),
			"skipped": len(result["balances"]["skipped"]),
			"unmatched": len(result["balances"]["unmatched"]),
		}
	if cint(allocate_sick):
		result["sick_allocations"] = allocate_sick_leave_entitlements()
		result["sick_allocations_count"] = len(result["sick_allocations"])
	frappe.db.commit()
	return result
