from datetime import timedelta

import frappe
from frappe.utils import format_datetime, getdate, nowdate


def _week_bounds(current_date):
	week_start = current_date - timedelta(days=current_date.weekday())
	week_end = week_start + timedelta(days=6)
	return week_start, week_end


@frappe.whitelist()
def get_registration_dashboard_data():
	frappe.only_for("System Manager")

	today = getdate(nowdate())
	week_start, week_end = _week_bounds(today)

	status_counts = {
		"pending": frappe.db.count("Registration", {"registration_status": "Pending"}),
		"approved": frappe.db.count("Registration", {"registration_status": "Approved"}),
		"rejected": frappe.db.count("Registration", {"registration_status": "Rejected"}),
	}

	flagged = (
		frappe.db.sql(
			"""
			SELECT COUNT(*) AS count
			FROM `tabRegistration`
			WHERE COALESCE(is_flagged, 0) = 1
				OR registration_status = 'Flagged'
			""",
			as_dict=True,
		)[0].count
		or 0
	)

	recent_submissions = frappe.get_all(
		"Registration",
		fields=[
			"name",
			"product_title",
			"full_name",
			"learner_surname",
			"registration_status",
			"creation",
		],
		order_by="creation desc",
		limit_page_length=10,
	)

	for row in recent_submissions:
		row["creation_label"] = format_datetime(row.get("creation"), "MMM d, yyyy, h:mm a")

	products = frappe.db.sql(
		"""
		SELECT
			COALESCE(product_title, 'Unspecified Product') AS product_title,
			COUNT(*) AS total,
			MAX(creation) AS last_submission
		FROM `tabRegistration`
		GROUP BY COALESCE(product_title, 'Unspecified Product')
		ORDER BY total DESC, last_submission DESC
		LIMIT 5
		""",
		as_dict=True,
	)

	for product in products:
		product["last_submission"] = (
			f"Last submitted {format_datetime(product.last_submission, 'MMM d, yyyy, h:mm a')}"
			if product.get("last_submission")
			else ""
		)

	return {
		"summary": {
			"total_submissions": frappe.db.count("Registration"),
			"pending": status_counts["pending"],
			"approved": status_counts["approved"],
			"rejected": status_counts["rejected"],
			"flagged": flagged,
			"today": frappe.db.count("Registration", {"creation": ["between", [f"{today} 00:00:00", f"{today} 23:59:59"]]}),
			"this_week": frappe.db.count(
				"Registration",
				{"creation": ["between", [f"{week_start} 00:00:00", f"{week_end} 23:59:59"]]},
			),
		},
		"status_rows": [
			{"label": "Pending", "count": status_counts["pending"], "note": "Awaiting admin review"},
			{"label": "Approved", "count": status_counts["approved"], "note": "Accepted registrations"},
			{"label": "Rejected", "count": status_counts["rejected"], "note": "Rejected submissions"},
			{"label": "Flagged", "count": flagged, "note": "Needs special attention"},
		],
		"products": products,
		"recent_submissions": recent_submissions,
	}
