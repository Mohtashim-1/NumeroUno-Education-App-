# Copyright (c) 2026, Numerouno and contributors
# SPDX-License-Identifier: MIT

"""Ensure Email Template Jinja receives both flat keys and a `doc` object (frappe._dict)."""

import json

import frappe
from frappe import _dict
from frappe.email.doctype.email_template.email_template import EmailTemplate as FrappeEmailTemplate


class NumerounoEmailTemplate(FrappeEmailTemplate):
	@staticmethod
	def _template_context(doc):
		if isinstance(doc, str):
			doc = json.loads(doc)
		data = doc.as_dict() if not isinstance(doc, dict) else dict(doc)
		ctx = dict(data)
		ctx["doc"] = _dict(data)
		return ctx

	def get_formatted_subject(self, doc):
		return frappe.render_template(self.subject, self._template_context(doc))

	def get_formatted_response(self, doc):
		return frappe.render_template(self.response_, self._template_context(doc))
