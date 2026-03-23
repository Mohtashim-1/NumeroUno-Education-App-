from collections import defaultdict

import frappe
from frappe.utils import flt, format_datetime, getdate, nowdate


def _normalize_filters(filters=None):
	filters = frappe.parse_json(filters) if filters else {}
	default_to = getdate(nowdate())
	default_from = default_to.replace(day=1)

	from_date = getdate(filters.get("from_date") or default_from)
	to_date = getdate(filters.get("to_date") or default_to)
	if from_date > to_date:
		from_date, to_date = to_date, from_date

	return {
		"from_date": from_date,
		"to_date": to_date,
		"department": filters.get("department"),
		"employee": filters.get("employee"),
		"status": filters.get("status"),
	}


def _build_filters(filters):
	out = [["date", "between", [filters["from_date"], filters["to_date"]]]]
	if filters.get("department"):
		out.append(["department", "=", filters["department"]])
	if filters.get("employee"):
		out.append(["employee", "=", filters["employee"]])
	if filters.get("status"):
		out.append(["workflow_state", "=", filters["status"]])
	return out


@frappe.whitelist()
def get_overtime_dashboard_data(filters=None):
	filters = _normalize_filters(filters)
	rows = frappe.get_list(
		"Overtime Request",
		filters=_build_filters(filters),
		fields=[
			"name",
			"employee",
			"employee_name",
			"department",
			"date",
			"time_from",
			"time_to",
			"overtime_hours",
			"status",
			"workflow_state",
			"reason_for_work",
			"creation",
		],
		order_by="date desc, creation desc",
		limit_page_length=5000,
	)

	status_counts = defaultdict(int)
	department_totals = defaultdict(lambda: {"label": "", "requests": 0, "hours": 0.0})
	employee_history = defaultdict(
		lambda: {
			"label": "",
			"department": "",
			"total_requests": 0,
			"total_hours": 0.0,
			"approved_requests": 0,
			"approved_hours": 0.0,
			"rejected_requests": 0,
			"rejected_hours": 0.0,
			"pending_requests": 0,
			"pending_hours": 0.0,
		}
	)

	total_hours = 0.0
	approved_hours = 0.0
	rejected_hours = 0.0
	pending_hours = 0.0
	sunday_hours = 0.0
	sunday_requests = 0

	for row in rows:
		status = row.get("workflow_state") or row.get("status") or "Draft"
		row["effective_status"] = status
		hours = flt(row.get("overtime_hours"))
		total_hours += hours
		status_counts[status] += 1

		if getdate(row.get("date")).weekday() == 6:
			sunday_requests += 1
			sunday_hours += hours

		if status == "Approved":
			approved_hours += hours
		elif status == "Rejected":
			rejected_hours += hours
		else:
			pending_hours += hours

		dept_label = row.get("department") or "Unassigned Department"
		department_totals[dept_label]["label"] = dept_label
		department_totals[dept_label]["requests"] += 1
		department_totals[dept_label]["hours"] += hours

		employee_label = row.get("employee_name") or row.get("employee") or "Unknown Employee"
		employee_entry = employee_history[employee_label]
		employee_entry["label"] = employee_label
		employee_entry["department"] = dept_label
		employee_entry["total_requests"] += 1
		employee_entry["total_hours"] += hours

		if status == "Approved":
			employee_entry["approved_requests"] += 1
			employee_entry["approved_hours"] += hours
		elif status == "Rejected":
			employee_entry["rejected_requests"] += 1
			employee_entry["rejected_hours"] += hours
		else:
			employee_entry["pending_requests"] += 1
			employee_entry["pending_hours"] += hours

		row["creation_label"] = format_datetime(row.get("creation"), "MMM d, yyyy, h:mm a")

	for item in department_totals.values():
		item["hours"] = flt(item["hours"], 2)

	for item in employee_history.values():
		item["total_hours"] = flt(item["total_hours"], 2)
		item["approved_hours"] = flt(item["approved_hours"], 2)
		item["rejected_hours"] = flt(item["rejected_hours"], 2)
		item["pending_hours"] = flt(item["pending_hours"], 2)

	status_rows = [
		{"label": "Draft", "count": status_counts["Draft"], "note": "Not submitted yet"},
		{"label": "Pending Direct Manager", "count": status_counts["Pending Direct Manager"], "note": "Waiting direct manager approval"},
		{"label": "Pending Next Manager", "count": status_counts["Pending Next Manager"], "note": "Waiting next manager approval"},
		{"label": "Pending HR", "count": status_counts["Pending HR"], "note": "Waiting HR approval"},
		{"label": "Approved", "count": status_counts["Approved"], "note": "Approved requests"},
		{"label": "Rejected", "count": status_counts["Rejected"], "note": "Rejected requests"},
	]

	return {
		"filters": {
			"from_date": filters["from_date"].isoformat(),
			"to_date": filters["to_date"].isoformat(),
		},
		"summary": {
			"total_requests": len(rows),
			"total_hours": flt(total_hours, 2),
			"approved_hours": flt(approved_hours, 2),
			"rejected_hours": flt(rejected_hours, 2),
			"pending_hours": flt(pending_hours, 2),
			"sunday_requests": sunday_requests,
			"sunday_hours": flt(sunday_hours, 2),
			"average_hours": flt(total_hours / len(rows), 2) if rows else 0,
		},
		"status_rows": status_rows,
		"department_rows": sorted(
			department_totals.values(), key=lambda row: (row["hours"], row["requests"]), reverse=True
		)[:10],
		"employee_rows": sorted(
			employee_history.values(),
			key=lambda row: (row["approved_hours"], row["total_hours"], row["total_requests"]),
			reverse=True,
		)[:20],
		"recent_requests": rows[:20],
	}
