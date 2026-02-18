import json

import frappe
from frappe import _


REASON_KEYWORDS = (
    "Assessment Result Creation Failed",
    "Failed to create Assessment Result",
    "Assessment Result was not created",
    "Error creating Assessment Result",
    "Assessment Plan has no criteria",
    "Assessment Plan not found",
    "Student Group not found",
)


def _ensure_admin_access():
    user = frappe.session.user
    if user == "Administrator":
        return
    if "System Manager" in frappe.get_roles(user):
        return
    frappe.throw(_("Only System Manager can access this page action."), frappe.PermissionError)


def _extract_reason(comment_text):
    text = (comment_text or "").strip()
    if not text:
        return ""

    if "Assessment Result Creation Failed:" in text:
        parts = text.split("Assessment Result Creation Failed:", 1)
        if len(parts) > 1:
            return parts[1].strip().split("\n\n")[0].strip()

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(("⚠️", "❌", "Error:", "Failed")):
            return line

    return text[:240]


@frappe.whitelist()
def get_failed_quiz_activities(limit=300):
    _ensure_admin_access()

    limit = min(max(int(limit or 300), 1), 1000)

    activities = frappe.get_all(
        "Quiz Activity",
        filters={
            "docstatus": ["<", 2],
            "student": ["is", "set"],
            "quiz": ["is", "set"],
        },
        fields=[
            "name",
            "student",
            "custom_student_group",
            "quiz",
            "score",
            "status",
            "activity_date",
            "custom_assesment_plan",
            "custom_assesment_result",
            "creation",
            "modified",
        ],
        order_by="modified desc",
        limit=limit,
    )

    if not activities:
        return {"records": []}

    unresolved = [row for row in activities if not row.custom_assesment_result]
    if not unresolved:
        return {"records": []}

    names = [row.name for row in unresolved]
    comments = frappe.get_all(
        "Comment",
        filters={
            "reference_doctype": "Quiz Activity",
            "reference_name": ["in", names],
        },
        fields=["reference_name", "content", "creation"],
        order_by="creation desc",
        limit=5000,
    )

    reason_map = {}
    for c in comments:
        ref = c.reference_name
        if ref in reason_map:
            continue
        content = (c.content or "").strip()
        if any(k in content for k in REASON_KEYWORDS) or content.startswith(("⚠️", "❌")):
            reason_map[ref] = _extract_reason(content)

    records = []
    for row in unresolved:
        records.append(
            {
                "quiz_activity": row.name,
                "student": row.student,
                "student_group": row.custom_student_group,
                "quiz": row.quiz,
                "score": row.score,
                "status": row.status,
                "activity_date": row.activity_date,
                "assessment_plan": row.custom_assesment_plan,
                "reason": reason_map.get(row.name) or "No explicit error reason found. Retry creation.",
            }
        )

    return {"records": records}


def _normalize_names(quiz_activity_names):
    if not quiz_activity_names:
        return []

    if isinstance(quiz_activity_names, str):
        try:
            parsed = json.loads(quiz_activity_names)
            if isinstance(parsed, list):
                return [x for x in parsed if x]
        except Exception:
            return [quiz_activity_names]

    if isinstance(quiz_activity_names, (list, tuple)):
        return [x for x in quiz_activity_names if x]

    return []


@frappe.whitelist()
def create_assessment_results_bulk(quiz_activity_names):
    _ensure_admin_access()

    names = _normalize_names(quiz_activity_names)
    if not names:
        frappe.throw(_("Please select at least one Quiz Activity."))

    from numerouno.numerouno.api.quiz_api import create_assessment_result_from_quiz_activity

    created = []
    existing = []
    failed = []

    for name in names:
        try:
            result = create_assessment_result_from_quiz_activity(name) or {}
            status = result.get("status")
            result_id = result.get("assessment_result_id") or result.get("assessment_result")
            message = result.get("message") or ""

            if status == "success" and result_id:
                created.append({"quiz_activity": name, "assessment_result": result_id})
            elif status == "info":
                existing.append(
                    {
                        "quiz_activity": name,
                        "assessment_result": result_id,
                        "reason": message or "Assessment Result already exists",
                    }
                )
            else:
                failed.append({"quiz_activity": name, "reason": message or "Unknown error"})
        except Exception as exc:
            failed.append({"quiz_activity": name, "reason": str(exc)})

    return {
        "created_count": len(created),
        "existing_count": len(existing),
        "failed_count": len(failed),
        "created": created,
        "existing": existing,
        "failed": failed,
    }
