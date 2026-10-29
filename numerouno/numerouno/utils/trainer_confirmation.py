"""Trainer must confirm each Assessment Result before certificate printing."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, now_datetime

CONFIRMED_FIELD = "custom_trainer_confirmed"
CONFIRMED_BY_FIELD = "custom_trainer_confirmed_by"
CONFIRMED_ON_FIELD = "custom_trainer_confirmed_on"

# Portal / client download / digest emails:
# - created before this date → visible without instructor confirmation (legacy)
# - created on/after this date → instructor confirmation required
# Policy start = Monday 26 Oct 2026 (legacy through Sunday 25 Oct 2026).
TRAINER_CONFIRMATION_POLICY_START = "2026-10-26"

# Temporary kill-switch: when False, certificate portal / downloads / digests
# ignore instructor confirmation and show certificates as before.
PORTAL_TRAINER_CONFIRMATION_ENABLED = False

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
	if isinstance(doc, dict):
		return bool(cint(doc.get(CONFIRMED_FIELD)))
	return bool(cint(getattr(doc, CONFIRMED_FIELD, 0)))


def has_trainer_confirmation_field() -> bool:
	return frappe.get_meta("Assessment Result").has_field(CONFIRMED_FIELD)


def is_portal_trainer_confirmation_enabled() -> bool:
	"""Whether portal/download/digest must enforce instructor confirmation."""
	return bool(PORTAL_TRAINER_CONFIRMATION_ENABLED) and has_trainer_confirmation_field()


def get_trainer_confirmation_policy_start():
	"""Datetime cutoff: confirmation required for certificates created on/after this instant."""
	return get_datetime(f"{TRAINER_CONFIRMATION_POLICY_START} 00:00:00")


def requires_trainer_confirmation_for_portal(doc) -> bool:
	"""True when certificate falls under the confirmation-required policy (from 26 Oct 2026)."""
	if not is_portal_trainer_confirmation_enabled():
		return False

	if isinstance(doc, dict):
		creation = doc.get("creation")
	elif isinstance(doc, str):
		creation = frappe.db.get_value("Assessment Result", doc, "creation")
	else:
		creation = getattr(doc, "creation", None)
		if not creation and getattr(doc, "name", None):
			creation = frappe.db.get_value("Assessment Result", doc.name, "creation")

	if not creation:
		# Fail closed for undated docs under the new policy.
		return True

	return get_datetime(creation) >= get_trainer_confirmation_policy_start()


def is_ready_for_client_portal(doc) -> bool:
	"""Portal visibility / client download / digest eligibility.

	Legacy certificates created before 26 Oct 2026 remain visible without
	instructor confirmation. From 26 Oct 2026 onward, confirmation is required.
	"""
	if not is_portal_trainer_confirmation_enabled():
		return True
	if not requires_trainer_confirmation_for_portal(doc):
		return True
	return is_trainer_confirmed(doc)


def portal_confirmation_sql(alias: str | None = None) -> str:
	"""SQL fragment: confirmed OR created before policy start."""
	if not is_portal_trainer_confirmation_enabled():
		return "(1 = 1)"
	prefix = f"`{alias}`." if alias else ""
	return (
		f"(IFNULL({prefix}`{CONFIRMED_FIELD}`, 0) = 1 "
		f"OR {prefix}`creation` < %(trainer_confirm_cutoff)s)"
	)


def apply_portal_confirmation_filter(filters: dict) -> dict:
	"""Mutate get_all filters when simple AND is enough (no OR with other fields).

	Prefer ``is_ready_for_client_portal`` / ``portal_confirmation_sql`` when OR
	search filters are also needed.
	"""
	filters = dict(filters or {})
	if not has_trainer_confirmation_field():
		return filters
	# Cannot express OR in a plain dict filter — callers must use SQL/helper.
	# Keep confirmed-only as safe default only when explicitly requested.
	return filters


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
	# Same temporary kill-switch as portal visibility.
	if not PORTAL_TRAINER_CONFIRMATION_ENABLED:
		return

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
