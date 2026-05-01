import json

import frappe

from numerouno.numerouno.api.public_portal import get_public_portal_form_list

no_cache = 1


def get_context(context):
	context.no_cache = 1
	context.show_sidebar = False
	context.title = "Public Forms"
	context.initial_forms = json.dumps(get_public_portal_form_list() or [])
	return context
