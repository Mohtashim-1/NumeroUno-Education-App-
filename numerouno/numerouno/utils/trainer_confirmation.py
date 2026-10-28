"""Trainer must confirm each Assessment Result before certificate printing."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime

CONFIRMED_FIELD = "custom_trainer_confirmed"
CONFIRMED_BY_FIELD = "custom_trainer_confirmed_by"
CONFIRMED_ON_FIELD = "custom_trainer_confirmed_on"

# Formats that are certificates (not theory reports / attendance / ID cards).
_CERTIFICATE_ALIASES = {
	"assesment result 1",
	"assesment result1",
	"assessment result",
	"assessment certificate",
	"assessment certificate old",
	"certificate of completion without image",
	"demo certificate",
	"sti / habc",
	"adsd",
	"nutc opito - certificate of completion",
	"nutc standard - certificate of attendance",
	"nutc standard - certificate of completion",
}

_EXCLUDE_SUBSTRINGS = (
	"theory",
	"attendance sheet",
	"atm card",
	"pocket card",
	"driving",
	"t-bosiet",
	"t-foet",
	"student card",
)


def is_certificate_print_format(print_format_name: str | None) -> bool:
	name = (print_format_name or "").strip().lower()
	if not name or name == "standard":
		return False
	if any(token in name for token in _EXCLUDE_SUBSTRINGS):
		return False
	if "certificate" in name:
		return True
	return name in _CERTIFICATE_ALIASES


def resolve_print_format_name(print_settings=None) -> str:
	for key in ("format", "print_format"):
		value = frappe.form_dict.get(key)
		if value:
			return str(value).strip()
	if isinstance(print_settings, dict):
		for key in ("format", "print_format"):
			value = print_settings.get(key)
			if value:
				return str(value).strip()
	return ""


def is_trainer_confirmed(doc) -> bool:
	if isinstance(doc, str):
		return bool(frappe.db.get_value("Assessment Result", doc, CONFIRMED_FIELD))
	return bool(getattr(doc, CONFIRMED_FIELD, 0))


def can_bypass_trainer_confirmation(user=None) -> bool:
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	roles = set(frappe.get_roles(user))
	return bool({"System Manager", "Certification"}.intersection(roles))


def assert_trainer_confirmed_for_certificate(doc, method=None, print_settings=None):
	"""Doc event: before_print on Assessment Result.

	Frappe hooks call ``(doc, method, *args)``, so ``method`` is required.
	"""
	print_format = resolve_print_format_name(print_settings)
	if not is_certificate_print_format(print_format):
		return

	if is_trainer_confirmed(doc):
		return

	if can_bypass_trainer_confirmation():
		return

	student = getattr(doc, "student_name", None) or getattr(doc, "student", None) or doc.name
	frappe.throw(
		_(
			"Trainer has not confirmed {0} for certificate printing. "
			"Open Instructor Portal → Certificate Confirm and confirm the student first."
		).format(student),
		title=_("Trainer Confirmation Required"),
	)


def set_trainer_confirmation(assessment_result: str, confirmed: int = 1) -> dict:
	assessment_result = (assessment_result or "").strip()
	if not assessment_result:
		frappe.throw(_("Assessment Result is required"))

	if not frappe.db.exists("Assessment Result", assessment_result):
		frappe.throw(_("Assessment Result {0} not found").format(assessment_result))

	confirmed = 1 if int(confirmed or 0) else 0
	values = {
		CONFIRMED_FIELD: confirmed,
		CONFIRMED_BY_FIELD: frappe.session.user if confirmed else None,
		CONFIRMED_ON_FIELD: now_datetime() if confirmed else None,
	}
	frappe.db.set_value("Assessment Result", assessment_result, values, update_modified=True)
	return {
		"assessment_result": assessment_result,
		"confirmed": confirmed,
		"confirmed_by": values[CONFIRMED_BY_FIELD],
		"confirmed_on": values[CONFIRMED_ON_FIELD],
	}
