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


def has_trainer_confirmation_field() -> bool:
	return frappe.get_meta("Assessment Result").has_field(CONFIRMED_FIELD)


def is_ready_for_client_portal(doc) -> bool:
	"""Certificates appear on client portal / digests only after trainer confirmation."""
	if not has_trainer_confirmation_field():
		return True
	return is_trainer_confirmed(doc)


def assert_ready_for_client_portal(doc):
	if is_ready_for_client_portal(doc):
		return
	student = getattr(doc, "student_name", None) or getattr(doc, "student", None) or getattr(doc, "name", doc)
	frappe.throw(
		_(
			"Certificate for {0} is not available yet. "
			"It will appear on the portal after the instructor confirms it."
		).format(student),
		title=_("Awaiting Instructor Confirmation"),
	)


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
	now = now_datetime()
	values = {
		CONFIRMED_FIELD: confirmed,
		CONFIRMED_BY_FIELD: frappe.session.user if confirmed else None,
		CONFIRMED_ON_FIELD: now if confirmed else None,
	}

	# Portal + digest emails: only after instructor confirmation.
	meta = frappe.get_meta("Assessment Result")
	if meta.has_field("custom_show_on_portal"):
		values["custom_show_on_portal"] = 1 if confirmed else 0
	if meta.has_field("custom_portal_enabled_on"):
		values["custom_portal_enabled_on"] = now if confirmed else None
	if meta.has_field("custom_portal_digest_sent"):
		# Reset so the next digest can notify the client after confirmation.
		values["custom_portal_digest_sent"] = 0

	frappe.db.set_value("Assessment Result", assessment_result, values, update_modified=True)
	return {
		"assessment_result": assessment_result,
		"confirmed": confirmed,
		"confirmed_by": values[CONFIRMED_BY_FIELD],
		"confirmed_on": values[CONFIRMED_ON_FIELD],
		"show_on_portal": values.get("custom_show_on_portal"),
	}
