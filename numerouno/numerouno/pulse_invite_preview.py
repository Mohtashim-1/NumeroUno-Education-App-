"""Dry-run helper to inspect the Pulse channel invitation email without sending it."""

import re

import frappe


def preview(channel_id="Raven-general", user_id=None):
	from raven import pulse_notifications as pn

	captured = {}

	def fake_sendmail(**kwargs):
		captured.update(kwargs)

	if not user_id:
		user_id = frappe.db.get_value(
			"Raven User", {"user": ["!=", "Administrator"], "enabled": 1}, "name"
		)

	channel = frappe.db.get_value(
		"Raven Channel", channel_id, ["channel_name", "type", "workspace"], as_dict=True
	)

	original = frappe.sendmail
	frappe.sendmail = fake_sendmail
	try:
		pn.send_channel_add_confirmation(
			user_id=user_id,
			channel_id=channel_id,
			channel_name=channel.channel_name,
			channel_type=channel.type,
			workspace=channel.workspace,
		)
	finally:
		frappe.sendmail = original

	message = captured.get("message") or ""
	print("would-be recipient:", captured.get("recipients"))
	print("subject:", captured.get("subject"))
	print("links:", sorted(set(re.findall(r"https?://[^\"\s<]+", message))))
	print("still uses /raven/:", "/raven/" in message)
	print("brand present:", "Pulse" in message)
	print("queued (delayed):", captured.get("delayed"))
	return captured
