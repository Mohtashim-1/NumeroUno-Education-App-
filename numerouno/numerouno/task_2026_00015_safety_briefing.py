"""One-off helpers for TASK-2026-00015 Safety Briefing / FOET checklist fixes."""

from __future__ import annotations

import frappe
from frappe.utils import cint

from numerouno.numerouno.page.course_assessor_checklist_form.course_assessor_checklist_form import (
	_normalize_checklist_layout,
)


def migrate_foet_ebs_checklists(limit: int = 500):
	"""Re-align existing FOET EBS / AGT / Gas Monitor checklists to Excel templates."""
	from numerouno.numerouno.doctype.assessor_checklist.assessor_checklist import (
		get_template_for_checklist_type,
	)

	updated = []
	checked = 0
	for checklist_type in ("FOET EBS", "AGT", "Gas Monitor"):
		names = frappe.get_all(
			"Assessor Checklist",
			filters={"checklist_type": checklist_type, "docstatus": ["<", 2]},
			pluck="name",
			limit_page_length=limit,
			order_by="modified desc",
		)
		checked += len(names)
		template = get_template_for_checklist_type(checklist_type)
		expected_assessors = template.get("assessors") or []
		for name in names:
			doc = frappe.get_doc("Assessor Checklist", name)
			changed = False
			if cint(doc.docstatus) == 0:
				if _normalize_checklist_layout(doc):
					doc.save(ignore_permissions=True)
					changed = True
			elif expected_assessors and not (doc.assessors or []):
				# Submitted docs: only backfill missing assessor/signature rows.
				for row in expected_assessors:
					child = frappe.get_doc(
						{
							"doctype": "Assessor Checklist Assessor",
							"parent": name,
							"parenttype": "Assessor Checklist",
							"parentfield": "assessors",
							"sr_no": row.get("sr_no"),
							"module": row.get("module"),
							"description": row.get("description"),
						}
					)
					child.db_insert()
				changed = True
			if changed:
				updated.append(name)
	frappe.db.commit()
	return {"checked": checked, "updated": updated}


def complete_task():
	"""Mark TASK-2026-00015 completed with a short completion note."""
	task_name = "TASK-2026-00015"
	if not frappe.db.exists("Task", task_name):
		return {"task": None}
	task = frappe.get_doc("Task", task_name)
	note = (
		"Completed:\n"
		"1) Safety Briefing attendee header renamed to Learners Signature (form + print).\n"
		"2) FOET EBS Assessor Checklist (NUTC-P14-F01.03) aligned to Excel template "
		"(added OIS-74 outcomes 1.2/2.1/2.2, assessor descriptions, unit text).\n"
		"3) Removed Modified timestamp column from Course Assessor Checklist portal list "
		"to avoid audit/NC concerns on delayed data entry."
	)
	if task.status != "Completed":
		task.status = "Completed"
		task.progress = 100
	# Keep description history and append completion note as comment
	frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Comment",
			"reference_doctype": "Task",
			"reference_name": task_name,
			"content": note.replace("\n", "<br>"),
		}
	).insert(ignore_permissions=True)
	task.save(ignore_permissions=True)
	frappe.db.commit()
	return {"task": task_name, "status": task.status}
