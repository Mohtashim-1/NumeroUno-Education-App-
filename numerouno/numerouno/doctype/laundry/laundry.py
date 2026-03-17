import frappe
from frappe.model.document import Document
from frappe.utils import nowtime


class Laundry(Document):
	def validate(self):
		self.employee_name = " ".join((self.employee_name or "").split())
		self.type = (self.type or "").strip().upper()

		if self.type not in {"IN", "OUT"}:
			frappe.throw("Type must be either IN or OUT.")

		for fieldname in ("coverall", "towel", "gloves"):
			value = cint(self.get(fieldname))
			if value < 0:
				frappe.throw(f"{frappe.bold(fieldname.replace('_', ' ').title())} cannot be negative.")
			self.set(fieldname, value)

		if not any(cint(self.get(fieldname)) for fieldname in ("coverall", "towel", "gloves")):
			frappe.throw("Please enter at least one item quantity.")

		if not self.transaction_time:
			self.transaction_time = nowtime()


def cint(value):
	try:
		return int(value or 0)
	except (TypeError, ValueError):
		return 0
