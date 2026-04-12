import json

from numerouno.numerouno.api.numerouno_registration import build_public_form_schema


no_cache = 1


def get_context(context):
	context.no_cache = 1
	context.show_sidebar = False
	context.title = "NumeroUno Registration"
	context.form_schema = json.dumps(build_public_form_schema())
