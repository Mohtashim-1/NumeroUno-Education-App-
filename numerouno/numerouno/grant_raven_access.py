"""Grant Pulse (Raven) chat access to every enabled system user."""

import frappe

WORKSPACE_FALLBACKS = ("Pulse", "Raven")


def _get_workspace():
	for name in WORKSPACE_FALLBACKS:
		if frappe.db.exists("Raven Workspace", name):
			return name
	return frappe.db.get_value("Raven Workspace", {"type": "Public"}, "name")


def grant_all(add_to_workspace=True):
	users = frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User"},
		pluck="name",
	)
	users = [u for u in users if u not in ("Guest",)]

	workspace = _get_workspace() if add_to_workspace else None
	general = frappe.db.exists("Raven Channel", "general")

	roles_added = raven_users = members = channel_members = 0

	for idx, username in enumerate(users, start=1):
		try:
			user = frappe.get_doc("User", username)
			if "Raven User" not in [d.role for d in user.get("roles")]:
				user.add_roles("Raven User")
				roles_added += 1

			raven_user = frappe.db.get_value("Raven User", {"user": username}, "name")
			if not raven_user:
				doc = frappe.new_doc("Raven User")
				doc.user = username
				doc.full_name = user.full_name or user.first_name
				doc.first_name = user.first_name
				doc.enabled = 1
				doc.insert(ignore_permissions=True)
				raven_user = doc.name
				raven_users += 1
			else:
				frappe.db.set_value("Raven User", raven_user, "enabled", 1, update_modified=False)

			if workspace and not frappe.db.exists(
				"Raven Workspace Member", {"workspace": workspace, "user": raven_user}
			):
				frappe.get_doc(
					{
						"doctype": "Raven Workspace Member",
						"workspace": workspace,
						"user": raven_user,
					}
				).insert(ignore_permissions=True)
				members += 1

			if general and not frappe.db.exists(
				"Raven Channel Member", {"channel_id": "general", "user_id": raven_user}
			):
				frappe.get_doc(
					{
						"doctype": "Raven Channel Member",
						"channel_id": "general",
						"user_id": raven_user,
					}
				).insert(ignore_permissions=True)
				channel_members += 1

		except Exception:
			frappe.log_error(title=f"Pulse access grant failed: {username}")

		if idx % 25 == 0:
			frappe.db.commit()

	frappe.db.commit()
	frappe.clear_cache()

	print(
		f"users scanned={len(users)} roles_added={roles_added} raven_users={raven_users} "
		f"workspace_members={members} general_members={channel_members} workspace={workspace}"
	)
