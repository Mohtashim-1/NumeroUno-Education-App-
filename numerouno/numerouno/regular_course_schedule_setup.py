"""Course fields that control auto daily sessions on the Training Schedule calendar."""

from __future__ import annotations

import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import cint

FLAG_AUTO = "custom_auto_create_daily_session"
FIELD_SLOTS = "custom_daily_session_slots"
FIELD_WEEKDAYS = "custom_daily_session_weekdays"

AFTER_FIELD = "custom_course_schedule_details"
FIELD_ORDER_AFTER = ("custom_course_schedule_details", "custom_learning_outcome", "description")

# Seed from the coordinator sheet (hint, slots_label, weekdays_or_empty)
# slots_label: Morning | Afternoon | Morning & Afternoon
SEED_ROWS = (
	("	", "Morning & Afternoon", ""),
	("H2S TRAINING LEVEL 2 (SCBA)", "Morning & Afternoon", ""),
	("ONSHORE HSE INDUCTION + ADNOC LIFE-SAVING RULES (AS PER ADNOC HSE REQUIREMENTS)", "Morning & Afternoon", ""),
	("CONFINED SPACE AWARENESS (AS PER ADNOC HSE REQUIREMENTS)", "Morning", ""),
	("CONFINED SPACE ENTRY TRAINING", "Morning & Afternoon", ""),
	("HOLE WATCHER", "Morning & Afternoon", ""),
	("Highfield International Emergency First Aid, AED & CPR All Ages", "Morning & Afternoon", ""),
	("HIGHFIELD LEVEL 2 INTERNATIONAL AWARD IN FIRE SAFETY", "Afternoon", ""),
	("FIRE SAFETY FOR FIRE WARDEN", "Morning", ""),
	("FIRE WARDEN TRAINING", "Afternoon", ""),
	("FIRE WATCHER TRAINING", "Afternoon", ""),
	("RIGGING, SLINGING & BANKSMAN", "Morning & Afternoon", ""),
	("BANKSMAN/SIGNALER - ONSHORE", "Morning & Afternoon", ""),
	("Banksman/Signaler", "Morning", ""),
	("WORKING AT HEIGHT TRAINING", "Afternoon", ""),
	("Tropical Further Offshore Emergency Training", "Morning", ""),
	("Further Offshore Emergency Training (FOET) with Emergency Breathing System", "Morning", ""),
	("Helicopter Underwater Escape Training (HUET) with Emergency Breathing System", "Morning", ""),
	("Helicopter Underwater Escape Training (HUET) OPITO", "Morning", ""),
	("Travel Safety by Boat", "Morning & Afternoon", ""),
	("BASIC H2S TRAINING (OPITO APPROVED) Course code – 9014", "Morning", ""),
	("OFFSHORE HSE INDUCTION + ADNOC LIFE-SAVING RULES", "Morning & Afternoon", ""),
	("Tropical Basic Offshore Safety Induction", "Morning", "Mon,Wed,Thu,Sat"),
	("Basic Offshore Safety Induction and Emergency Training (BOSIET) with Emergency Breathing System", "Morning", "Mon,Wed,Thu,Sat"),
)


def get_custom_fields():
	return {
		"Course": [
			{
				"fieldname": FLAG_AUTO,
				"label": "Auto Create Daily Session",
				"fieldtype": "Check",
				"insert_after": AFTER_FIELD,
				"default": "0",
				"description": "When checked, the daily job opens this course on the Training Schedule calendar for upcoming days.",
				"translatable": 0,
			},
			{
				"fieldname": FIELD_SLOTS,
				"label": "Daily Session Slots",
				"fieldtype": "Select",
				"options": "\nMorning\nAfternoon\nMorning & Afternoon\nEvening",
				"default": "Morning & Afternoon",
				"insert_after": FLAG_AUTO,
				"depends_on": f"eval:doc.{FLAG_AUTO}",
				"description": "Morning = 08:00–12:00, Afternoon = 13:00–17:00, Evening = 18:00–22:00.",
				"translatable": 0,
			},
			{
				"fieldname": FIELD_WEEKDAYS,
				"label": "Daily Session Weekdays",
				"fieldtype": "Data",
				"insert_after": FIELD_SLOTS,
				"depends_on": f"eval:doc.{FLAG_AUTO}",
				"description": "Optional. Empty = Mon–Sat (Sunday off). Example: Mon,Wed,Thu,Sat",
				"translatable": 0,
			},
		]
	}


def setup():
	create_custom_fields(get_custom_fields(), update=True)
	_insert_in_field_order("Course", [FLAG_AUTO, FIELD_SLOTS, FIELD_WEEKDAYS])
	frappe.clear_cache(doctype="Course")
	frappe.db.commit()
	return {"ok": 1}


def after_migrate():
	setup()
	seed_from_sheet(only_unset=True)


def seed_from_sheet(only_unset: bool = True) -> dict:
	"""Mark matching Course rows from the fixed coordinator sheet."""
	from numerouno.numerouno.regular_course_schedule import _resolve_course

	if not frappe.db.has_column("Course", FLAG_AUTO):
		setup()

	updated = []
	missing = []
	for hint, slots, weekdays in SEED_ROWS:
		course = _resolve_course(hint)
		if not course:
			missing.append(hint)
			continue
		if only_unset and cint(frappe.db.get_value("Course", course, FLAG_AUTO)):
			continue
		frappe.db.set_value(
			"Course",
			course,
			{
				FLAG_AUTO: 1,
				FIELD_SLOTS: slots or "Morning & Afternoon",
				FIELD_WEEKDAYS: weekdays or "",
			},
			update_modified=False,
		)
		updated.append(course)

	frappe.db.commit()
	return {"updated": updated, "missing": missing, "count": len(updated)}


@frappe.whitelist()
def seed_auto_daily_flags():
	if frappe.session.user != "Administrator" and "System Manager" not in frappe.get_roles():
		frappe.throw("Not allowed", frappe.PermissionError)
	return seed_from_sheet(only_unset=False)


def _insert_in_field_order(doctype, fieldnames):
	name = frappe.db.get_value(
		"Property Setter",
		{"doc_type": doctype, "property": "field_order", "doctype_or_field": "DocType"},
		"name",
	)
	if not name:
		return

	doc = frappe.get_doc("Property Setter", name)
	try:
		order = json.loads(doc.value or "[]")
	except Exception:
		return

	after = next((field for field in FIELD_ORDER_AFTER if field in order), None)
	insert_at = order.index(after) + 1 if after else len(order)
	for fieldname in fieldnames:
		if fieldname in order:
			continue
		order.insert(insert_at, fieldname)
		insert_at += 1

	doc.value = json.dumps(order)
	doc.save(ignore_permissions=True)
